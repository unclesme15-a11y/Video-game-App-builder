"""App Store Review Ingestion (basic scraper).

Pulls customer reviews from Apple's public RSS feed for each app ID in
APP_STORE_APP_IDS. Low-star reviews are the richest pain signal, so 1-3 star
reviews are kept and 4-5 star ones skipped.
"""

from __future__ import annotations

import requests

from engine.config import settings
from engine.database import store

FEED = "https://itunes.apple.com/us/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"


def ingest(app_ids: list[str] | None = None) -> int:
    added = 0
    for app_id in app_ids or settings.APP_STORE_APP_IDS:
        r = requests.get(FEED.format(app_id=app_id), timeout=30)
        if r.status_code != 200:
            print(f"[app_store] app {app_id} failed: {r.status_code}")
            continue
        entries = r.json().get("feed", {}).get("entry", [])
        for e in entries:
            if "im:rating" not in e:
                continue  # first entry is app metadata, not a review
            rating = int(e["im:rating"]["label"])
            if rating > 3:
                continue
            text = f"[{rating}★] {e['title']['label']}\n{e['content']['label'][:2000]}"
            if store.add_signal(
                source="app_store",
                external_id=e["id"]["label"],
                text=text,
                metadata={"app_id": app_id, "rating": rating},
            ):
                added += 1
    print(f"[app_store] ingested {added} new signals")
    return added
