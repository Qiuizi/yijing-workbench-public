"""发布预检的反向测试：输入、路径、SHA、Tag 任何一项不合规都必须拒绝。"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.updater.release_preflight import (
    PreflightError,
    _gh_json,
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


def _as_bytes(value: str | bytes | None) -> bytes | None:
    if value is None or isinstance(value, bytes):
        return value
    return value.encode("utf-8")


def _gh_result(returncode: int, stderr: str | bytes, stdout: str | bytes | None = b""):
    return subprocess.CompletedProcess(
        ["gh", "api"],
        returncode,
        stdout=_as_bytes(stdout),
        stderr=_as_bytes(stderr),
    )


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


CHINESE_COMMIT = "修复预检提交"


def _chinese_commit_payload() -> bytes:
    payload = json.dumps(
        {"sha": SHA, "commit": {"message": CHINESE_COMMIT}},
        ensure_ascii=False,
    ).encode("utf-8")
    # 「提」的 UTF-8 含 0x8F，CP1252 没有这个字节。这是第二次 Dry Run 的失败字节。
    assert b"\x8f" in payload
    return payload


def _run_like_windows_cp1252(script: Path):
    """把 text=True 的管道按 Windows Runner 的 CP1252 解码，text=False 则保留原始字节。"""
    real_run = subprocess.run

    def run(cmd, **kwargs):
        assert cmd[0] == "gh"
        forwarded = dict(kwargs)
        if forwarded.get("text") or forwarded.get("encoding") or forwarded.get("universal_newlines"):
            forwarded["text"] = True
            forwarded["encoding"] = "cp1252"
        return real_run([sys.executable, str(script)], **forwarded)

    return run


def test_utf8_commit_message_parses_under_windows_cp1252(monkeypatch, tmp_path):
    """静态配置不够。这里真的拉起子进程，并在 text=True 时强制 CP1252。"""
    payload = _chinese_commit_payload()
    with pytest.raises(UnicodeDecodeError):
        payload.decode("cp1252")
    script = tmp_path / "emit.py"
    script.write_bytes(b"import sys\nsys.stdout.buffer.write(" + repr(payload).encode("ascii") + b")\n")
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        _run_like_windows_cp1252(script),
    )
    data = _gh_json("repos/Qiuizi/yijing-workbench-public/commits/main")
    assert data is not None
    assert data["sha"] == SHA
    assert data["commit"]["message"] == CHINESE_COMMIT


@pytest.mark.parametrize(
    "stderr",
    ["gh: Not Found (HTTP 404)\n", b"HTTP 404", b"gh: Not Found (HTTP 404)\n\xff"],
)
def test_explicit_404_returns_none(monkeypatch, stderr):
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(1, stderr, b'{"message":"Not Found"}'),
    )
    assert _gh_json("repos/Qiuizi/yijing-workbench-public/releases/tags/v3.3.2") is None


def test_explicit_404_does_not_block_absent_tag(monkeypatch):
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(1, "gh: Not Found (HTTP 404)\n"),
    )
    ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "v3.3.1\n")


@pytest.mark.parametrize("stderr", [b"HTTP 401", b"HTTP 403", b"HTTP 500", b"Bad credentials"])
def test_non_404_errors_are_not_an_absent_release(monkeypatch, stderr):
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(1, stderr, b""),
    )
    with pytest.raises(PreflightError) as error:
        ensure_tag_absent("Qiuizi/yijing-workbench-public", "v3.3.2", "")
    message = str(error.value)
    assert "失败" in message
    assert "已存在 release" not in message


@pytest.mark.parametrize("stdout", [b"", b"\n", b"   ", None])
def test_empty_stdout_is_a_preflight_error(monkeypatch, stdout):
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(0, b"", stdout),
    )
    with pytest.raises(PreflightError) as error:
        _gh_json("repos/Qiuizi/yijing-workbench-public/commits/main")
    assert "空响应" in str(error.value)


@pytest.mark.parametrize("stdout", [b"not-json", b"{", b"null", b"[]", b'"sha"'])
def test_invalid_json_is_a_preflight_error(monkeypatch, stdout):
    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(0, b"", stdout),
    )
    with pytest.raises(PreflightError) as error:
        _gh_json("repos/Qiuizi/yijing-workbench-public/commits/main")
    assert "JSON" in str(error.value)


def test_missing_gh_executable_is_a_preflight_error(monkeypatch):
    def boom(*args, **kwargs):
        raise FileNotFoundError(2, "The system cannot find the file specified", "gh")

    monkeypatch.setattr("scripts.updater.release_preflight.subprocess.run", boom)
    with pytest.raises(PreflightError) as error:
        _gh_json("repos/Qiuizi/yijing-workbench-public/commits/main")
    assert "不可执行" in str(error.value)


def test_main_reports_invalid_json_instead_of_a_secondary_exception(monkeypatch, capsys):
    from scripts.updater.release_preflight import main

    monkeypatch.setattr(
        "scripts.updater.release_preflight.subprocess.run",
        lambda *args, **kwargs: _gh_result(0, b"", b"not-json"),
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
    assert "JSON" in capsys.readouterr().err
