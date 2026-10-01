"""Narrative payload minimization, validation, and fact-token expansion."""

from __future__ import annotations

import re
from typing import Any

from .llm import GeminiConfig, NarrativeProviderError, generate_narrative
from .models import EvidenceFact, NarrativeResponse


TOKEN_RE = re.compile(r"\[\[FACT:([A-Za-z0-9_-]+)\]\]")
NUMBER_RE = re.compile(r"(?<![\w\]])[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?%?")
BANNED = {
    "en": ("statistically significant", "caused", "causes", "proved", "citation", "references"),
    "zh-CN": ("统计显著", "导致了", "证明了", "参考文献", "引用"),
    "es": ("estadísticamente significativo", "causó", "demostró", "referencias", "citación"),
    "fi": ("tilastollisesti merkitsevä", "aiheutti", "todisti", "lähdeviitteet", "viittaus"),
}


def build_ai_payload(
    facts: list[EvidenceFact], *, language: str, audience: str, depth: str,
    study_context: str = "", share_labels: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    """Select up to 30 non-small-cell facts and alias bindings by default."""

    approved: list[dict[str, Any]] = []
    selected_ids: list[str] = []
    for fact in facts:
        if fact.denominator is not None and fact.denominator < 5:
            continue
        if any(isinstance(value, int) and value < 5 for key, value in fact.values.items() if key.endswith("_n")):
            continue
        alias = fact.id if not share_labels else fact.sentence
        approved.append({
            "id": fact.id,
            "token": f"[[FACT:{fact.id}]]",
            "binding": alias,
            "kind": fact.kind,
            "allowed_interpretation_codes": fact.allowed_interpretation_codes,
        })
        selected_ids.append(fact.id)
        if len(approved) == 30:
            break
    payload = {
        "language": language,
        "audience": audience,
        "depth": depth,
        "study_context": study_context[:2000] if share_labels else "",
        "facts": approved,
        "instructions": "Use FACT tokens for every empirical statement; prose may only connect them cautiously.",
    }
    return payload, selected_ids


def validate_narrative(response: NarrativeResponse, facts: list[EvidenceFact], language: str) -> list[str]:
    errors: list[str] = []
    fact_map = {fact.id: fact for fact in facts}
    if response.language != language:
        errors.append("wrong_language")
    for block in response.blocks:
        if not block.prose.strip():
            errors.append("empty_prose")
            continue
        token_ids = TOKEN_RE.findall(block.prose)
        if any(fact_id not in fact_map for fact_id in token_ids + block.fact_ids):
            errors.append("unknown_fact")
        if "[[FACT:" in block.prose and not token_ids:
            errors.append("unresolved_token")
        free_text = TOKEN_RE.sub("", block.prose)
        if NUMBER_RE.search(free_text):
            errors.append("literal_quantitative_claim")
        folded = free_text.casefold()
        if any(term.casefold() in folded for term in BANNED.get(language, ())):
            errors.append("unsupported_claim")
        if block.interpretation_code:
            allowed = {code for fact_id in block.fact_ids if fact_id in fact_map for code in fact_map[fact_id].allowed_interpretation_codes}
            if block.interpretation_code not in allowed:
                errors.append("unsupported_interpretation")
    return sorted(set(errors))


def expand_fact_tokens(text: str, facts: list[EvidenceFact]) -> str:
    fact_map = {fact.id: fact.sentence for fact in facts}
    return TOKEN_RE.sub(lambda match: fact_map.get(match.group(1), ""), text)


def request_validated_narrative(
    facts: list[EvidenceFact], payload: dict[str, Any], config: GeminiConfig,
) -> tuple[NarrativeResponse | None, str | None, str | None, int]:
    """Try once, then allow one correction with the same approved evidence."""

    attempts = 0
    errors: list[str] = []
    returned_model: str | None = None
    for attempt in range(2):
        attempts += 1
        request = dict(payload)
        if errors:
            request["validation_errors"] = errors
            request["instructions"] = "Correct only the listed validation errors; use the identical approved evidence."
        try:
            response, returned_model = generate_narrative(
                request,
                GeminiConfig(
                    api_key=config.api_key, model=config.model, paid_service=config.paid_service,
                    session_attempts=config.session_attempts + attempt,
                ),
            )
        except NarrativeProviderError as exc:
            return None, returned_model, str(exc), attempts
        errors = validate_narrative(response, facts, str(payload["language"]))
        if not errors:
            return response, returned_model, None, attempts
    return None, returned_model, "AI text did not pass evidence validation.", attempts
