"""检查 NSIS 安装包内容，确保用户真的能拿到桌面应用。

发布门禁不能只看「安装包哈希与签名正确」：2026-11-02 的 v3.3.2 正式资产
签名与哈希全部通过，但 Tauri CLI 把 `verify-updater-signature` 当成了主程序，
安装包里根本没有 `yijing-workbench.exe`。用户安装/升级后应用消失。

因此这里用 7-Zip 读取 NSIS 容器（不执行安装包），至少验证：
- 根目录存在主程序 `yijing-workbench.exe`；
- 存在 Python sidecar `binaries/yijing-backend/yijing-backend.exe`；
- 安装包没有夹带发布门禁内部工具 `verify-updater-signature.exe`。

7-Zip 缺失时 fail closed：发布门禁不能因为环境缺工具而静默跳过。
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path, PurePosixPath

SEVEN_ZIP_NAMES = ("7z", "7za", "7zz", "7z.exe", "7za.exe")
DEFAULT_MAIN_EXE = "yijing-workbench.exe"
DEFAULT_SIDECAR = "binaries/yijing-backend/yijing-backend.exe"
DEFAULT_FORBIDDEN = ("verify-updater-signature.exe",)


class InstallerContentsError(ValueError):
    """安装包无法读取或结构不符合发布契约。"""


def _seven_zip() -> str | None:
    for name in SEVEN_ZIP_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


def _normalize(path: str) -> str:
    return str(PurePosixPath(path.replace("\\", "/"))).lstrip("./")


def list_nsis_files(installer: Path, *, seven_zip: str | None = None) -> set[str]:
    """返回安装包内的文件路径（正斜杠、相对路径）。

    只读取容器，不执行安装包。7-Zip 不可用或读取失败时抛出
    `InstallerContentsError`，由调用方转成发布阻断。
    """
    executable = seven_zip or _seven_zip()
    if not executable:
        raise InstallerContentsError("找不到 7z，无法检查安装包内容（发布门禁拒绝跳过）")
    result = subprocess.run(
        [executable, "l", "-slt", str(installer)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise InstallerContentsError(
            f"7z 无法读取安装包（exit={result.returncode}）：{detail[-1] if detail else '无输出'}"
        )

    entries: set[str] = set()
    for line in result.stdout.splitlines():
        if not line.startswith("Path = "):
            continue
        raw = line[len("Path = "):].strip()
        if not raw:
            continue
        normalized = _normalize(raw)
        # 7z 先输出归档文件自身；它不是安装内容。
        if normalized in {_normalize(str(installer)), _normalize(installer.name)}:
            continue
        entries.add(normalized)
    if not entries:
        raise InstallerContentsError("7z 没有返回任何安装文件条目")
    return entries


def verify_nsis_contents(
    installer: Path,
    *,
    expected_main: str = DEFAULT_MAIN_EXE,
    expected_sidecar: str = DEFAULT_SIDECAR,
    forbidden: tuple[str, ...] = DEFAULT_FORBIDDEN,
    seven_zip: str | None = None,
) -> list[str]:
    """返回问题列表；空列表表示安装包内容符合契约。"""
    try:
        files = list_nsis_files(installer, seven_zip=seven_zip)
    except InstallerContentsError as error:
        return [str(error)]

    problems: list[str] = []
    root_names = {
        PurePosixPath(path).name
        for path in files
        if PurePosixPath(path).parent == PurePosixPath(".")
    }
    if expected_main not in root_names:
        shown = ", ".join(sorted(root_names)) or "空"
        problems.append(f"安装包根目录缺少主程序 {expected_main}（根目录实际内容：{shown}）")
    if expected_sidecar and _normalize(expected_sidecar) not in files:
        problems.append(f"安装包缺少 Python sidecar {expected_sidecar}")
    for name in forbidden:
        if any(PurePosixPath(path).name == name for path in files):
            problems.append(f"安装包不应包含发布门禁内部工具 {name}")
    return problems
