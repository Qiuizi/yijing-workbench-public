#!/usr/bin/env python3
"""Sign an already verified staging installer without rebuilding it.

The signer binary must be compiled from this checkout. This module refuses to
launch it until the installer path has passed the same relative-path check as
the provenance file list. Signing writes a separate ``.sig``; the installer
bytes are hashed before and after and must be identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key
from scripts.updater.manifest import (
    build_latest_json,
    decode_signature,
    public_key_fingerprint,
    public_key_key_id,
    read_signature,
    signature_key_id,
    write_latest_json,
)
from scripts.updater.provenance import FORBIDDEN_TEXT, locate_bundle_file

REPO_ROOT = _REPO_ROOT


class SignError(RuntimeError):
    """Signing or the signed-chain check failed before any publish step."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _trusted_version(signature: str) -> str | None:
    lines = decode_signature(signature) or []
    trusted = next((line.split(":", 1)[1].strip() for line in lines if line.startswith("trusted comment:")), "")
    for field in trusted.split("\t"):
        if field.startswith("version:"):
            return field.split(":", 1)[1]
    return None


def _reject_secret_text(text: str, label: str) -> None:
    lowered = text.lower()
    markers = (*FORBIDDEN_TEXT, "encrypted secret key", "TAURI_SIGNING_PRIVATE_KEY=")
    for marker in markers:
        if marker.lower() in lowered:
            raise SignError(f"{label} 含有敏感材料")


def assemble_signed_bundle(
    staging_dir: Path,
    out_dir: Path,
    *,
    signer: Path,
    key_file: Path,
    version: str,
    tag: str,
    notes: str,
    repo: str,
    source_sha: str,
    source_ref: str,
    workflow_run: str,
    staging_artifact_id: str,
    staging_artifact_digest: str,
    expected_installer_sha256: str,
) -> str:
    if not signer.is_file() or signer.is_symlink():
        raise SignError("签名工具必须是本次 checkout 编译出的普通文件")
    if not key_file.is_file() or key_file.is_symlink():
        raise SignError("签名私钥文件不存在或是符号链接")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise SignError("签名输出目录必须为空")
    manifest_path = staging_dir / "manifest.json"
    manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    filename = manifest_doc.get("installer", {}).get("filename")
    installer, error = locate_bundle_file(staging_dir, filename)
    if error or installer is None:
        raise SignError(f"staging 安装包路径被拒绝：{error}")
    before = sha256_file(installer)
    expected = expected_installer_sha256.strip().lower()
    if before != expected:
        raise SignError("staging 安装包 SHA-256 与构建作业记录不一致")
    pubkey = app_public_key(REPO_ROOT)
    if is_qa_key(pubkey) or not describe_public_key(pubkey).get("valid"):
        raise SignError("仓库公钥不是可用的正式公钥")
    out_dir.mkdir(parents=True, exist_ok=True)
    signature_path = out_dir / f"{filename}.sig"
    completed = subprocess.run(
        [
            str(signer),
            "--file",
            str(installer),
            "--key-file",
            str(key_file),
            "--signature-out",
            str(signature_path),
            "--version",
            version,
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "signer failed").strip()
        _reject_secret_text(message, "签名工具输出")
        raise SignError(message)
    _reject_secret_text(completed.stdout or "", "签名工具输出")
    after = sha256_file(installer)
    if after != before:
        raise SignError("签名过程改变了安装包字节")
    signature = read_signature(signature_path)
    if signature_key_id(signature) != public_key_key_id(pubkey):
        raise SignError("签名 key id 与仓库正式公钥不一致")
    if _trusted_version(signature) != version:
        raise SignError("正式签名没有绑定本次版本")
    signed_installer = out_dir / filename
    signed_installer.write_bytes(installer.read_bytes())
    if sha256_file(signed_installer) != before:
        raise SignError("复制到签名目录后安装包字节发生变化")
    digest = before.upper()
    (out_dir / "SHA256SUMS.txt").write_text(f"{digest}  {filename}\n", encoding="utf-8")
    latest = build_latest_json(
        version=version,
        notes=notes,
        asset_name=filename,
        signature=signature,
        repo=repo,
        tag=tag,
    )
    write_latest_json(out_dir / "latest.json", latest)
    signed_manifest = {
        "version": version,
        "tag": tag,
        "source_sha": source_sha,
        "source_ref": source_ref,
        "workflow_run": workflow_run,
        "signing_status": "production_signed",
        "updater_pubkey_source": "argument",
        "updater_pubkey_is_qa": False,
        "updater_pubkey_key_id": public_key_key_id(pubkey),
        "updater_pubkey_fingerprint": public_key_fingerprint(pubkey),
        "signature_key_id": signature_key_id(signature),
        "signature_file": signature_path.name,
        "staging_artifact_id": str(staging_artifact_id),
        "staging_artifact_digest": staging_artifact_digest,
        "staging_installer_sha256": before,
        "installer_bytes_unchanged": True,
        "installer": {
            "filename": filename,
            "bytes": signed_installer.stat().st_size,
            "sha256": digest,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    encoded = json.dumps(signed_manifest, ensure_ascii=False, indent=2)
    _reject_secret_text(encoded, "signed manifest")
    (out_dir / "manifest.json").write_text(encoded + "\n", encoding="utf-8")
    (out_dir / "PROVENANCE.md").write_text(
        "\n".join(
            [
                f"# {tag} 正式签名",
                "",
                f"- 版本：`{version}`",
                f"- 源码：`{source_sha}`",
                f"- 安装包 SHA-256：`{digest}`",
                "- 签名前后安装包字节一致。签名是独立的 `.sig`，不是重新编译的安装包。",
                f"- staging artifact：`{staging_artifact_id}`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return before


def verify_signed_chain(
    signed_dir: Path,
    *,
    expected_version: str,
    expected_installer_sha256: str,
    expected_staging_artifact_id: str,
    expected_source_sha: str,
) -> None:
    manifest_doc = json.loads((signed_dir / "manifest.json").read_text(encoding="utf-8"))
    filename = manifest_doc.get("installer", {}).get("filename")
    installer, error = locate_bundle_file(signed_dir, filename)
    if error or installer is None:
        raise SignError(f"签名目录安装包路径被拒绝：{error}")
    actual = sha256_file(installer)
    expected = expected_installer_sha256.strip().lower()
    if actual != expected or str(manifest_doc.get("staging_installer_sha256") or "").lower() != expected:
        raise SignError("签名后的安装包 SHA-256 与 staging 不一致")
    if manifest_doc.get("version") != expected_version:
        raise SignError("签名清单版本不一致")
    if str(manifest_doc.get("source_sha") or "").lower() != expected_source_sha.lower():
        raise SignError("签名清单 source SHA 不一致")
    if str(manifest_doc.get("staging_artifact_id") or "") != str(expected_staging_artifact_id):
        raise SignError("签名清单没有绑定本次 staging Artifact ID")
    if manifest_doc.get("installer_bytes_unchanged") is not True:
        raise SignError("签名清单没有确认安装包字节未变")
    signature_name = manifest_doc.get("signature_file")
    signature_path, signature_error = locate_bundle_file(signed_dir, signature_name)
    if signature_error or signature_path is None:
        raise SignError(f"签名文件路径被拒绝：{signature_error}")
    if not (signed_dir / "latest.json").is_file():
        raise SignError("缺少 latest.json")
    if _trusted_version(read_signature(signature_path)) != expected_version:
        raise SignError("正式签名没有绑定预期版本")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="对已验证的 staging 安装包做正式签名")
    sub = parser.add_subparsers(dest="command", required=True)
    assemble = sub.add_parser("assemble")
    assemble.add_argument("--staging-dir", type=Path, required=True)
    assemble.add_argument("--out", type=Path, required=True)
    assemble.add_argument("--signer", type=Path, required=True)
    assemble.add_argument("--key-file", type=Path, required=True)
    assemble.add_argument("--version", required=True)
    assemble.add_argument("--tag", required=True)
    assemble.add_argument("--notes-file", type=Path, required=True)
    assemble.add_argument("--repo", default="Qiuizi/yijing-workbench-public")
    assemble.add_argument("--source-sha", required=True)
    assemble.add_argument("--source-ref", required=True)
    assemble.add_argument("--workflow-run", required=True)
    assemble.add_argument("--staging-artifact-id", required=True)
    assemble.add_argument("--staging-artifact-digest", required=True)
    assemble.add_argument("--expected-installer-sha256", required=True)
    assemble.add_argument("--github-output", type=Path, default=None)
    verify = sub.add_parser("verify-chain")
    verify.add_argument("--signed-dir", type=Path, required=True)
    verify.add_argument("--expected-version", required=True)
    verify.add_argument("--expected-installer-sha256", required=True)
    verify.add_argument("--expected-staging-artifact-id", required=True)
    verify.add_argument("--expected-source-sha", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-chain":
            verify_signed_chain(
                args.signed_dir,
                expected_version=args.expected_version,
                expected_installer_sha256=args.expected_installer_sha256,
                expected_staging_artifact_id=args.expected_staging_artifact_id,
                expected_source_sha=args.expected_source_sha,
            )
            print("OK  signed chain")
            return 0
        digest = assemble_signed_bundle(
            args.staging_dir,
            args.out,
            signer=args.signer,
            key_file=args.key_file,
            version=args.version,
            tag=args.tag,
            notes=args.notes_file.read_text(encoding="utf-8"),
            repo=args.repo,
            source_sha=args.source_sha,
            source_ref=args.source_ref,
            workflow_run=args.workflow_run,
            staging_artifact_id=args.staging_artifact_id,
            staging_artifact_digest=args.staging_artifact_digest,
            expected_installer_sha256=args.expected_installer_sha256,
        )
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write(f"installer-sha256={digest}\n")
        print(f"OK  signed installer sha256={digest}")
        return 0
    except (SignError, OSError, json.JSONDecodeError) as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
