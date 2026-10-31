#!/usr/bin/env python3
"""Assemble an unsigned production staging bundle.

Tauri CLI 2.11.5 enables updater signing only when
``bundle.createUpdaterArtifacts`` is not false. This module writes the build
override that keeps it false, then copies the NSIS installer without creating
a ``.sig`` or ``latest.json``. A later job signs those exact bytes. The
installer is not a candidate package and is not a publishable release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key
from scripts.updater.manifest import (
    UpdaterManifestError,
    canonical_asset_name,
    find_installer,
    public_key_fingerprint,
)
from scripts.updater.provenance import locate_bundle_file

REPO_ROOT = _REPO_ROOT


class StagingError(RuntimeError):
    """The unsigned bundle cannot be assembled."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def unsigned_build_override(pubkey: str) -> dict[str, object]:
    """Config passed to ``tauri build --config``. Signing stays off."""
    info = describe_public_key(pubkey)
    if not info.get("valid") or is_qa_key(pubkey):
        raise StagingError("未签名构建只能注入仓库正式公钥")
    return {
        "bundle": {"createUpdaterArtifacts": False},
        "plugins": {"updater": {"pubkey": "".join(pubkey.split())}},
    }


def write_unsigned_override(path: Path, pubkey: str | None = None) -> Path:
    document = unsigned_build_override(pubkey or app_public_key(REPO_ROOT))
    path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return path


def _reject_signed_inputs(bundle_dir: Path) -> None:
    signed = [path.name for path in bundle_dir.glob("*.sig")]
    if (bundle_dir / "latest.json").exists():
        signed.append("latest.json")
    if signed:
        raise StagingError("NSIS 目录已有签名或 latest.json，拒绝把它们当成未签名 staging：" + ", ".join(signed))


def assemble_unsigned_staging(
    nsis_dir: Path,
    out_dir: Path,
    *,
    version: str,
    source_sha: str,
    source_ref: str,
    workflow_run: str,
    includes: list[Path] | None = None,
) -> str:
    """Copy the installer and metadata. Returns the uppercase SHA-256."""
    _reject_signed_inputs(nsis_dir)
    installer = find_installer(nsis_dir)
    if installer.is_symlink():
        raise StagingError(f"拒绝符号链接安装包：{installer.name}")
    filename = canonical_asset_name(version)
    out_dir.mkdir(parents=True, exist_ok=True)
    if any(out_dir.iterdir()):
        raise StagingError("staging 输出目录必须为空")
    target = out_dir / filename
    payload = installer.read_bytes()
    target.write_bytes(payload)
    if target.is_symlink() or sha256_file(target) != sha256_file(installer):
        raise StagingError("复制安装包后字节发生变化")
    digest = sha256_file(target)
    pubkey = app_public_key(REPO_ROOT)
    info = describe_public_key(pubkey)
    (out_dir / "SHA256SUMS.txt").write_text(f"{digest}  {filename}\n", encoding="utf-8")
    manifest = {
        "version": version,
        "tag": f"v{version}",
        "source_sha": source_sha,
        "source_ref": source_ref,
        "workflow_run": workflow_run,
        "signing_status": "unsigned_staging",
        "updater_pubkey_source": "repo_config",
        "updater_pubkey_is_qa": False,
        "updater_pubkey_key_id": info.get("key_id"),
        "updater_pubkey_fingerprint": public_key_fingerprint(pubkey),
        "installer": {
            "filename": filename,
            "original_filename": installer.name,
            "bytes": target.stat().st_size,
            "sha256": digest,
        },
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "PROVENANCE.md").write_text(
        "\n".join(
            [
                f"# v{version} 未签名 staging",
                "",
                f"- 版本：`{version}`",
                f"- 源码：`{source_sha}`（{source_ref}）",
                f"- 工作流运行：{workflow_run}",
                f"- 安装包：`{filename}`（{target.stat().st_size} bytes）",
                f"- SHA-256：`{digest}`",
                "- 更新签名：无。此目录不是正式发布产物，也不是候选临时签名包。",
                "- `createUpdaterArtifacts` 为 false，构建作业没有正式私钥。",
                "",
            ]
        ),
        encoding="utf-8",
    )
    for extra in includes or []:
        located, error = locate_bundle_file(extra.parent, extra.name)
        if error or located is None:
            raise StagingError(f"附加文件被拒绝：{extra.name}：{error}")
        if extra.name in {"latest.json"} or extra.name.endswith(".sig"):
            raise StagingError(f"未签名 staging 拒绝附加文件：{extra.name}")
        (out_dir / extra.name).write_bytes(located.read_bytes())
    if _reject_signed_inputs_soft(out_dir):
        raise StagingError("未签名 staging 生成后出现了签名文件")
    return digest


def _reject_signed_inputs_soft(bundle_dir: Path) -> bool:
    return any(bundle_dir.glob("*.sig")) or (bundle_dir / "latest.json").exists()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成未签名正式 staging")
    sub = parser.add_subparsers(dest="command", required=True)
    override = sub.add_parser("write-override")
    override.add_argument("--out", type=Path, required=True)
    assemble = sub.add_parser("assemble")
    assemble.add_argument("--nsis-dir", type=Path, required=True)
    assemble.add_argument("--out", type=Path, required=True)
    assemble.add_argument("--version", required=True)
    assemble.add_argument("--source-sha", required=True)
    assemble.add_argument("--source-ref", required=True)
    assemble.add_argument("--workflow-run", required=True)
    assemble.add_argument("--include", type=Path, action="append", default=[])
    assemble.add_argument("--github-output", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "write-override":
            write_unsigned_override(args.out)
            print(f"OK  unsigned override {args.out}")
            return 0
        digest = assemble_unsigned_staging(
            args.nsis_dir,
            args.out,
            version=args.version,
            source_sha=args.source_sha,
            source_ref=args.source_ref,
            workflow_run=args.workflow_run,
            includes=args.include,
        )
        if args.github_output:
            with args.github_output.open("a", encoding="utf-8") as handle:
                handle.write(f"installer-sha256={digest.lower()}\n")
        print(f"OK  unsigned staging sha256={digest.lower()}")
        return 0
    except (StagingError, UpdaterManifestError, OSError) as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
