#!/usr/bin/env python3
"""候选构建产物的来源证明。

provenance.json 在上传前最后写入，列出同目录里除自身以外的每个文件的
大小和 SHA-256。它不包含自己的哈希，避免循环引用。Artifact ID 和
Artifact Digest 由 GitHub 在上传时分配，不能写进这份文件里再上传；
验证方用上传步骤的输出和 Artifacts API 对照它们。

这不是 GitHub Artifact Attestation。三者要分开看：
- provenance.json：本仓库计算的文件清单和构建上下文
- artifact digest：GitHub 对上传归档计算的摘要
- attestation：GitHub OIDC 对文件摘要的签名来源证明
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater.keys import app_public_key, describe_public_key, is_qa_key
from scripts.updater.manifest import public_key_key_id, read_signature, signature_key_id
from scripts.updater.verify_release import run_signature_verifier

REPO_ROOT = _REPO_ROOT
SCHEMA_VERSION = 1
PROVENANCE_FILENAME = "provenance.json"
SIGNING_MODES = frozenset({"ephemeral_candidate", "production"})
SHA256_RE = r"^[0-9a-f]{64}$"
SHA_RE = r"^[0-9a-f]{40}$"
FORBIDDEN_TEXT = (
    "TAURI_SIGNING_PRIVATE_KEY",
    "PRIVATE KEY",
    "minisign encrypted secret key",
    "BEGIN OPENSSH PRIVATE KEY",
    "GH_TOKEN",
    "github_pat_",
)


class ProvenanceError(ValueError):
    """来源证明无法生成或无法通过校验。"""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_sha256(value: str) -> str:
    text = (value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1]
    return text


def _reject_secret_material(value: str, label: str) -> None:
    lowered = value.lower()
    for marker in FORBIDDEN_TEXT:
        if marker.lower() in lowered:
            raise ProvenanceError(f"{label} 含有敏感材料，拒绝写入来源证明")


def _require_public_key(pubkey: str) -> dict[str, object]:
    _reject_secret_material(pubkey, "updater 公钥")
    info = describe_public_key(pubkey)
    if not info.get("valid"):
        raise ProvenanceError("updater 公钥不是有效的 minisign 公钥")
    if is_qa_key(pubkey):
        raise ProvenanceError("来源证明拒绝 QA 测试公钥")
    comment = ""
    try:
        import base64

        comment = base64.b64decode("".join(pubkey.split())).decode("utf-8", errors="replace")
    except ValueError:
        comment = ""
    if "secret key" in comment.lower():
        raise ProvenanceError("updater 公钥字段里出现了私钥注释")
    return info


def collect_files(bundle_dir: Path) -> list[dict[str, object]]:
    """哈希 bundle 目录中除 provenance.json 以外的全部文件。"""
    if not bundle_dir.is_dir():
        raise ProvenanceError(f"产物目录不存在：{bundle_dir}")
    records: list[dict[str, object]] = []
    for path in sorted(p for p in bundle_dir.rglob("*") if p.is_file()):
        relative = path.relative_to(bundle_dir).as_posix()
        if relative == PROVENANCE_FILENAME:
            continue
        records.append(
            {
                "name": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if not records:
        raise ProvenanceError("产物目录里没有可证明的文件")
    return records


def build_provenance(
    bundle_dir: Path,
    *,
    repository: str,
    version: str,
    source_sha: str,
    workflow_ref: str,
    workflow_sha: str,
    run_id: str,
    run_attempt: str,
    event_name: str,
    runner_os: str,
    python_version: str,
    node_version: str,
    rust_version: str,
    vc143_dir: str,
    signing_mode: str,
    updater_pubkey: str,
    artifact_name: str,
    build_target: str = "windows-x64",
) -> dict[str, Any]:
    """根据磁盘上的真实文件生成来源证明。不读取环境变量，避免把密钥扫进去。"""
    for label, value in (
        ("repository", repository),
        ("version", version),
        ("source_sha", source_sha),
        ("workflow_ref", workflow_ref),
        ("workflow_sha", workflow_sha),
        ("run_id", run_id),
        ("run_attempt", run_attempt),
        ("event_name", event_name),
        ("runner_os", runner_os),
        ("python_version", python_version),
        ("node_version", node_version),
        ("rust_version", rust_version),
        ("vc143_dir", vc143_dir),
        ("artifact_name", artifact_name),
    ):
        if not str(value).strip():
            raise ProvenanceError(f"缺少 {label}")
        _reject_secret_material(str(value), label)
    if signing_mode not in SIGNING_MODES:
        raise ProvenanceError(f"未知签名模式：{signing_mode}")
    info = _require_public_key(updater_pubkey)
    key_id = str(info.get("key_id") or "")
    repo_key_id = public_key_key_id(app_public_key(REPO_ROOT))
    if signing_mode == "ephemeral_candidate" and key_id == repo_key_id:
        raise ProvenanceError("候选构建不能使用仓库内置的正式公钥对应的钥匙")
    if signing_mode == "production" and repo_key_id and key_id != repo_key_id:
        raise ProvenanceError("正式签名模式的公钥与仓库内置正式公钥不一致")
    document = {
        "schema_version": SCHEMA_VERSION,
        "repository": repository,
        "version": version,
        "source_sha": source_sha.strip().lower(),
        "workflow_ref": workflow_ref,
        "workflow_sha": workflow_sha.strip().lower(),
        "run_id": str(run_id),
        "run_attempt": str(run_attempt),
        "event_name": event_name,
        "runner_os": runner_os,
        "build_target": build_target,
        "toolchain": {
            "python": python_version,
            "node": node_version,
            "rust": rust_version,
            "vc143": vc143_dir,
        },
        "signing_mode": signing_mode,
        "updater_pubkey_key_id": key_id,
        "updater_pubkey": "".join(updater_pubkey.split()),
        "artifact_name": artifact_name,
        "files": collect_files(bundle_dir),
    }
    encoded = json.dumps(document, ensure_ascii=False)
    _reject_secret_material(encoded, "provenance")
    return document


def write_provenance(bundle_dir: Path, document: dict[str, Any]) -> Path:
    target = bundle_dir / PROVENANCE_FILENAME
    if target.exists():
        raise ProvenanceError("provenance.json 已存在，拒绝覆盖已生成的来源证明")
    target.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def find_bundle_dir(root: Path) -> Path:
    if (root / PROVENANCE_FILENAME).is_file():
        return root
    matches = sorted(path.parent for path in root.rglob(PROVENANCE_FILENAME) if path.is_file())
    if len(matches) != 1:
        raise ProvenanceError(f"应有且仅有一份 provenance.json，实际 {len(matches)} 份")
    return matches[0]


def _problems_for_files(bundle_dir: Path, listed: list[dict[str, Any]]) -> list[str]:
    problems: list[str] = []
    if not isinstance(listed, list) or not listed:
        return ["files 必须是非空数组"]
    seen: set[str] = set()
    listed_names: set[str] = set()
    for item in listed:
        if not isinstance(item, dict):
            problems.append("files 项必须是对象")
            continue
        name = item.get("name")
        size = item.get("size_bytes")
        digest = item.get("sha256")
        if not isinstance(name, str) or not name or name == PROVENANCE_FILENAME or ".." in Path(name).parts:
            problems.append(f"非法文件名：{name!r}")
            continue
        if name in seen:
            problems.append(f"文件重复列出：{name}")
        seen.add(name)
        listed_names.add(name)
        path = bundle_dir / name
        if not path.is_file():
            problems.append(f"清单引用了不存在的文件：{name}")
            continue
        if not isinstance(size, int) or isinstance(size, bool):
            problems.append(f"{name} 的 size_bytes 不是整数")
        elif path.stat().st_size != size:
            problems.append(f"{name} 文件大小不一致：实际 {path.stat().st_size}，清单 {size}")
        if not isinstance(digest, str) or len(normalize_sha256(digest)) != 64:
            problems.append(f"{name} 的 sha256 格式无效")
        elif sha256_file(path) != normalize_sha256(digest):
            problems.append(f"{name} 的 SHA-256 与清单不一致")
    actual = {
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != PROVENANCE_FILENAME
    }
    missing = sorted(actual - listed_names)
    if missing:
        problems.append("目录中有未列入来源证明的文件：" + ", ".join(missing))
    return problems


def _check_manifest_and_sums(bundle_dir: Path, document: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    manifest_path = bundle_dir / "manifest.json"
    sums_path = bundle_dir / "SHA256SUMS.txt"
    if not manifest_path.is_file():
        return ["缺少 manifest.json"]
    if not sums_path.is_file():
        problems.append("缺少 SHA256SUMS.txt")
    try:
        manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"manifest.json 不是合法 JSON：{error}"]
    installer = manifest_doc.get("installer") if isinstance(manifest_doc, dict) else None
    if not isinstance(installer, dict):
        return problems + ["manifest.json 没有 installer 对象"]
    filename = installer.get("filename")
    if not isinstance(filename, str) or not (bundle_dir / filename).is_file():
        problems.append(f"manifest 引用了不存在的安装包：{filename!r}")
        return problems
    actual_size = (bundle_dir / filename).stat().st_size
    actual_hash = sha256_file(bundle_dir / filename)
    if installer.get("bytes") != actual_size:
        problems.append("manifest 安装包大小与文件不一致")
    recorded = str(installer.get("sha256") or "")
    if normalize_sha256(recorded) != actual_hash:
        problems.append("manifest 安装包 SHA-256 与文件不一致")
    if manifest_doc.get("version") != document.get("version"):
        problems.append("manifest 版本与来源证明不一致")
    if str(manifest_doc.get("source_sha") or "").lower() != str(document.get("source_sha") or ""):
        problems.append("manifest source_sha 与来源证明不一致")
    signature_name = manifest_doc.get("signature_file")
    if not isinstance(signature_name, str) or not (bundle_dir / signature_name).is_file():
        problems.append(f"manifest 引用了不存在的签名文件：{signature_name!r}")
    if sums_path.is_file():
        lines = [line.split() for line in sums_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        recorded_sums = {parts[-1]: parts[0] for parts in lines if len(parts) >= 2}
        if normalize_sha256(recorded_sums.get(filename, "")) != actual_hash:
            problems.append("SHA256SUMS.txt 与安装包实际哈希不一致")
    return problems


def _check_signature(
    bundle_dir: Path,
    document: dict[str, Any],
    signature_verifier: Path | None,
) -> list[str]:
    problems: list[str] = []
    pubkey = str(document.get("updater_pubkey") or "")
    info = describe_public_key(pubkey)
    if not info.get("valid"):
        return ["来源证明里的 updater 公钥无效"]
    if str(document.get("updater_pubkey_key_id") or "") != info.get("key_id"):
        problems.append("updater_pubkey_key_id 与公钥不一致")
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        return problems
    manifest_doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    signature_name = str(manifest_doc.get("signature_file") or "")
    signature_path = bundle_dir / signature_name
    if not signature_path.is_file():
        return problems
    signature = read_signature(signature_path)
    sig_key = signature_key_id(signature)
    if not sig_key or sig_key != info.get("key_id"):
        problems.append(f"签名无效：签名 key id {sig_key or '缺失'} 与公钥 {info.get('key_id')} 不一致")
        return problems
    if signature_verifier is not None:
        installer_name = manifest_doc.get("installer", {}).get("filename")
        installer = bundle_dir / str(installer_name)
        problems.extend(run_signature_verifier(signature_verifier, installer, signature, pubkey))
    return problems


def validate_provenance(
    document: dict[str, Any],
    bundle_dir: Path,
    *,
    expected_repository: str,
    expected_source_sha: str,
    expected_run_id: str,
    expected_run_attempt: str,
    expected_event_name: str,
    expected_signing_mode: str,
    expected_version: str | None = None,
    expected_artifact_id: str | None = None,
    observed_artifact_id: str | None = None,
    expected_artifact_digest: str | None = None,
    observed_artifact_digest: str | None = None,
    observed_artifact_name: str | None = None,
    signature_verifier: Path | None = None,
) -> list[str]:
    """返回全部不一致项。空列表表示这份已下载产物与声明的上下文一致。"""
    problems: list[str] = []
    if not isinstance(document, dict):
        return ["provenance 不是 JSON 对象"]
    required = (
        "schema_version",
        "repository",
        "version",
        "source_sha",
        "workflow_ref",
        "workflow_sha",
        "run_id",
        "run_attempt",
        "event_name",
        "runner_os",
        "build_target",
        "toolchain",
        "signing_mode",
        "updater_pubkey_key_id",
        "updater_pubkey",
        "artifact_name",
        "files",
    )
    for field in required:
        if field not in document:
            problems.append(f"provenance 缺少必需字段：{field}")
    if problems:
        return problems
    if document.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version 必须是 {SCHEMA_VERSION}")
    if "artifact_id" in document or "artifact_digest" in document:
        problems.append("provenance.json 不能包含上传后才知道的 artifact_id 或 artifact_digest")
    encoded = json.dumps(document, ensure_ascii=False)
    for marker in FORBIDDEN_TEXT:
        if marker.lower() in encoded.lower():
            problems.append("provenance 含有敏感材料")
            break
    if document.get("repository") != expected_repository:
        problems.append("repository 不一致")
    if str(document.get("source_sha") or "").lower() != expected_source_sha.strip().lower():
        problems.append("Source SHA 不一致")
    if str(document.get("run_id")) != str(expected_run_id):
        problems.append("Run ID 不一致")
    if str(document.get("run_attempt")) != str(expected_run_attempt):
        problems.append("Run Attempt 不一致")
    if document.get("event_name") != expected_event_name:
        problems.append("event_name 不一致")
    if document.get("signing_mode") != expected_signing_mode:
        problems.append("签名模式不一致")
    if expected_version is not None and document.get("version") != expected_version:
        problems.append("版本号不一致")
    toolchain = document.get("toolchain")
    if not isinstance(toolchain, dict) or not all(toolchain.get(key) for key in ("python", "node", "rust", "vc143")):
        problems.append("toolchain 缺少 python、node、rust 或 vc143")
    problems.extend(_problems_for_files(bundle_dir, document.get("files")))
    problems.extend(_check_manifest_and_sums(bundle_dir, document))
    problems.extend(_check_signature(bundle_dir, document, signature_verifier))
    if expected_artifact_id is not None or observed_artifact_id is not None:
        if str(expected_artifact_id or "") != str(observed_artifact_id or ""):
            problems.append("Artifact ID 不一致")
    if expected_artifact_digest is not None or observed_artifact_digest is not None:
        if normalize_sha256(expected_artifact_digest or "") != normalize_sha256(observed_artifact_digest or ""):
            problems.append("Artifact Digest 不一致")
        if len(normalize_sha256(expected_artifact_digest or "")) != 64:
            problems.append("Artifact Digest 格式无效")
    if observed_artifact_name is not None and observed_artifact_name != document.get("artifact_name"):
        problems.append("Artifact 名称与来源证明不一致")
    return problems


def load_provenance(bundle_dir: Path) -> tuple[Path, dict[str, Any]]:
    root = find_bundle_dir(bundle_dir)
    path = root / PROVENANCE_FILENAME
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ProvenanceError(f"provenance JSON 无效：{error}") from error
    if not isinstance(data, dict):
        raise ProvenanceError("provenance JSON 无效：顶层不是对象")
    return root, data


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="生成或校验候选构建来源证明")
    sub = parser.add_subparsers(dest="command", required=True)
    write = sub.add_parser("write")
    write.add_argument("--bundle-dir", type=Path, required=True)
    for name in (
        "--repository",
        "--version",
        "--source-sha",
        "--workflow-ref",
        "--workflow-sha",
        "--run-id",
        "--run-attempt",
        "--event-name",
        "--runner-os",
        "--python-version",
        "--node-version",
        "--rust-version",
        "--vc143-dir",
        "--signing-mode",
        "--updater-pubkey",
        "--artifact-name",
    ):
        write.add_argument(name, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--bundle-dir", type=Path, required=True)
    verify.add_argument("--expected-repository", required=True)
    verify.add_argument("--expected-source-sha", required=True)
    verify.add_argument("--expected-run-id", required=True)
    verify.add_argument("--expected-run-attempt", required=True)
    verify.add_argument("--expected-event-name", required=True)
    verify.add_argument("--expected-signing-mode", required=True)
    verify.add_argument("--expected-version", default=None)
    verify.add_argument("--expected-artifact-id", default=None)
    verify.add_argument("--observed-artifact-id", default=None)
    verify.add_argument("--expected-artifact-digest", default=None)
    verify.add_argument("--observed-artifact-digest", default=None)
    verify.add_argument("--observed-artifact-name", default=None)
    verify.add_argument("--signature-verifier", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "write":
            document = build_provenance(
                args.bundle_dir,
                repository=args.repository,
                version=args.version,
                source_sha=args.source_sha,
                workflow_ref=args.workflow_ref,
                workflow_sha=args.workflow_sha,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                event_name=args.event_name,
                runner_os=args.runner_os,
                python_version=args.python_version,
                node_version=args.node_version,
                rust_version=args.rust_version,
                vc143_dir=args.vc143_dir,
                signing_mode=args.signing_mode,
                updater_pubkey=args.updater_pubkey,
                artifact_name=args.artifact_name,
            )
            path = write_provenance(args.bundle_dir, document)
            print(f"wrote {path} files={len(document['files'])} key_id={document['updater_pubkey_key_id']}")
            return 0
        root, document = load_provenance(args.bundle_dir)
        problems = validate_provenance(
            document,
            root,
            expected_repository=args.expected_repository,
            expected_source_sha=args.expected_source_sha,
            expected_run_id=args.expected_run_id,
            expected_run_attempt=args.expected_run_attempt,
            expected_event_name=args.expected_event_name,
            expected_signing_mode=args.expected_signing_mode,
            expected_version=args.expected_version,
            expected_artifact_id=args.expected_artifact_id,
            observed_artifact_id=args.observed_artifact_id,
            expected_artifact_digest=args.expected_artifact_digest,
            observed_artifact_digest=args.observed_artifact_digest,
            observed_artifact_name=args.observed_artifact_name,
            signature_verifier=args.signature_verifier,
        )
    except ProvenanceError as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1
    if problems:
        print("FAIL", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("OK  provenance verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
