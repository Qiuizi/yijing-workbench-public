"""A digest mismatch must fail before the archive is treated as the candidate."""

from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

import pytest

from scripts.updater.artifact_digest import extract_archive, verify_archive

DIGEST = "ab" * 32


def _zip(path: Path, payload: bytes = b"installer") -> str:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("yijing-workbench-3.3.2-x64-setup.exe", payload)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metadata(digest: str, artifact_id: str = "13030254437") -> dict:
    return {
        "id": int(artifact_id),
        "digest": f"sha256:{digest}",
        "expired": False,
        "workflow_run": {"id": 41169572944, "head_sha": "c" * 40},
    }


def test_matching_upload_api_and_zip_digests_pass(tmp_path):
    archive = tmp_path / "artifact.zip"
    digest = _zip(archive)
    assert verify_archive(
        _metadata(digest),
        archive,
        expected_digest=f"sha256:{digest}",
        expected_artifact_id="13030254437",
        expected_run_id="41169572944",
        expected_head_sha="c" * 40,
    ) == []


def test_missing_or_mismatched_digest_fails_without_a_name_lookup(tmp_path):
    archive = tmp_path / "artifact.zip"
    digest = _zip(archive)
    assert any("没有返回" in item for item in verify_archive(
        {"id": 1, "expired": False, "workflow_run": {"id": 1, "head_sha": "c" * 40}},
        archive,
        expected_digest=f"sha256:{digest}",
        expected_artifact_id="1",
        expected_run_id="1",
        expected_head_sha="c" * 40,
    ))
    assert any("不一致" in item for item in verify_archive(
        _metadata("cd" * 32),
        archive,
        expected_digest=f"sha256:{digest}",
        expected_artifact_id="13030254437",
        expected_run_id="41169572944",
        expected_head_sha="c" * 40,
    ))
    assert any("当前 Run" in item for item in verify_archive(
        _metadata(digest),
        archive,
        expected_digest=f"sha256:{digest}",
        expected_artifact_id="13030254437",
        expected_run_id="999",
        expected_head_sha="c" * 40,
    ))


def test_extract_allows_provenance_and_rejects_absolute_entries(tmp_path):
    archive = tmp_path / "good.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("provenance.json", b"{}")
        bundle.writestr("SHA256SUMS.txt", b"ok")
    out = tmp_path / "out"
    extract_archive(archive, out)
    assert (out / "provenance.json").read_bytes() == b"{}"


def test_extract_rejects_absolute_and_traversal_entries(tmp_path):
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("C:/Windows/win.ini", b"nope")
    with pytest.raises(ValueError, match="不安全"):
        extract_archive(archive, tmp_path / "out")
