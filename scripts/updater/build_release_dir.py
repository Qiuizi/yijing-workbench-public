#!/usr/bin/env python3
"""把一次构建产物整理成可直接上传的 Release 目录。

输入：Tauri NSIS 产物目录（含 *setup.exe 与同名 .sig）
输出（默认 ./release）：
    <installer>.exe
    <installer>.exe.sig
    latest.json          ← Tauri updater 静态清单
    SHA256SUMS.txt       ← 安装包字节校验
    manifest.json        ← 机器可读的构建来源
    PROVENANCE.md        ← 人可读的来源说明

用法：
    python scripts/updater/build_release_dir.py \
        --bundle-dir frontend/src-tauri/target/release/bundle/nsis \
        --out release --tag v3.3.2 \
        --notes-file docs/release-notes-v3.3.2.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater import manifest
from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key

REPO_ROOT = Path(__file__).resolve().parents[2]

def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="整理 Tauri 更新产物为 Release 目录")
    parser.add_argument("--bundle-dir", required=True, type=Path, help="NSIS 产物目录")
    parser.add_argument("--out", required=True, type=Path, help="输出目录")
    parser.add_argument("--tag", required=True, help="发布 tag，例如 v3.3.2")
    parser.add_argument("--version", default=None, help="默认读取仓库版本")
    parser.add_argument("--repo", default="Qiuizi/yijing-workbench-public")
    parser.add_argument("--notes-file", type=Path, default=None)
    parser.add_argument("--notes", default="")
    parser.add_argument("--source-sha", default="")
    parser.add_argument("--source-ref", default="")
    parser.add_argument("--source-trigger", default="")
    parser.add_argument("--workflow-run", default="")
    parser.add_argument("--sidecar", type=Path, default=None)
    parser.add_argument("--pub-date", default=None)
    parser.add_argument("--allow-prerelease", action="store_true", help="QA/候选构建允许 3.3.2-qa.N")
    parser.add_argument(
        "--updater-pubkey",
        default=None,
        help="本次构建实际注入的 updater 公钥（base64）；正式发布必须传，默认取仓库配置（QA）",
    )
    args = parser.parse_args(argv)
    manifest.enable_utf8_console()

    version = args.version or manifest.assert_versions_consistent(REPO_ROOT)
    notes = args.notes
    if args.notes_file:
        notes = args.notes_file.read_text(encoding="utf-8")
    if not notes.strip():
        notes = f"易经起卦工作台 {version}"

    bundle = manifest.collect_bundle(args.bundle_dir, version)
    args.out.mkdir(parents=True, exist_ok=True)

    installer_out = args.out / bundle.filename
    shutil.copy2(bundle.path, installer_out)
    signature_out = args.out / f"{bundle.filename}.sig"
    signature_out.write_text(bundle.signature + "\n", encoding="utf-8")

    digest = sha256_of(installer_out)
    (args.out / "SHA256SUMS.txt").write_text(f"{digest}  {bundle.filename}\n", encoding="utf-8")

    latest = manifest.build_latest_json(
        version=version,
        notes=notes,
        asset_name=bundle.filename,
        signature=bundle.signature,
        repo=args.repo,
        tag=args.tag,
        pub_date=args.pub_date,
    )
    manifest.assert_latest_json(
        latest,
        expected_version=version,
        repo=args.repo,
        tag=args.tag,
        allow_prerelease=args.allow_prerelease,
    )
    manifest.write_latest_json(args.out / "latest.json", latest, allow_prerelease=args.allow_prerelease)

    injected_pubkey = (args.updater_pubkey or "").strip()
    pubkey_source = "argument" if injected_pubkey else "repo_config"
    pubkey = injected_pubkey or app_public_key(REPO_ROOT)
    info = describe_public_key(pubkey)
    signature_key_id = manifest.signature_key_id(bundle.signature)
    if not info.get("valid"):
        raise SystemExit("注入的 updater 公钥不是有效的 minisign 公钥")
    if signature_key_id and manifest.public_key_key_id(pubkey) != signature_key_id:
        raise SystemExit(
            f"公钥与签名的 key id 不一致：pubkey={manifest.public_key_key_id(pubkey)} signature={signature_key_id}"
        )
    build_manifest = {
        "version": version,
        "tag": args.tag,
        "source_sha": args.source_sha,
        "source_ref": args.source_ref,
        "source_trigger": args.source_trigger,
        "workflow_run": args.workflow_run,
        "install_mode": "currentUser",
        "updater_target": manifest.WINDOWS_TARGET,
        "updater_pubkey_source": pubkey_source,
        "updater_pubkey_is_qa": is_qa_key(pubkey),
        "updater_pubkey_key_id": manifest.public_key_key_id(pubkey),
        "updater_pubkey_fingerprint": manifest.public_key_fingerprint(pubkey),
        "signature_key_id": signature_key_id,
        "installer": {
            "filename": bundle.filename,
            "original_filename": bundle.source_name,
            "bytes": installer_out.stat().st_size,
            "sha256": digest,
        },
        "signature_file": signature_out.name,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if args.sidecar and args.sidecar.exists():
        build_manifest["sidecar_sha256"] = sha256_of(args.sidecar)
    (args.out / "manifest.json").write_text(
        json.dumps(build_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    provenance = [
        f"# {args.tag} 构建来源",
        "",
        f"- 版本：`{version}`",
        f"- 源码：`{args.source_sha or '未提供'}`（{args.source_ref or '未提供'}，触发：{args.source_trigger or '未提供'}）",
        f"- 工作流运行：{args.workflow_run or '未提供'}",
        f"- 安装包：`{bundle.filename}`（{installer_out.stat().st_size} bytes；原始产物 `{bundle.source_name}`，仅重命名，字节不变）",
        f"- SHA-256：`{digest}`",
        f"- 更新签名：`{signature_out.name}`（minisign/ed25519，公钥 key id `{manifest.public_key_key_id(pubkey)}`，签名 key id `{signature_key_id}`）",
        f"- 公钥来源：{pubkey_source}（指纹 `{manifest.public_key_fingerprint(pubkey)}`）",
        f"- 更新公钥是否为 QA 测试密钥：{'是（禁止正式发布）' if is_qa_key(pubkey) else '否'}",
        f"- 安装模式：currentUser（NSIS）",
        "",
        "## 三类完整性凭据的区别",
        "",
        "1. **Tauri Updater 签名**（`.sig`）：证明更新包出自持有私钥的一方，应用安装前校验；",
        "2. **SHA-256**（`SHA256SUMS.txt`）：证明字节未被改动，用于人工与脚本核对；",
        "3. **Windows Authenticode**：操作系统层面的发布者签名，本项目当前未提供。",
        "",
        "前两者不能互相替代：哈希可被重新计算，签名不能伪造。",
        "",
    ]
    (args.out / "PROVENANCE.md").write_text("\n".join(provenance), encoding="utf-8")

    print(f"version={version} installer={bundle.filename} bytes={installer_out.stat().st_size}")
    print(f"sha256={digest}")
    print(f"signature={signature_out.name} pubkey_is_qa={is_qa_key(pubkey)}")
    print(f"out={args.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
