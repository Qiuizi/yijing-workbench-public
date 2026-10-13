"""Read-only hexagram catalog loaded from the bundled JSON source."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit


DATA_PATH = Path(__file__).parent / "data" / "hexagrams.json"
SPECIAL_LINE_NAMES = {1: "用九", 2: "用六"}


class HexagramCatalog:
    def __init__(self, entries: list[dict[str, Any]]):
        self.entries = entries
        self.by_id = {int(entry["wenwang_order"]): entry for entry in entries}
        self.by_code = {entry["binary_code"]: int(entry["wenwang_order"]) for entry in entries}
        self.validate()

    def validate(self) -> None:
        if len(self.entries) != 64 or set(self.by_id) != set(range(1, 65)):
            raise ValueError("hexagrams.json 必须包含文王序 1 至 64 的全部卦")
        if len(self.by_code) != 64 or any(len(code) != 6 or set(code) - {"0", "1"} for code in self.by_code):
            raise ValueError("六十四个六位卦象编码必须完整且唯一")
        if len({entry["name"] for entry in self.entries}) != 64:
            raise ValueError("卦名必须唯一")
        source_revision_ids: set[int] = set()
        for entry in self.entries:
            if len(entry["line_texts"]) != 6:
                raise ValueError(f"第 {entry['wenwang_order']} 卦必须有六条爻辞")
            revision_id = entry.get("source_revision_id")
            if type(revision_id) is not int or revision_id <= 0 or revision_id in source_revision_ids:
                raise ValueError(f"第 {entry['wenwang_order']} 卦必须有唯一且有效的维基文库修订号")
            source_revision_ids.add(revision_id)

            source = urlsplit(entry.get("source_url", ""))
            source_params = parse_qs(source.query)
            source_title = source_params.get("title", [""])[0]
            if (
                source.scheme != "https"
                or source.netloc != "zh.wikisource.org"
                or source.path != "/w/index.php"
                or not source_title.startswith("周易/")
                or source_params.get("oldid") != [str(revision_id)]
            ):
                raise ValueError(f"第 {entry['wenwang_order']} 卦来源链接必须固定到对应修订号")

            expected_special_name = SPECIAL_LINE_NAMES.get(entry["wenwang_order"])
            special_line = entry.get("special_line")
            if expected_special_name is None:
                if special_line is not None:
                    raise ValueError(f"第 {entry['wenwang_order']} 卦不能配置乾坤特殊爻辞")
                continue
            if (
                not isinstance(special_line, dict)
                or special_line.get("name") != expected_special_name
                or not isinstance(special_line.get("text"), str)
                or not special_line["text"].strip().startswith(f"{expected_special_name}：")
                or special_line.get("source_url") != entry["source_url"]
                or source_title != f"周易/{'乾' if entry['wenwang_order'] == 1 else '坤'}"
            ):
                raise ValueError(f"第 {entry['wenwang_order']} 卦特殊爻辞或出处无效")

    def get(self, wenwang_order: int) -> dict[str, Any] | None:
        return self.by_id.get(wenwang_order)

    def by_binary(self, code: str) -> dict[str, Any] | None:
        entry_id = self.by_code.get(code)
        return self.by_id.get(entry_id) if entry_id is not None else None


def load_catalog(path: Path = DATA_PATH) -> HexagramCatalog:
    with path.open("r", encoding="utf-8") as file:
        return HexagramCatalog(json.load(file))
