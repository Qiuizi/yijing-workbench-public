"""锁定 Tauri/Cargo 的主程序选择，防止校验器再次取代桌面应用被打包。"""

from __future__ import annotations

import tomllib
from pathlib import Path

CARGO = Path(__file__).resolve().parents[2] / "frontend" / "src-tauri" / "Cargo.toml"


def _cargo() -> dict:
    return tomllib.loads(CARGO.read_text(encoding="utf-8"))


def test_default_run_points_at_the_desktop_app():
    package = _cargo()["package"]
    assert package["name"] == "yijing-workbench"
    assert package["default-run"] == "yijing-workbench"


def test_verifier_is_a_feature_gated_bin_not_part_of_normal_bundles():
    data = _cargo()
    assert data["features"]["verify"] == []
    bins = {item["name"]: item for item in data.get("bin", [])}
    assert bins["yijing-workbench"]["path"] == "src/main.rs"
    verifier = bins["verify-updater-signature"]
    assert verifier["path"] == "src/bin/verify-updater-signature.rs"
    assert verifier["required-features"] == ["verify"]
