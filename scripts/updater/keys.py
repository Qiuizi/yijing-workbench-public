"""签名公钥的分级管理。

- 仓库里只出现**公钥**；私钥与密码永远不进仓库、不进 Artifact、不进安装包。
- `QA_PUBLIC_KEY` 是用于候选构建与隔离升级实验的测试公钥，本身不敏感。
- 正式发布必须使用维护者私钥对应的公钥；`verify_release.py --production`
  会发现「仍在用 QA 公钥」并直接失败。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

# 由 `npx tauri signer generate` 生成的 QA 密钥对中的公钥（仅用于候选/隔离测试）。
QA_PUBLIC_KEY = (
    "dW50cnVzdGVkIGNvbW1lbnQ6IG1pbmlzaWduIHB1YmxpYyBrZXk6IDJGNDA4QkNGQzkyRjA3N0IK"
    "UldSN0J5L0p6NHRBTC8wN3MweVVMbXV1YVNEY3pqZ2Y1Z2Q3enhlY2hyZElXNnZlTlBRM2xTT1oK"
)

# minisign 公钥文本形如：
#   untrusted comment: minisign public key: <ID>
#   <base64 key>
REQUIRED_COMMENT_PREFIX = "untrusted comment:"
PUBLIC_KEY_BYTES = 42  # "Ed" + 8 字节 key id + 32 字节 ed25519 公钥


def app_public_key(repo_root: Path | str) -> str:
    """读取应用实际内置的更新公钥。"""
    repo_root = Path(repo_root)
    config = json.loads((repo_root / "frontend/src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    return str(config.get("plugins", {}).get("updater", {}).get("pubkey", "")).strip()


def normalize(value: str) -> str:
    return "".join(value.split())


def is_qa_key(value: str) -> bool:
    return bool(value) and normalize(value) == normalize(QA_PUBLIC_KEY)


def describe_public_key(value: str) -> dict[str, object]:
    """解析并描述一个公钥，供日志与校验使用（不含任何私钥信息）。"""
    normalized = value.strip()
    result: dict[str, object] = {"present": bool(normalized), "valid": False}
    if not normalized:
        return result
    try:
        decoded = base64.b64decode(normalized)
    except ValueError:
        return result
    text = decoded.decode("utf-8", errors="replace")
    lines = [line for line in text.splitlines() if line.strip()]
    result["lines"] = len(lines)
    if len(lines) >= 2 and lines[0].startswith(REQUIRED_COMMENT_PREFIX):
        try:
            key_bytes = base64.b64decode(lines[1])
        except ValueError:
            return result
        result["bytes"] = len(key_bytes)
        result["valid"] = len(key_bytes) == PUBLIC_KEY_BYTES
        result["key_id"] = key_bytes[2:10].hex().upper() if len(key_bytes) >= 10 else ""
        result["is_qa"] = is_qa_key(normalized)
    return result
