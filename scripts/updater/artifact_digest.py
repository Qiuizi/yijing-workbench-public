#!/usr/bin/env python3
"""Fail closed unless the downloaded archive is the uploaded artifact.

actions/download-artifact only warns on a digest mismatch. This check compares
three values and refuses to extract unless all three exist and match:

- the digest returned by the upload step
- the digest GitHub records for this exact artifact ID
- the SHA-256 of the zip downloaded from that artifact ID

It does not look up an artifact by name, and it does not accept a missing digest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater.provenance import reject_bundle_relative_path

SHA256_RE = r"^[0-9a-f]{64}$"


def normalize_sha256(value: str) -> str:
    text = (value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1]
    return text


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _zip_entry_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return mode & 0o170000 == 0o120000


def verify_archive(
    metadata: dict[str, Any],
    archive: Path,
    *,
    expected_digest: str,
    expected_artifact_id: str,
    expected_run_id: str,
    expected_head_sha: str,
) -> list[str]:
    problems: list[str] = []
    if not str(expected_artifact_id).strip():
        problems.append("Artifact ID 为空")
    if str(metadata.get("id") or "") != str(expected_artifact_id):
        problems.append("Artifact ID 与 API 记录不一致")
    workflow_run = metadata.get("workflow_run")
    if not isinstance(workflow_run, dict) or str(workflow_run.get("id") or "") != str(expected_run_id):
        problems.append("Artifact 不属于当前 Run")
    if str(workflow_run.get("head_sha") or "") != expected_head_sha if isinstance(workflow_run, dict) else True:
        problems.append("Artifact head SHA 与预期不一致")
    if metadata.get("expired") is not False:
        problems.append("Artifact 已过期或缺少 expired 字段")
    upload_digest = normalize_sha256(expected_digest)
    api_digest = normalize_sha256(str(metadata.get("digest") or ""))
    if len(upload_digest) != 64 or any(ch not in "0123456789abcdef" for ch in upload_digest):
        problems.append("上传步骤没有返回可用的 Artifact Digest")
    if len(api_digest) != 64 or any(ch not in "0123456789abcdef" for ch in api_digest):
        problems.append("GitHub API 没有返回可用的 Artifact Digest")
    if not archive.is_file():
        return problems + ["下载的 Artifact 归档不存在"]
    actual = sha256_file(archive)
    if upload_digest != api_digest or upload_digest != actual:
        problems.append("Artifact Digest 不一致")
    return problems


def extract_archive(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if info.is_dir():
                continue
            reason = reject_bundle_relative_path(info.filename)
            if reason or _zip_entry_is_symlink(info):
                raise ValueError(f"拒绝解压不安全的归档项：{info.filename}")
            target = destination / info.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(info))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验并解压精确 Artifact ID 的归档")
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--zip-path", type=Path, required=True)
    parser.add_argument("--expected-digest", required=True)
    parser.add_argument("--expected-artifact-id", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-head-sha", required=True)
    parser.add_argument("--extract-dir", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL  artifact metadata 无效：{error}", file=sys.stderr)
        return 1
    if not isinstance(metadata, dict):
        print("FAIL  artifact metadata 不是对象", file=sys.stderr)
        return 1
    problems = verify_archive(
        metadata,
        args.zip_path,
        expected_digest=args.expected_digest,
        expected_artifact_id=args.expected_artifact_id,
        expected_run_id=args.expected_run_id,
        expected_head_sha=args.expected_head_sha,
    )
    if problems:
        print("FAIL", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        return 1
    try:
        extract_archive(args.zip_path, args.extract_dir)
    except (OSError, zipfile.BadZipFile, ValueError) as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1
    print("OK  artifact digest verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
