"""Tauri Updater 更新清单（latest.json）的构造与校验。

三件事必须分开，不能互相替代：
  1. Tauri Updater 签名（minisign/ed25519，`.sig`）：证明更新包由持有私钥的人构建；
  2. SHA-256（SHA256SUMS.txt）：证明字节完整；
  3. Windows Authenticode：操作系统层面的发布者签名（本仓库当前未提供）。

本模块只做「清单结构 + 版本一致性 + 资产指向」的静态校验，真正的密码学验证
由 Tauri updater 在安装时完成（错签名/被篡改的包会被拒绝安装）。
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$")
WINDOWS_TARGET = "windows-x86_64"
SIGNATURE_MIN_LINES = 3

# 允许出现版本号的所有来源；新增来源时必须同步这里，否则一致性检查会漏。
VERSION_SOURCES = (
    ("frontend/package.json", ("version",)),
    ("frontend/package-lock.json", ("version",)),
    ("frontend/package-lock.json", ("packages", "", "version")),
    ("frontend/src-tauri/tauri.conf.json", ("version",)),
)


class UpdaterManifestError(ValueError):
    """清单或版本信息不符合发布契约。"""


# 公开发布时的规范资产名（与 v3.3.1 既有约定一致；只是重命名，字节不变）
CANONICAL_ASSET = "yijing-workbench-{version}-x64-setup.exe"
VERSION_IN_NAME = re.compile(r"(?:^|[_-])(\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+?)?)[_-]x64-setup\.exe$")


@dataclass(frozen=True)
class BundleAsset:
    path: Path
    filename: str
    signature: str
    source_name: str = ""


def _dig(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_versions(repo_root: Path | str) -> dict[str, str]:
    """收集所有构建版本号来源，返回 {来源描述: 版本}。"""
    repo_root = Path(repo_root)
    versions: dict[str, str] = {}
    for relative, path in VERSION_SOURCES:
        data = read_json(repo_root / relative)
        value = _dig(data, path)
        label = relative if len(path) == 1 else f"{relative}:{'.'.join(path)}"
        versions[label] = str(value) if value is not None else ""

    cargo = (repo_root / "frontend/src-tauri/Cargo.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', cargo, re.MULTILINE)
    versions["frontend/src-tauri/Cargo.toml"] = match.group(1) if match else ""

    lock = (repo_root / "frontend/src-tauri/Cargo.lock").read_text(encoding="utf-8")
    lock_match = re.search(r'name = "yijing-workbench"\r?\nversion = "([^"]+)"', lock)
    versions["frontend/src-tauri/Cargo.lock"] = lock_match.group(1) if lock_match else ""

    backend = (repo_root / "backend/main.py").read_text(encoding="utf-8")
    backend_match = re.search(r'version="([^"]+)"', backend)
    versions["backend/main.py"] = backend_match.group(1) if backend_match else ""

    return versions


def app_version(repo_root: Path | str) -> str:
    repo_root = Path(repo_root)
    return str(read_json(repo_root / "frontend/src-tauri/tauri.conf.json")["version"])


def assert_versions_consistent(repo_root: Path | str, expected: str | None = None) -> str:
    """全部来源必须同版本、且是合法 SemVer；返回该版本。"""
    repo_root = Path(repo_root)
    versions = collect_versions(repo_root)
    empty = [name for name, value in versions.items() if not value]
    if empty:
        raise UpdaterManifestError(f"以下位置读不到版本号：{', '.join(empty)}")
    unique = sorted(set(versions.values()))
    if len(unique) != 1:
        detail = "；".join(f"{name}={value}" for name, value in versions.items())
        raise UpdaterManifestError(f"版本号不一致：{detail}")
    version = unique[0]
    if not SEMVER_RE.match(version):
        raise UpdaterManifestError(f"版本号不是合法 SemVer：{version}")
    if expected is not None and version != expected:
        raise UpdaterManifestError(f"构建版本 {version} 与期望的 {expected} 不一致")
    return version


def decode_signature(signature: str) -> list[str] | None:
    """Tauri 的 .sig 是「整份 minisign 文件的 base64」，不是明文多行文本。

    解出来至少要有 3 行，且首行是 untrusted comment、含 trusted comment。
    返回解码后的行列表；不符合格式返回 None。
    """
    compact = "".join(signature.split())
    if not compact:
        return None
    try:
        decoded = base64.b64decode(compact, validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    lines = [line for line in decoded.splitlines() if line.strip()]
    if len(lines) < SIGNATURE_MIN_LINES:
        return None
    if not lines[0].startswith("untrusted comment:"):
        return None
    if not any(line.startswith("trusted comment:") for line in lines):
        return None
    return lines


def read_signature(path: Path) -> str:
    if not path.exists():
        raise UpdaterManifestError(f"缺少签名文件：{path.name}")
    signature = path.read_text(encoding="utf-8").strip()
    if not signature:
        raise UpdaterManifestError(f"签名文件为空：{path.name}")
    if decode_signature(signature) is None:
        raise UpdaterManifestError(f"签名文件不是 Tauri/minisign 格式：{path.name}")
    return signature


def find_installer(bundle_dir: Path) -> Path:
    installers = sorted(path for path in bundle_dir.glob("*setup.exe") if path.is_file())
    if len(installers) != 1:
        raise UpdaterManifestError(f"应有且仅有一个 NSIS 安装包，实际 {len(installers)} 个")
    return installers[0]


def canonical_asset_name(version: str) -> str:
    return CANONICAL_ASSET.format(version=version)


def collect_bundle(bundle_dir: Path, version: str) -> BundleAsset:
    """找到唯一的 NSIS 安装包 + 同名 .sig，并给出公开发布用的规范名。

    Tauri 的原始产物名形如 `<productName>_<version>_x64-setup.exe`；公开下载统一
    重命名为 `yijing-workbench-<version>-x64-setup.exe`（与 v3.3.1 一致）。
    重命名不影响签名：`.sig` 是对文件字节签名，与文件名无关。
    """
    installer = find_installer(bundle_dir)
    match = VERSION_IN_NAME.search(installer.name)
    if not match:
        raise UpdaterManifestError(f"安装包文件名里读不到版本号：{installer.name}")
    found = match.group(1)
    if found != version:
        raise UpdaterManifestError(f"安装包版本 {found} 与构建版本 {version} 不一致")
    signature_path = installer.with_name(installer.name + ".sig")
    return BundleAsset(
        path=installer,
        filename=canonical_asset_name(version),
        signature=read_signature(signature_path),
        source_name=installer.name,
    )


def asset_url(repo: str, tag: str, filename: str) -> str:
    return f"https://github.com/{repo}/releases/download/{tag}/{filename}"


def build_latest_json(
    *,
    version: str,
    notes: str,
    asset_name: str,
    signature: str,
    repo: str,
    tag: str,
    pub_date: str | None = None,
) -> dict[str, Any]:
    if not SEMVER_RE.match(version):
        raise UpdaterManifestError(f"版本号不是合法 SemVer：{version}")
    if not signature.strip():
        raise UpdaterManifestError("缺少更新包签名，拒绝生成 latest.json")
    if not asset_name.endswith("-setup.exe"):
        raise UpdaterManifestError(f"更新资产必须是 Windows 安装包：{asset_name}")
    if version not in asset_name:
        raise UpdaterManifestError(f"资产名与版本不一致：{asset_name} vs {version}")
    date = pub_date or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "version": version,
        "notes": notes.strip(),
        "pub_date": date,
        "platforms": {
            WINDOWS_TARGET: {
                "signature": signature.strip(),
                "url": asset_url(repo, tag, asset_name),
            }
        },
    }


def validate_latest_json(
    data: Any,
    *,
    expected_version: str | None = None,
    repo: str | None = None,
    tag: str | None = None,
    allow_prerelease: bool = False,
) -> list[str]:
    """返回错误列表；空列表表示可以进入正式更新渠道。"""
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["latest.json 顶层必须是对象"]

    version = data.get("version")
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        errors.append(f"version 不是合法 SemVer：{version!r}")
    elif expected_version and version != expected_version:
        errors.append(f"version={version} 与期望 {expected_version} 不一致")
    if not allow_prerelease and isinstance(version, str) and "-" in version:
        errors.append(f"正式更新渠道不允许预发布版本：{version}")

    if not isinstance(data.get("notes"), str):
        errors.append("缺少 notes（更新说明）")

    pub_date = data.get("pub_date")
    if not isinstance(pub_date, str) or not pub_date.strip():
        errors.append("缺少 pub_date")
    else:
        try:
            datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
        except ValueError:
            errors.append(f"pub_date 不是 ISO 8601：{pub_date}")

    platforms = data.get("platforms")
    if not isinstance(platforms, dict):
        errors.append("缺少 platforms")
        return errors
    entry = platforms.get(WINDOWS_TARGET)
    if not isinstance(entry, dict):
        errors.append(f"缺少 platforms.{WINDOWS_TARGET}")
        return errors

    signature = entry.get("signature")
    if not isinstance(signature, str) or not signature.strip():
        errors.append(f"platforms.{WINDOWS_TARGET}.signature 缺失（必须是 .sig 文本本身）")
    elif signature.strip().lower().startswith("http"):
        errors.append("signature 不能是签名文件链接，必须是签名文本")
    elif decode_signature(signature) is None:
        errors.append(f"platforms.{WINDOWS_TARGET}.signature 不是有效的签名内容（必须是 .sig 文件内容本身）")

    url = entry.get("url")
    if not isinstance(url, str) or not url.startswith("https://"):
        errors.append("url 必须是 HTTPS 地址")
    else:
        if repo and f"github.com/{repo}/releases/download/" not in url:
            errors.append(f"url 不指向本仓库的 Release 资产：{url}")
        if tag and f"/releases/download/{tag}/" not in url:
            errors.append(f"url 与发布 tag 不一致：{url}")
        if not url.split("/")[-1].endswith(".exe"):
            errors.append("url 必须指向 .exe 安装包")
    return errors


def assert_latest_json(data: Any, **kwargs: Any) -> None:
    errors = validate_latest_json(data, **kwargs)
    if errors:
        raise UpdaterManifestError("latest.json 校验失败：" + "；".join(errors))


def write_latest_json(path: Path, data: dict[str, Any], *, allow_prerelease: bool = False) -> None:
    assert_latest_json(data, allow_prerelease=allow_prerelease)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
