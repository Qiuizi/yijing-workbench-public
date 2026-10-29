"""发布预检的反向测试：输入、路径、SHA、Tag 任何一项不合规都必须拒绝。"""

from pathlib import Path

import pytest

from scripts.updater.release_preflight import (
    PreflightError,
    ensure_tag_absent,
    validate_inputs,
    validate_ref,
    validate_sha,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40
OTHER = "b" * 40


def test_valid_inputs_pass():
    summary = validate_inputs("3.3.2", "3.3.2", "docs/release-notes-v3.3.2.md", REPO_ROOT)
    assert summary["version"] == "3.3.2"
    assert summary["repo_version"] == "3.3.2"


@pytest.mark.parametrize(
    "version,confirm,keyword",
    [
        ("3.3", "3.3", "SemVer"),
        ("v3.3.2", "v3.3.2", "SemVer"),
        ("3.3.2-beta.1", "3.3.2-beta.1", "稳定版本号"),
        ("3.3.2", "3.3.3", "不一致"),
        ("9.9.9", "9.9.9", "不一致"),  # 与仓库版本不一致
    ],
)
def test_bad_version_or_confirm_is_rejected(version: str, confirm: str, keyword: str):
    with pytest.raises(PreflightError) as error:
        validate_inputs(version, confirm, "docs/release-notes-v3.3.2.md", REPO_ROOT)
    assert keyword in str(error.value)


@pytest.mark.parametrize(
    "notes",
    [
        "",
        "../../etc/passwd",
        "docs/release-notes-v3.3.2.md/../../../README.md",
        "scripts/build_sidecar.ps1",
        "docs/other.md",
        "docs/release-notes-v3.3.9.md",  # 存在性校验
    ],
)
def test_unsafe_or_missing_notes_file_is_rejected(notes: str):
    with pytest.raises(PreflightError):
        validate_inputs("3.3.2", "3.3.2", notes, REPO_ROOT)


def test_notes_file_with_backslashes_is_normalised():
    summary = validate_inputs("3.3.2", "3.3.2", "docs\\release-notes-v3.3.2.md", REPO_ROOT)
    assert summary["notes_file"] == "docs/release-notes-v3.3.2.md"


def test_non_main_ref_is_rejected():
    validate_ref("refs/heads/main")
    for ref in ("refs/heads/dev", "refs/pull/43/merge", "refs/tags/v3.3.2", ""):
        with pytest.raises(PreflightError):
            validate_ref(ref)


def test_sha_must_match_worktree_and_main_tip():
    validate_sha(SHA, SHA, SHA)
    with pytest.raises(PreflightError) as error:
        validate_sha(SHA, OTHER, SHA)
    assert "不一致" in str(error.value)
    with pytest.raises(PreflightError) as error:
        validate_sha(SHA, SHA, OTHER)
    assert "main 已前进" in str(error.value)
    with pytest.raises(PreflightError):
        validate_sha("main", "main", None)


def test_existing_tag_blocks_release():
    with pytest.raises(PreflightError) as error:
        ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "v3.3.1\nv3.3.2\n")
    assert "已存在 tag" in str(error.value)


def test_absent_tag_passes_when_api_returns_404(monkeypatch):
    monkeypatch.setattr(
        "scripts.updater.release_preflight._gh_json",
        lambda path: None,
    )
    ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "v3.3.1\nv3.3.0\n")


def test_existing_release_on_github_blocks_release(monkeypatch):
    monkeypatch.setattr(
        "scripts.updater.release_preflight._gh_json",
        lambda path: {"id": 123},
    )
    with pytest.raises(PreflightError) as error:
        ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "")
    assert "已存在 release" in str(error.value)


def _gh_result(returncode: int, stderr: str):
    class Result:
        stdout = ""

    result = Result()
    result.returncode = returncode
    result.stderr = stderr
    return result


def test_missing_gh_token_is_not_treated_as_absent_release(monkeypatch):
    """没有 GH_TOKEN 时 gh 会失败。这必须拦住发布，不能当成「Release 不存在」。"""
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(
            1,
            "gh: To use GitHub CLI in a GitHub Actions workflow,\nset the GH_TOKEN environment variable.\n",
        ),
    )
    with pytest.raises(PreflightError) as error:
        ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "v3.3.1\n")
    assert "失败" in str(error.value)


def test_failed_github_api_is_not_treated_as_absent_release(monkeypatch):
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(1, "HTTP 502"),
    )
    with pytest.raises(PreflightError) as error:
        ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "")
    assert "失败" in str(error.value)


def test_preflight_command_fails_when_github_cli_has_no_credentials(monkeypatch, capsys):
    from scripts.updater.release_preflight import main

    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(
            1,
            "gh: To use GitHub CLI in a GitHub Actions workflow, set the GH_TOKEN environment variable.",
        ),
    )
    code = main(
        [
            "--version", "3.3.2",
            "--confirm", "3.3.2",
            "--notes-file", "docs/release-notes-v3.3.2.md",
            "--pinned-sha", SHA,
            "--ref", "refs/heads/main",
            "--repo", "Qiuizi/yijing-workbench-public",
            "--git-head", SHA,
            "--git-tags", "v3.3.1\n",
        ]
    )
    assert code == 1
    assert "GH_TOKEN" in capsys.readouterr().err
