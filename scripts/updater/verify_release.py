#!/usr/bin/env python3
"""校验一个 Release 目录是否满足自动更新契约（正式发布前的最后一道门）。

检查项：
  1. 安装包 / 签名 / latest.json / SHA256SUMS.txt / manifest.json / PROVENANCE.md 齐全；
  2. 安装包 SHA-256 与 SHA256SUMS.txt、manifest.json 三方一致；
  3. latest.json 结构合法，version / url / signature 指向同一次构建；
  4. 签名文件命名与安装包匹配，且 latest.json.signature 与 .sig 内容逐字相同；
  5. 仓库内所有版本来源一致（package.json / Cargo.toml / tauri.conf.json / backend）；
  6. `--production` 模式下，拒绝仍在用 QA 测试公钥的构建。

用法：
    python scripts/updater/verify_release.py release --tag v3.3.2
    python scripts/updater/verify_release.py release --tag v3.3.2 --production
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater import manifest
from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key

REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FILES = ("SHA256SUMS.txt", "latest.json", "manifest.json", "PROVENANCE.md")

def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()

def verify(
    release_dir: Path,
    *,
    tag: str,
    repo: str,
    production: bool,
    expected_version: str | None,
    allow_prerelease: bool = False,
) -> list[str]:
    problems: list[str] = []
    if not release_dir.is_dir():
        return [f"目录不存在：{release_dir}"]

    for name in REQUIRED_FILES:
        if not (release_dir / name).is_file():
            problems.append(f"缺少文件：{name}")
    if problems:
        return problems

    build_manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))

    if allow_prerelease:
        # QA/候选构建用 --config 覆盖版本，仓库版本仍是发布版本，不能拿来做一致性对比
        version = str(build_manifest.get("version") or expected_version or "")
        if not manifest.SEMVER_RE.match(version):
            return [f"manifest.json 的 version 无效：{version!r}"]
        if expected_version and version != expected_version:
            return [f"构建版本 {version} 与期望的 {expected_version} 不一致"]
    else:
        try:
            version = manifest.assert_versions_consistent(REPO_ROOT, expected=expected_version)
        except manifest.UpdaterManifestError as error:
            return [str(error)]

    try:
        asset = manifest.collect_bundle(release_dir, version)
    except manifest.UpdaterManifestError as error:
        return [str(error)]

    digest = sha256_of(asset.path)

    sums_lines = [line.split() for line in (release_dir / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    recorded = {parts[-1]: parts[0] for parts in sums_lines if len(parts) >= 2}
    if recorded.get(asset.filename) != digest:
        problems.append("SHA256SUMS.txt 与安装包实际哈希不一致")

    installer = build_manifest.get("installer", {})
    if installer.get("filename") != asset.filename:
        problems.append("manifest.json 的安装包文件名不一致")
    if installer.get("sha256") != digest:
        problems.append("manifest.json 的 SHA-256 不一致")
    if installer.get("bytes") != asset.path.stat().st_size:
        problems.append("manifest.json 的字节数不一致")
    if build_manifest.get("version") != version:
        problems.append(f"manifest.json 版本 {build_manifest.get('version')} 与构建版本 {version} 不一致")
    if build_manifest.get("tag") != tag:
        problems.append(f"manifest.json tag {build_manifest.get('tag')} 与 {tag} 不一致")

    latest = json.loads((release_dir / "latest.json").read_text(encoding="utf-8"))
    errors = manifest.validate_latest_json(
        latest, expected_version=version, repo=repo, tag=tag, allow_prerelease=allow_prerelease
    )
    problems.extend(errors)
    entry = latest.get("platforms", {}).get(manifest.WINDOWS_TARGET, {})
    if isinstance(entry, dict):
        if entry.get("signature", "").strip() != asset.signature:
            problems.append("latest.json 的 signature 与 .sig 文件内容不一致")
        if not str(entry.get("url", "")).endswith(asset.filename):
            problems.append("latest.json 的 url 未指向本次安装包")

    pubkey_info = describe_public_key(app_public_key(REPO_ROOT))
    if not pubkey_info.get("valid"):
        problems.append("tauri.conf.json 里的更新公钥不是有效的 minisign 公钥")
    if production and is_qa_key(app_public_key(REPO_ROOT)):
        problems.append(
            "正式发布禁止使用 QA 测试公钥：请把 tauri.conf.json 的 plugins.updater.pubkey "
            "换成维护者私钥对应的公钥后再构建"
        )
    if build_manifest.get("updater_pubkey_is_qa") and production:
        problems.append("manifest 记录的构建使用了 QA 公钥，不能进入正式更新渠道")

    return problems

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="校验 Release 目录是否满足自动更新契约")
    parser.add_argument("release_dir", type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--repo", default="Qiuizi/yijing-workbench-public")
    parser.add_argument("--expected-version", default=None)
    parser.add_argument("--production", action="store_true", help="正式渠道校验：拒绝 QA 公钥")
    parser.add_argument("--allow-prerelease", action="store_true", help="QA/候选构建允许 3.3.2-qa.N")
    args = parser.parse_args(argv)
    manifest.enable_utf8_console()

    problems = verify(
        args.release_dir,
        tag=args.tag,
        repo=args.repo,
        production=args.production,
        expected_version=args.expected_version,
        allow_prerelease=args.allow_prerelease,
    )
    if problems:
        print("发布校验失败：", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print(f"OK  {args.release_dir} (tag={args.tag}, production={args.production})")
    return 0

if __name__ == "__main__":
    sys.exit(main())
