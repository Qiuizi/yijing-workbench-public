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

from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key, normalize
from scripts.updater.manifest import UpdaterManifestError, assert_versions_consistent

REPO_ROOT = Path(__file__).resolve().parents[2]

def check(expect_version: str | None, expect_pubkey: str | None = None) -> tuple[bool, str]:
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

    if expect_pubkey:
        expect_info = describe_public_key(expect_pubkey)
        if not expect_info.get("valid"):
            return False, "release 环境里的 TAURI_UPDATER_PUBKEY 不是有效的 minisign 公钥"
        if is_qa_key(expect_pubkey):
            return False, "release 环境里的 TAURI_UPDATER_PUBKEY 是 QA 测试公钥"
        if normalize(expect_pubkey) != normalize(key):
            return False, (
                "仓库内置公钥与 release 环境的正式公钥不一致："
                f"repo={info.get('key_id')} env={expect_info.get('key_id')}；"
                "请先提交正式公钥再发布"
            )

    return True, f"version={version} pubkey_key_id={info.get('key_id')}"

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="正式发布前置门禁")
    parser.add_argument("--expect-version", default=None)
    parser.add_argument("--expect-pubkey", default=None, help="release 环境配置的正式公钥（base64）")
    args = parser.parse_args(argv)

    ok, message = check(args.expect_version, args.expect_pubkey)
    print(("OK  " if ok else "FAIL  ") + message, file=sys.stdout if ok else sys.stderr)
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
