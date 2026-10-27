#!/usr/bin/env python3
"""正式发布前置门禁：版本一致 + 公钥可用且不是 QA 测试密钥。

流水线里单独一步，便于失败时一眼看出是「版本没对齐」还是「还在用测试公钥」。

用法：
    python scripts/updater/release_gate.py --expect-version 3.3.2
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key
from scripts.updater.manifest import UpdaterManifestError, assert_versions_consistent

REPO_ROOT = Path(__file__).resolve().parents[2]

def check(expect_version: str | None) -> tuple[bool, str]:
    try:
        version = assert_versions_consistent(REPO_ROOT, expected=expect_version)
    except UpdaterManifestError as error:
        return False, str(error)

    key = app_public_key(REPO_ROOT)
    info = describe_public_key(key)
    if not info.get("valid"):
        return False, "tauri.conf.json 的 plugins.updater.pubkey 不是有效的 minisign 公钥"
    if is_qa_key(key):
        return False, "仓库仍在使用 QA 测试公钥，禁止正式发布；请替换后重新构建"

    return True, f"version={version} pubkey_key_id={info.get('key_id')}"

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="正式发布前置门禁")
    parser.add_argument("--expect-version", default=None)
    args = parser.parse_args(argv)

    ok, message = check(args.expect_version)
    print(("OK  " if ok else "FAIL  ") + message, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
