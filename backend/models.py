"""Shared request and response contracts for the HTTP API."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr, field_validator, model_validator


class DivinationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=500)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("请先写下要占问的问题")
        return normalized


class ManualDivinationRequest(DivinationRequest):
    lines: list[StrictInt] = Field(min_length=6, max_length=6)

    @field_validator("lines")
    @classmethod
    def validate_line_values(cls, values: list[int]) -> list[int]:
        if any(value not in (6, 7, 8, 9) for value in values):
            raise ValueError("每一爻只能是 6、7、8 或 9")
        return values


class NajiaAnalysisToggles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    use_god: StrictBool = False
    time_relations: StrictBool = False
    branch_relations: StrictBool = False
    moving_changes: StrictBool = False


class NajiaAnalysisOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: NajiaAnalysisToggles = Field(default_factory=NajiaAnalysisToggles)
    question_category: Literal[
        "parent_elder_document", "sibling", "wealth_spouse", "descendant_student", "official_career", "medicine"
    ] | None = None
    manual_use_god_candidate: StrictStr | None = Field(default=None, min_length=6, max_length=12)

    @model_validator(mode="after")
    def validate_assist_options(self) -> "NajiaAnalysisOptions":
        if not self.enabled.use_god and (
            self.question_category is not None or self.manual_use_god_candidate is not None
        ):
            raise ValueError("关闭用神辅助时不能提交占问类别或手动用神位置")
        return self


class NajiaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["manual", "automatic"] = "manual"
    day_ganzhi: StrictStr | None = Field(default=None, min_length=2, max_length=2)
    month_branch: StrictStr | None = Field(default=None, min_length=1, max_length=1)
    local_datetime: StrictStr | None = Field(default=None, min_length=16, max_length=19)
    timezone: StrictStr | None = Field(default=None, min_length=1, max_length=100)
    analysis: NajiaAnalysisOptions = Field(default_factory=NajiaAnalysisOptions)

    @model_validator(mode="after")
    def validate_source_fields(self) -> "NajiaRequest":
        if self.source == "manual":
            if not self.day_ganzhi or not self.month_branch:
                raise ValueError("手动模式需要提供日干支和月建")
            if self.local_datetime is not None or self.timezone is not None:
                raise ValueError("手动模式不能同时提交自动历法参数")
        else:
            if not self.local_datetime or not self.timezone:
                raise ValueError("自动模式需要提供本地日期时间和 IANA 时区")
            if self.day_ganzhi is not None or self.month_branch is not None:
                raise ValueError("自动模式不能覆盖计算得到的干支和月建")
        return self


class AISettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    api_key: StrictStr | None = Field(default=None, min_length=1, max_length=500)
    model_id: StrictStr | None = Field(default=None, min_length=1, max_length=150)
    ai_enabled: StrictBool | None = None


class AISessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    divination_id: StrictInt
    mode: Literal["classical", "najia"] = "classical"


class AIMessageRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: StrictStr = Field(min_length=1, max_length=2000)
    request_id: UUID = Field(default_factory=uuid4)
    regenerate_from_message_id: StrictInt | None = None

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("追问内容不能为空")
        return normalized


class PreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_method: Literal["coins", "manual"]
    timezone: StrictStr | None = Field(default=None, min_length=1, max_length=100)
    ai_default_mode: Literal["classical", "najia"] | None = None


class TrigramResponse(BaseModel):
    name: str
    symbol: str
    binary_code: str
    image: str


class SpecialLineResponse(BaseModel):
    name: Literal["用九", "用六"]
    text: str
    source_url: str


class HexagramResponse(BaseModel):
    wenwang_order: int
    name: str
    title: str
    binary_code: str
    upper_trigram: TrigramResponse
    lower_trigram: TrigramResponse
    judgment: str
    line_texts: list[str]
    text_source: str
    source_url: str
    source_revision_id: int | None = None
    special_line: SpecialLineResponse | None = None


class LineResponse(BaseModel):
    position: int
    value: int
    yin_yang: Literal["阴", "阳"]
    changing: bool
    coins: list[int] | None = None


class ReadingPassageResponse(BaseModel):
    kind: Literal["judgment", "line", "special_line"]
    hexagram_order: int
    hexagram_title: str
    label: str
    text: str
    line_position: int | None = None
    primary: bool
    source_url: str
    source_revision_id: int | None = None


class TraditionalReadingResponse(BaseModel):
    ruleset_id: str
    ruleset_version: str
    ruleset_name: str
    source_title: str
    source_url: str
    source_revision_id: int
    moving_count: int
    passages: list[ReadingPassageResponse]
    rationale: str
    plain_rule_explanation: str
    interpretation_limit: str


class NajiaSourceResponse(BaseModel):
    scope: str
    title: str
    url: str
    revision_id: int


class NajiaLineResponse(BaseModel):
    position: int
    yin_yang: Literal["阴", "阳"]
    moving: bool
    stem: str
    branch: str
    element: str
    relative: str
    spirit: str | None = None
    role: Literal["世", "应"] | None = None
    hidden_relative: str | None = None
    hidden_stem: str | None = None
    hidden_branch: str | None = None
    hidden_element: str | None = None
    flying_relative: str | None = None
    xunkong: bool
    month_build: bool


class NajiaBoardResponse(BaseModel):
    hexagram_order: int
    hexagram_title: str
    binary_code: str
    lines: list[NajiaLineResponse]


class NajiaChartResponse(BaseModel):
    sources: list[NajiaSourceResponse]
    palace: str
    palace_element: str
    palace_position: str
    world_position: int
    response_position: int
    day_ganzhi: str
    xunkong: list[str]
    month_branch: str
    base: NajiaBoardResponse
    changed: NajiaBoardResponse
    rules_note: str
    timestamp_source: Literal["manual", "automatic"]
    calendar_context: dict[str, str] | None = None
    rule_analysis: dict[str, Any] | None = None


class DivinationResponse(BaseModel):
    id: int | None = None
    question: str
    method: Literal["coins", "manual"]
    lines: list[LineResponse]
    changed_lines: list[LineResponse]
    moving_positions: list[int]
    base_hexagram: HexagramResponse
    changed_hexagram: HexagramResponse
    created_at: str | None = None
    traditional_reading: TraditionalReadingResponse | None = None
    najia_chart: NajiaChartResponse | None = None
    ai_sessions: list[dict[str, Any]] = Field(default_factory=list)


class HistorySummary(BaseModel):
    id: int
    question: str
    method: Literal["coins", "manual"]
    base_name: str
    changed_name: str
    moving_positions: list[int]
    created_at: str
    has_ai_sessions: bool = False


class HistoryListResponse(BaseModel):
    items: list[HistorySummary]
    total: int


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
