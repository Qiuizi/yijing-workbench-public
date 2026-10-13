"""PyInstaller entry point for the Tauri-managed FastAPI sidecar."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def main() -> int:
    try:
        port = int(os.environ["YIJING_SERVER_PORT"])
        token = os.environ["YIJING_API_TOKEN"]
        database = Path(os.environ["YIJING_DB_PATH"])
        log_path = Path(os.environ["YIJING_LOG_PATH"])
        backup_dir = Path(os.environ["YIJING_BACKUP_DIR"])
    except (KeyError, ValueError) as exc:
        print("桌面服务启动配置不完整。", file=sys.stderr)
        return 2
    if not 1 <= port <= 65535 or len(token) < 32:
        print("桌面服务启动参数无效。", file=sys.stderr)
        return 2

    database.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.environ["YIJING_DESKTOP_MODE"] = "1"
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        encoding="utf-8",
    )

    try:
        import uvicorn
        from backend.main import create_app

        uvicorn.run(
            create_app(db_path=database, desktop_mode=True, desktop_api_token=token),
            host="127.0.0.1",
            port=port,
            log_config=None,
            log_level="info",
            access_log=False,
        )
    except Exception:
        logging.exception("桌面本地服务无法启动")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
