"""安装包内容门禁：哈希/签名正确 ≠ 用户装完有应用。"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.updater import installer_contents


def _fake_listing(stdout: str, returncode: int = 0, stderr: str = ""):
    def fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)

    return fake_run


def test_list_nsis_files_parses_7z_slt_output(monkeypatch):
    stdout = """Path = C:\\qa\\setup.exe
Type = Nsis

----------
Path = yijing-workbench.exe
Size = 10449408

Path = binaries\\yijing-backend\\yijing-backend.exe
Size = 5867336

Path = $PLUGINSDIR\\System.dll
Size = 12288
"""
    monkeypatch.setattr(installer_contents.subprocess, "run", _fake_listing(stdout))
    files = installer_contents.list_nsis_files(Path("C:/qa/setup.exe"), seven_zip="7z")
    assert "yijing-workbench.exe" in files
    assert "binaries/yijing-backend/yijing-backend.exe" in files
    assert "$PLUGINSDIR/System.dll" in files
    assert "C:/qa/setup.exe" not in files


def test_missing_7z_fails_closed(monkeypatch):
    monkeypatch.setattr(installer_contents, "_seven_zip", lambda: None)
    problems = installer_contents.verify_nsis_contents(Path("setup.exe"))
    assert problems
    assert "找不到 7z" in problems[0]


def test_verify_accepts_main_app_sidecar_without_verifier(monkeypatch):
    monkeypatch.setattr(
        installer_contents,
        "list_nsis_files",
        lambda *args, **kwargs: {
            "yijing-workbench.exe",
            "binaries/yijing-backend/yijing-backend.exe",
            "LICENSE",
        },
    )
    assert installer_contents.verify_nsis_contents(Path("setup.exe")) == []


def test_verify_rejects_missing_main_app(monkeypatch):
    monkeypatch.setattr(
        installer_contents,
        "list_nsis_files",
        lambda *args, **kwargs: {
            "verify-updater-signature.exe",
            "binaries/yijing-backend/yijing-backend.exe",
        },
    )
    problems = installer_contents.verify_nsis_contents(Path("setup.exe"))
    assert any("缺少主程序 yijing-workbench.exe" in item for item in problems)
    assert any("不应包含发布门禁内部工具" in item for item in problems)


def test_verify_rejects_missing_sidecar(monkeypatch):
    monkeypatch.setattr(
        installer_contents,
        "list_nsis_files",
        lambda *args, **kwargs: {"yijing-workbench.exe"},
    )
    problems = installer_contents.verify_nsis_contents(Path("setup.exe"))
    assert any("缺少 Python sidecar" in item for item in problems)


def test_verify_release_runs_the_content_gate(tmp_path, monkeypatch):
    """verify_release 必须把安装包内容问题并入发布阻断，而不是只做哈希/签名。"""
    from backend.tests.test_updater_manifest import _build_release
    from scripts.updater import verify_release

    release = _build_release(tmp_path)
    seen: list[Path] = []
    monkeypatch.setattr(
        verify_release.installer_contents,
        "verify_nsis_contents",
        lambda path: seen.append(path) or ["安装包根目录缺少主程序 yijing-workbench.exe"],
    )
    problems = verify_release.verify(
        release,
        tag="v3.3.3",
        repo="Qiuizi/yijing-workbench-public",
        production=False,
        expected_version="3.3.3",
    )
    assert seen
    assert any("缺少主程序" in item for item in problems)
