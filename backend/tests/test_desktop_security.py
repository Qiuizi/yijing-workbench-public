from fastapi.testclient import TestClient

from backend.main import create_app


def test_desktop_api_requires_token_and_trusted_origin(tmp_path):
    app = create_app(db_path=tmp_path / "desktop.sqlite3", desktop_mode=True, desktop_api_token="t" * 48)
    with TestClient(app) as client:
        assert client.get("/api/desktop/health").status_code == 401
        headers = {"Authorization": f"Bearer {'t' * 48}", "Origin": "https://example.invalid"}
        assert client.get("/api/history", headers=headers).status_code == 403
        headers["Origin"] = "http://tauri.localhost"
        response = client.get("/api/desktop/health", headers=headers)
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "mode": "desktop"}


def test_desktop_cors_preflight_is_limited_to_app_origins(tmp_path):
    app = create_app(db_path=tmp_path / "desktop.sqlite3", desktop_mode=True, desktop_api_token="t" * 48)
    with TestClient(app) as client:
        allowed = client.options(
            "/api/history",
            headers={
                "Origin": "http://tauri.localhost",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        denied = client.options(
            "/api/history",
            headers={
                "Origin": "https://example.invalid",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization",
            },
        )
        assert allowed.headers.get("access-control-allow-origin") == "http://tauri.localhost"
        assert "access-control-allow-origin" not in denied.headers


def test_desktop_development_origin_is_only_allowed_in_dev_mode(tmp_path):
    production = create_app(db_path=tmp_path / "prod.sqlite3", desktop_mode=True, desktop_api_token="p" * 48)
    dev = create_app(
        db_path=tmp_path / "dev.sqlite3", desktop_mode=True, desktop_api_token="d" * 48, desktop_dev_mode=True
    )
    headers = {
        "Origin": "http://127.0.0.1:5174",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    }
    with TestClient(production) as client:
        response = client.options("/api/history", headers=headers)
        assert "access-control-allow-origin" not in response.headers
    with TestClient(dev) as client:
        response = client.options("/api/history", headers=headers)
        assert response.headers.get("access-control-allow-origin") == "http://127.0.0.1:5174"


def test_browser_web_mode_keeps_existing_no_token_api_contract(tmp_path):
    app = create_app(db_path=tmp_path / "web.sqlite3", desktop_mode=False)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/history", headers={"Origin": "http://127.0.0.1:5173"}).status_code == 200
