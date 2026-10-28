"""发布 CI 门禁的反向测试：缺检查、失败、取消、超时、跨提交都必须拦住。

这些用例模拟 GitHub API 的真实返回，不访问网络。
"""

from pathlib import Path

import pytest

from scripts.updater.ci_gate import ALLOWED_EVENTS, REQUIRED_WORKFLOWS, evaluate

SHA = "a" * 40
OTHER_SHA = "b" * 40


def workflow_run(
    path: str,
    *,
    sha: str = SHA,
    status: str = "completed",
    conclusion: str = "success",
    event: str = "push",
    run_number: int = 1,
    created_at: str = "2026-10-27T10:00:00Z",
) -> dict:
    return {
        "path": path,
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "event": event,
        "run_number": run_number,
        "created_at": created_at,
    }


def check_run(
    name: str,
    *,
    sha: str = SHA,
    status: str = "completed",
    conclusion: str = "success",
    app_slug: str = "github-actions",
    started_at: str = "2026-10-27T10:00:00Z",
) -> dict:
    return {
        "name": name,
        "head_sha": sha,
        "status": status,
        "conclusion": conclusion,
        "app": {"slug": app_slug},
        "started_at": started_at,
    }


def all_green_runs() -> list[dict]:
    runs: list[dict] = []
    for workflow in REQUIRED_WORKFLOWS:
        runs.append(workflow_run(workflow.path))
    return runs


def all_green_checks() -> list[dict]:
    return [check_run(name) for workflow in REQUIRED_WORKFLOWS for name in workflow.checks]


def test_all_required_workflows_success_is_ok():
    report = evaluate(all_green_runs(), SHA, check_runs=all_green_checks())
    assert report.ok is True
    assert report.problems == []
    assert len(report.rows) == len(REQUIRED_WORKFLOWS)


@pytest.mark.parametrize("missing", [workflow.path for workflow in REQUIRED_WORKFLOWS])
def test_missing_workflow_blocks_release(missing: str):
    runs = [run for run in all_green_runs() if run["path"] != missing]
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is False
    assert any(missing in item and "没有这次工作流的运行记录" in item for item in report.problems)


@pytest.mark.parametrize(
    "status,conclusion,keyword",
    [
        ("completed", "failure", "结论不是 success"),
        ("completed", "cancelled", "结论不是 success"),
        ("completed", "timed_out", "结论不是 success"),
        ("completed", "skipped", "结论不是 success"),
        ("in_progress", "", "尚未完成"),
        ("queued", "", "尚未完成"),
    ],
)
def test_bad_conclusion_blocks_release(status: str, conclusion: str, keyword: str):
    runs = all_green_runs()
    runs[0] = workflow_run(REQUIRED_WORKFLOWS[0].path, status=status, conclusion=conclusion)
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is False
    assert any(keyword in item for item in report.problems)


def test_runs_from_other_commit_are_not_reused():
    runs = [workflow_run(w.path, sha=OTHER_SHA) for w in REQUIRED_WORKFLOWS]
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is False
    assert all("没有这次工作流的运行记录" in item for item in report.problems)


def test_pull_request_event_is_not_accepted():
    """PR 的合并测试提交不能当正式发布的绿灯。"""
    runs = [workflow_run(w.path, event="pull_request") for w in REQUIRED_WORKFLOWS]
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is False
    assert all("触发事件不被接受" in item for item in report.problems)
    assert "pull_request" not in ALLOWED_EVENTS


def test_manual_dispatch_is_accepted():
    runs = [workflow_run(w.path, event="workflow_dispatch") for w in REQUIRED_WORKFLOWS]
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is True


def test_latest_run_wins_when_earlier_failed():
    runs = all_green_runs()
    runs.append(workflow_run(REQUIRED_WORKFLOWS[0].path, conclusion="failure", run_number=1))
    runs[0] = workflow_run(REQUIRED_WORKFLOWS[0].path, run_number=2)
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is True


def test_newer_failure_after_success_is_blocked():
    runs = all_green_runs()
    runs.append(workflow_run(REQUIRED_WORKFLOWS[0].path, conclusion="failure", run_number=9))
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is False


def test_missing_check_run_detects_skipped_job():
    """workflow 整体 success 但 job 被跳过时，check run 不存在 → 必须拦住。"""
    checks = [run for run in all_green_checks() if run["name"] != "Backend regression tests"]
    report = evaluate(all_green_runs(), SHA, check_runs=checks)
    assert report.ok is False
    assert any("缺少 check run：Backend regression tests" in item for item in report.problems)


def test_same_named_check_from_other_app_is_ignored():
    checks = all_green_checks()
    checks = [run for run in checks if run["name"] != "website-validation"]
    checks.append(check_run("website-validation", app_slug="someone-else"))
    report = evaluate(all_green_runs(), SHA, check_runs=checks)
    assert report.ok is False
    assert any("缺少 check run：website-validation" in item for item in report.problems)


def test_check_run_from_other_sha_is_ignored():
    checks = all_green_checks()
    checks = [run for run in checks if run["name"] != "Frontend tests and build"]
    checks.append(check_run("Frontend tests and build", sha=OTHER_SHA))
    report = evaluate(all_green_runs(), SHA, check_runs=checks)
    assert report.ok is False


def test_failed_check_run_blocks_even_when_workflow_succeeded():
    checks = all_green_checks()
    checks = [run for run in checks if run["name"] != "Windows x64 tests and NSIS candidate"]
    checks.append(check_run("Windows x64 tests and NSIS candidate", conclusion="failure"))
    report = evaluate(all_green_runs(), SHA, check_runs=checks)
    assert report.ok is False
    assert any("check run 未通过" in item for item in report.problems)


def test_invalid_sha_is_rejected():
    report = evaluate(all_green_runs(), "main")
    assert report.ok is False
    assert "40 位十六进制" in report.problems[0]


def test_repository_main_sha_is_currently_blocked():
    """这条是「现状证据」：main 的 tip 现在只有 windows-rc + pages 两类运行。

    若哪天四个工作流都覆盖了 main，这条测试会失败，提示把断言更新为 ok。
    """
    runs = [
        workflow_run(".github/workflows/pages.yml"),
        workflow_run(".github/workflows/windows-rc.yml"),
    ]
    report = evaluate(runs, SHA, check_runs=None)
    assert report.ok is False
    blocked_paths = {item.split(":")[0] for item in report.problems}
    assert ".github/workflows/v1-learning-ci.yml" in blocked_paths
    assert ".github/workflows/website-ci.yml" in blocked_paths
    assert ".github/workflows/windows-rc.yml" not in blocked_paths
