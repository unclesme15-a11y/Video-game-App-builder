"""Distribution Router — decides the channel for each opportunity:
mobile app, SaaS, or AI tool.
"""

from __future__ import annotations

from engine.adapters import llm

SCHEMA = {
    "type": "object",
    "properties": {
        "channel": {"type": "string", "enum": ["mobile", "saas", "ai_tool"]},
        "reason": {"type": "string"},
    },
    "required": ["channel", "reason"],
    "additionalProperties": False,
}

PROMPT = """Given this product opportunity, pick the best distribution channel.

Pain point: {title}
{summary}

Channels:
- mobile: consumer-facing, app-store distribution (Unity or native)
- saas: web app with subscriptions
- ai_tool: developer/pro tool built around an AI capability

Pick exactly one and explain briefly."""


def route(pain_point: dict) -> str:
    result = llm.cloud().complete_json(
        PROMPT.format(title=pain_point["title"], summary=pain_point["summary"]),
        schema=SCHEMA,
    )
    print(f"[routing] {pain_point['title']!r} -> {result['channel']}")
    return result["channel"]
