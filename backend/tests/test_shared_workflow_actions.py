"""Candidate 与 Release 必须调用同一套无密钥 Windows 构建 Action。

只解析 workflow 和 action 文件，不触发 release.yml，不读取 Secret。
"""

from __future__ import annotations

from pathlib import Path

from backend.tests.test_legacy_publish_disabled import _raw_job_ifs
from backend.tests.test_release_workflow_auth import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
ACTIONS = REPO_ROOT / ".github" / "actions"
SHARED = {
    "toolchain": "./.github/actions/setup-windows-toolchain",
    "deps": "./.github/actions/install-frozen-windows-deps",
    "regression": "./.github/actions/run-windows-regression",
    "vc143": "./.github/actions/discover-vc143",
}
PRODUCTION_SECRETS = (
    "secrets.TAURI_SIGNING_PRIVATE_KEY",
    "secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD",
    "secrets.TAURI_UPDATER_PUBKEY",
)
CANDIDATE_SECRETS = (
    "secrets.YIJING_CANDIDATE_SIGNING_KEY",
    "secrets.YIJING_CANDIDATE_SIGNING_KEY_PASSWORD",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _workflow(name: str) -> dict:
    return parse_workflow(_text(WORKFLOWS / name))


def _action(folder: str) -> dict:
    return parse_workflow(_text(ACTIONS / folder / "action.yml"))


def _steps(job: dict) -> list[dict]:
    steps = job["steps"]
    assert isinstance(steps, list)
    return steps


def _named(steps: list[dict], name: str) -> dict:
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _index(steps: list[dict], name: str) -> int:
    return [step.get("name") for step in steps].index(name)


def _run(step: dict) -> str:
    return str(step.get("run") or "")


def test_shared_action_files_exist_and_have_no_signing_secrets():
    for folder in (
        "setup-windows-toolchain",
        "install-frozen-windows-deps",
        "run-windows-regression",
        "discover-vc143",
    ):
        path = ACTIONS / folder / "action.yml"
        assert path.is_file(), path
        text = _text(path)
        for secret in (*PRODUCTION_SECRETS, *CANDIDATE_SECRETS, "GH_TOKEN"):
            assert secret not in text, f"{folder} references {secret}"
        action = parse_workflow(text)
        assert action["runs"]["using"] == "composite"
        assert action["runs"]["steps"]


def test_toolchain_pin_is_single_sourced_and_cache_is_unchanged():
    action = _action("setup-windows-toolchain")
    uses = [step["uses"] for step in action["runs"]["steps"] if step.get("uses")]
    assert uses == [
        "actions/setup-python@v5",
        "actions/setup-node@v4",
        "dtolnay/rust-toolchain@stable",
    ]
    python, node, rust = [step for step in action["runs"]["steps"] if step.get("uses")]
    assert python["with"] == {"python-version": "3.12"}
    assert node["with"] == {
        "node-version": "24",
        "cache": "npm",
        "cache-dependency-path": "frontend/package-lock.json",
    }
    assert rust["with"] == {"toolchain": "1.98.1", "targets": "x86_64-pc-windows-msvc"}
    verify = action["runs"]["steps"][-1]["run"]
    assert "Expected Python 3.12" in verify
    assert "Expected Node.js 24" in verify
    assert "Expected rustc 1.98.1" in verify

    for name in ("windows-rc.yml", "release.yml"):
        text = _text(WORKFLOWS / name)
        assert "actions/setup-python@" not in text
        assert "actions/setup-node@" not in text
        assert "python-version:" not in text
    assert "dtolnay/rust-toolchain@" not in _text(WORKFLOWS / "release.yml")
    windows = _workflow("windows-rc.yml")
    build_uses = [step.get("uses") for step in _steps(windows["jobs"]["windows-rc"])]
    assert "dtolnay/rust-toolchain@stable" not in build_uses
    build_steps = _steps(windows["jobs"]["windows-rc"])
    assert all(step.get("name") != "Build signature verifier only" for step in build_steps)
    assert "YIJING_SKIP_TAURI_BUILD" not in "\n".join(str(step.get("run") or "") for step in build_steps)
    verifier = _named(_steps(windows["jobs"]["verify-candidate-artifact"]), "Compile signature verifier from this checkout")
    assert verifier["env"]["YIJING_SKIP_TAURI_BUILD"] == "1"
    assert verifier["run"] == "cargo build --release --bin verify-updater-signature"
    assert "tauri build" not in verifier["run"]


def test_candidate_and_release_call_the_same_build_actions_in_safe_order():
    candidate = _steps(_workflow("windows-rc.yml")["jobs"]["windows-rc"])
    release = _steps(_workflow("release.yml")["jobs"]["build"])

    for steps in (candidate, release):
        assert _named(steps, "Set up Windows toolchain")["uses"] == SHARED["toolchain"]
        assert "with" not in _named(steps, "Set up Windows toolchain")
        assert _named(steps, "Find and verify the VS2022 VC143 x64 redist")["uses"] == SHARED["vc143"]

    assert _named(candidate, "Install frozen Python release dependencies")["with"] == {
        "python": "true",
        "frontend": "false",
    }
    assert _named(candidate, "Install frontend locked dependencies")["with"] == {
        "python": "false",
        "frontend": "true",
    }
    assert _named(candidate, "Windows backend regression tests")["with"] == {
        "backend": "true",
        "vitest": "false",
        "typecheck": "false",
    }
    assert _named(candidate, "Frontend regression tests")["with"] == {
        "backend": "false",
        "vitest": "true",
        "typecheck": "false",
    }
    assert _named(candidate, "Typecheck")["with"] == {
        "backend": "false",
        "vitest": "false",
        "typecheck": "true",
    }
    assert _index(candidate, "Install frozen Python release dependencies") < _index(
        candidate, "Windows backend regression tests"
    )
    assert _index(candidate, "Windows backend regression tests") < _index(
        candidate, "Install frontend locked dependencies"
    )
    assert _index(candidate, "Typecheck") < _index(
        candidate, "Find and verify the VS2022 VC143 x64 redist"
    )

    install = _named(release, "Install dependencies")
    regression = _named(release, "Regression tests before the release build")
    assert install["uses"] == SHARED["deps"]
    assert "with" not in install
    assert regression["uses"] == SHARED["regression"]
    assert "with" not in regression
    assert _index(release, "Install dependencies") < _index(
        release, "Regression tests before the release build"
    )
    assert _index(release, "Regression tests before the release build") < _index(
        release, "Find and verify the VS2022 VC143 x64 redist"
    )
    assert _index(release, "Find and verify the VS2022 VC143 x64 redist") < _index(
        release, "Build sidecar and unsigned NSIS installer"
    )


def test_dependency_and_regression_commands_remain_frozen_and_separate():
    deps = _action("install-frozen-windows-deps")
    assert deps["inputs"]["python"]["default"] == "true"
    assert deps["inputs"]["frontend"]["default"] == "true"
    dep_steps = {step["name"]: step for step in deps["runs"]["steps"] if step.get("name")}
    python = dep_steps["Install frozen Python release dependencies"]
    assert python["if"] == "${{ inputs.python == 'true' }}"
    assert "python -m venv .venv" in python["run"]
    assert "pip install -r requirements-win.lock.txt" in python["run"]
    assert "pip install -r requirements-build.txt" in python["run"]
    assert "pip install -U" not in python["run"]
    assert "npm install" not in python["run"]
    frontend = dep_steps["Install frontend locked dependencies"]
    assert frontend["working-directory"] == "frontend"
    assert frontend["run"] == "npm ci"

    checks = _action("run-windows-regression")
    assert checks["inputs"]["backend"]["default"] == "true"
    assert checks["inputs"]["vitest"]["default"] == "true"
    assert checks["inputs"]["typecheck"]["default"] == "true"
    named = {step["name"]: step for step in checks["runs"]["steps"]}
    assert named["Windows backend regression tests"]["run"] == r".\.venv\Scripts\python.exe -X utf8 -m pytest"
    assert named["Frontend regression tests"]["working-directory"] == "frontend"
    assert named["Frontend regression tests"]["run"] == "npm test"
    assert named["Typecheck"]["working-directory"] == "frontend"
    assert named["Typecheck"]["run"] == "npm run typecheck"
    assert named["Windows backend regression tests"]["if"] == "${{ inputs.backend == 'true' }}"
    assert named["Frontend regression tests"]["if"] == "${{ inputs.vitest == 'true' }}"
    assert named["Typecheck"]["if"] == "${{ inputs.typecheck == 'true' }}"


def test_vc143_action_checks_both_dlls_before_either_sidecar_build():
    action = _action("discover-vc143")
    assert action["outputs"]["redist-dir"]["value"] == "${{ steps.discover.outputs.redist-dir }}"
    run = action["runs"]["steps"][0]["run"]
    assert "vswhere.exe" in run
    assert "ProgramFiles(x86)" in run
    assert r"VC\Redist\MSVC" in run
    assert "Sort-Object Name -Descending" in run
    assert r"x64\Microsoft.VC143.CRT" in run
    assert "vcruntime140.dll" in run
    assert "vcruntime140_1.dll" in run
    assert "Get-AuthenticodeSignature" in run
    assert "'Valid'" in run
    assert "O=Microsoft Corporation" in run
    assert "YIJING_VC_REDIST_DIR=$redist" in run
    assert "C:\\Program Files\\Microsoft Visual Studio" not in run

    for name in ("windows-rc.yml", "release.yml"):
        text = _text(WORKFLOWS / name)
        assert "vswhere.exe" not in text
        assert "Get-AuthenticodeSignature" not in text


def test_signing_boundaries_stay_in_the_caller_workflows():
    candidate_text = _text(WORKFLOWS / "windows-rc.yml")
    release_text = _text(WORKFLOWS / "release.yml")
    for secret in PRODUCTION_SECRETS:
        assert secret not in candidate_text
    for secret in CANDIDATE_SECRETS:
        assert secret not in release_text

    candidate = _steps(_workflow("windows-rc.yml")["jobs"]["windows-rc"])
    build = _named(candidate, "Build PyInstaller sidecar and updater-signed NSIS candidate")
    assert build["env"]["YIJING_CANDIDATE_SIGNING_KEY"] == "${{ secrets.YIJING_CANDIDATE_SIGNING_KEY }}"
    assert "uses" not in build
    assert "npx tauri build --bundles nsis --config $override" in _run(build)
    assert "secrets.TAURI_SIGNING_PRIVATE_KEY" not in _run(build)

    release = _steps(_workflow("release.yml")["jobs"]["build"])
    production = _named(release, "Build sidecar and unsigned NSIS installer")
    assert "env" not in production
    assert "secrets.TAURI_SIGNING_PRIVATE_KEY" not in _run(production)
    assert "createUpdaterArtifacts" in _run(production)
    assert "npx tauri build --bundles nsis --config $override" in _run(production)
    sign = _named(
        _steps(_workflow("release.yml")["jobs"]["production-sign"]),
        "Sign the verified installer with the production key",
    )
    assert sign["env"]["TAURI_SIGNING_PRIVATE_KEY"] == "${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}"
    assert sign["env"]["TAURI_SIGNING_PRIVATE_KEY_PASSWORD"] == "${{ secrets.TAURI_SIGNING_PRIVATE_KEY_PASSWORD }}"
    assert sign["env"]["TAURI_UPDATER_PUBKEY"] == "${{ secrets.TAURI_UPDATER_PUBKEY }}"
    assert "YIJING_CANDIDATE_SIGNING_KEY" not in release_text


def test_release_auth_environment_and_artifact_contracts_are_unchanged():
    release = _workflow("release.yml")
    assert release["permissions"] == {"contents": "read", "actions": "read"}
    assert set(release["on"]) == {"workflow_dispatch"}
    dry_run = release["on"]["workflow_dispatch"]["inputs"]["dry_run"]
    assert dry_run["type"] == "boolean"
    assert dry_run["default"] == "true"
    jobs = release["jobs"]
    assert "environment" not in jobs["build"]
    assert jobs["build"]["permissions"] == {"contents": "read", "actions": "read"}
    assert jobs["production-sign"]["environment"] == "release"
    assert "needs.verify-signed.result == 'success'" in jobs["publish"]["if"]
    assert jobs["publish"]["environment"] == "release"
    assert jobs["publish"]["permissions"] == {"contents": "write"}
    assert jobs["publish"]["needs"] == ["production-sign", "verify-signed"]
    assert "inputs.dry_run &&" in jobs["dry-run-check"]["if"]
    assert jobs["dry-run-check"]["permissions"] == {"contents": "read"}
    assert "environment" not in jobs["dry-run-check"]

    preflight = _named(_steps(jobs["build"]), "Preflight inputs, ref, SHA and tag availability")
    assert preflight["env"]["GH_TOKEN"] == "${{ github.token }}"
    ci_gate = _named(_steps(jobs["build"]), "Require green CI for this exact commit")
    assert ci_gate["env"]["GH_TOKEN"] == "${{ github.token }}"

    upload = _named(_steps(jobs["build"]), "Upload unsigned staging artifact")
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert upload["with"]["name"] == "yijing-workbench-${{ env.YIJING_VERSION_INPUT }}-windows-x64-staging"
    assert upload["with"]["retention-days"] == "14"
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["overwrite"] == "false"
    assert "yijing-staging-" in upload["with"]["path"]

    candidate = _workflow("windows-rc.yml")
    assert candidate["permissions"] == {"contents": "read"}
    assert "environment" not in candidate["jobs"]["windows-rc"]
    candidate_upload = _named(
        _steps(candidate["jobs"]["windows-rc"]),
        "Upload candidate artifacts (never a public Release, never the update channel)",
    )
    assert candidate_upload["with"]["name"] == "yijing-workbench-${{ env.YIJING_VERSION }}-windows-x64-rc"
    assert candidate_upload["with"]["retention-days"] == "14"
    assert candidate_upload["with"]["if-no-files-found"] == "error"

    legacy = _text(WORKFLOWS / "publish-v3.3.1.yml")
    assert _raw_job_ifs(legacy) == {"verify-and-publish": "false"}
    assert "contents: write" not in legacy
