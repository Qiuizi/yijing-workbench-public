"""release.yml 的静态结构检查。

这里解析工作流文件，确认每个真正调用 GitHub CLI 的步骤都有步骤级 GH_TOKEN，
并且权限没有被抬高。这不是 GitHub Actions 的实际运行结果；那一次失败的
Dry Run 仍然是失败，本测试也不负责重新触发 release.yml。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "release.yml"
GITHUB_TOKEN = "${{ github.token }}"
BLOCK_MARKERS = {"|", "|-", "|+", ">", ">-", ">+"}


def _is_comment(line: str) -> bool:
    return line.lstrip().startswith("#")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_kv(content: str) -> tuple[str, str]:
    key, _, rest = content.partition(":")
    return key.strip(), rest.strip()


def _read_block(lines: list[str], index: int, parent_indent: int) -> tuple[str, int]:
    collected: list[str] = []
    while index < len(lines):
        line = lines[index]
        if line.strip() and not _is_comment(line) and _indent(line) <= parent_indent:
            break
        if line.strip() and not _is_comment(line):
            collected.append(line.strip())
        index += 1
    return "\n".join(collected), index


def _next_content(lines: list[str], index: int) -> int:
    while index < len(lines) and (not lines[index].strip() or _is_comment(lines[index])):
        index += 1
    return index


def _parse_map(lines: list[str], index: int, indent: int) -> tuple[dict, int]:
    mapping: dict = {}
    while True:
        index = _next_content(lines, index)
        if index >= len(lines) or _indent(lines[index]) < indent:
            break
        if _indent(lines[index]) != indent:
            raise ValueError(f"第 {index + 1} 行缩进无法解析：{lines[index]!r}")
        content = lines[index].strip()
        if content.startswith("- "):
            raise ValueError(f"第 {index + 1} 行应为映射，实际是列表：{content}")
        key, rest = _split_kv(content)
        if rest in BLOCK_MARKERS:
            mapping[key], index = _read_block(lines, index + 1, indent)
            continue
        if rest == "":
            peek = _next_content(lines, index + 1)
            if peek >= len(lines) or _indent(lines[peek]) <= indent:
                mapping[key] = None
                index = peek
                continue
            child_indent = _indent(lines[peek])
            if lines[peek].strip().startswith("- "):
                mapping[key], index = _parse_list(lines, peek, child_indent)
            else:
                mapping[key], index = _parse_map(lines, peek, child_indent)
            continue
        mapping[key] = _unquote(rest)
        index += 1
    return mapping, index


def _parse_list(lines: list[str], index: int, indent: int) -> tuple[list, int]:
    items: list = []
    while True:
        index = _next_content(lines, index)
        if index >= len(lines) or _indent(lines[index]) < indent:
            break
        if _indent(lines[index]) != indent or not lines[index].strip().startswith("- "):
            break
        body = lines[index].strip()[2:]
        key_indent = indent + 2
        if body in BLOCK_MARKERS:
            value, index = _read_block(lines, index + 1, indent)
            items.append(value)
            continue
        if ":" not in body:
            items.append(_unquote(body))
            index += 1
            continue
        key, rest = _split_kv(body)
        item: dict = {}
        if rest in BLOCK_MARKERS:
            item[key], index = _read_block(lines, index + 1, key_indent)
        elif rest == "":
            peek = _next_content(lines, index + 1)
            if peek >= len(lines) or _indent(lines[peek]) <= key_indent:
                item[key] = None
                index = peek
            elif lines[peek].strip().startswith("- "):
                item[key], index = _parse_list(lines, peek, _indent(lines[peek]))
            else:
                item[key], index = _parse_map(lines, peek, _indent(lines[peek]))
        else:
            item[key] = _unquote(rest)
            index += 1
        extra, index = _parse_map(lines, index, key_indent)
        item.update(extra)
        items.append(item)
    return items, index


def parse_workflow(text: str) -> dict:
    document, index = _parse_map(text.splitlines(), 0, 0)
    leftover = _next_content(text.splitlines(), index)
    if leftover < len(text.splitlines()):
        raise ValueError(f"工作流在第 {leftover + 1} 行之后还有无法归位的内容")
    return document


def load_workflow() -> dict:
    return parse_workflow(WORKFLOW_PATH.read_text(encoding="utf-8"))


def _script_calls_gh(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    return bool(re.search(r"""subprocess\.run\(\s*\[\s*["']gh["']""", source))


def step_calls_github_cli(step: dict) -> bool:
    run = str(step.get("run") or "")
    if re.search(r"\bgh\b", run):
        return True
    for relative in re.findall(r"scripts/[\w./-]+\.(?:py|ps1)", run):
        target = REPO_ROOT / relative
        if target.suffix == ".py" and target.is_file() and _script_calls_gh(target):
            return True
    return False


def _jobs(workflow: dict) -> dict:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict)
    return jobs


def _steps(job: dict) -> list[dict]:
    steps = job["steps"]
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return steps


def test_workflow_file_parses_and_keeps_least_privilege():
    workflow = load_workflow()
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    assert "GH_TOKEN" not in (workflow.get("env") or {})

    jobs = _jobs(workflow)
    assert set(jobs) == {"build", "publish", "dry-run-check"}
    assert "permissions" not in jobs["build"]
    assert "GH_TOKEN" not in (jobs["build"].get("env") or {})
    assert jobs["publish"]["permissions"] == {"contents": "write"}
    assert jobs["dry-run-check"]["permissions"] == {"contents": "read"}

    for name, job in jobs.items():
        permissions = job.get("permissions", workflow["permissions"])
        assert set(permissions) <= {"contents", "actions"}
        for scope, level in permissions.items():
            if name == "publish":
                assert (scope, level) == ("contents", "write")
            else:
                assert level == "read"
                assert scope in {"contents", "actions"}


def test_preflight_and_every_github_cli_step_has_a_step_token():
    jobs = _jobs(load_workflow())
    callers: list[tuple[str, str]] = []
    for job_name, job in jobs.items():
        for step in _steps(job):
            if not step_calls_github_cli(step):
                continue
            label = str(step.get("name") or step.get("uses") or "<unnamed>")
            callers.append((job_name, label))
            env = step.get("env") or {}
            assert env.get("GH_TOKEN") == GITHUB_TOKEN, f"{job_name}/{label} 缺少步骤级 GH_TOKEN"
            assert "secrets." not in env["GH_TOKEN"]

    assert ("build", "Preflight inputs, ref, SHA and tag availability") in callers
    assert ("build", "Require green CI for this exact commit") in callers
    assert ("publish", "Refuse to overwrite an existing tag or release") in callers
    assert ("publish", "Create draft release and upload assets") in callers
    assert ("publish", "Re-read uploaded assets from the API and verify byte-for-byte") in callers
    assert ("publish", "Publish the release (irreversible; latest.json enters the update channel)") in callers
    assert ("dry-run-check", "Prove nothing was published") in callers


def test_dry_run_cannot_create_tag_or_release_and_publish_requires_opt_in():
    workflow = load_workflow()
    dry_input = workflow["on"]["workflow_dispatch"]["inputs"]["dry_run"]
    assert dry_input["type"] == "boolean"
    assert dry_input["default"] == "true"

    jobs = _jobs(workflow)
    assert jobs["publish"]["if"] == "${{ !inputs.dry_run }}"
    assert jobs["dry-run-check"]["if"] == "${{ inputs.dry_run }}"
    assert jobs["publish"].get("needs") == "build"
    assert jobs["dry-run-check"].get("needs") == "build"

    for job_name, job in jobs.items():
        for step in _steps(job):
            run = str(step.get("run") or "")
            if job_name != "publish":
                assert "gh release create" not in run
                assert "gh release upload" not in run
                assert "gh release edit" not in run

    publish_runs = "\n".join(str(step.get("run") or "") for step in _steps(jobs["publish"]))
    assert "gh release create" in publish_runs
    dry_runs = "\n".join(str(step.get("run") or "") for step in _steps(jobs["dry-run-check"]))
    assert "releases/tags/" in dry_runs
    assert "dry run 竟然创建了 release" in dry_runs
    assert "dry run 竟然创建了 tag" in dry_runs
    assert "官网" in dry_runs


def test_non_cli_steps_are_not_given_a_workflow_wide_token():
    """构建、验签和公开文件核对不调用 gh，也不应靠全局 Token。"""
    build_steps = _steps(_jobs(load_workflow())["build"])
    names = [step.get("name") for step in build_steps]
    assert "Require production secrets and a matching public key" in names
    assert "Assemble release directory and verify the contract" in names
    for step in build_steps:
        if step_calls_github_cli(step):
            continue
        assert "GH_TOKEN" not in (step.get("env") or {})


def test_parser_rejects_broken_indent():
    with pytest.raises(ValueError, match="缩进"):
        parse_workflow("name: ok\n  dangling: true\n")


REDIST_STEP = "Find and verify the VS2022 VC143 x64 redist"
REGRESSION_STEP = "Regression tests before the release build"
SIDECAR_STEP = "Build sidecar and NSIS installer with the production key"
REQUIRED_DLLS = ("vcruntime140.dll", "vcruntime140_1.dll")


def _named_step(steps: list[dict], name: str) -> dict:
    matches = [step for step in steps if step.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _step_index(steps: list[dict], name: str) -> int:
    return [step.get("name") for step in steps].index(name)


def _script_lines(run: str) -> list[str]:
    return [line.strip() for line in run.splitlines() if line.strip()]


def test_release_discovers_signed_vc143_before_the_sidecar_build():
    """正式构建必须先自动发现并验签 VC143，再进入 Sidecar。

    这是工作流结构检查，不是生产 Dry Run 的执行结果。
    """
    workflow = load_workflow()
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    jobs = _jobs(workflow)
    assert jobs["publish"]["if"] == "${{ !inputs.dry_run }}"
    assert jobs["dry-run-check"]["if"] == "${{ inputs.dry_run }}"
    assert workflow["on"]["workflow_dispatch"]["inputs"]["dry_run"]["default"] == "true"

    build_steps = _steps(jobs["build"])
    redist_at = _step_index(build_steps, REDIST_STEP)
    assert _step_index(build_steps, REGRESSION_STEP) < redist_at
    assert redist_at < _step_index(build_steps, SIDECAR_STEP)

    step = _named_step(build_steps, REDIST_STEP)
    assert step.get("uses") == "./.github/actions/discover-vc143"
    assert "run" not in step
    assert "env" not in step
    assert "GH_TOKEN" not in step
    action = parse_workflow(
        (REPO_ROOT / ".github" / "actions" / "discover-vc143" / "action.yml").read_text(encoding="utf-8")
    )
    action_steps = action["runs"]["steps"]
    assert len(action_steps) == 1
    run = action_steps[0]["run"]
    lines = _script_lines(run)

    vswhere = [line for line in lines if line.startswith("$vsWhere")]
    assert len(vswhere) == 1
    assert "Join-Path" in vswhere[0]
    assert "vswhere.exe" in vswhere[0]
    assert "ProgramFiles(x86)" in vswhere[0]
    assert re.search(r"[A-Za-z]:\\", vswhere[0]) is None

    assert any("VC\\Redist\\MSVC" in line for line in lines)
    version_scan = [line for line in lines if "Get-ChildItem" in line and "Sort-Object Name -Descending" in line]
    assert len(version_scan) == 1
    candidate = [line for line in lines if line.startswith("$candidate =")]
    assert len(candidate) == 1
    assert r"x64\Microsoft.VC143.CRT" in candidate[0]

    presence_at = next(
        index for index, line in enumerate(lines)
        if "Test-Path" in line and "vcruntime140.dll" in line and "vcruntime140_1.dll" not in line
    )
    assert lines[presence_at].endswith("-and")
    assert "Test-Path" in lines[presence_at + 1]
    assert "vcruntime140_1.dll" in lines[presence_at + 1]
    signature_names = [line for line in lines if line.startswith("foreach ($name in")]
    assert len(signature_names) == 1
    assert all(dll in signature_names[0] for dll in REQUIRED_DLLS)
    signature = [line for line in lines if "Get-AuthenticodeSignature" in line]
    assert len(signature) == 1
    assert "$redist" in signature[0]
    guard = [line for line in lines if "$sig.Status" in line]
    assert len(guard) == 1
    assert "'Valid'" in guard[0]
    assert "O=Microsoft Corporation" in guard[0]

    chosen = [line for line in lines if line.startswith("$redist")]
    assert chosen == ["$redist = $candidates[0]"]
    published = [line for line in lines if "YIJING_VC_REDIST_DIR" in line]
    assert published == [
        '"YIJING_VC_REDIST_DIR=$redist" | Out-File -FilePath $env:GITHUB_ENV -Append -Encoding utf8'
    ]
    assert any(line.startswith("Write-Output") and "$redist" in line for line in lines)
    assert re.search(r"YIJING_VC_REDIST_DIR=[A-Za-z]:\\", run) is None
    assert re.search(r"[A-Za-z]:\\Program Files\\Microsoft Visual Studio", run) is None

    candidate_workflow = parse_workflow(
        (REPO_ROOT / ".github" / "workflows" / "windows-rc.yml").read_text(encoding="utf-8")
    )
    candidate_steps = _steps(next(iter(_jobs(candidate_workflow).values())))
    candidate_step = _named_step(candidate_steps, REDIST_STEP)
    assert candidate_step.get("uses") == step["uses"]
    assert "run" not in candidate_step
