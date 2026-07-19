"""Turns a ranked opportunity into a build spec the builder agents can execute."""

from __future__ import annotations

from engine.adapters import llm

SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "one_liner": {"type": "string"},
        "tech_stack": {"type": "string"},
        "mvp_features": {"type": "array", "items": {"type": "string"}},
        "out_of_scope": {"type": "array", "items": {"type": "string"}},
        "monetization": {"type": "string"},
        "needs_gpu_jobs": {"type": "boolean"},
    },
    "required": [
        "project_name", "one_liner", "tech_stack", "mvp_features",
        "out_of_scope", "monetization", "needs_gpu_jobs",
    ],
    "additionalProperties": False,
}

PROMPT = """Write a build spec for a small AI-assisted builder team.

Opportunity (scored {score}, channel: {channel}):
{title}
{summary}

Rules:
- MVP only: 3-6 features, shippable in days not months.
- tech_stack must match the channel: mobile -> Unity (C#), saas -> FastAPI + web
  frontend, ai_tool -> Python CLI/API around a Claude API core.
- needs_gpu_jobs is true only if the build requires Unity builds or local model
  inference (those get queued for the GPU worker).
- project_name: lowercase, hyphenated, filesystem-safe."""


def create(opportunity: dict) -> dict:
    spec = llm.cloud().complete_json(
        PROMPT.format(
            score=opportunity["total_score"],
            channel=opportunity["channel"],
            title=opportunity["title"],
            summary=opportunity["pain_summary"],
        ),
        schema=SCHEMA,
    )
    print(f"[spec] {spec['project_name']}: {spec['one_liner']}")
    return spec
