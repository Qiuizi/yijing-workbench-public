"""A source-labelled Wen Wang Gua layout engine with explicit date inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EARTHLY_BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
HEAVENLY_STEMS = ("甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸")
FIVE_ELEMENTS = ("木", "火", "土", "金", "水")
BRANCH_ELEMENTS = {
    "子": "水", "亥": "水", "寅": "木", "卯": "木", "巳": "火", "午": "火",
    "申": "金", "酉": "金", "辰": "土", "戌": "土", "丑": "土", "未": "土",
}
GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# Explicitly transcribed from the eight pure-hexagram Na Jia table in the cited source.
# Each branch tuple is in line order 初爻 -> 上爻.
TRIGRAM_NAJIA: dict[str, dict[str, Any]] = {
    "111": {"name": "乾", "element": "金", "inner_stem": "甲", "outer_stem": "壬", "inner": ("子", "寅", "辰"), "outer": ("午", "申", "戌")},
    "010": {"name": "坎", "element": "水", "inner_stem": "戊", "outer_stem": "戊", "inner": ("寅", "辰", "午"), "outer": ("申", "戌", "子")},
    "100": {"name": "艮", "element": "土", "inner_stem": "丙", "outer_stem": "丙", "inner": ("辰", "午", "申"), "outer": ("戌", "子", "寅")},
    "001": {"name": "震", "element": "木", "inner_stem": "庚", "outer_stem": "庚", "inner": ("子", "寅", "辰"), "outer": ("午", "申", "戌")},
    "110": {"name": "巽", "element": "木", "inner_stem": "辛", "outer_stem": "辛", "inner": ("丑", "亥", "酉"), "outer": ("未", "巳", "卯")},
    "101": {"name": "离", "element": "火", "inner_stem": "己", "outer_stem": "己", "inner": ("卯", "丑", "亥"), "outer": ("酉", "未", "巳")},
    "011": {"name": "兑", "element": "金", "inner_stem": "丁", "outer_stem": "丁", "inner": ("巳", "卯", "丑"), "outer": ("亥", "酉", "未")},
    "000": {"name": "坤", "element": "土", "inner_stem": "乙", "outer_stem": "癸", "inner": ("未", "巳", "卯"), "outer": ("丑", "亥", "酉")},
}

TRIGRAMS_BY_NAME = {value["name"]: value for value in TRIGRAM_NAJIA.values()}
PALACE_TRIGRAM_ORDER = ("乾", "坎", "艮", "震", "巽", "离", "坤", "兑")
PALACE_POSITION_NAMES = ("本宫", "一世", "二世", "三世", "四世", "五世", "游魂", "归魂")
WORLD_POSITIONS = (6, 1, 2, 3, 4, 5, 4, 3)
SIX_SPIRITS = ("青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武")
SPIRIT_START = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}

SOURCE_RECORDS = (
    {
        "scope": "八宫卦序、宫五行及世应全图",
        "title": "《增删卜易》卷一·八宫图第三",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/3&oldid=2100295",
        "revision_id": 2100295,
    },
    {
        "scope": "浑天甲子纳甲篇章（具体八纯卦表另据编者增补资料）",
        "title": "《增删卜易》卷一·浑天甲子章第四",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/4&oldid=2100293",
        "revision_id": 2100293,
    },
    {
        "scope": "八卦纳甲天干、地支；六神起例；旬空起例（维基文库编者增补）",
        "title": "《增删卜易》篇首·原剑增订说明及纳甲资料",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易&oldid=2572918",
        "revision_id": 2572918,
    },
    {
        "scope": "六亲与五行生克歌诀",
        "title": "《增删卜易》卷一·六亲歌章第五",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/5&oldid=2100292",
        "revision_id": 2100292,
    },
    {
        "scope": "世应位置规则",
        "title": "《增删卜易》卷一·世应章第六",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/6&oldid=2100291",
        "revision_id": 2100291,
    },
    {
        "scope": "六神起例",
        "title": "《增删卜易》篇首·起六神诀（维基文库编者增补）",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易&oldid=2572918",
        "revision_id": 2572918,
    },
    {
        "scope": "六神章语境（逐爻起例据编者增补资料）",
        "title": "《增删卜易》卷一·六神章第十八",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易/18&oldid=2101727",
        "revision_id": 2101727,
    },
    {
        "scope": "伏神、飞神及本宫首卦寻伏例证（当前维基文库合编页）",
        "title": "《增删卜易》卷二·飞伏神章第二十八",
        "url": "https://zh.wikisource.org/w/index.php?title=增刪卜易&oldid=2572918",
        "revision_id": 2572918,
    },
)


@dataclass(frozen=True)
class PalaceAssignment:
    palace: str
    palace_element: str
    position_index: int
    position_name: str
    world_position: int
    response_position: int
    pure_code: str


def sexagenary_cycle() -> tuple[str, ...]:
    return tuple(HEAVENLY_STEMS[index % 10] + EARTHLY_BRANCHES[index % 12] for index in range(60))


SEXAGENARY_CYCLE = sexagenary_cycle()


def validate_day_ganzhi(day_ganzhi: str) -> tuple[str, str]:
    if not isinstance(day_ganzhi, str) or day_ganzhi not in SEXAGENARY_CYCLE:
        raise ValueError("日干支必须是六十甲子中的一项，例如甲子")
    return day_ganzhi[0], day_ganzhi[1]


def xunkong_for_day(day_ganzhi: str) -> tuple[str, str]:
    stem, branch = validate_day_ganzhi(day_ganzhi)
    stem_index = HEAVENLY_STEMS.index(stem)
    branch_index = EARTHLY_BRANCHES.index(branch)
    first_branch_offset = (branch_index - stem_index) % 12
    return (
        EARTHLY_BRANCHES[(first_branch_offset + 10) % 12],
        EARTHLY_BRANCHES[(first_branch_offset + 11) % 12],
    )


def _flip_code_line(code: str, position: int) -> str:
    index = 6 - position
    replacement = "0" if code[index] == "1" else "1"
    return code[:index] + replacement + code[index + 1 :]


def _palace_members(catalog: Any) -> dict[str, PalaceAssignment]:
    members: dict[str, PalaceAssignment] = {}
    for palace_name in PALACE_TRIGRAM_ORDER:
        trigram = TRIGRAMS_BY_NAME[palace_name]
        pure_code = next(code for code, value in TRIGRAM_NAJIA.items() if value["name"] == palace_name) * 2
        current = pure_code
        sequence: list[str] = [current]
        for position in range(1, 6):
            current = _flip_code_line(current, position)
            sequence.append(current)
        current = _flip_code_line(current, 4)  # 五世卦返变四爻为游魂
        sequence.append(current)
        for position in (1, 2, 3):  # 归魂卦再变内卦三爻
            current = _flip_code_line(current, position)
        sequence.append(current)

        if len(set(sequence)) != 8:
            raise ValueError(f"{palace_name}宫八卦序列存在重复编码")
        for position_index, code in enumerate(sequence):
            entry_id = catalog.by_code.get(code)
            if entry_id is None:
                raise ValueError(f"八宫映射缺少卦码 {code}")
            entry = catalog.by_id.get(entry_id)
            if entry is None:
                raise ValueError(f"八宫映射包含无效卦序 {entry_id}")
            world = WORLD_POSITIONS[position_index]
            response = (world - 1 + 3) % 6 + 1
            members[code] = PalaceAssignment(
                palace=palace_name,
                palace_element=trigram["element"],
                position_index=position_index,
                position_name=PALACE_POSITION_NAMES[position_index],
                world_position=world,
                response_position=response,
                pure_code=pure_code,
            )
    if len(members) != 64:
        raise ValueError("八宫映射必须恰好覆盖 64 个不同卦象")
    return members


def _relative(line_element: str, palace_element: str) -> str:
    if line_element == palace_element:
        return "兄弟"
    if GENERATES[line_element] == palace_element:
        return "父母"
    if GENERATES[palace_element] == line_element:
        return "子孙"
    if CONTROLS[line_element] == palace_element:
        return "官鬼"
    if CONTROLS[palace_element] == line_element:
        return "妻财"
    raise ValueError("无法确定六亲")


def _trigram_line_data(upper_code: str, lower_code: str) -> tuple[dict[str, str], ...]:
    if upper_code not in TRIGRAM_NAJIA or lower_code not in TRIGRAM_NAJIA:
        raise ValueError("卦象包含未知三画卦")
    upper = TRIGRAM_NAJIA[upper_code]
    lower = TRIGRAM_NAJIA[lower_code]
    rows: list[dict[str, str]] = []
    for trigram, is_inner in ((lower, True), (upper, False)):
        branches = trigram["inner"] if is_inner else trigram["outer"]
        stem = trigram["inner_stem"] if is_inner else trigram["outer_stem"]
        rows.extend(
            {"stem": stem, "branch": branch, "element": BRANCH_ELEMENTS[branch]}
            for branch in branches
        )
    return tuple(rows)


def build_najia_chart(
    *,
    calculation: Any,
    base_hexagram: dict[str, Any],
    changed_hexagram: dict[str, Any],
    day_ganzhi: str,
    month_branch: str,
    catalog: Any,
    timestamp_source: str = "manual",
) -> dict[str, Any]:
    """Build base and changed boards; all line arrays remain bottom to top."""
    if timestamp_source not in {"manual", "automatic"}:
        raise ValueError("timestamp_source 只能是 manual 或 automatic")
    day_stem, _ = validate_day_ganzhi(day_ganzhi)
    if month_branch not in EARTHLY_BRANCHES:
        raise ValueError("月建只能是子、丑、寅、卯、辰、巳、午、未、申、酉、戌、亥")
    xunkong = xunkong_for_day(day_ganzhi)
    palace_map = _palace_members(catalog)
    assignment = palace_map.get(calculation.base_code)
    if assignment is None:
        raise ValueError("本卦未找到八宫归属")

    hidden_by_position: dict[int, dict[str, str]] = {}
    base_trigram_data = _trigram_line_data(
        base_hexagram["upper_trigram"]["binary_code"],
        base_hexagram["lower_trigram"]["binary_code"],
    )
    base_relatives = tuple(_relative(row["element"], assignment.palace_element) for row in base_trigram_data)
    present_relatives = set(base_relatives)
    pure_entry = catalog.by_id[catalog.by_code[assignment.pure_code]]
    pure_data = _trigram_line_data(
        pure_entry["upper_trigram"]["binary_code"],
        pure_entry["lower_trigram"]["binary_code"],
    )
    pure_relatives = tuple(_relative(row["element"], assignment.palace_element) for row in pure_data)
    for missing_relative in ("父母", "兄弟", "子孙", "妻财", "官鬼"):
        if missing_relative in present_relatives:
            continue
        source_index = pure_relatives.index(missing_relative)
        target_position = source_index + 1
        hidden_by_position[target_position] = {
            "relative": missing_relative,
            "stem": pure_data[source_index]["stem"],
            "branch": pure_data[source_index]["branch"],
            "element": pure_data[source_index]["element"],
        }

    def make_board(entry: dict[str, Any], line_values: tuple[int, ...], *, with_hidden: bool, with_roles: bool):
        trigram_data = _trigram_line_data(
            entry["upper_trigram"]["binary_code"],
            entry["lower_trigram"]["binary_code"],
        )
        rows = []
        for index, (value, na_jia) in enumerate(zip(line_values, trigram_data, strict=True)):
            position = index + 1
            hidden = hidden_by_position.get(position) if with_hidden else None
            line_relative = _relative(na_jia["element"], assignment.palace_element)
            row = {
                "position": position,
                "yin_yang": "阳" if value in (7, 9) else "阴",
                "moving": position in calculation.moving_positions,
                "stem": na_jia["stem"],
                "branch": na_jia["branch"],
                "element": na_jia["element"],
                "relative": line_relative,
                "spirit": SIX_SPIRITS[(SPIRIT_START[day_stem] + index) % 6],
                "role": (
                    "世" if with_roles and position == assignment.world_position else
                    "应" if with_roles and position == assignment.response_position else None
                ),
                "hidden_relative": hidden["relative"] if hidden else None,
                "hidden_stem": hidden["stem"] if hidden else None,
                "hidden_branch": hidden["branch"] if hidden else None,
                "hidden_element": hidden["element"] if hidden else None,
                "flying_relative": line_relative if hidden else None,
                "xunkong": na_jia["branch"] in xunkong,
                "month_build": na_jia["branch"] == month_branch,
            }
            rows.append(row)
        return {
            "hexagram_order": entry["wenwang_order"],
            "hexagram_title": entry["title"],
            "binary_code": entry["binary_code"],
            "lines": rows,
        }

    base_board = make_board(base_hexagram, calculation.lines, with_hidden=True, with_roles=True)
    changed_board = make_board(changed_hexagram, calculation.changed_lines, with_hidden=False, with_roles=False)
    calendar_note = (
        "日干支与月建由所选日期时间及 IANA 时区自动计算，并随历史记录保存计算版本。"
        if timestamp_source == "automatic"
        else "日干支与月建由用户手动录入，旬空据所填日干支计算。"
    )
    return {
        "sources": [dict(source) for source in SOURCE_RECORDS],
        "palace": assignment.palace,
        "palace_element": assignment.palace_element,
        "palace_position": assignment.position_name,
        "world_position": assignment.world_position,
        "response_position": assignment.response_position,
        "day_ganzhi": day_ganzhi,
        "xunkong": list(xunkong),
        "month_branch": month_branch,
        "base": base_board,
        "changed": changed_board,
        "rules_note": (
            "纳甲地支按内、外卦分别配置；六亲以本卦宫五行为基准；六神从所填日干起例。"
            "本宫首卦中缺少的六亲作为伏神，按初爻至上爻的首个对应爻取值，伏于本卦同位飞神之下。"
            f"之卦使用本卦宫五行标六亲，世应只标本卦。{calendar_note}"
        ),
        "timestamp_source": timestamp_source,
    }
