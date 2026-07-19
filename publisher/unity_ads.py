"""Pull actual ad revenue per game from the Unity Ads Monetization Stats API.

This is the ground truth for promotion decisions: not downloads, but dollars.
Setup: Unity dashboard -> Organization settings -> API management -> copy the
Monetization Stats API key and your Organization core ID.

Env: UNITY_ORG_ID, UNITY_STATS_API_KEY
"""

from __future__ import annotations

import csv
import io
import os
from datetime import datetime, timedelta, timezone

import requests

BASE = "https://monetization.api.unity.com/stats/v1/operate/organizations"

UNITY_ORG_ID = os.getenv("UNITY_ORG_ID", "")
UNITY_STATS_API_KEY = os.getenv("UNITY_STATS_API_KEY", "")


def revenue_last_30d() -> dict[str, dict]:
    """Returns {game_name: {"revenue": usd, "impressions": n}} for the last 30 days."""
    if not (UNITY_ORG_ID and UNITY_STATS_API_KEY):
        print("[unity_ads] UNITY_ORG_ID / UNITY_STATS_API_KEY not set — skipping")
        return {}

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=30)
    r = requests.get(
        f"{BASE}/{UNITY_ORG_ID}/reports",
        params={
            "apikey": UNITY_STATS_API_KEY,
            "start": start.strftime("%Y-%m-%dT00:00:00Z"),
            "end": end.strftime("%Y-%m-%dT00:00:00Z"),
            "scale": "all",
            "splitBy": "game",
            "fields": "revenue_sum,impression_sum",
        },
        timeout=60,
    )
    r.raise_for_status()

    # The stats API returns CSV; column names vary slightly by account age,
    # so match them loosely.
    games: dict[str, dict] = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        name = next((row[k] for k in row if "game" in k.lower() or "source" in k.lower()), None)
        revenue = next((row[k] for k in row if "revenue" in k.lower()), 0)
        impressions = next((row[k] for k in row if "impression" in k.lower()), 0)
        if name is None:
            continue
        entry = games.setdefault(name, {"revenue": 0.0, "impressions": 0})
        entry["revenue"] += float(revenue or 0)
        entry["impressions"] += int(float(impressions or 0))
    return games
