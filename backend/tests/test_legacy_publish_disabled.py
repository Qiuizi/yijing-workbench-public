"""遗留一次性发布工作流必须保持禁用。

只解析仓库里的 workflow 文件，不触发 release.yml，不创建 tag 或 Release。
job 级 `if: false` 必须是未加引号的布尔值。引号字符串在 GitHub Actions 里是真值。
解析器会去掉引号，所以禁用判定以源码中的 job 级 if 为准。
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


def _step_blob(job: dict) -> str:
    return "\n".join(_run(step) for step in _steps(job))


def _unquoted_false_lines(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.strip() == "if: false" and not line.lstrip().startswith("#")
    ]


def _raw_job_ifs(text: str) -> dict[str, str | None]:
    """返回每个 job 的源码级 if 值，不去掉引号。没有 if 时为 None。"""
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line == "jobs:")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line and not line.startswith(" ") and not line.lstrip().startswith("#"):
            end = index
            break

    found: dict[str, str | None] = {}
    current: str | None = None
    for line in lines[start + 1 : end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent == 2 and line.rstrip().endswith(":") and not line.strip().startswith("- "):
            current = line.strip()[:-1]
            found[current] = None
            continue
        if current is not None and indent == 4 and line.strip().startswith("if:"):
            found[current] = line.strip()[3:].strip()
    return found


def _job_writes_release_or_main(job: dict) -> bool:
    blob = _step_blob(job)
    return any(command in blob for command in (*RELEASE_COMMANDS, *MAIN_WRITE_COMMANDS))


def _enabled_publish_jobs(text: str) -> list[tuple[str, str | None]]:
    workflow = parse_workflow(text)
    raw_ifs = _raw_job_ifs(text)
    found: list[tuple[str, str | None]] = []
    for name, job in _jobs(workflow).items():
        if not _job_writes_release_or_main(job):
            continue
        condition = raw_ifs[name]
        if condition == "false":
            continue
        found.append((name, condition))
    return found


def test_live_repository_guard_is_not_treated_as_disabled():
    """仓库名守卫曾经会放行正式仓库。它不是禁用。"""
    text = "\n".join(
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
    assert _enabled_publish_jobs(text) == [
        ("verify-and-publish", "github.repository == 'Qiuizi/yijing-workbench-public'")
    ]


def test_quoted_false_on_a_publish_job_is_still_enabled():
    """引号里的 false 不是布尔 false。旁边另一个 job 的真 if: false 不能替它免检。"""
    text = "\n".join(
        [
            "name: example",
            "on:",
            "  workflow_dispatch:",
            "jobs:",
            "  safe:",
            "    if: false",
            "    runs-on: ubuntu-24.04",
            "    steps:",
            "      - run: echo ok",
            "  verify-and-publish:",
            "    if: 'false'",
            "    runs-on: ubuntu-24.04",
            "    steps:",
            "      - run: gh release create v3.3.1",
            "",
        ]
    )
    assert _raw_job_ifs(text)["safe"] == "false"
    assert _raw_job_ifs(text)["verify-and-publish"] == "'false'"
    assert _enabled_publish_jobs(text) == [("verify-and-publish", "'false'")]


def test_v331_publish_job_and_publish_step_never_run():
    text = _text("publish-v3.3.1.yml")
    workflow = parse_workflow(text)
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    assert "contents: write" not in text

    jobs = _jobs(workflow)
    assert list(jobs) == ["verify-and-publish"]
    assert _raw_job_ifs(text) == {"verify-and-publish": "false"}
    assert _unquoted_false_lines(text) == ["    if: false", "        if: false"]

    publish_steps = [step for step in _steps(jobs["verify-and-publish"]) if "gh release create" in _run(step)]
    assert len(publish_steps) == 1
    assert publish_steps[0]["if"] == "false"
    assert "git push" not in _run(publish_steps[0])
    assert _enabled_publish_jobs(text) == []


def test_historical_v331_file_is_retained_not_deleted():
    text = _text("publish-v3.3.1.yml")
    assert "gh release create v3.3.1" in text
    assert "yijing-workbench-3.3.1-x64-setup.exe" in text
    assert (WORKFLOWS / "publish-v3.3.1.yml").is_file()


def test_every_legacy_publisher_job_is_unconditionally_disabled():
    for name in LEGACY_PUBLISHERS:
        text = _text(name)
        assert _unquoted_false_lines(text), name
        raw_ifs = _raw_job_ifs(text)
        assert raw_ifs, name
        for job_name, condition in raw_ifs.items():
            assert condition == "false", f"{name}:{job_name} 仍可能执行，if={condition!r}"
        assert _enabled_publish_jobs(text) == []


def test_no_other_enabled_release_or_main_write_path():
    enabled: list[tuple[str, str, str | None]] = []
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for job_name, condition in _enabled_publish_jobs(path.read_text(encoding="utf-8")):
            enabled.append((path.name, job_name, condition))

    assert enabled == [(CURRENT_PUBLISHER, "publish", "${{ !inputs.dry_run }}")]
