"""The signature gate must use the compiled verifier, not a stub that always exits 1."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
TAURI = REPO / "frontend" / "src-tauri"
PROOF = REPO / "scripts" / "updater" / "verifier-proof"


@pytest.mark.skipif(shutil.which("cargo") is None or shutil.which("rustc") is None, reason="cargo required")
def test_build_gate_executes_both_paths():
    binary = Path(os.environ.get("TEMP", ".")) / "tauri_build_gate_test.exe"
    subprocess.run(
        ["rustc", "--test", "frontend/src-tauri/tauri_build_gate.rs", "-o", str(binary)],
        cwd=REPO,
        check=True,
    )
    completed = subprocess.run([str(binary)], check=True, capture_output=True, text=True)
    assert "normal_builds_do_not_skip" in completed.stdout
    assert "isolated_verifier_skips_only_the_exact_switch" in completed.stdout


@pytest.mark.skipif(shutil.which("cargo") is None, reason="cargo required")
def test_compiled_verifier_accepts_real_signature_and_rejects_tampering(tmp_path):
    env = os.environ.copy()
    env["YIJING_SKIP_TAURI_BUILD"] = "1"
    subprocess.run(
        ["cargo", "build", "--release", "--bin", "verify-updater-signature"],
        cwd=TAURI,
        env=env,
        check=True,
    )
    verifier = TAURI / "target" / "release" / "verify-updater-signature.exe"
    if not verifier.exists():
        verifier = TAURI / "target" / "release" / "verify-updater-signature"
    proof_env = os.environ.copy()
    proof_env["VERIFIER_EXE"] = str(verifier)
    proof_env["PROOF_DIR"] = str(tmp_path)
    completed = subprocess.run(
        ["cargo", "run", "--quiet", "--manifest-path", str(PROOF / "Cargo.toml")],
        cwd=PROOF,
        env=proof_env,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert "rejected invalid signatures" in completed.stdout
