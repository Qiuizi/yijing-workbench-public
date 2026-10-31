"""Attestation identity checks must reject a same-repo proof from the wrong workflow."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.updater.attestation_identity import (
    GITHUB_OIDC_ISSUER,
    validate_verification_payload,
    workflow_identity,
)

REPO = "Qiuizi/yijing-workbench-public"
REF = "refs/heads/main"
SOURCE = "a" * 40
WORKFLOW = "b" * 40
RUN_ID = "41169572944"
ATTEMPT = "1"


def _files(bundle: Path) -> None:
    names = [
        "PROVENANCE.md",
        "SHA256SUMS.txt",
        "latest.json",
        "manifest-rc.json",
        "manifest.json",
        "provenance.json",
        "sidecar-smoke.json",
        "yijing-workbench-3.3.2-x64-setup.exe",
        "yijing-workbench-3.3.2-x64-setup.exe.sig",
    ]
    for index, name in enumerate(names):
        (bundle / name).write_bytes(f"file-{index}".encode())


def _payload(bundle: Path, **certificate_overrides) -> list[dict]:
    subjects = []
    for path in sorted(p for p in bundle.iterdir() if p.is_file()):
        subjects.append(
            {
                "name": path.name,
                "digest": {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()},
            }
        )
    certificate = {
        "issuer": GITHUB_OIDC_ISSUER,
        "subjectAlternativeName": workflow_identity(REPO, REF),
        "sourceRepositoryDigest": SOURCE,
        "sourceRepositoryRef": REF,
        "sourceRepositoryURI": f"https://github.com/{REPO}",
        "githubWorkflowRepository": REPO,
        "githubWorkflowRef": REF,
        "githubWorkflowSHA": WORKFLOW,
        "buildSignerDigest": WORKFLOW,
        "runInvocationURI": f"https://github.com/{REPO}/actions/runs/{RUN_ID}/attempts/{ATTEMPT}",
        "runnerEnvironment": "github-hosted",
    }
    certificate.update(certificate_overrides)
    return [
        {
            "verificationResult": {
                "signature": {"certificate": certificate},
                "statement": {
                    "predicateType": "https://slsa.dev/provenance/v1",
                    "subject": subjects,
                    "predicate": {"forged": True},
                },
            }
        }
    ]


def _check(bundle: Path, payload: list[dict], **overrides) -> list[str]:
    values = dict(
        expected_repository=REPO,
        expected_ref=REF,
        expected_source_sha=SOURCE,
        expected_workflow_sha=WORKFLOW,
        expected_issuer=GITHUB_OIDC_ISSUER,
        expected_run_id=RUN_ID,
        expected_run_attempt=ATTEMPT,
    )
    values.update(overrides)
    return validate_verification_payload(payload, bundle, **values)


def test_matching_certificate_and_all_nine_subjects_pass(tmp_path):
    _files(tmp_path)
    assert _check(tmp_path, _payload(tmp_path)) == []


def test_same_repository_wrong_workflow_is_rejected(tmp_path):
    _files(tmp_path)
    payload = _payload(
        tmp_path,
        subjectAlternativeName=workflow_identity(REPO, REF, ".github/workflows/release.yml"),
    )
    assert any("workflow 身份" in item for item in _check(tmp_path, payload))


def test_wrong_source_sha_issuer_run_and_attempt_are_rejected(tmp_path):
    _files(tmp_path)
    payload = _payload(tmp_path)
    assert any("Source SHA" in item for item in _check(tmp_path, payload, expected_source_sha="c" * 40))
    assert any("OIDC issuer" in item for item in _check(tmp_path, payload, expected_issuer="https://evil.example"))
    assert any("Run ID" in item for item in _check(tmp_path, payload, expected_run_id="1"))
    assert any("Run Attempt" in item for item in _check(tmp_path, payload, expected_run_attempt="2"))
    assert any("40 位" in item for item in _check(tmp_path, payload, expected_source_sha="not-a-sha"))


def test_missing_unexpected_and_modified_subjects_are_rejected(tmp_path):
    _files(tmp_path)
    payload = _payload(tmp_path)
    payload[0]["verificationResult"]["statement"]["subject"].pop()
    assert any("缺少 subject" in item for item in _check(tmp_path, payload))

    payload = _payload(tmp_path)
    payload[0]["verificationResult"]["statement"]["subject"].append(
        {"name": "extra.bin", "digest": {"sha256": "ab" * 32}}
    )
    assert any("意外的 subject" in item for item in _check(tmp_path, payload))

    payload = _payload(tmp_path)
    payload[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = "cd" * 32
    assert any("不一致" in item for item in _check(tmp_path, payload))

    payload = _payload(tmp_path)
    payload[0]["verificationResult"]["statement"]["subject"].append(
        payload[0]["verificationResult"]["statement"]["subject"][0]
    )
    assert any("重复的 subject" in item for item in _check(tmp_path, payload))


def test_workflow_uses_exact_identity_flags_not_repo_only():
    workflow = Path(__file__).resolve().parents[2].joinpath(".github/workflows/windows-rc.yml").read_text(encoding="utf-8")
    attest = workflow.split("attest-candidate-artifact:", 1)[1]
    assert 'gh attestation verify "$installer" --repo "$GITHUB_REPOSITORY"' not in attest
    for flag in (
        "--cert-identity",
        "--source-ref",
        "--source-digest",
        "--signer-digest",
        "--cert-oidc-issuer",
        "--deny-self-hosted-runners",
        "--format json",
    ):
        assert flag in attest
    assert "attestation_identity.py" in attest
    assert "https://token.actions.githubusercontent.com" in attest
    assert 'github.event_name != \'pull_request\'' in workflow or "github.event_name != 'pull_request'" in workflow
