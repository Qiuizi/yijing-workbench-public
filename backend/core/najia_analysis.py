"""Source-labelled, non-predictive six-line relationship analysis.

These pure functions report traditional rule matches as facts. They do not
grade auspiciousness, decide an outcome, or alter the underlying chart.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any

from backend.core.najia import BRANCH_ELEMENTS, CONTROLS, EARTHLY_BRANCHES, GENERATES, SEXAGENARY_CYCLE, SOURCE_RECORDS, xunkong_for_day


RULESET_ID = "zengshan-buyi-relations"
RULESET_VERSION = "1.0.0"

SOURCE_RECORDS_ANALYSIS = (
    {
        "id": "zengshan-use-god-chapter-8",
        "title": "《增删卜易》卷一·用神章第八",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/8&oldid=2100700",
        "revision_id": 2100700,
        "scope": "占问类别与六亲用神的原文对应；仅生成候选，不自动择一。",
    },
    {
        "id": "zengshan-moving-relations-chapter-15",
        "title": "《增删卜易》卷一·动变生克冲合章第十五",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/15&oldid=2100321",
        "revision_id": 2100321,
        "scope": "动爻与变爻的五行、地支关系；本实现只标记关系。",
    },
    {
        "id": "zengshan-month-building-chapter-16",
        "title": "《增删卜易》卷一·月将章第十六",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/16&oldid=2100331",
        "revision_id": 2100331,
        "scope": "月建与爻的同支、相冲（月破）关系；不推衍旺衰吉凶。",
    },
    {
        "id": "zengshan-day-branch-chapter-17",
        "title": "《增删卜易》卷一·日辰章第十七",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/17&oldid=2100338",
        "revision_id": 2100338,
        "scope": "日辰与爻的相冲关系；本实现不判暗动或日破。",
    },
    {
        "id": "zengshan-six-combinations-chapter-19",
        "title": "《增删卜易》卷一·六合章第十九",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/19&oldid=2100447",
        "revision_id": 2100447,
        "scope": "地支六合、爻与爻合、动爻化合及卦逢六合的识别。",
    },
    {
        "id": "zengshan-six-clashes-chapter-20",
        "title": "《增删卜易》卷一·六冲章第二十",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/20&oldid=2100449",
        "revision_id": 2100449,
        "scope": "地支六冲、卦逢六冲及月破/日冲术语；已核对固定修订。",
    },
)

# Existing V2 sources provide pinned support for the five-element and void
# tables. Keep their attribution rather than silently copying a third-party
# implementation.
_V2_ELEMENT_SOURCE = SOURCE_RECORDS[3]
_V2_XUNKONG_SOURCE = SOURCE_RECORDS[2]

QUESTION_CATEGORIES: dict[str, dict[str, str]] = {
    "parent_elder_document": {
        "label": "父母、长辈、师长、房屋或文书",
        "relative": "父母",
        "basis": "《用神章》将父母长辈、师长、宅舍及文书等列入父母爻。",
        "source_id": "zengshan-use-god-chapter-8",
    },
    "sibling": {
        "label": "兄弟姐妹或同辈",
        "relative": "兄弟",
        "basis": "《用神章》以兄弟爻对应兄弟、姐妹及同辈亲属。",
        "source_id": "zengshan-use-god-chapter-8",
    },
    "wealth_spouse": {
        "label": "配偶、财物或求财",
        "relative": "妻财",
        "basis": "《用神章》以妻财爻对应妻妾及货财等。",
        "source_id": "zengshan-use-god-chapter-8",
    },
    "descendant_student": {
        "label": "子女、晚辈或门生",
        "relative": "子孙",
        "basis": "《用神章》以子孙爻对应子孙辈、门生等。",
        "source_id": "zengshan-use-god-chapter-8",
    },
    "official_career": {
        "label": "功名、官府或妻占夫",
        "relative": "官鬼",
        "basis": "《用神章》将功名、官府及妻占夫列入官鬼爻。",
        "source_id": "zengshan-use-god-chapter-8",
    },
    "medicine": {
        "label": "医药",
        "relative": "子孙",
        "basis": "《用神章》将医药列入子孙爻；此条只映射典籍类别，不分析病情。",
        "source_id": "zengshan-use-god-chapter-8",
    },
}

LIU_HE = {
    frozenset(pair)
    for pair in (
        ("子", "丑"), ("寅", "亥"), ("卯", "戌"),
        ("辰", "酉"), ("巳", "申"), ("午", "未"),
    )
}
LIU_CHONG = {
    frozenset(pair)
    for pair in (
        ("子", "午"), ("丑", "未"), ("寅", "申"),
        ("卯", "酉"), ("辰", "戌"), ("巳", "亥"),
    )
}

_ANALYSIS_SOURCE_BY_ID = {item["id"]: item for item in SOURCE_RECORDS_ANALYSIS}
_ANALYSIS_SOURCE_BY_ID["zengshan-five-elements-and-six-relatives"] = _V2_ELEMENT_SOURCE
_ANALYSIS_SOURCE_BY_ID["zengshan-xunkong-editorial"] = _V2_XUNKONG_SOURCE


def _source(source_id: str) -> dict[str, Any]:
    value = _ANALYSIS_SOURCE_BY_ID[source_id]
    return {"id": source_id, **{key: value[key] for key in ("title", "url", "revision_id", "scope") if key in value}}


def _evidence(
    *,
    module: str,
    inputs: dict[str, Any],
    results: Any,
    matched_rules: list[dict[str, str]],
    applied_rules: list[dict[str, str]] | None = None,
    explanation: str,
    source_ids: list[str],
) -> dict[str, Any]:
    return {
        "ruleset": {"id": RULESET_ID, "version": RULESET_VERSION},
        "module": module,
        "inputs": inputs,
        "results": results,
        "matched_rules": matched_rules,
        "applied_rules": applied_rules if applied_rules is not None else matched_rules,
        "sources": [_source(source_id) for source_id in source_ids],
        "explanation": explanation,
    }


def earthly_branch_relation(left: str, right: str) -> str | None:
    """Return only the explicitly tabulated 六合 or 六冲 relation."""
    if left not in EARTHLY_BRANCHES or right not in EARTHLY_BRANCHES:
        raise ValueError("地支必须是十二地支之一")
    pair = frozenset((left, right))
    if pair in LIU_HE:
        return "六合"
    if pair in LIU_CHONG:
        return "六冲"
    return None


def five_element_relation(source: str, target: str) -> str:
    """Describe a directional generating/controlling relation, without grading it."""
    if source not in GENERATES or target not in GENERATES:
        raise ValueError("五行必须是木、火、土、金、水之一")
    if source == target:
        return "比和"
    if GENERATES[source] == target:
        return "source_generates_target"
    if GENERATES[target] == source:
        return "target_generates_source"
    if CONTROLS[source] == target:
        return "source_controls_target"
    if CONTROLS[target] == source:
        return "target_controls_source"
    raise ValueError("无法确定五行关系")


def analyze_use_god_assist(
    base_board: dict[str, Any],
    *,
    question_category: str | None,
    manual_candidate: str | None,
) -> dict[str, Any]:
    if question_category is not None and question_category not in QUESTION_CATEGORIES:
        raise ValueError("未知占问类别")

    category = QUESTION_CATEGORIES.get(question_category) if question_category else None
    all_candidates: list[dict[str, Any]] = []
    for line in base_board["lines"]:
        all_candidates.append({
            "id": f"line:{line['position']}",
            "kind": "本卦爻",
            "position": line["position"],
            "relative": line["relative"],
            "stem": line["stem"],
            "branch": line["branch"],
            "element": line["element"],
        })
        if line.get("hidden_relative"):
            all_candidates.append({
                "id": f"hidden:{line['position']}",
                "kind": "伏神候选",
                "position": line["position"],
                "relative": line["hidden_relative"],
                "stem": line["hidden_stem"],
                "branch": line["hidden_branch"],
                "element": line["hidden_element"],
                "flying_relative": line["flying_relative"],
                "flying_branch": line["branch"],
                "flying_element_relation": five_element_relation(line["element"], line["hidden_element"]),
            })
    candidates = [
        candidate for candidate in all_candidates
        if category is None or candidate["relative"] == category["relative"]
    ]
    selected = next((candidate for candidate in all_candidates if candidate["id"] == manual_candidate), None)
    if manual_candidate is not None and selected is None:
        raise ValueError("手动指定的候选不属于本卦或当前可见伏神")
    selection_basis = "未指定"
    if selected is not None:
        selected = {**selected, "kind": f"手动指定：{selected['kind']}"}
        selection_basis = "manual"

    source_id = category["source_id"] if category else "zengshan-use-god-chapter-8"
    applied_use_rule = {
        "id": "use-god-category-to-relative",
        "name": "按《用神章》将占问类别映射为对应六亲",
        "source_id": source_id,
    }
    return _evidence(
        module="用神候选辅助",
        inputs={"question_category": question_category, "manual_candidate": manual_candidate},
        results={
            "question_category_label": category["label"] if category else None,
            "candidate_relative": category["relative"] if category else None,
            "candidates": candidates,
            "manual_selection": selected,
            "selection_basis": selection_basis,
        },
        matched_rules=([{
            "id": f"use-god-category:{question_category}",
            "name": "按占问类别列出对应六亲候选",
            "source_id": category["source_id"],
        }] if category else []),
        applied_rules=[applied_use_rule] if category else [],
        explanation=(category["basis"] + "候选爻可能不止一条，系统不自动裁定唯一用神；可按用户判断手动指定一爻。"
                     if category else "请选择占问类别或手动指定爻位；系统不会自动确定唯一用神。"),
        source_ids=[source_id],
    )


def analyze_time_relations(
    base_board: dict[str, Any], *, day_ganzhi: str, month_branch: str, xunkong: tuple[str, str] | list[str]
) -> dict[str, Any]:
    if day_ganzhi not in SEXAGENARY_CYCLE:
        raise ValueError("日干支必须是有效六十甲子日")
    if month_branch not in EARTHLY_BRANCHES:
        raise ValueError("月建必须是十二地支之一")
    if len(xunkong) != 2 or any(branch not in EARTHLY_BRANCHES for branch in xunkong):
        raise ValueError("旬空必须包含两个有效地支")
    if tuple(xunkong) != xunkong_for_day(day_ganzhi):
        raise ValueError("旬空必须与该日干支相符")
    day_branch = day_ganzhi[1]
    lines = []
    for line in base_board["lines"]:
        branch = line["branch"]
        month_branch_relation = earthly_branch_relation(month_branch, branch)
        day_branch_relation = earthly_branch_relation(day_branch, branch)
        lines.append({
            "position": line["position"],
            "branch": branch,
            "element": line["element"],
            "month_element_relation": five_element_relation(BRANCH_ELEMENTS[month_branch], line["element"]),
            "day_element_relation": five_element_relation(BRANCH_ELEMENTS[day_branch], line["element"]),
            "month_branch_relation": month_branch_relation,
            "day_branch_relation": day_branch_relation,
            "month_break": month_branch_relation == "六冲",
            "day_clash": day_branch_relation == "六冲",
            "xunkong": branch in xunkong,
        })
    applied = [
        {"id": "month-branch-clash-month-break", "name": "月支与爻支相冲，标记月破", "source_id": "zengshan-month-building-chapter-16"},
        {"id": "day-branch-clash", "name": "日支与爻支相冲，标记日冲", "source_id": "zengshan-six-clashes-chapter-20"},
        {"id": "branch-in-xunkong", "name": "爻支属于该日旬空", "source_id": "zengshan-xunkong-editorial"},
        {"id": "month-branch-liuhe", "name": "月支与爻支六合", "source_id": "zengshan-six-combinations-chapter-19"},
        {"id": "day-branch-liuhe", "name": "日支与爻支六合", "source_id": "zengshan-six-combinations-chapter-19"},
        {"id": "five-element-cycle", "name": "按五行生克表报告方向关系", "source_id": "zengshan-five-elements-and-six-relatives"},
    ]
    matched: list[dict[str, str]] = []
    if any(line["month_break"] for line in lines):
        matched.append(applied[0])
    if any(line["day_clash"] for line in lines):
        matched.append(applied[1])
    if any(line["xunkong"] for line in lines):
        matched.append(applied[2])
    if any(line["month_branch_relation"] == "六合" for line in lines):
        matched.append(applied[3])
    if any(line["day_branch_relation"] == "六合" for line in lines):
        matched.append(applied[4])
    for scope in ("month", "day"):
        observed = {line[f"{scope}_element_relation"] for line in lines}
        for relation in sorted(observed):
            matched.append({
                "id": f"five-element:{scope}:{relation}",
                "name": f"{scope}支与爻五行关系：{relation}",
                "source_id": "zengshan-five-elements-and-six-relatives",
            })
    return _evidence(
        module="日月及旬空关系",
        inputs={"day_ganzhi": day_ganzhi, "day_branch": day_branch, "month_branch": month_branch, "xunkong": list(xunkong)},
        results={"lines": lines},
        matched_rules=matched,
        applied_rules=applied,
        explanation="此处只记录月支/日支与爻支的五行、冲及旬空关系；日冲不自动判作暗动或日破，月破与旬空也不等同于吉凶结论。",
        source_ids=["zengshan-month-building-chapter-16", "zengshan-day-branch-chapter-17", "zengshan-six-clashes-chapter-20", "zengshan-xunkong-editorial", "zengshan-five-elements-and-six-relatives"],
    )


def _board_signature(board: dict[str, Any]) -> dict[str, Any]:
    lines = sorted(board["lines"], key=lambda line: line["position"])
    paired = [
        {"positions": [index + 1, index + 4], "branches": [lines[index]["branch"], lines[index + 3]["branch"]],
         "relation": earthly_branch_relation(lines[index]["branch"], lines[index + 3]["branch"])}
        for index in range(3)
    ]
    relations = [item["relation"] for item in paired]
    kind = "六合卦" if all(relation == "六合" for relation in relations) else "六冲卦" if all(relation == "六冲" for relation in relations) else None
    return {"kind": kind, "paired_lines": paired}


def analyze_branch_relations(base_board: dict[str, Any], changed_board: dict[str, Any]) -> dict[str, Any]:
    def matches(board: dict[str, Any]) -> list[dict[str, Any]]:
        lines = sorted(board["lines"], key=lambda line: line["position"])
        found = []
        for left, right in combinations(lines, 2):
            relation = earthly_branch_relation(left["branch"], right["branch"])
            if relation:
                found.append({
                    "positions": [left["position"], right["position"]],
                    "branches": [left["branch"], right["branch"]],
                    "relation": relation,
                })
        return found

    base_signature = _board_signature(base_board)
    changed_signature = _board_signature(changed_board)
    base_matches = matches(base_board)
    changed_matches = matches(changed_board)
    all_matches = base_matches + changed_matches
    matched_rules: list[dict[str, str]] = []
    if any(item["relation"] == "六合" for item in all_matches):
        matched_rules.append({"id": "earthly-branch-liuhe", "name": "发现地支六合配对", "source_id": "zengshan-six-combinations-chapter-19"})
    if any(item["relation"] == "六冲" for item in all_matches):
        matched_rules.append({"id": "earthly-branch-liuchong", "name": "发现地支六冲配对", "source_id": "zengshan-six-clashes-chapter-20"})
    if any(item["kind"] == "六合卦" for item in (base_signature, changed_signature)):
        matched_rules.append({"id": "hexagram-liuhe", "name": "本卦或变卦满足卦逢六合结构", "source_id": "zengshan-six-combinations-chapter-19"})
    if any(item["kind"] == "六冲卦" for item in (base_signature, changed_signature)):
        matched_rules.append({"id": "hexagram-liuchong", "name": "本卦或变卦满足卦逢六冲结构", "source_id": "zengshan-six-clashes-chapter-20"})
    return _evidence(
        module="地支六合、六冲",
        inputs={"base_code": base_board["binary_code"], "changed_code": changed_board["binary_code"]},
        results={
            "base_pair_matches": base_matches,
            "changed_pair_matches": changed_matches,
            "base_hexagram_relation": base_signature,
            "changed_hexagram_relation": changed_signature,
        },
        matched_rules=matched_rules,
        applied_rules=[
            {"id": "earthly-branch-liuhe", "name": "地支六合配对", "source_id": "zengshan-six-combinations-chapter-19"},
            {"id": "earthly-branch-liuchong", "name": "地支六冲配对", "source_id": "zengshan-six-clashes-chapter-20"},
            {"id": "hexagram-liuhe-liuchong", "name": "初至三爻与四至上爻逐位相合/相冲时标记卦逢六合/六冲", "source_id": "zengshan-six-combinations-chapter-19"},
        ],
        explanation="逐对列出六爻地支中的六合/六冲。卦级标签要求初、二、三爻分别与四、五、上爻的地支三组全部同为六合或同为六冲；仅报告结构，不推断占事结果。",
        source_ids=["zengshan-six-combinations-chapter-19", "zengshan-six-clashes-chapter-20"],
    )


def analyze_moving_changes(base_board: dict[str, Any], changed_board: dict[str, Any]) -> dict[str, Any]:
    changed_by_position = {line["position"]: line for line in changed_board["lines"]}
    transitions = []
    for line in sorted(base_board["lines"], key=lambda item: item["position"]):
        if not line["moving"]:
            continue
        changed = changed_by_position[line["position"]]
        transitions.append({
            "position": line["position"],
            "from": {"relative": line["relative"], "branch": line["branch"], "element": line["element"]},
            "to": {"relative": changed["relative"], "branch": changed["branch"], "element": changed["element"]},
            "element_relation": five_element_relation(line["element"], changed["element"]),
            "branch_relation": earthly_branch_relation(line["branch"], changed["branch"]),
        })
    applied = [
        {"id": "moving-line-corresponding-change", "name": "按同一爻位对应本爻与变爻", "source_id": "zengshan-moving-relations-chapter-15"},
        {"id": "moving-line-element-relation", "name": "报告本爻与变爻五行生克方向", "source_id": "zengshan-moving-relations-chapter-15"},
        {"id": "moving-line-branch-relation", "name": "报告本爻与变爻地支六合/六冲", "source_id": "zengshan-moving-relations-chapter-15"},
    ]
    matched: list[dict[str, str]] = []
    if transitions:
        matched.append(applied[0])
    for relation in sorted({line["element_relation"] for line in transitions}):
        matched.append({
            "id": f"moving-element:{relation}", "name": f"动爻到变爻五行关系：{relation}",
            "source_id": "zengshan-moving-relations-chapter-15",
        })
    for relation in sorted({line["branch_relation"] for line in transitions if line["branch_relation"]}):
        source_id = "zengshan-six-combinations-chapter-19" if relation == "六合" else "zengshan-six-clashes-chapter-20"
        matched.append({"id": f"moving-branch:{relation}", "name": f"动爻支与变爻支：{relation}", "source_id": source_id})
    return _evidence(
        module="动爻与变爻对应关系",
        inputs={"base_code": base_board["binary_code"], "changed_code": changed_board["binary_code"]},
        results={"transitions": transitions},
        matched_rules=matched,
        applied_rules=applied,
        explanation="只比较动爻及其相同位置的变爻并标记五行方向与地支六合/六冲，不据此自动判定回头生克的吉凶。",
        source_ids=["zengshan-moving-relations-chapter-15", "zengshan-six-combinations-chapter-19", "zengshan-six-clashes-chapter-20"],
    )


def analyze_najia_chart(
    chart: dict[str, Any],
    *,
    enabled: dict[str, bool],
    question_category: str | None = None,
    manual_use_god_candidate: str | None = None,
) -> dict[str, Any]:
    expected = {"use_god", "time_relations", "branch_relations", "moving_changes"}
    if set(enabled) != expected or any(type(value) is not bool for value in enabled.values()):
        raise ValueError("分析开关必须恰好包含四个布尔选项")
    if not enabled["use_god"] and (question_category is not None or manual_use_god_candidate is not None):
        raise ValueError("关闭用神辅助时不能提交占问类别或手动候选")

    modules: dict[str, dict[str, Any] | None] = {name: None for name in sorted(expected)}
    if enabled["use_god"]:
        modules["use_god"] = analyze_use_god_assist(
            chart["base"], question_category=question_category, manual_candidate=manual_use_god_candidate
        )
    if enabled["time_relations"]:
        modules["time_relations"] = analyze_time_relations(
            chart["base"], day_ganzhi=chart["day_ganzhi"], month_branch=chart["month_branch"], xunkong=chart["xunkong"]
        )
    if enabled["branch_relations"]:
        modules["branch_relations"] = analyze_branch_relations(chart["base"], chart["changed"])
    if enabled["moving_changes"]:
        modules["moving_changes"] = analyze_moving_changes(chart["base"], chart["changed"])
    return {
        "ruleset": {"id": RULESET_ID, "version": RULESET_VERSION},
        "enabled": dict(enabled),
        "question_category": question_category,
        "manual_use_god_candidate": manual_use_god_candidate,
        "modules": modules,
    }
