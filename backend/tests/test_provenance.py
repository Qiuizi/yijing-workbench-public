"""来源证明的反向测试：不一致的产物必须失败，不能只测正常路径。"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from scripts.updater.keys import QA_PUBLIC_KEY
from scripts.updater.manifest import public_key_key_id
from scripts.updater import provenance
from scripts.updater.provenance import (
    PROVENANCE_FILENAME,
    ProvenanceError,
    build_provenance,
    load_provenance,
    locate_bundle_file,
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
        expected_workflow_ref=context["workflow_ref"],
        expected_workflow_sha=context["workflow_sha"],
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


def test_windows_absolute_path_traversal_case_and_sha_format(tmp_path):
    bundle, document = _write_bundle(tmp_path)
    document["files"].append({"name": "C:/Windows/win.ini", "size_bytes": 1, "sha256": "ab" * 32})
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    problems = _expect(bundle)
    assert any("绝对路径" in item or "非法文件名" in item for item in problems)
    assert not any(item.startswith("C:/Windows/win.ini 的 SHA-256") for item in problems)

    bundle, document = _write_bundle(tmp_path / "dotdot")
    document["files"].append({"name": "../secret", "size_bytes": 1, "sha256": "ab" * 32})
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    assert any("路径穿越" in item or "非法文件名" in item for item in _expect(bundle))

    bundle, document = _write_bundle(tmp_path / "unc")
    document["files"].append({"name": "//server/share", "size_bytes": 1, "sha256": "ab" * 32})
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    assert any("绝对路径" in item or "非法文件名" in item for item in _expect(bundle))

    bundle, document = _write_bundle(tmp_path / "case")
    first = document["files"][0]
    document["files"].append({**first, "name": first["name"].upper()})
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    assert any("大小写" in item or "重复" in item for item in _expect(bundle))

    bundle, document = _write_bundle(tmp_path / "sha")
    document["files"][0]["sha256"] = "g" * 64
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    assert any("sha256 格式无效" in item for item in _expect(bundle))
    assert any("workflow_ref" in item for item in _expect(bundle, expected_workflow_ref="other.yml@refs/heads/main"))
    assert any("workflow_sha" in item for item in _expect(bundle, expected_workflow_sha="d" * 40))
    assert any("Source SHA 格式无效" in item for item in _expect(bundle, expected_source_sha="not-a-sha"))


def _retarget_manifest(bundle: Path, *, installer: str | None = None, signature: str | None = None) -> None:
    manifest_path = bundle / "manifest.json"
    document = json.loads((bundle / PROVENANCE_FILENAME).read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if installer is not None:
        manifest["installer"]["filename"] = installer
    if signature is not None:
        manifest["signature_file"] = signature
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    data = manifest_path.read_bytes()
    for item in document["files"]:
        if item["name"] == "manifest.json":
            item["sha256"] = __import__("hashlib").sha256(data).hexdigest()
            item["size_bytes"] = len(data)
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")


def _forbid_external_access(monkeypatch, marker: str) -> None:
    def wrap(method):
        def wrapped(self, *args, **kwargs):
            if marker.lower() in str(self).lower():
                raise AssertionError(f"external filesystem access via {method.__name__}: {self}")
            return method(self, *args, **kwargs)

        return wrapped

    monkeypatch.setattr(Path, "open", wrap(Path.open))
    monkeypatch.setattr(Path, "stat", wrap(Path.stat))
    monkeypatch.setattr(Path, "is_file", wrap(Path.is_file))
    monkeypatch.setattr(Path, "is_symlink", wrap(Path.is_symlink))
    monkeypatch.setattr(Path, "resolve", wrap(Path.resolve))
    real_hash = provenance.sha256_file

    def guarded_hash(path):
        if marker.lower() in str(path).lower():
            raise AssertionError(f"hashed external file: {path}")
        return real_hash(path)

    monkeypatch.setattr(provenance, "sha256_file", guarded_hash)


@pytest.mark.parametrize(
    "field, malicious",
    [
        ("installer", "C:/Windows/win.ini"),
        ("installer", "C:\\Windows\\win.ini"),
        ("installer", "//server/share/file"),
        ("installer", "\\\\server\\share\\file"),
        ("installer", "/etc/passwd"),
        ("installer", "../outside.exe"),
        ("installer", "subdir/../../outside.exe"),
        ("signature", "C:/Windows/win.ini"),
        ("signature", "C:\\Windows\\win.ini"),
        ("signature", "//server/share/file"),
        ("signature", "\\\\server\\share\\file"),
        ("signature", "/etc/passwd"),
        ("signature", "../outside.exe"),
        ("signature", "subdir/../../outside.exe"),
    ],
)
def test_manifest_path_escapes_are_rejected_before_external_access(tmp_path, monkeypatch, field, malicious):
    bundle, _ = _write_bundle(tmp_path)
    if field == "installer":
        _retarget_manifest(bundle, installer=malicious)
    else:
        _retarget_manifest(bundle, signature=malicious)
    _forbid_external_access(monkeypatch, "win.ini" if "win.ini" in malicious else malicious.replace("\\", "/").split("/")[-1])
    problems = _expect(bundle)
    assert any("路径被拒绝" in item or "非法文件名" in item or "绝对路径" in item or "路径穿越" in item for item in problems)
    assert not any("SHA-256" in item and malicious in item for item in problems)


def test_manifest_windows_path_does_not_hash_win_ini(tmp_path, monkeypatch):
    bundle, _ = _write_bundle(tmp_path)
    _retarget_manifest(bundle, installer="C:/Windows/win.ini")
    _forbid_external_access(monkeypatch, "win.ini")
    problems = _expect(bundle)
    assert any("安装包路径被拒绝" in item for item in problems)

    bundle, _ = _write_bundle(tmp_path / "sig")
    _retarget_manifest(bundle, signature="C:\\Windows\\win.ini")
    _forbid_external_access(monkeypatch, "win.ini")
    problems = _expect(bundle)
    assert any("签名路径被拒绝" in item or "签名文件路径被拒绝" in item for item in problems)


def test_manifest_symlink_flag_is_rejected_before_open(tmp_path, monkeypatch):
    bundle, _ = _write_bundle(tmp_path)
    outside = tmp_path / "outside.exe"
    outside.write_bytes(b"outside-bytes")
    link = bundle / "linked.exe"
    link.write_bytes(b"not-the-target")
    _retarget_manifest(bundle, installer="linked.exe")
    real_is_symlink = Path.is_symlink
    real_open = Path.open

    def fake_is_symlink(self):
        if self.name == "linked.exe":
            return True
        return real_is_symlink(self)

    def guarded_open(self, *args, **kwargs):
        if self.name == "outside.exe":
            raise AssertionError(f"followed symlink to {self}")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    monkeypatch.setattr(Path, "open", guarded_open)
    problems = _expect(bundle)
    assert any("符号链接" in item for item in problems)


def test_manifest_symlink_is_rejected_before_following_it(tmp_path, monkeypatch):
    bundle, _ = _write_bundle(tmp_path)
    outside = tmp_path / "outside.exe"
    outside.write_bytes(b"outside-bytes")
    link = bundle / "linked.exe"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink not permitted: {error}")
    _retarget_manifest(bundle, installer="linked.exe")
    real_open = Path.open

    def guarded_open(self, *args, **kwargs):
        if self.name == "outside.exe":
            raise AssertionError(f"followed symlink to {self}")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded_open)
    problems = _expect(bundle)
    assert any("符号链接" in item for item in problems)


def test_case_collision_is_reported_when_the_other_case_is_missing(tmp_path, monkeypatch):
    bundle, document = _write_bundle(tmp_path)
    first = document["files"][0]
    upper = first["name"].upper()
    document["files"].append({**first, "name": upper})
    (bundle / PROVENANCE_FILENAME).write_text(json.dumps(document), encoding="utf-8")
    real_locate = provenance.locate_bundle_file

    def missing_other_case(bundle_dir, name):
        if name == upper:
            return None, f"清单引用了不存在的文件：{name}"
        return real_locate(bundle_dir, name)

    monkeypatch.setattr(provenance, "locate_bundle_file", missing_other_case)
    problems = _expect(bundle)
    assert any("大小写" in item or "重复" in item for item in problems)


def test_manifest_missing_signature_file_is_rejected(tmp_path):
    bundle, _ = _write_bundle(tmp_path)
    _retarget_manifest(bundle, signature="missing.sig")
    problems = _expect(bundle)
    assert any("不存在的签名文件" in item or "不存在" in item for item in problems)


def test_normal_installer_and_signature_names_are_accepted(tmp_path):
    bundle, _ = _write_bundle(tmp_path)
    installer, installer_error = locate_bundle_file(bundle, "yijing-workbench-3.3.2-x64-setup.exe")
    signature, signature_error = locate_bundle_file(bundle, "yijing-workbench-3.3.2-x64-setup.exe.sig")
    assert installer_error is None and installer is not None and installer.is_file()
    assert signature_error is None and signature is not None and signature.is_file()
    assert _expect(bundle) == []


def test_candidate_workflow_uploads_once_and_verify_job_does_not_rebuild():
    workflow = parse_workflow(WORKFLOW.read_text(encoding="utf-8"))
    build = workflow["jobs"]["windows-rc"]
    uploads = [step for step in build["steps"] if step.get("uses") == "actions/upload-artifact@v4"]
    assert len(uploads) == 1
    assert uploads[0]["with"]["overwrite"] == "false"
    assert uploads[0]["with"]["retention-days"] == "14"
    assert uploads[0]["with"]["name"] == "yijing-workbench-${{ env.YIJING_VERSION }}-windows-x64-rc"
    assert uploads[0]["id"] == "upload-candidate"
    assert "verifier-artifact-id" not in build.get("outputs", {})
    assert build["outputs"]["artifact-id"] == "${{ steps.upload-candidate.outputs.artifact-id }}"
    assert build["outputs"]["artifact-digest"] == "${{ steps.upload-candidate.outputs.artifact-digest }}"

    verify = workflow["jobs"]["verify-candidate-artifact"]
    assert verify["needs"] == "windows-rc"
    assert all(step.get("uses") != "actions/download-artifact@v4" for step in verify["steps"])
    joined = "\n".join(str(step.get("run") or "") for step in verify["steps"])
    assert "actions/artifacts/${ARTIFACT_ID}/zip" in joined
    assert "artifact_digest.py" in joined
    assert "tauri build" not in joined
    assert "build:sidecar" not in joined
    assert "PyInstaller" not in joined
    assert "YIJING_SKIP_TAURI_BUILD" in joined or any(
        step.get("env", {}).get("YIJING_SKIP_TAURI_BUILD") == "1" for step in verify["steps"]
    )
    assert "cargo build --release --bin verify-updater-signature" in joined
    assert "downloaded-verifier" not in joined
    assert "frontend/src-tauri/target/release/verify-updater-signature.exe" in joined
    assert "--expected-version" in joined
    assert "--expected-workflow-ref" in joined
    assert "--expected-workflow-sha" in joined
    assert "provenance.py verify" in joined

    attest = workflow["jobs"]["attest-candidate-artifact"]
    assert attest["needs"] == ["windows-rc", "verify-candidate-artifact"]
    assert attest["if"] == "github.event_name != 'pull_request'"
    assert attest["permissions"]["id-token"] == "write"
    assert attest["permissions"]["attestations"] == "write"
    assert attest["permissions"]["contents"] == "read"
    attest_uses = [step.get("uses") for step in attest["steps"] if step.get("uses")]
    assert any(item.startswith("actions/attest-build-provenance@") and "@v" not in item for item in attest_uses)
    attest_run = "\n".join(str(step.get("run") or "") for step in attest["steps"])
    assert "gh attestation verify" in attest_run
    assert "--cert-identity" in attest_run
    assert 'gh attestation verify "$installer" --repo "$GITHUB_REPOSITORY"' not in attest_run
    assert "artifact_digest.py" in attest_run
    assert "actions/download-artifact@v4" not in "\n".join(str(step.get("uses") or "") for step in attest["steps"])
    assert public_key_key_id(_pubkey()) == "1122334455667788"
