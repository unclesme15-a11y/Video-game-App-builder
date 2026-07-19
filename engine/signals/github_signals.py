"""GitHub Signal Ingestion Module.

Searches GitHub issues for pain language ("wish this existed", "no good tool
for", ...) and stores each hit as a raw signal. Unauthenticated works but is
rate-limited; set GITHUB_TOKEN to raise limits.
"""

from __future__ import annotations

import requests

from engine.config import settings
from engine.database import store

API = "https://api.github.com/search/issues"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if settings.GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return h


def ingest(queries: list[str] | None = None, per_query: int = 30) -> int:
    added = 0
    for query in queries or settings.GITHUB_SEARCH_QUERIES:
        r = requests.get(
            API,
            headers=_headers(),
            params={"q": f'"{query}" in:title,body is:issue', "per_page": per_query},
            timeout=30,
        )
        if r.status_code != 200:
            print(f"[github] query {query!r} failed: {r.status_code}")
            continue
        for item in r.json().get("items", []):
            text = f"{item.get('title', '')}\n{(item.get('body') or '')[:2000]}"
            if store.add_signal(
                source="github",
                external_id=str(item["id"]),
                text=text,
                metadata={"url": item.get("html_url"), "query": query},
            ):
                added += 1
    print(f"[github] ingested {added} new signals")
    return added
