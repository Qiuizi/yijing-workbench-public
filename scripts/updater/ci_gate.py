#!/usr/bin/env python3
"""正式发布前置门禁：这个 SHA 上的四条必需检查必须全部真实通过。

为什么按**工作流文件路径**判定，而不是只按名字：
    同名的 check run 可能来自别的工作流或别的 App（本仓库的 Pages 工作流就会
    产出 `build` / `deploy` 这种通用名字）。只看名字会把无关结果当成绿灯。
    这里同时核对：
      - `.github/workflows/<file>.yml` 的 run 必须存在于**该 SHA** 上；
      - 事件必须是 push / workflow_dispatch（PR 的合并测试提交不算）；
      - 最新的那次 run 必须 completed + success；
      - 可选：对应 job 的 check run 也必须 completed + success
        （workflow 整体 success 但 job 被 if 跳过时，这里会暴露出来）。

任何一项不满足都不允许继续发布；本模块只做判断，不修改任何状态。

用法：
    python scripts/updater/ci_gate.py --repo Qiuizi/yijing-workbench-public --sha <40位sha>
    python scripts/updater/ci_gate.py --input-dir <含 runs.json / check-runs.json 的目录> --sha <sha>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


@dataclass(frozen=True)
class RequiredWorkflow:
    path: str
    checks: tuple[str, ...]


REQUIRED_WORKFLOWS: tuple[RequiredWorkflow, ...] = (
    RequiredWorkflow(
        ".github/workflows/windows-rc.yml",
        ("Windows x64 tests and NSIS candidate",),
    ),
    RequiredWorkflow(
        ".github/workflows/v1-learning-ci.yml",
        ("Frontend tests and build", "Backend regression tests"),
    ),
    RequiredWorkflow(
        ".github/workflows/website-ci.yml",
        ("website-validation",),
    ),
)

ALLOWED_EVENTS = frozenset({"push", "workflow_dispatch"})
TERMINAL_BAD_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "action_required", "startup_failure", "stale", "skipped"}
)
CHECK_APP_SLUG = "github-actions"


@dataclass
class GateReport:
    sha: str
    ok: bool
    problems: list[str]
    rows: list[dict[str, str]]

    def lines(self) -> list[str]:
        out = [f"source sha: {self.sha}"]
        for row in self.rows:
            out.append(
                f"  {'OK  ' if row['ok'] == 'yes' else 'FAIL'} {row['workflow']:<42} {row['detail']}"
            )
        return out


def _run_sort_key(run: dict[str, Any]) -> tuple[int, str]:
    # run_number 在同一工作流内单调递增；created_at 兜底
    try:
        number = int(run.get("run_number") or 0)
    except (TypeError, ValueError):
        number = 0
    return (number, str(run.get("created_at") or ""))


def _pick_latest(runs: Iterable[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = list(runs)
    if not candidates:
        return None
    return max(candidates, key=_run_sort_key)


def _evaluate_run(run: dict[str, Any] | None, sha: str) -> tuple[bool, str]:
    if run is None:
        return False, "该 SHA 上没有这次工作流的运行记录"
    if str(run.get("head_sha") or "") != sha:
        return False, f"运行属于其它提交（{str(run.get('head_sha') or '?')[:7]}）"
    event = str(run.get("event") or "")
    if event not in ALLOWED_EVENTS:
        return False, f"触发事件不被接受（{event or '?'}）"
    status = str(run.get("status") or "")
    conclusion = str(run.get("conclusion") or "")
    if status != "completed":
        return False, f"尚未完成（{status or '?'}）"
    if conclusion != "success":
        return False, f"结论不是 success（{conclusion or '?'}）"
    return True, f"success · run {run.get('run_number') or '?'} · {event}"


def _check_run_problems(
    check_runs: Sequence[dict[str, Any]] | None,
    sha: str,
    workflow: RequiredWorkflow,
) -> list[str]:
    if check_runs is None:
        return []
    problems: list[str] = []
    for name in workflow.checks:
        same_name = [
            run
            for run in check_runs
            if run.get("name") == name
            and str((run.get("app") or {}).get("slug") or "") == CHECK_APP_SLUG
            and str(run.get("head_sha") or "") == sha
        ]
        latest = _pick_latest(same_name)
        if latest is None:
            problems.append(f"缺少 check run：{name}（可能该 job 被条件跳过）")
            continue
        if latest.get("status") != "completed" or latest.get("conclusion") != "success":
            problems.append(
                f"check run 未通过：{name}（{latest.get('status')}/{latest.get('conclusion')}）"
            )
    return problems


def evaluate(
    runs: Sequence[dict[str, Any]],
    sha: str,
    *,
    check_runs: Sequence[dict[str, Any]] | None = None,
    required: Sequence[RequiredWorkflow] = REQUIRED_WORKFLOWS,
) -> GateReport:
    """纯函数：给定 GitHub API 返回，判断该 SHA 是否可以进入发布。"""
    sha = sha.strip().lower()
    problems: list[str] = []
    rows: list[dict[str, str]] = []

    if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha):
        return GateReport(sha=sha, ok=False, problems=["sha 不是 40 位十六进制提交号"], rows=[])

    for workflow in required:
        same_workflow = [
            run
            for run in runs
            if str(run.get("path") or "") == workflow.path and str(run.get("head_sha") or "") == sha
        ]
        latest = _pick_latest(same_workflow)
        ok, detail = _evaluate_run(latest, sha)
        if not ok:
            problems.append(f"{workflow.path}: {detail}")
        extra = _check_run_problems(check_runs, sha, workflow)
        problems.extend(f"{workflow.path}: {item}" for item in extra)
        rows.append(
            {
                "workflow": workflow.path,
                "ok": "yes" if ok and not extra else "no",
                "detail": detail if not extra else f"{detail}；" + "；".join(extra),
            }
        )

    return GateReport(sha=sha, ok=not problems, problems=problems, rows=rows)


def _gh_api(path: str) -> Any:
    """读取 gh api。与预检相同，避开 Windows CP1252 文本模式。

    actions/runs 的 head_commit.message 含中文。text=True 时读线程用
    CP1252 解码失败，stdout 变成 None，json.loads 再抛 TypeError。
    """
    try:
        result = subprocess.run(
            ["gh", "api", path],
            capture_output=True,
            text=False,
            check=False,
        )
    except OSError as error:
        raise RuntimeError(f"gh 不可执行：{error}") from error

    stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
    if result.returncode != 0:
        raise RuntimeError(f"gh api {path} 失败：{stderr[:200] or f'exit {result.returncode}'}")
    raw = result.stdout
    if raw is None or not raw.strip():
        raise RuntimeError(f"gh api {path} 返回空响应")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"gh api {path} 的响应不是 UTF-8：{error}") from error
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"gh api {path} 返回的不是 JSON：{error}") from error


def collect_from_api(repo: str, sha: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    runs = _gh_api(f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100").get("workflow_runs", [])
    checks = _gh_api(f"repos/{repo}/commits/{sha}/check-runs?per_page=100").get("check_runs", [])
    return runs, checks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="正式发布 CI 门禁")
    parser.add_argument("--repo", default="")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--input-dir", type=Path, default=None, help="离线模式：读 runs.json / check-runs.json")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.input_dir:
        runs = json.loads((args.input_dir / "runs.json").read_text(encoding="utf-8"))
        check_path = args.input_dir / "check-runs.json"
        checks = json.loads(check_path.read_text(encoding="utf-8")) if check_path.exists() else None
        runs = runs.get("workflow_runs", runs) if isinstance(runs, dict) else runs
        checks = checks.get("check_runs", checks) if isinstance(checks, dict) else checks
    else:
        if not args.repo:
            parser.error("需要 --repo 或 --input-dir")
        runs, checks = collect_from_api(args.repo, args.sha)

    report = evaluate(runs, args.sha, check_runs=checks)
    for line in report.lines():
        print(line)
    if report.problems:
        print("\n阻断项：", file=sys.stderr)
        for item in report.problems:
            print(f"  - {item}", file=sys.stderr)
    if args.json_out:
        args.json_out.write_text(
            json.dumps(
                {"sha": report.sha, "ok": report.ok, "problems": report.problems, "rows": report.rows},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
