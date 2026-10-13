from __future__ import annotations

import json

import pytest

from backend.services.ai_runtime import (
    AIOutputValidationError,
    build_chat_messages,
    build_system_prompt,
    validate_ai_output,
)


def classical_context() -> dict:
    return {
        "mode": "classical",
        "traditional_reading": {
            "ruleset_id": "qiming-tongshi",
            "ruleset_version": "1.0.0",
            "ruleset_name": "启蒙通释",
            "passages": [
                {
                    "id": "p1", "label": "卦辞", "text": "本地原文甲。",
                    "source_url": "https://local.invalid/source#1", "source_revision_id": 101,
                },
                {
                    "id": "p2", "label": "初九", "text": "本地原文乙。",
                    "source_url": "https://local.invalid/source#2", "source_revision_id": 102,
                },
            ],
        },
        "rule_versions": {"traditional_reading": {"id": "qiming-tongshi", "version": "1.0.0"}},
    }


def najia_context() -> dict:
    return {
        "mode": "najia",
        "rule_evidence": [{
            "id": "rule-month-branch", "name": "月建关系", "source_id": "zengshan-buyi",
            "source_title": "增删卜易", "source_url": "https://local.invalid/rule",
            "source_revision_id": 7, "rule_scope": "仅作规则资料",
        }],
        "rule_versions": {"najia": {"id": "najia-test", "version": "1.0.0"}},
    }


def model_output(*, basis: list[dict] | None = None, **overrides) -> dict:
    payload = {
        "response_schema": "ai-response@2",
        "overview": "简短概述",
        "traditional_basis": basis or [],
        "modern_interpretation": "结合问题的现代解释",
        "suggestions": ["核对现实信息"],
        "caution": "不代表确定未来",
    }
    payload.update(overrides)
    return payload


def validate(payload: dict, context: dict | None = None) -> dict:
    return validate_ai_output(json.dumps(payload, ensure_ascii=False), context or classical_context())


def test_evidence_id_injects_authoritative_local_passage_and_source():
    result = validate(model_output(basis=[{"evidence_id": "p1", "explanation": "对应卦辞的说明。"}]))

    assert result["response_schema"] == "ai-response@2"
    assert result["traditional_basis"] == [{"evidence_id": "p1", "explanation": "对应卦辞的说明。"}]
    assert result["cited_passages"] == [{
        "id": "p1", "label": "卦辞", "text": "本地原文甲。",
        "source_url": "https://local.invalid/source#1", "source_revision_id": 101,
    }]


def test_multiple_evidence_ids_resolve_to_matching_local_passages_in_order():
    result = validate(model_output(basis=[
        {"evidence_id": "p2", "explanation": "解释乙。"},
        {"evidence_id": "p1", "explanation": "解释甲。"},
    ]))

    assert [item["id"] for item in result["cited_passages"]] == ["p2", "p1"]
    assert [item["text"] for item in result["cited_passages"]] == ["本地原文乙。", "本地原文甲。"]


def test_output_without_any_model_generated_quotation_is_valid():
    result = validate(model_output())
    assert result["cited_passages"] == []
    assert result["traditional_basis"] == []


@pytest.mark.parametrize("evidence_id,context", [
    ("missing-id", classical_context()),
    ("p1", najia_context()),
])
def test_unknown_or_cross_mode_evidence_id_is_rejected(evidence_id: str, context: dict):
    with pytest.raises(AIOutputValidationError) as exc:
        validate(model_output(basis=[{"evidence_id": evidence_id, "explanation": "说明。"}]), context)
    assert exc.value.code == "invalid_evidence_id"


@pytest.mark.parametrize("field", [
    "quote", "source_text", "quotation", "scripture_text", "source_url",
    "citation", "cited_passage_ids", "cited_rule_ids",
])
def test_schema_rejects_model_generated_authoritative_text_or_source_fields(field: str):
    with pytest.raises(AIOutputValidationError) as exc:
        validate(model_output(**{field: "模型生成字段"}))
    assert exc.value.code == "invalid_schema"


def test_schema_rejects_authoritative_text_fields_inside_evidence_explanations():
    with pytest.raises(AIOutputValidationError) as exc:
        validate(model_output(basis=[{
            "evidence_id": "p1", "explanation": "说明。", "quote": "模型生成原文",
        }]))
    assert exc.value.code == "invalid_schema"


def test_chinese_quotation_marks_in_modern_interpretation_are_not_treated_as_canonical_citations():
    result = validate(model_output(
        basis=[{"evidence_id": "p1", "explanation": "古义提示可用于观察变化。"}],
        modern_interpretation="“先核对事实”是现代表达，不是典籍原文。",
    ))
    assert result["modern_interpretation"].startswith("“先核对事实”")
    assert result["cited_passages"][0]["text"] == "本地原文甲。"


def test_plain_paraphrase_of_classical_text_is_accepted():
    result = validate(model_output(
        basis=[{"evidence_id": "p1", "explanation": "此处强调起步时应审慎。"}],
        modern_interpretation="可以先把不确定因素拆开核验。",
    ))
    assert result["traditional_basis"][0]["explanation"] == "此处强调起步时应审慎。"


def test_referenced_local_evidence_without_authoritative_text_is_rejected():
    context = classical_context()
    context["traditional_reading"]["passages"][0].pop("text")
    with pytest.raises(AIOutputValidationError) as exc:
        validate(model_output(basis=[{"evidence_id": "p1", "explanation": "说明。"}]), context)
    assert exc.value.code == "missing_local_evidence"


def test_evidence_ids_are_isolated_by_mode_and_najia_uses_local_rule_records():
    prompt = build_system_prompt(najia_context())
    assert "payload.rule_evidence" in prompt
    result = validate(model_output(
        basis=[{"evidence_id": "rule-month-branch", "explanation": "依本次命中的规则说明。"}],
    ), najia_context())
    assert result["cited_passages"] == []
    assert result["cited_rules"][0]["id"] == "rule-month-branch"
    assert result["mode"] == "najia"


def test_prompt_declares_v2_and_forbids_model_generated_scripture_and_citations():
    prompt = build_system_prompt(classical_context())
    assert '"response_schema":"ai-response@2"' in prompt
    assert "不要复述、引用或复制任何典籍原文" in prompt
    assert "所有原文将由服务器根据 evidence_id 注入" in prompt
    schema = prompt.split("结构必须且只能包含字段：", 1)[1].split("。不要复述", 1)[0]
    assert "quote" not in schema and "source_text" not in schema
    assert "quote" in prompt and "source_text" in prompt


def test_model_context_keeps_evidence_text_but_hides_authoritative_source_metadata():
    context = classical_context()
    context_json = build_chat_messages(context, [], "synthetic question")[1]["content"].split("\n", 1)[1]
    model_context = json.loads(context_json)

    assert model_context["traditional_reading"]["passages"][0]["text"] == "本地原文甲。"
    assert model_context["traditional_reading"]["passages"][0]["id"] == "p1"
    assert "source_url" not in context_json and "source_revision_id" not in context_json
    assert context["traditional_reading"]["passages"][0]["source_revision_id"] == 101
