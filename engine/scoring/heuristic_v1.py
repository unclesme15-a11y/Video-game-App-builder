"""Heuristic Scoring Model v1 — Blended Scoring Formula V2.

O = 0.25*PainIntensity + 0.20*MarketGap + 0.15*MonetizationClarity
  + 0.15*ImplementationEase + 0.15*DistributionFit + 0.10*CompetitiveWeakness

Factor scores (0-10) come from the cloud model — scoring quality directly
drives what gets built, so this stays on the strong model rather than the
local one.
"""

from __future__ import annotations

from engine.adapters import llm
from engine.config import settings

FACTORS = list(settings.SCORING_WEIGHTS.keys())

SCHEMA = {
    "type": "object",
    "properties": {f: {"type": "number"} for f in FACTORS} | {
        "rationale": {"type": "string"}
    },
    "required": FACTORS + ["rationale"],
    "additionalProperties": False,
}

PROMPT = """Score this product opportunity on six factors, each 0-10.

Pain point: {title}
{summary}
(backed by {signal_count} scraped complaints)

Factors:
- pain_intensity: how badly do users feel this problem?
- market_gap: how underserved is it by existing products?
- monetization_clarity: how obvious is the path to revenue?
- implementation_ease: how feasible is it for a small AI-assisted builder team? (10 = a weekend, 0 = years)
- distribution_fit: how easily can it reach users through app stores / web / dev channels?
- competitive_weakness: how weak are the incumbents?

Include a one-paragraph rationale."""


def blended_score(factor_scores: dict) -> float:
    return round(
        sum(settings.SCORING_WEIGHTS[f] * float(factor_scores[f]) for f in FACTORS), 2
    )


def score(pain_point: dict) -> tuple[dict, float]:
    """Returns (factor_scores_with_rationale, blended_total)."""
    result = llm.cloud().complete_json(
        PROMPT.format(
            title=pain_point["title"],
            summary=pain_point["summary"],
            signal_count=pain_point.get("signal_count", "?"),
        ),
        schema=SCHEMA,
    )
    total = blended_score(result)
    print(f"[scoring] {pain_point['title']!r} -> {total}")
    return result, total
