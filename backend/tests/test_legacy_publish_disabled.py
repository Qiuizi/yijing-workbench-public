"""遗留一次性发布工作流必须保持禁用。

只解析仓库里的 workflow 文件，不触发 release.yml，不创建 tag 或 Release。
`if: false` 必须是未加引号的布尔值。引号字符串在 GitHub Actions 里可能被当成真值。
"""

from __future__ import annotations

from pathlib import Path

from backend.tests.test_release_workflow_auth import parse_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
LEGACY_PUBLISHERS = ("publish-v3.3.0.yml", "publish-v3.3.1.yml")
CURRENT_PUBLISHER = "release.yml"
RELEASE_COMMANDS = ("gh release create", "gh release upload", "gh release edit")
MAIN_WRITE_COMMANDS = ("git push", "git commit")


def _text(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def _workflow(name: str) -> dict:
    return parse_workflow(_text(name))


def _jobs(workflow: dict) -> dict[str, dict]:
    jobs = workflow["jobs"]
    assert isinstance(jobs, dict) and jobs
    return jobs


def _steps(job: dict) -> list[dict]:
    steps = job.get("steps") or []
    assert isinstance(steps, list)
    assert all(isinstance(step, dict) for step in steps)
    return steps


def _run(step: dict) -> str:
    return str(step.get("run") or "")


def _unquoted_false_lines(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.strip() == "if: false" and not line.lstrip().startswith("#")
    ]


def _is_unconditionally_disabled(job: dict) -> bool:
    return job.get("if") == "false"


def _contains_publish_command(job: dict) -> bool:
    blob = "\n".join(_run(step) for step in _steps(job))
    return any(command in blob for command in RELEASE_COMMANDS)


def _contains_main_write(job: dict) -> bool:
    blob = "\n".join(_run(step) for step in _steps(job))
    return any(command in blob for command in MAIN_WRITE_COMMANDS)


def _enabled_publish_jobs(workflow: dict) -> list[tuple[str, str | None]]:
    found: list[tuple[str, str | None]] = []
    for name, job in _jobs(workflow).items():
        if not (_contains_publish_command(job) or _contains_main_write(job)):
            continue
        if _is_unconditionally_disabled(job):
            continue
        found.append((name, job.get("if")))
    return found


def test_live_repository_guard_is_not_treated_as_disabled():
    """仓库名守卫曾经会放行正式仓库。它不是禁用。"""
    workflow = parse_workflow(
        "\n".join(
            [
                "name: example",
                "on:",
                "  workflow_dispatch:",
                "permissions:",
                "  contents: write",
                "jobs:",
                "  verify-and-publish:",
                "    if: github.repository == 'Qiuizi/yijing-workbench-public'",
                "    runs-on: ubuntu-24.04",
                "    steps:",
                "      - name: publish",
                "        if: github.event_name == 'push'",
                "        run: gh release create v3.3.1",
                "",
            ]
        )
    )
    assert _enabled_publish_jobs(workflow) == [
        ("verify-and-publish", "github.repository == 'Qiuizi/yijing-workbench-public'")
    ]


def test_quoted_false_is_not_an_unquoted_disable():
    """解析器会去掉引号。源码行必须是未加引号的 `if: false`，否则不算禁用。"""
    assert _unquoted_false_lines("    if: 'false'\n    if: \"false\"\n") == []
    assert _unquoted_false_lines("    if: false\n") == ["    if: false"]
    assert _unquoted_false_lines("    # if: false\n") == []


def test_v331_publish_job_and_publish_step_never_run():
    text = _text("publish-v3.3.1.yml")
    workflow = parse_workflow(text)
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    assert "contents: write" not in text

    jobs = _jobs(workflow)
    assert list(jobs) == ["verify-and-publish"]
    job = jobs["verify-and-publish"]
    assert _is_unconditionally_disabled(job)
    assert _unquoted_false_lines(text) == ["    if: false", "        if: false"]

    publish_steps = [
        step for step in _steps(job) if _contains_publish_command({"steps": [step]})
    ]
    assert len(publish_steps) == 1
    assert publish_steps[0]["if"] == "false"
    assert "gh release create" in _run(publish_steps[0])
    assert "git push" not in _run(publish_steps[0])
    assert _enabled_publish_jobs(workflow) == []


def test_historical_v331_file_is_retained_not_deleted():
    text = _text("publish-v3.3.1.yml")
    assert "gh release create v3.3.1" in text
    assert "yijing-workbench-3.3.1-x64-setup.exe" in text
    assert (WORKFLOWS / "publish-v3.3.1.yml").is_file()


def test_every_legacy_publisher_job_is_unconditionally_disabled():
    for name in LEGACY_PUBLISHERS:
        text = _text(name)
        workflow = _workflow(name)
        assert _unquoted_false_lines(text), name
        for job_name, job in _jobs(workflow).items():
            assert _is_unconditionally_disabled(job), f"{name}:{job_name} 仍可能执行"
            if _contains_publish_command(job) or _contains_main_write(job):
                assert job["if"] == "false"


def test_no_other_enabled_release_or_main_write_path():
    enabled: list[tuple[str, str, str | None]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        workflow = parse_workflow(path.read_text(encoding="utf-8"))
        for job_name, condition in _enabled_publish_jobs(workflow):
            enabled.append((path.name, job_name, condition))

    assert enabled == [(CURRENT_PUBLISHER, "publish", "${{ !inputs.dry_run }}")]

    release = _workflow(CURRENT_PUBLISHER)
    assert set(release["on"]) == {"workflow_dispatch"}
    dry_run = release["on"]["workflow_dispatch"]["inputs"]["dry_run"]
    assert dry_run["type"] == "boolean"
    assert dry_run["default"] == "true"
    assert _jobs(release)["publish"]["permissions"] == {"contents": "write"}
    assert _jobs(release)["build"].get("permissions") is None
    assert release["permissions"]["contents"] == "read"
