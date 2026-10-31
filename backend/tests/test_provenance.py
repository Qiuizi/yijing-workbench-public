"""来源证明的反向测试：不一致的产物必须失败，不能只测正常路径。"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from scripts.updater.keys import QA_PUBLIC_KEY
from scripts.updater.manifest import public_key_key_id
from scripts.updater.provenance import (
    PROVENANCE_FILENAME,
    ProvenanceError,
    build_provenance,
    load_provenance,
    validate_provenance,
    write_provenance,
)
from backend.tests.test_release_workflow_auth import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "windows-rc.yml"
_KEY_ID = bytes.fromhex("1122334455667788")
_OTHER_KEY_ID = bytes.fromhex("99aabbccddeeff00")


def _pubkey(key_id: bytes = _KEY_ID) -> str:
    payload = b"Ed" + key_id + bytes(range(32))
    text = "untrusted comment: minisign public key: TEST\n" + base64.b64encode(payload).decode() + "\n"
    return base64.b64encode(text.encode()).decode()


def _signature(key_id: bytes = _KEY_ID) -> str:
    line = base64.b64encode(b"Ed" + key_id + bytes(64)).decode()
    text = (
        "untrusted comment: signature from tauri secret key\n"
        f"{line}\n"
        "trusted comment: timestamp:1793081026\tfile:test-setup.exe\n"
        f"{line}\n"
    )
    return base64.b64encode(text.encode()).decode()


def _context() -> dict[str, str]:
    return {
        "repository": "Qiuizi/yijing-workbench-public",
        "version": "3.3.2",
        "source_sha": "a" * 40,
        "workflow_ref": "Qiuizi/yijing-workbench-public/.github/workflows/windows-rc.yml@refs/heads/main",
        "workflow_sha": "b" * 40,
        "run_id": "41165588895",
        "run_attempt": "1",
        "event_name": "push",
        "runner_os": "Windows",
        "python_version": "3.12.7",
        "node_version": "24.11.0",
        "rust_version": "rustc 1.98.1 (test)",
        "vc143_dir": r"C:\runner\VC\Redist\MSVC\14.44.35112\x64\Microsoft.VC143.CRT",
        "signing_mode": "ephemeral_candidate",
        "updater_pubkey": _pubkey(),
        "artifact_name": "yijing-workbench-3.3.2-windows-x64-rc",
    }


def _write_bundle(root: Path, installer: bytes = b"installer-bytes") -> tuple[Path, dict]:
    bundle = root / "bundle"
    bundle.mkdir(parents=True)
    filename = "yijing-workbench-3.3.2-x64-setup.exe"
    (bundle / filename).write_bytes(installer)
    (bundle / f"{filename}.sig").write_text(_signature() + "\n", encoding="utf-8")
    digest = __import__("hashlib").sha256(installer).hexdigest().upper()
    (bundle / "SHA256SUMS.txt").write_text(f"{digest}  {filename}\n", encoding="utf-8")
    manifest = {
        "version": "3.3.2",
        "source_sha": "a" * 40,
        "signature_file": f"{filename}.sig",
        "installer": {"filename": filename, "bytes": len(installer), "sha256": digest},
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (bundle / "latest.json").write_text("{}\n", encoding="utf-8")
    (bundle / "PROVENANCE.md").write_text("human provenance\n", encoding="utf-8")
    document = build_provenance(bundle, **_context())
    write_provenance(bundle, document)
    return bundle, document


def _expect(bundle: Path, **overrides):
    context = _context()
    document = json.loads((bundle / PROVENANCE_FILENAME).read_text(encoding="utf-8"))
    values = dict(
        expected_repository=context["repository"],
        expected_source_sha=context["source_sha"],
        expected_run_id=context["run_id"],
        expected_run_attempt=context["run_attempt"],
        expected_event_name=context["event_name"],
        expected_signing_mode=context["signing_mode"],
        expected_version=context["version"],
        expected_artifact_id="13029132070",
        observed_artifact_id="13029132070",
        expected_artifact_digest="sha256:" + "ab" * 32,
        observed_artifact_digest="ab" * 32,
        observed_artifact_name=context["artifact_name"],
    )
    values.update(overrides)
    return validate_provenance(document, bundle, **values)


def test_valid_bundle_has_no_self_hash_and_distinguishes_runs(tmp_path):
    bundle, document = _write_bundle(tmp_path)
    assert document["schema_version"] == 1
    assert PROVENANCE_FILENAME not in {item["name"] for item in document["files"]}
    assert "artifact_id" not in document
    assert _expect(bundle) == []
    other = build_provenance(bundle, **{**_context(), "run_id": "999"})
    assert other["run_id"] != document["run_id"]
    assert other["version"] == document["version"]


def test_tampered_installer_byte_fails(tmp_path):
    bundle, _ = _write_bundle(tmp_path)
    installer = next(bundle.glob("*.exe"))
    installer.write_bytes(installer.read_bytes() + b"\x00")
    problems = _expect(bundle)
    assert any("SHA-256" in item for item in problems)


def test_tampered_sha256sums_fails_even_if_file_hash_is_updated(tmp_path):
    bundle, document = _write_bundle(tmp_path)
    sums = bundle / "SHA256SUMS.txt"
    sums.write_text("aa" * 32 + "  yijing-workbench-3.3.2-x64-setup.exe\n", encoding="utf-8")
    for item in document["files"]:
        if item["name"] == "SHA256SUMS.txt":
            item["sha256"] = __import__("hashlib").sha256(sums.read_bytes()).hexdigest()
            item["size_bytes"] = sums.stat().st_size
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    problems = _expect(bundle)
    assert any("SHA256SUMS.txt" in item for item in problems)


def test_manifest_missing_file_fails(tmp_path):
    bundle, document = _write_bundle(tmp_path)
    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["installer"]["filename"] = "missing-setup.exe"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    for item in document["files"]:
        if item["name"] == "manifest.json":
            item["sha256"] = __import__("hashlib").sha256(manifest_path.read_bytes()).hexdigest()
            item["size_bytes"] = manifest_path.stat().st_size
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    problems = _expect(bundle)
    assert any("不存在的安装包" in item for item in problems)


def test_size_source_run_attempt_artifact_and_version_mismatches(tmp_path):
    bundle, document = _write_bundle(tmp_path)
    document["files"][0]["size_bytes"] = 1
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    assert any("文件大小不一致" in item for item in _expect(bundle))

    bundle, _ = _write_bundle(tmp_path / "sha")
    assert any("Source SHA" in item for item in _expect(bundle, expected_source_sha="c" * 40))
    assert any("Run ID" in item for item in _expect(bundle, expected_run_id="1"))
    assert any("Run Attempt" in item for item in _expect(bundle, expected_run_attempt="2"))
    assert any("Artifact ID" in item for item in _expect(bundle, observed_artifact_id="999"))
    assert any("版本号不一致" in item for item in _expect(bundle, expected_version="9.9.9"))
    assert any("Artifact Digest" in item for item in _expect(bundle, observed_artifact_digest="cd" * 32))


def test_invalid_signature_key_and_verifier_failure(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir(parents=True)
    filename = "yijing-workbench-3.3.2-x64-setup.exe"
    (bundle / filename).write_bytes(b"installer-bytes")
    (bundle / f"{filename}.sig").write_text(_signature(_OTHER_KEY_ID) + "\n", encoding="utf-8")
    digest = __import__("hashlib").sha256(b"installer-bytes").hexdigest().upper()
    (bundle / "SHA256SUMS.txt").write_text(f"{digest}  {filename}\n", encoding="utf-8")
    (bundle / "manifest.json").write_text(
        json.dumps(
            {
                "version": "3.3.2",
                "source_sha": "a" * 40,
                "signature_file": f"{filename}.sig",
                "installer": {"filename": filename, "bytes": 15, "sha256": digest},
            }
        ),
        encoding="utf-8",
    )
    (bundle / "latest.json").write_text("{}\n", encoding="utf-8")
    document = build_provenance(bundle, **_context())
    write_provenance(bundle, document)
    problems = _expect(bundle)
    assert any("签名无效" in item for item in problems)

    if __import__("os").name == "nt":
        verifier = tmp_path / "fail.cmd"
        verifier.write_text("@echo signature is invalid\r\n@exit /b 1\r\n", encoding="utf-8")
    else:
        verifier = tmp_path / "fail.sh"
        verifier.write_text("#!/bin/sh\necho signature is invalid\nexit 1\n", encoding="utf-8")
        verifier.chmod(0o755)
    bundle2, _ = _write_bundle(tmp_path / "verifier")
    verified = _expect(bundle2, signature_verifier=verifier)
    assert any("签名验证失败" in item for item in verified)


def test_missing_field_invalid_json_and_secret_rejection(tmp_path):
    bundle, document = _write_bundle(tmp_path)
    del document["schema_version"]
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    assert any("缺少必需字段" in item for item in _expect(bundle))

    (bundle / PROVENANCE_FILENAME).write_text("{", encoding="utf-8")
    with pytest.raises(ProvenanceError, match="JSON 无效"):
        load_provenance(bundle)

    secret = tmp_path / "secret"
    secret.mkdir()
    (secret / "file.bin").write_bytes(b"x")
    with pytest.raises(ProvenanceError, match="敏感材料"):
        build_provenance(secret, **{**_context(), "updater_pubkey": "TAURI_SIGNING_PRIVATE_KEY=secret"})
    with pytest.raises(ProvenanceError):
        build_provenance(secret, **{**_context(), "updater_pubkey": QA_PUBLIC_KEY})


def test_candidate_workflow_uploads_once_and_verify_job_does_not_rebuild():
    workflow = parse_workflow(WORKFLOW.read_text(encoding="utf-8"))
    build = workflow["jobs"]["windows-rc"]
    uploads = [step for step in build["steps"] if step.get("uses") == "actions/upload-artifact@v4"]
    assert len(uploads) == 1
    assert uploads[0]["with"]["overwrite"] == "false"
    assert uploads[0]["with"]["name"] == "yijing-workbench-${{ env.YIJING_VERSION }}-windows-x64-rc"
    assert uploads[0]["with"]["retention-days"] == "14"
    assert build["outputs"]["artifact-id"] == "${{ steps.upload-candidate.outputs.artifact-id }}"
    assert build["outputs"]["artifact-digest"] == "${{ steps.upload-candidate.outputs.artifact-digest }}"

    verify = workflow["jobs"]["verify-candidate-artifact"]
    assert verify["needs"] == "windows-rc"
    download = next(step for step in verify["steps"] if step.get("uses") == "actions/download-artifact@v4")
    assert download["with"]["artifact-ids"] == "${{ needs.windows-rc.outputs.artifact-id }}"
    assert "name" not in download["with"]
    joined = "\n".join(str(step.get("run") or "") for step in verify["steps"])
    assert "tauri build" not in joined
    assert "build:sidecar" not in joined
    assert "PyInstaller" not in joined
    assert "verify-updater-signature" in joined
    assert "provenance.py verify" in joined

    attest = workflow["jobs"]["attest-candidate-artifact"]
    assert attest["needs"] == ["windows-rc", "verify-candidate-artifact"]
    assert attest["if"] == "github.event_name != 'pull_request'"
    assert attest["permissions"]["id-token"] == "write"
    assert attest["permissions"]["attestations"] == "write"
    assert attest["permissions"]["contents"] == "read"
    attest_uses = [step.get("uses") for step in attest["steps"]]
    assert any(item.startswith("actions/attest-build-provenance@") and "@v" not in item for item in attest_uses)
    assert "gh attestation verify" in "\n".join(str(step.get("run") or "") for step in attest["steps"])
    assert public_key_key_id(_pubkey()) == "1122334455667788"
