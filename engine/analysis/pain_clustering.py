"""Pain Clustering Engine.

Groups raw signals into named pain points. This is bulk work, so it runs on the
Nitro's local model when it's online (see adapters.llm.bulk) and falls back to
the cloud model otherwise.
"""

from __future__ import annotations

import json

from engine.adapters import llm
from engine.database import store

SYSTEM = (
    "You cluster user complaints into distinct product pain points. "
    "Respond ONLY with a JSON array, no prose."
)

PROMPT = """Below are raw user complaints scraped from GitHub issues and app store reviews.
Cluster them into at most {max_clusters} distinct pain points.

Return a JSON array where each element is:
{{"title": "<short pain point name>", "summary": "<2-3 sentence description of the pain and who feels it>", "signal_count": <number of complaints in this cluster>}}

Complaints:
{signals}
"""


def cluster(max_clusters: int = 8, signal_limit: int = 150) -> list[dict]:
    signals = store.recent_signals(limit=signal_limit)
    if not signals:
        print("[clustering] no signals to cluster")
        return []

    blob = "\n---\n".join(s["text"][:500] for s in signals)
    raw = llm.bulk(PROMPT.format(max_clusters=max_clusters, signals=blob), system=SYSTEM)

    # Local models sometimes wrap JSON in prose/fences — extract the array.
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        print(f"[clustering] unparseable model output: {raw[:200]}")
        return []
    try:
        clusters = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        print("[clustering] invalid JSON from model")
        return []

    print(f"[clustering] {len(signals)} signals -> {len(clusters)} pain points")
    return clusters
