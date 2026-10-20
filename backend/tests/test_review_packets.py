"""Review packets must preserve all originals and keep unapproved guides gated."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def test_offline_review_packets_are_complete_and_do_not_publish(tmp_path: Path) -> None:
    guide_file = ROOT / "frontend/src/data/learning_guides.json"
    approvals_file = ROOT / "frontend/src/data/learning_approvals.json"
    classic_file = ROOT / "backend/data/hexagrams.json"
    originals = [f.read_bytes() for f in (guide_file, approvals_file, classic_file)]
    output = tmp_path / "review-packets"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/prepare_learning_review.py"),
         "--output", str(output)],
        text=True, encoding="utf-8", capture_output=True, check=True,
    )
    assert "64 Markdown files, 4 approved, 60 drafts" in result.stdout
    assert len(list(output.glob("hexagram-*.md"))) == 64
    assert len(list(output.glob("*.md"))) == 65
    catalog = json.loads(classic_file.read_text(encoding="utf-8"))
    guides = json.loads(guide_file.read_text(encoding="utf-8"))
    index = (output / "index.md").read_text(encoding="utf-8")
    assert index.count("| 待审 |") == 60
    assert index.count("| 已批准 |") == 4
    assert "user" not in result.stdout.lower()
    for n, (original, guide) in enumerate(zip(catalog, guides), 1):
        path = output / f"hexagram-{n:03d}.md"
        text = path.read_text(encoding="utf-8")
        assert original["judgment"] in text
        assert original["source_url"] in text
        assert guide["overview"] in text
        for line in original["line_texts"]:
            assert line in text
        for line in guide["line_guides"].values():
            assert line in text
        assert "不能由此文件自动批准" in text
        if n <= 4:
            assert "已批准展示" in text
        else:
            assert "未获批准，不在正式 UI 展示" in text
    assert [f.read_bytes() for f in (guide_file, approvals_file, classic_file)] == originals
