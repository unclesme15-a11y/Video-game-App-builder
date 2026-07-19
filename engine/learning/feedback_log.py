"""Feedback Logging Endpoint backend.

Records real-world outcomes per opportunity (shipped, revenue, abandoned...).
This log is the raw material for the Phase 2 Scoring Weight Adjustment Engine —
compounding feedback data is the moat, so log everything.
"""

from __future__ import annotations

from engine.database import store

VALID_OUTCOMES = {"dispatched", "built", "shipped", "revenue", "abandoned", "rejected"}


def record(opportunity_id: str, outcome: str, notes: str = "") -> None:
    if outcome not in VALID_OUTCOMES:
        raise ValueError(f"outcome must be one of {sorted(VALID_OUTCOMES)}")
    store.add_feedback(opportunity_id, outcome, notes)
    if outcome in {"dispatched", "built", "shipped", "rejected"}:
        store.set_opportunity_status(opportunity_id, outcome)
