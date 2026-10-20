"""Produce reproducible, privacy-safe Markdown review packets for all 64 hexagrams.

This is an editorial export, NOT publication approval. It never edits guide JSON,
the approval ledger, historical source text, or a personal SQLite database.
Run: python scripts/prepare_learning_review.py --output review-packets
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDES = ROOT / "frontend/src/data/learning_guides.json"
CATALOG = ROOT / "backend/data/hexagrams.json"
APPROVALS = ROOT / "frontend/src/data/learning_approvals.json"

def audit_dossier(hexagram_id: int) -> str:
    if hexagram_id <= 20:
        low = (hexagram_id - 1) // 4 * 4 + 1
        high = low + 3
    elif hexagram_id <= 32:
        low, high = 21, 32
    elif hexagram_id <= 44:
        low, high = 33, 44
    elif hexagram_id <= 56:
        low, high = 45, 56
    else:
        low, high = 57, 64
    return f"docs/learning-guides-review-{low:02d}-{high:02d}.md"

def packet(guide: dict, classical: dict, approval: dict | None) -> str:
    hid = guide["hexagram_id"]
    title = classical["title"]
    status = "已批准展示" if approval is not None else "未获批准，不在正式 UI 展示"
    intro = [
        f"# {hid:02d} {title} | 学习导读审核工作包",
        "",
        f"> 当前状态：**{status}**。本文由仓库数据自动整理，非新的古籍校勘或授权。",
        "",
        "## 原始经文与版本",
        "",
        f"- 来源版本：[{classical['source_revision_id']}]({classical['source_url']})",
        f"- 卦序：{hid}；卦名：{classical['name']}；二进制卦画：`{classical['binary_code']}`",
        f"- 卦辞：{classical['judgment']}",
        "",
        "## 现代编辑稿（必须核对出处）",
        "",
        f"**一句话**：{guide['one_liner']}",
        "",
        guide["overview"],
        "",
        "## 逐爻：原文与现代注释并排核对",
        "",
    ]
    for number, line in enumerate(classical["line_texts"], 1):
        intro.extend([
            f"### 第 {number} 爻", "",
            f"**经文**：{line}",
            "",
            f"**现代注释**：{guide['line_guides'][str(number)]}",
            "",
            "- [ ] 逐字核对经文及词义、王弼注、孔颖达疏、朱熹解释与异文",
            "",
        ])
    if classical.get("special_line"):
        intro.extend([
            f"**特殊爻辞（仅经典原文）**：{classical['special_line']['text']}",
            "",
        ])
    intro.extend([
        "## 逐条来源入口", "",
    ])
    for ref in guide["references"]:
        intro.append(f"- [{ref['title']}]({ref['url']})")
    dossier = audit_dossier(hid)
    intro.extend([
        "",
        f"- [现有审核档案](https://github.com/Qiuizi/yijing-workbench-public/blob/main/{dossier})",
    ])
    if 13 <= hid <= 20:
        intro.append("- [王注孔疏与《本义》对照](https://github.com/Qiuizi/yijing-workbench-public/blob/main/docs/learning-guides-dualcommentary-13-20.md)")
    if 21 <= hid <= 24:
        intro.append("- [王注孔疏与《本义》对照](https://github.com/Qiuizi/yijing-workbench-public/blob/main/docs/learning-guides-dualcommentary-21-24.md)")
    if hid == 25:
        intro.append("- [无妄逐爻校读](https://github.com/Qiuizi/yijing-workbench-public/blob/main/docs/learning-guides-source-audit-25.md)")
    if 26 <= hid <= 28:
        intro.append("- [王注孔疏与《本义》对照](https://github.com/Qiuizi/yijing-workbench-public/blob/main/docs/learning-guides-dualcommentary-26-28.md)")
    if 29 <= hid <= 32:
        intro.append("- [王注孔疏与《本义》对照](https://github.com/Qiuizi/yijing-workbench-public/blob/main/docs/learning-guides-dualcommentary-29-32.md)")
    intro.extend([
        "",
        "## 维护者审核门槛（每项均需可追溯证据）",
        "",
        "- [ ] 原始经文 fixed oldid、对应卦辞、六爻及重要异文已独立核对",
        "- [ ] 《周易正义》六爻王注孔疏逐条校读且归属无混淆",
        "- [ ] 《周易本义》六爻相关异说逐条核对，未采信项注明存疑",
        "- [ ] 原文断句、术语、礼法、刑罚、性别或疾病等风险已复核",
        "- [ ] 如需改动现代说明，已同步 JSON、审核文档及回归测试",
        "- [ ] 维护者明确按卦批准并通过 PR 记录（不能由此文件自动批准）",
        "",
        "**注意**：本文档不会修改 `review_status` 或 `learning_approvals.json`；审批必须遵守 `docs/learning-approval-policy.md`。",
        "",
    ])
    if approval is not None:
        intro.append(f"此前批准记录：[{approval['approved_on']}]({approval['approval_pr']})")
    return "\n".join(intro) + "\n"

def build(output: Path) -> tuple[int, int]:
    guides = json.loads(GUIDES.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    approvals = json.loads(APPROVALS.read_text(encoding="utf-8"))["approved"]
    approved = {row["hexagram_id"]: row for row in approvals}
    if len(guides) != 64 or len(catalog) != 64 or len(approved) != len(approvals):
        raise ValueError("Guide/catalog/approval counts are inconsistent")
    output.mkdir(parents=True, exist_ok=True)
    index = ["# 64 卦审核工作包索引", "",
             "本目录仅是可离线阅读的审核工作材料；不包含私有历史、DeepSeek 密钥或用户档案。",
             "生成后应与对应源码提交一起保留，不可视作批准台账。", "",
             "| 卦序 | 标题 | 当前状态 | 审核资料 |",
             "| ---: | --- | --- | --- |"]
    for n, (g, h) in enumerate(zip(guides, catalog), 1):
        if g["hexagram_id"] != n or h["wenwang_order"] != n:
            raise ValueError(f"King Wen order mismatch: {n}")
        is_approved = n in approved
        if (g["review_status"] == "reviewed") != is_approved:
            raise ValueError(f"Approval gate mismatch at hexagram {n}")
        if set(g["line_guides"]) != {str(v) for v in range(1, 7)} or len(h["line_texts"]) != 6:
            raise ValueError(f"Line content mismatch at hexagram {n}")
        name = f"hexagram-{n:03d}.md"  # ASCII avoids Windows ZIP filename encoding issues
        (output / name).write_text(packet(g, h, approved.get(n)), encoding="utf-8")
        state = "已批准" if is_approved else "待审"
        index.append(f"| {n:02d} | {h['title']} | {state} | [{name}]({name}) |")
    (output / "index.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return len(guides), len(approved)

if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    count, approved = build(args.output)
    print(f"REVIEW PACKETS: {count} Markdown files, {approved} approved, {count - approved} drafts; no publication state changed")
