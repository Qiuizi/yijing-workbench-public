#!/usr/bin/env python3
"""把官网「下载区」的静态回退信息更新为某个正式 Release 的事实。

只在正式发布成功后由发布流水线调用（最后一公里）；本地/候选构建不要跑它，
否则官网会提前指向尚未发布的版本。

用法：
    python scripts/updater/update_site_release.py --release-dir release --tag v3.3.2
    python scripts/updater/update_site_release.py --release-dir release --tag v3.3.2 --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

REPO_ROOT = Path(__file__).resolve().parents[2]
LINKS_TS = REPO_ROOT / "website/src/links.ts"

def render(release_dir: Path, tag: str, date: str) -> tuple[str, dict[str, object]]:
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    installer = manifest["installer"]
    version = manifest["version"]
    facts = {
        "tag": tag,
        "date": date,
        "assetName": installer["filename"],
        "bytes": installer["bytes"],
        "sha256": installer["sha256"],
        "version": f"v{version}",
    }
    return version, facts

def apply_to_source(source: str, facts: dict[str, object]) -> str:
    tag = str(facts["tag"])
    asset = str(facts["assetName"])
    updated = source
    updated = re.sub(r"releaseTag: REPO \+ '/releases/tag/[^']+'", f"releaseTag: REPO + '/releases/tag/{tag}'", updated)
    updated = re.sub(
        r"download: REPO \+ '/releases/download/[^']+'",
        f"download: REPO + '/releases/download/{tag}/{asset}'",
        updated,
    )
    updated = re.sub(r"checksums: REPO \+ '/releases/download/[^']+'", f"checksums: REPO + '/releases/download/{tag}/SHA256SUMS.txt'", updated)
    updated = re.sub(r"provenance: REPO \+ '/releases/download/[^']+'", f"provenance: REPO + '/releases/download/{tag}/PROVENANCE.md'", updated)
    updated = re.sub(r"tag: 'v[^']+'", f"tag: '{tag}'", updated, count=1)
    updated = re.sub(r"date: '\d{4}-\d{2}-\d{2}'", f"date: '{facts['date']}'", updated, count=1)
    updated = re.sub(r"assetName: '[^']+'", f"assetName: '{asset}'", updated, count=1)
    updated = re.sub(r"bytes: \d+", f"bytes: {facts['bytes']}", updated, count=1)
    updated = re.sub(r"sha256: '[0-9A-Fa-f]+'", f"sha256: '{facts['sha256']}'", updated, count=1)
    updated = re.sub(r"export const APP_VERSION = 'v[^']+'", f"export const APP_VERSION = '{facts['version']}'", updated)
    return updated

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="更新官网静态发布事实")
    parser.add_argument("--release-dir", required=True, type=Path)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--date", default=None, help="发布日 YYYY-MM-DD，默认取 manifest.generated_at")
    parser.add_argument("--check", action="store_true", help="只检查是否已同步，不写文件")
    args = parser.parse_args(argv)

    manifest = json.loads((args.release_dir / "manifest.json").read_text(encoding="utf-8"))
    date = args.date or str(manifest.get("generated_at", ""))[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        print(f"无法确定发布日期：{date!r}", file=sys.stderr)
        return 1

    _, facts = render(args.release_dir, args.tag, date)
    current = LINKS_TS.read_text(encoding="utf-8")
    updated = apply_to_source(current, facts)

    if args.check:
        if current == updated:
            print("OK  官网静态发布事实已同步")
            return 0
        print("官网静态发布事实尚未同步到该 Release", file=sys.stderr)
        return 1

    LINKS_TS.write_text(updated, encoding="utf-8")
    print(f"updated {LINKS_TS.relative_to(REPO_ROOT)} → {facts['tag']} / {facts['assetName']} / {facts['sha256'][:12]}…")
    return 0

if __name__ == "__main__":
    sys.exit(main())
