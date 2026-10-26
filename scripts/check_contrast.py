"""WCAG 对比度校验：读取双端 design token，逐对检查文字/背景组合。

用法： python scripts/check_contrast.py
退出码：0 全部达标；1 有未达标项（用于门禁）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBSITE_TOKENS = ROOT / "website" / "src" / "styles" / "tokens.css"
FRONTEND_TOKENS = ROOT / "frontend" / "src" / "theme.css"

VAR_RE = re.compile(r"--([\w-]+)\s*:\s*([^;]+);")


def parse_vars(text: str) -> dict[str, str]:
    return {name: value.strip() for name, value in VAR_RE.findall(text)}


def split_blocks(text: str) -> list[tuple[str, dict[str, str]]]:
    """把 CSS 拆成 (选择器, 变量表) 的列表，按出现顺序。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    blocks: list[tuple[str, dict[str, str]]] = []
    for match in re.finditer(r"([^{}]+)\{([^}]*)\}", text):
        selector = " ".join(match.group(1).split())
        blocks.append((selector, parse_vars(match.group(2))))
    return blocks


def resolve(name: str, scope: dict[str, str], depth: int = 0) -> str:
    if depth > 12:
        raise ValueError(f"circular var(--{name})")
    raw = scope.get(name)
    if raw is None:
        raise KeyError(name)
    ref = re.fullmatch(r"var\(\s*--([\w-]+)\s*(?:,[^)]*)?\)", raw.strip())
    if ref:
        return resolve(ref.group(1), scope, depth + 1)
    return raw


def hex_to_rgb(value: str) -> tuple[int, int, int] | None:
    value = value.strip()
    m = re.fullmatch(r"#([0-9a-fA-F]{3})", value)
    if m:
        return tuple(int(c * 2, 16) for c in m.group(1))  # type: ignore[return-value]
    m = re.fullmatch(r"#([0-9a-fA-F]{6})", value)
    if m:
        h = m.group(1)
        return tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    return None


def luminance(rgb: tuple[int, int, int]) -> float:
    def channel(c: int) -> float:
        s = c / 255
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg: str, bg: str) -> float:
    a, b = hex_to_rgb(fg), hex_to_rgb(bg)
    if a is None or b is None:
        raise ValueError(f"non-hex colour: {fg} / {bg}")
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# (前景, 背景, 阈值, 说明)
WEBSITE_PAIRS = [
    ("text-1", "bg", 7.0, "正文主色 / 页面底"),
    ("text-2", "bg", 4.6, "正文次色 / 页面底"),
    ("text-3", "bg", 4.6, "弱化文字 / 页面底"),
    ("text-1", "surface-1", 7.0, "正文主色 / 一级表面"),
    ("text-2", "surface-1", 4.6, "正文次色 / 一级表面"),
    ("text-3", "surface-1", 4.6, "弱化文字 / 一级表面"),
    ("text-3", "surface-2", 4.6, "弱化文字 / 二级表面"),
    ("accent", "bg", 4.6, "强调色 / 页面底"),
    ("accent", "surface-1", 4.6, "强调色 / 一级表面"),
    ("accent-strong", "accent-soft", 4.6, "强调色 / 强调底"),
    ("bronze", "bg", 4.6, "铜金 / 页面底"),
    ("bronze", "surface-1", 4.6, "铜金 / 一级表面"),
    ("success", "surface-1", 4.6, "成功色 / 一级表面"),
    ("warning", "surface-1", 4.6, "警示色 / 一级表面"),
    ("danger", "surface-1", 4.6, "危险色 / 一级表面"),
    ("shell-text", "shell-bg", 7.0, "墨玉区正文"),
    ("shell-text-soft", "shell-bg", 4.6, "墨玉区次文"),
    ("shell-bronze", "shell-bg", 4.6, "墨玉区铜金"),
    ("text-inverse", "accent", 4.6, "反白字 / 强调底"),
]

FRONTEND_PAIRS = [
    ("text-primary", "bg", 7.0, "正文主色 / 页面底"),
    ("text-primary", "surface", 7.0, "正文主色 / 一级表面"),
    ("text-secondary", "surface", 4.6, "正文次色 / 一级表面"),
    ("text-muted", "surface", 4.6, "弱化文字 / 一级表面"),
    ("text-muted", "surface-muted", 4.6, "弱化文字 / 二级表面"),
    ("text-secondary", "surface-muted", 4.6, "正文次色 / 二级表面"),
    ("accent", "surface", 4.6, "强调色 / 一级表面"),
    ("accent", "bg", 4.6, "强调色 / 页面底"),
    ("accent", "accent-soft", 4.6, "强调色 / 强调底"),
    ("bronze", "surface", 4.6, "铜金 / 一级表面"),
    ("success", "surface", 4.6, "成功色 / 一级表面"),
    ("warning", "surface", 4.6, "警示色 / 一级表面"),
    ("danger", "surface", 4.6, "危险色 / 一级表面"),
    ("text-inverse", "accent", 4.6, "按钮文字 / 强调填充"),
]


def pairs_for(kind: str, theme: str) -> list[tuple[str, str, float, str]]:
    source = WEBSITE_PAIRS if kind == "website" else FRONTEND_PAIRS
    return [(fg, bg, need, f"[{theme}] {label}") for fg, bg, need, label in source]


def check(css_path: Path, kind: str, themes: dict[str, str]) -> int:
    text = css_path.read_text(encoding="utf-8")
    blocks = split_blocks(text)

    base_scope: dict[str, str] = {}
    theme_scopes: dict[str, dict[str, str]] = {name: {} for name in themes}

    for selector, variables in blocks:
        if selector == ":root":
            base_scope.update(variables)
        for name, needle in themes.items():
            if needle in selector:
                theme_scopes[name].update(variables)

    # light 主题的选择器是 ':root, :root[data-theme='light']'，会被 needle 命中
    failures = 0
    print(f"\n=== {css_path.relative_to(ROOT)} ===")
    for name, needle in themes.items():
        scope = dict(base_scope)
        scope.update(theme_scopes[name])
        rows = []
        for fg, bg, need, label in pairs_for(kind, name):
            try:
                got = ratio(resolve(fg, scope), resolve(bg, scope))
            except (KeyError, ValueError) as exc:
                print(f"  !! {label}: {exc}")
                failures += 1
                continue
            ok = got >= need
            failures += 0 if ok else 1
            rows.append((label, got, need, ok))
        print(f"-- {name} --")
        for label, got, need, ok in rows:
            flag = "ok  " if ok else "FAIL"
            print(f"  {flag} {got:5.2f} (>= {need:.1f})  {label}")
    return failures


def main() -> int:
    failures = 0
    if WEBSITE_TOKENS.exists():
        failures += check(
            WEBSITE_TOKENS, "website",
            {"light": "[data-theme='light']", "dark": "[data-theme='dark']"},
        )
    if FRONTEND_TOKENS.exists():
        failures += check(
            FRONTEND_TOKENS, "frontend",
            {"light": "[data-theme='light']", "dark": "[data-theme='dark']"},
        )
    print(f"\n{'PASS' if failures == 0 else f'{failures} FAILED'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
