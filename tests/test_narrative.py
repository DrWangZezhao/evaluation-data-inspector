from __future__ import annotations

import pytest

from inspector.llm import GeminiConfig, NarrativeProviderError, generate_narrative
from inspector.models import EvidenceFact, NarrativeBlock, NarrativeResponse
from inspector.narrative import build_ai_payload, expand_fact_tokens, validate_narrative


def facts() -> list[EvidenceFact]:
    return [
        EvidenceFact(id="large", kind="numeric", denominator=10, values={"mean": 2.5}, method="mean", sentence="The verified mean was 2.50.", allowed_interpretation_codes=["describe_direction"]),
        EvidenceFact(id="small", kind="group", denominator=3, values={"group_n": 3}, method="group", sentence="Small cell."),
    ]


def test_payload_aliases_labels_suppresses_small_cells_and_contains_no_rows() -> None:
    payload, ids = build_ai_payload(facts(), language="en", audience="researcher", depth="standard", study_context="private context", share_labels=False)
    assert ids == ["large"]
    assert payload["study_context"] == ""
    assert "2.50" not in str(payload)
    assert "rows" not in payload


def test_fact_tokens_expand_complete_sentence() -> None:
    assert expand_fact_tokens("Observed: [[FACT:large]]", facts()) == "Observed: The verified mean was 2.50."


@pytest.mark.parametrize(
    "prose,expected",
    [
        ("The mean was 2.50.", "literal_quantitative_claim"),
        ("It was statistically significant.", "unsupported_claim"),
        ("[[FACT:unknown]]", "unknown_fact"),
        ("[[FACT:large", "unresolved_token"),
    ],
)
def test_narrative_validation_rejects_unsupported_output(prose: str, expected: str) -> None:
    response = NarrativeResponse(language="en", blocks=[NarrativeBlock(section_id="interpretation", prose=prose)])
    assert expected in validate_narrative(response, facts(), "en")


def test_narrative_accepts_known_fact_token_and_allowed_code() -> None:
    response = NarrativeResponse(language="en", blocks=[NarrativeBlock(section_id="interpretation", prose="Observed pattern: [[FACT:large]]", fact_ids=["large"], interpretation_code="describe_direction")])
    assert validate_narrative(response, facts(), "en") == []


def test_missing_key_or_paid_declaration_never_calls_provider() -> None:
    with pytest.raises(NarrativeProviderError, match="not configured"):
        generate_narrative({"facts": []}, GeminiConfig(api_key="", paid_service=False))
