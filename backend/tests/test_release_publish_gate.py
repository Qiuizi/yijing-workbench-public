"""Publish 门禁的条件行为测试。

表达式从 release.yml 读出后按 GitHub Actions 的 && / || / ! / == 求值，
不是只检查字符串里有没有某个单词。
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from scripts.updater.artifact_digest import verify_archive
from scripts.updater.attestation_identity import (
    GITHUB_OIDC_ISSUER,
    validate_verification_payload,
    workflow_identity,
)
from scripts.updater.production_sign import SignError, verify_signed_chain
from backend.tests.test_release_workflow_auth import load_workflow

PUBLISH_IF = (
    "${{ !cancelled() && !inputs.dry_run && needs.build.result == 'success' "
    "&& needs.production-sign.result == 'success' && needs.verify-signed.result == 'success' "
    "&& needs.attest-signed.result == 'success' }}"
)
STATUS_FUNCTIONS = ("success()", "always()", "cancelled()", "failure()")


class ExprError(ValueError):
    pass


def _strip(expression: str) -> str:
    text = expression.strip()
    if text.startswith("${{") and text.endswith("}}"):
        text = text[3:-2].strip()
    return text


def _lookup(token: str, inputs: dict, needs: dict):
    if token.startswith("inputs."):
        name = token[len("inputs.") :]
        if name not in inputs:
            raise ExprError(f"missing input {name}")
        return inputs[name]
    if token.startswith("needs.") and token.endswith(".result"):
        job = token[len("needs.") : -len(".result")]
        return needs.get(job, "missing")
    raise ExprError(f"unknown path {token}")


def evaluate_github_bool(expression: str, *, inputs: dict, needs: dict, cancelled: bool) -> bool:
    text = _strip(expression)
    pos = 0

    def skip() -> None:
        nonlocal pos
        while pos < len(text) and text[pos].isspace():
            pos += 1

    def parse_or() -> bool:
        nonlocal pos
        left = parse_and()
        while True:
            skip()
            if text.startswith("||", pos):
                pos += 2
                right = parse_and()
                left = left or right
            else:
                return left

    def parse_and() -> bool:
        nonlocal pos
        left = parse_not()
        while True:
            skip()
            if text.startswith("&&", pos):
                pos += 2
                right = parse_not()
                left = left and right
            else:
                return left

    def parse_not() -> bool:
        nonlocal pos
        skip()
        if text.startswith("!", pos) and not text.startswith("!=", pos):
            pos += 1
            return not parse_not()
        return parse_primary()

    def parse_primary() -> bool:
        nonlocal pos
        skip()
        if text.startswith("(", pos):
            pos += 1
            value = parse_or()
            skip()
            if not text.startswith(")", pos):
                raise ExprError("missing )")
            pos += 1
            return value
        match = re.match(r"[A-Za-z0-9_.-]+", text[pos:])
        if not match:
            raise ExprError(f"bad token at {text[pos:pos + 20]!r}")
        token = match.group(0)
        pos += len(token)
        skip()
        if text.startswith("(", pos):
            pos += 1
            skip()
            if not text.startswith(")", pos):
                raise ExprError("only zero-arg calls are supported")
            pos += 1
            if token == "cancelled":
                return cancelled
            raise ExprError(f"unknown call {token}")
        if text.startswith("==", pos) or text.startswith("!=", pos):
            negate = text.startswith("!=", pos)
            pos += 2
            skip()
            if text.startswith("'", pos):
                end = text.find("'", pos + 1)
                literal = text[pos + 1 : end]
                pos = end + 1
            elif text.startswith("true", pos) and not text[pos + 4 : pos + 5].isalnum():
                literal = True
                pos += 4
            elif text.startswith("false", pos) and not text[pos + 5 : pos + 6].isalnum():
                literal = False
                pos += 5
            else:
                raise ExprError("expected literal")
            actual = _lookup(token, inputs, needs)
            return (actual != literal) if negate else (actual == literal)
        value = _lookup(token, inputs, needs)
        if isinstance(value, bool):
            return value
        raise ExprError(f"non-bool {token}")

    result = parse_or()
    skip()
    if pos != len(text):
        raise ExprError(f"trailing {text[pos:]!r}")
    return result


def publish_job_starts(expression: str, *, dry_run: bool, needs: dict[str, str], cancelled: bool = False) -> bool:
    text = _strip(expression)
    if not any(name in text for name in STATUS_FUNCTIONS):
        raise ExprError("publish if 没有状态函数，依赖失败时 GitHub 不会计算显式结果比较")
    if "always()" in text:
        raise ExprError("publish if 不能使用 always()")
    return evaluate_github_bool(
        expression,
        inputs={"dry_run": dry_run},
        needs=needs,
        cancelled=cancelled,
    )


def _success_needs() -> dict[str, str]:
    return {
        "build": "success",
        "production-sign": "success",
        "verify-signed": "success",
        "attest-signed": "success",
    }


def _publish_if() -> str:
    workflow = load_workflow()
    expression = workflow["jobs"]["publish"]["if"]
    assert expression == PUBLISH_IF
    return expression


def test_publish_starts_only_when_attestation_succeeded():
    expression = _publish_if()
    assert publish_job_starts(expression, dry_run=False, needs=_success_needs()) is True
    assert publish_job_starts(expression, dry_run=True, needs=_success_needs()) is False


@pytest.mark.parametrize("result", ["failure", "skipped", "cancelled", "missing"])
def test_publish_does_not_start_when_attestation_is_not_success(result: str):
    needs = _success_needs()
    if result == "missing":
        del needs["attest-signed"]
    else:
        needs["attest-signed"] = result
    assert publish_job_starts(_publish_if(), dry_run=False, needs=needs) is False


def test_cancelled_workflow_does_not_start_publish():
    assert publish_job_starts(_publish_if(), dry_run=False, needs=_success_needs(), cancelled=True) is False


def test_sibling_failure_does_not_start_publish():
    for job in ("build", "production-sign", "verify-signed"):
        needs = _success_needs()
        needs[job] = "failure"
        assert publish_job_starts(_publish_if(), dry_run=False, needs=needs) is False


def test_publish_writes_happen_after_identity_recheck_and_do_not_push_main():
    job = load_workflow()["jobs"]["publish"]
    names = [step.get("name") for step in job["steps"]]
    recheck = names.index("Re-check provenance, signature binding, and attestation identity")
    create = names.index("Create draft release and upload assets")
    site = names.index("Open a pull request for website release facts")
    publish = names.index("Publish the release (irreversible; latest.json enters the update channel)")
    assert recheck < create < site < publish
    runs = "\n".join(str(step.get("run") or "") for step in job["steps"])
    assert "HEAD:main" not in runs
    assert "git push origin HEAD:main" not in runs
    assert "refs/heads/$branch" in runs
    assert "gh pr create" in runs
    assert '"gh", "release", "view"' in runs
    assert "assets,isDraft,tagName" in runs
    assert "releases/tags/" not in runs
    assert "attestation_identity.py" in runs
    assert "--bundle-profile release-signed" in runs
    assert "--workflow-path .github/workflows/release.yml" in runs
    assert "secrets.TAURI_SIGNING_PRIVATE_KEY" not in runs
    signed_upload = next(
        step for step in load_workflow()["jobs"]["production-sign"]["steps"] if step.get("id") == "upload-signed"
    )
    assert signed_upload["with"]["retention-days"] == "${{ inputs.dry_run && 1 || 14 }}"


def test_wrong_artifact_digest_is_rejected_by_the_publish_checker(tmp_path: Path):
    archive = tmp_path / "artifact.zip"
    archive.write_bytes(b"not-the-expected-bytes")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    metadata = {
        "id": 42,
        "digest": f"sha256:{digest}",
        "expired": False,
        "workflow_run": {"id": 7, "head_sha": "a" * 40},
    }
    assert verify_archive(
        metadata,
        archive,
        expected_digest=digest,
        expected_artifact_id="42",
        expected_run_id="7",
        expected_head_sha="a" * 40,
    ) == []
    assert "Artifact ID 与 API 记录不一致" in verify_archive(
        metadata,
        archive,
        expected_digest=digest,
        expected_artifact_id="99",
        expected_run_id="7",
        expected_head_sha="a" * 40,
    )
    assert "Artifact Digest 不一致" in verify_archive(
        metadata,
        archive,
        expected_digest="b" * 64,
        expected_artifact_id="42",
        expected_run_id="7",
        expected_head_sha="a" * 40,
    )


def test_wrong_installer_sha256_is_rejected_before_signature_use(tmp_path: Path):
    signed = tmp_path / "signed"
    signed.mkdir()
    installer = signed / "yijing-workbench-3.3.2-x64-setup.exe"
    installer.write_bytes(b"installer-bytes")
    actual = hashlib.sha256(installer.read_bytes()).hexdigest()
    (signed / "manifest.json").write_text(
        '{"installer":{"filename":"yijing-workbench-3.3.2-x64-setup.exe"},'
        f'"staging_installer_sha256":"{actual}","version":"3.3.2",'
        '"source_sha":"' + "a" * 40 + '","staging_artifact_id":"9",'
        '"installer_bytes_unchanged":true,"signature_file":"missing.sig"}',
        encoding="utf-8",
    )
    with pytest.raises(SignError, match="SHA-256"):
        verify_signed_chain(
            signed,
            expected_version="3.3.2",
            expected_installer_sha256="c" * 64,
            expected_staging_artifact_id="9",
            expected_source_sha="a" * 40,
        )


def test_wrong_attestation_workflow_identity_is_rejected(tmp_path: Path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    names = [
        "PROVENANCE.md",
        "SHA256SUMS.txt",
        "latest.json",
        "manifest.json",
        "provenance.json",
        "yijing-workbench-3.3.2-x64-setup.exe",
        "yijing-workbench-3.3.2-x64-setup.exe.sig",
    ]
    for index, name in enumerate(names):
        (bundle / name).write_bytes(f"file-{index}".encode())
    subjects = [
        {"name": path.name, "digest": {"sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}
        for path in sorted(bundle.iterdir())
    ]
    source = "d" * 40
    workflow_sha = "e" * 40
    certificate = {
        "issuer": GITHUB_OIDC_ISSUER,
        "subjectAlternativeName": workflow_identity( "Qiuizi/yijing-workbench-public", "refs/heads/main", ".github/workflows/windows-rc.yml"),
        "sourceRepositoryDigest": source,
        "sourceRepositoryRef": "refs/heads/main",
        "sourceRepositoryURI": "https://github.com/Qiuizi/yijing-workbench-public",
        "githubWorkflowRepository": "Qiuizi/yijing-workbench-public",
        "githubWorkflowRef": "refs/heads/main",
        "githubWorkflowSHA": workflow_sha,
        "buildSignerDigest": workflow_sha,
        "runInvocationURI": "https://github.com/Qiuizi/yijing-workbench-public/actions/runs/8/attempts/1",
        "runnerEnvironment": "github-hosted",
    }
    payload = [{
        "verificationResult": {
            "signature": {"certificate": certificate},
            "statement": {
                "predicateType": "https://slsa.dev/provenance/v1",
                "subject": subjects,
                "predicate": {"forged": True},
            },
        }
    }]
    problems = validate_verification_payload(
        payload,
        bundle,
        expected_repository="Qiuizi/yijing-workbench-public",
        expected_ref="refs/heads/main",
        expected_source_sha=source,
        expected_workflow_sha=workflow_sha,
        expected_issuer=GITHUB_OIDC_ISSUER,
        expected_run_id="8",
        expected_run_attempt="1",
        workflow_path=".github/workflows/release.yml",
        bundle_profile="release-signed",
    )
    assert any("workflow 身份不一致" in item for item in problems)
    certificate["subjectAlternativeName"] = workflow_identity(
        "Qiuizi/yijing-workbench-public", "refs/heads/main", ".github/workflows/release.yml"
    )
    assert validate_verification_payload(
        payload,
        bundle,
        expected_repository="Qiuizi/yijing-workbench-public",
        expected_ref="refs/heads/main",
        expected_source_sha=source,
        expected_workflow_sha=workflow_sha,
        expected_issuer=GITHUB_OIDC_ISSUER,
        expected_run_id="8",
        expected_run_attempt="1",
        workflow_path=".github/workflows/release.yml",
        bundle_profile="release-signed",
    ) == []
