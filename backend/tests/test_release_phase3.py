"""Phase 3 release boundary tests. These parse the workflow and exercise the
unsigned/sign helpers. They do not trigger release.yml or read production secrets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.updater.keys import QA_PUBLIC_KEY, app_public_key
from scripts.updater.provenance import locate_bundle_file
from scripts.updater.staging_bundle import StagingError, unsigned_build_override
from scripts.updater.production_sign import SignError, assemble_signed_bundle
from backend.tests.test_release_workflow_auth import load_workflow, parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "release.yml"


def _steps(job: dict) -> list[dict]:
    return job["steps"]


def test_private_key_is_only_on_the_sign_step():
    workflow = load_workflow()
    offenders = []
    for job_name, job in workflow["jobs"].items():
        blob = json.dumps(job.get("env") or {})
        if "TAURI_SIGNING_PRIVATE_KEY" in blob:
            offenders.append(job_name)
        for step in _steps(job):
            env = json.dumps(step.get("env") or {})
            run = str(step.get("run") or "")
            if "secrets.TAURI_SIGNING_PRIVATE_KEY" in env or "secrets.TAURI_SIGNING_PRIVATE_KEY" in run:
                offenders.append(f"{job_name}/{step.get('name')}")
    assert offenders == ["production-sign/Sign the verified installer with the production key"]
    assert "environment" not in workflow["jobs"]["build"]
    assert "environment" not in workflow["jobs"]["verify-staging"]
    assert "environment" not in workflow["jobs"]["verify-signed"]
    assert "environment" not in workflow["jobs"]["publish"] or workflow["jobs"]["publish"]["environment"] == "release"
    assert workflow["jobs"]["production-sign"]["environment"] == "release"
    assert workflow["jobs"]["publish"]["permissions"] == {"contents": "write"}
    assert "contents: write" not in json.dumps(workflow["jobs"]["build"]["permissions"])


def test_default_dry_run_does_not_enter_the_signing_environment():
    inputs = load_workflow()["on"]["workflow_dispatch"]["inputs"]
    assert inputs["dry_run"]["default"] == "true"
    assert inputs["exercise_production_sign"]["default"] == "false"
    sign_if = load_workflow()["jobs"]["production-sign"]["if"]
    assert "exercise_production_sign" in sign_if
    assert "refs/heads/main" in sign_if
    publish_if = load_workflow()["jobs"]["publish"]["if"]
    assert "!inputs.dry_run" in publish_if
    assert "needs.verify-signed.result == 'success'" in publish_if


def test_unsigned_override_disables_updater_artifacts_and_rejects_qa_key():
    override = unsigned_build_override(app_public_key(REPO_ROOT))
    assert override["bundle"]["createUpdaterArtifacts"] is False
    assert override["plugins"]["updater"]["pubkey"] == app_public_key(REPO_ROOT)
    with pytest.raises(StagingError):
        unsigned_build_override(QA_PUBLIC_KEY)


def test_sign_helper_rejects_manifest_escape_before_launching_signer(tmp_path, monkeypatch):
    staging = tmp_path / "staging"
    staging.mkdir()
    (staging / "manifest.json").write_text(
        json.dumps({"installer": {"filename": "C:/Windows/win.ini"}}),
        encoding="utf-8",
    )
    signer = tmp_path / "signer.exe"
    signer.write_bytes(b"not-run")
    key = tmp_path / "key"
    key.write_text("not-a-real-key", encoding="utf-8")

    def explode(*_args, **_kwargs):
        raise AssertionError("signer was launched for an escaping path")

    monkeypatch.setattr("scripts.updater.production_sign.subprocess.run", explode)
    with pytest.raises(SignError, match="路径被拒绝"):
        assemble_signed_bundle(
            staging,
            tmp_path / "out",
            signer=signer,
            key_file=key,
            version="3.3.2",
            tag="v3.3.2",
            notes="notes",
            repo="Qiuizi/yijing-workbench-public",
            source_sha="a" * 40,
            source_ref="refs/heads/main",
            workflow_run="https://example.test/run",
            staging_artifact_id="1",
            staging_artifact_digest="sha256:" + "ab" * 32,
            expected_installer_sha256="ab" * 32,
        )
    located, error = locate_bundle_file(staging, "C:/Windows/win.ini")
    assert located is None and error


def test_workflow_still_parses_after_phase3_split():
    document = parse_workflow(WORKFLOW.read_text(encoding="utf-8"))
    assert document["jobs"]["build"]["permissions"]["contents"] == "read"
    assert "gh release create" not in "\n".join(
        str(step.get("run") or "") for step in document["jobs"]["build"]["steps"]
    )
