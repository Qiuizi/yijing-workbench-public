#!/usr/bin/env python3
"""正式发布预检：把 workflow_dispatch 的输入、ref、SHA 与 Tag 状态一次校验干净。

为什么单独做成脚本：
    这些判断以前分散在 PowerShell 里、用 `${{ inputs.x }}` 直接拼字符串，
    既不好测，也有注入面。这里统一用 Python 处理参数，PowerShell 只传 `$env:`
    列表，任何不合规的输入都会在构建前失败。

不通过就退出 1，不修改任何状态。

用法：
    python scripts/updater/release_preflight.py \
        --version 3.3.2 --confirm 3.3.2 \
        --notes-file docs/release-notes-v3.3.2.md \
        --pinned-sha <40位sha> --ref refs/heads/main \
        --repo Qiuizi/yijing-workbench-public
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.updater.manifest import SEMVER_RE, UpdaterManifestError, assert_versions_consistent  # noqa: E402

ALLOWED_NOTES_PATTERN = re.compile(r"^docs/release-notes-v\d+\.\d+\.\d+\.md$")
MAX_NOTES_BYTES = 64 * 1024
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class PreflightError(RuntimeError):
    """预检失败，消息直接面向维护者。"""


def validate_inputs(version: str, confirm: str, notes_file: str, repo_root: Path | str = _REPO_ROOT) -> dict[str, str]:
    """纯函数：只校验输入本身，不访问网络。"""
    repo_root = Path(repo_root).resolve()
    problems: list[str] = []

    if not SEMVER_RE.match(version or ""):
        problems.append(f"version 不是合法 SemVer：{version!r}")
    elif not re.match(r"^\d+\.\d+\.\d+$", version):
        problems.append(f"正式发布只接受稳定版本号（不允许 - 后缀）：{version}")
    if version != confirm:
        problems.append(f"confirm({confirm!r}) 与 version({version!r}) 不一致")

    notes_rel = (notes_file or "").strip().replace("\\", "/")
    if not notes_rel:
        problems.append("notes_file 不能为空")
    elif not ALLOWED_NOTES_PATTERN.match(notes_rel):
        problems.append(
            f"notes_file 只允许仓库内的 docs/release-notes-v<版本>.md：{notes_file!r}"
        )
    else:
        notes_path = (repo_root / notes_rel).resolve()
        if repo_root not in notes_path.parents:
            problems.append(f"notes_file 越出仓库目录：{notes_file!r}")
        elif not notes_path.is_file():
            problems.append(f"notes_file 不存在：{notes_rel}")
        elif notes_path.stat().st_size > MAX_NOTES_BYTES:
            problems.append(f"notes_file 过大（>{MAX_NOTES_BYTES} 字节）：{notes_rel}")

    try:
        repo_version = assert_versions_consistent(repo_root, expected=version)
    except UpdaterManifestError as error:
        problems.append(str(error))
        repo_version = ""

    if problems:
        raise PreflightError("；".join(problems))
    return {"version": version, "notes_file": notes_rel, "repo_version": repo_version}


def validate_ref(ref: str) -> None:
    if ref != "refs/heads/main":
        raise PreflightError(f"正式发布只能从 main 触发，当前 ref={ref!r}")


def validate_sha(sha: str, git_head: str, main_tip: str | None) -> None:
    if not SHA_RE.match(sha or ""):
        raise PreflightError(f"pinned SHA 非法：{sha!r}")
    if git_head != sha:
        raise PreflightError(f"工作区 HEAD({git_head[:7]}) 与钉住的 SHA({sha[:7]}) 不一致")
    if main_tip is not None and main_tip != sha:
        raise PreflightError(
            f"main 已前进到 {main_tip[:7]}，与本次钉住的 {sha[:7]} 不一致；请重新触发发布"
        )


def _gh_json(api_path: str) -> dict | None:
    """读取 gh api 的 JSON 对象。

    拿原始字节再按 UTF-8 解码。Windows Runner 上 text=True 会用 CP1252
    在读线程里解码；中文提交说明里的字节（例如 0x8F）解不开时，异常留在
    读线程，stdout 变成 None，json.loads 接着抛 TypeError。
    只有退出码非 0 且 stderr 明确包含 Not Found / 404，才表示资源不存在。
    """
    try:
        result = subprocess.run(
            ["gh", "api", api_path],
            capture_output=True,
            text=False,
            check=False,
        )
    except OSError as error:
        raise PreflightError(f"gh 不可执行：{error}") from error

    stderr = (result.stderr or b"").decode("utf-8", errors="replace")
    if result.returncode != 0:
        if "Not Found" in stderr or "404" in stderr:
            return None
        detail = stderr.strip()[:200] or f"exit {result.returncode}"
        raise PreflightError(f"gh api {api_path} 失败：{detail}")

    raw = result.stdout
    if raw is None or not raw.strip():
        raise PreflightError(f"gh api {api_path} 返回空响应")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PreflightError(f"gh api {api_path} 的响应不是 UTF-8：{error}") from error
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise PreflightError(f"gh api {api_path} 返回的不是 JSON：{error}") from error
    if not isinstance(data, dict):
        raise PreflightError(f"gh api {api_path} 返回的 JSON 不是对象：{type(data).__name__}")
    return data


def ensure_tag_absent(repo: str, tag: str, git_tags: str) -> None:
    if tag in {line.strip() for line in git_tags.splitlines() if line.strip()}:
        raise PreflightError(f"本地已存在 tag {tag}，正式发布不允许覆盖历史版本")
    existing = _gh_json(f"repos/{repo}/releases/tags/{tag}")
    if existing is not None:
        raise PreflightError(f"GitHub 上已存在 release {tag}（id={existing.get('id')}），拒绝覆盖")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="正式发布预检")
    parser.add_argument("--version", required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--notes-file", required=True)
    parser.add_argument("--pinned-sha", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--git-head", default=None, help="默认取 git rev-parse HEAD")
    parser.add_argument("--git-tags", default=None, help="默认取 git tag -l")
    parser.add_argument("--main-tip", default=None, help="默认调 GitHub API 取 main 顶端")
    args = parser.parse_args(argv)

    try:
        summary = validate_inputs(args.version, args.confirm, args.notes_file)
        validate_ref(args.ref)

        head = args.git_head
        if head is None:
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        tags = args.git_tags
        if tags is None:
            tags = subprocess.check_output(["git", "tag", "-l"], text=True)
        main_tip = args.main_tip
        if main_tip is None:
            data = _gh_json(f"repos/{args.repo}/commits/main") or {}
            main_tip = str(data.get("sha") or "") or None

        validate_sha(args.pinned_sha, head, main_tip)
        ensure_tag_absent(args.repo, f"v{args.version}", tags)
    except (PreflightError, UpdaterManifestError) as error:
        print(f"FAIL  {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(f"FAIL  无法读取 git 状态：{error}", file=sys.stderr)
        return 1

    summary.update({"sha": args.pinned_sha, "tag": f"v{args.version}", "ref": args.ref})
    print("OK    " + json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
