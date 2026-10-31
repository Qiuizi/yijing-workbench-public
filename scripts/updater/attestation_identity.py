#!/usr/bin/env python3
"""Check a `gh attestation verify --format json` result against this run.

`gh` 2.103.3 cannot combine `--cert-identity` and `--signer-workflow`.
`--cert-identity` is the exact SubjectAlternativeName, which already contains
the workflow path and ref. Run ID and Attempt are not gh flags; they are
read from the certificate's runInvocationURI, which the CLI documents as
not forgeable by the workflow.

This module does not trust statement.predicate. It does compare statement
subjects to local file hashes, because verifying one installer must not be
treated as proof of the other files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
PREDICATE_TYPE = "https://slsa.dev/provenance/v1"
WORKFLOW_PATH = ".github/workflows/windows-rc.yml"
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_BUNDLE_FILES = (
    "PROVENANCE.md",
    "SHA256SUMS.txt",
    "latest.json",
    "manifest-rc.json",
    "manifest.json",
    "provenance.json",
    "sidecar-smoke.json",
)
INSTALLER_RE = re.compile(r"^yijing-workbench-.+-x64-setup\.exe$")
RELEASE_STAGING_FILES = (
    "PROVENANCE.md",
    "SHA256SUMS.txt",
    "ci-gate.json",
    "manifest.json",
    "provenance.json",
    "sidecar-smoke.json",
)
RELEASE_SIGNED_FILES = (
    "PROVENANCE.md",
    "SHA256SUMS.txt",
    "latest.json",
    "manifest.json",
    "provenance.json",
)


class AttestationIdentityError(ValueError):
    """The attestation payload cannot be checked."""


def workflow_identity(repository: str, ref: str, workflow_path: str = WORKFLOW_PATH) -> str:
    return f"https://github.com/{repository}/{workflow_path}@{ref}"


def invocation_uri(repository: str, run_id: str, run_attempt: str) -> str:
    return f"https://github.com/{repository}/actions/runs/{run_id}/attempts/{run_attempt}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def expected_bundle_files(bundle_dir: Path) -> list[str]:
    """The candidate bundle contract: seven fixed names plus one installer and its .sig."""
    present = {path.name for path in bundle_dir.iterdir() if path.is_file()}
    installers = sorted(name for name in present if INSTALLER_RE.fullmatch(name))
    signatures = sorted(name for name in present if name.endswith(".sig") and INSTALLER_RE.fullmatch(name[: -len(".sig")]))
    expected = list(REQUIRED_BUNDLE_FILES)
    if len(installers) == 1:
        expected.append(installers[0])
    if len(signatures) == 1:
        expected.append(signatures[0])
    return sorted(expected)


def expected_files_for_profile(bundle_dir: Path, profile: str) -> list[str]:
    present = {path.name for path in bundle_dir.iterdir() if path.is_file()}
    installers = sorted(name for name in present if INSTALLER_RE.fullmatch(name))
    signatures = sorted(
        name for name in present if name.endswith(".sig") and INSTALLER_RE.fullmatch(name[: -len(".sig")])
    )
    if profile == "candidate":
        return expected_bundle_files(bundle_dir)
    if profile == "release-staging":
        expected = list(RELEASE_STAGING_FILES)
        if len(installers) == 1 and not signatures:
            expected.append(installers[0])
        return sorted(expected)
    if profile == "release-signed":
        expected = list(RELEASE_SIGNED_FILES)
        if len(installers) == 1:
            expected.append(installers[0])
        if len(signatures) == 1:
            expected.append(signatures[0])
        return sorted(expected)
    raise AttestationIdentityError(f"未知 attestation bundle profile：{profile}")


def _require_sha(value: str, label: str, problems: list[str]) -> str:
    text = (value or "").strip().lower()
    if not GIT_SHA_RE.fullmatch(text):
        problems.append(f"{label} 不是 40 位十六进制 Git SHA")
    return text


def _certificate(entry: dict[str, Any]) -> dict[str, Any] | None:
    verification = entry.get("verificationResult")
    if not isinstance(verification, dict):
        return None
    signature = verification.get("signature")
    if not isinstance(signature, dict):
        return None
    certificate = signature.get("certificate")
    if not isinstance(certificate, dict):
        return None
    return certificate


def _statement(entry: dict[str, Any]) -> dict[str, Any] | None:
    verification = entry.get("verificationResult")
    if not isinstance(verification, dict):
        return None
    statement = verification.get("statement")
    if not isinstance(statement, dict):
        return None
    return statement


def _subject_problems(statement: dict[str, Any], bundle_dir: Path, profile: str = "candidate") -> list[str]:
    problems: list[str] = []
    if statement.get("predicateType") != PREDICATE_TYPE:
        problems.append("attestation predicateType 不是 SLSA provenance v1")
    subjects = statement.get("subject")
    if not isinstance(subjects, list) or not subjects:
        return problems + ["attestation 没有 subject"]
    expected = expected_files_for_profile(bundle_dir, profile)
    actual_files = sorted(path.name for path in bundle_dir.iterdir() if path.is_file())
    required_count = {"candidate": 9, "release-staging": 7, "release-signed": 7}[profile]
    if actual_files != expected or len(expected) != required_count:
        problems.append(
            f"bundle 文件集合不是预期的 {required_count} 个交付文件：" + ", ".join(actual_files)
        )
    seen: set[str] = set()
    folded: set[str] = set()
    digests: dict[str, str] = {}
    for subject in subjects:
        if not isinstance(subject, dict):
            problems.append("subject 不是对象")
            continue
        name = subject.get("name")
        digest = subject.get("digest")
        if not isinstance(name, str) or not name or "/" in name or "\\" in name or ".." in name:
            problems.append(f"意外的 subject 名称：{name!r}")
            continue
        if name in seen or name.casefold() in folded:
            problems.append(f"重复的 subject：{name}")
        seen.add(name)
        folded.add(name.casefold())
        sha = digest.get("sha256") if isinstance(digest, dict) else None
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha.lower()):
            problems.append(f"{name} 的 subject digest 无效")
            continue
        digests[name] = sha.lower()
    missing = sorted(set(expected) - seen)
    unexpected = sorted(seen - set(expected))
    if missing:
        problems.append("缺少 subject：" + ", ".join(missing))
    if unexpected:
        problems.append("意外的 subject：" + ", ".join(unexpected))
    for name, recorded in digests.items():
        path = bundle_dir / name
        if not path.is_file() or path.is_symlink():
            problems.append(f"subject 在本地不存在或不是普通文件：{name}")
            continue
        actual = sha256_file(path)
        if actual != recorded:
            problems.append(f"{name} 的本地 SHA-256 与 attestation subject 不一致")
    return problems


def validate_verification_payload(
    payload: Any,
    bundle_dir: Path,
    *,
    expected_repository: str,
    expected_ref: str,
    expected_source_sha: str,
    expected_workflow_sha: str,
    expected_issuer: str,
    expected_run_id: str,
    expected_run_attempt: str,
    workflow_path: str = WORKFLOW_PATH,
    bundle_profile: str = "candidate",
) -> list[str]:
    problems: list[str] = []
    if not isinstance(payload, list) or not payload:
        return ["attestation JSON 不是非空数组"]
    source_sha = _require_sha(expected_source_sha, "expected source SHA", problems)
    workflow_sha = _require_sha(expected_workflow_sha, "expected workflow SHA", problems)
    if not str(expected_run_id).isdigit() or not str(expected_run_attempt).isdigit():
        problems.append("Run ID 或 Run Attempt 不是十进制数字")
    identity = workflow_identity(expected_repository, expected_ref, workflow_path)
    invocation = invocation_uri(expected_repository, str(expected_run_id), str(expected_run_attempt))
    for index, entry in enumerate(payload):
        if not isinstance(entry, dict):
            problems.append(f"attestation[{index}] 不是对象")
            continue
        certificate = _certificate(entry)
        statement = _statement(entry)
        if certificate is None or statement is None:
            problems.append(f"attestation[{index}] 缺少 certificate 或 statement")
            continue
        if certificate.get("issuer") != expected_issuer:
            problems.append("OIDC issuer 不一致")
        if certificate.get("subjectAlternativeName") != identity:
            problems.append("workflow 身份不一致")
        if certificate.get("githubWorkflowRepository") != expected_repository:
            problems.append("workflow 仓库不一致")
        if certificate.get("sourceRepositoryURI") != f"https://github.com/{expected_repository}":
            problems.append("source repository 不一致")
        if str(certificate.get("sourceRepositoryDigest") or "").lower() != source_sha:
            problems.append("Source SHA 不一致")
        if certificate.get("sourceRepositoryRef") != expected_ref:
            problems.append("source ref 不一致")
        if certificate.get("githubWorkflowRef") != expected_ref:
            problems.append("workflow ref 不一致")
        signer = str(certificate.get("githubWorkflowSHA") or "").lower()
        signer_digest = str(certificate.get("buildSignerDigest") or "").lower()
        if signer != workflow_sha or signer_digest != workflow_sha:
            problems.append("workflow SHA 不一致")
        if certificate.get("runInvocationURI") != invocation:
            problems.append("Run ID 或 Run Attempt 不一致")
        if certificate.get("runnerEnvironment") != "github-hosted":
            problems.append("runner 不是 github-hosted")
        problems.extend(_subject_problems(statement, bundle_dir, bundle_profile))
    return problems


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="校验 gh attestation verify 的 JSON 身份")
    parser.add_argument("--verification-json", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--expected-ref", required=True)
    parser.add_argument("--expected-source-sha", required=True)
    parser.add_argument("--expected-workflow-sha", required=True)
    parser.add_argument("--expected-run-id", required=True)
    parser.add_argument("--expected-run-attempt", required=True)
    parser.add_argument("--expected-issuer", default=GITHUB_OIDC_ISSUER)
    parser.add_argument("--workflow-path", default=WORKFLOW_PATH)
    parser.add_argument("--bundle-profile", default="candidate")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = json.loads(args.verification_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"FAIL  attestation JSON 无效：{error}", file=sys.stderr)
        return 1
    try:
        problems = validate_verification_payload(
            payload,
            args.bundle_dir,
            expected_repository=args.expected_repository,
            expected_ref=args.expected_ref,
            expected_source_sha=args.expected_source_sha,
            expected_workflow_sha=args.expected_workflow_sha,
            expected_issuer=args.expected_issuer,
            expected_run_id=args.expected_run_id,
            expected_run_attempt=args.expected_run_attempt,
            workflow_path=args.workflow_path,
            bundle_profile=args.bundle_profile,
        )
    except AttestationIdentityError as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1
    if problems:
        print("FAIL", file=sys.stderr)
        for item in problems:
            print(f"  - {item}", file=sys.stderr)
        return 1
    print("OK  attestation identity verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
