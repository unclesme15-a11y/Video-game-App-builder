"""Store performance tracker — the "is this app worth real money?" signal.

Verdict logic, in priority order:

1. REVENUE (ground truth): Unity Ads revenue over the last 30 days.
   >= PROMOTE_REVENUE_THRESHOLD/mo  -> PROMOTE (it already pays for itself on
   free-store traffic; the same game on Google Play sees far more players)
2. DOWNLOADS (early signal, before ad data accumulates): itch.io downloads
   >= PROMOTE_DOWNLOAD_THRESHOLD -> WATCH CLOSELY
3. Neither -> keep watching, or kill after KILL_AFTER_DAYS with no traction.

Runs on the Acer (cron):  python -m publisher.tracker
"""

from __future__ import annotations

import os

import requests

from engine.database import store
from publisher import unity_ads

ITCHIO_API_KEY = os.getenv("ITCHIO_API_KEY", "")
PROMOTE_REVENUE_THRESHOLD = float(os.getenv("PROMOTE_REVENUE_THRESHOLD", "10"))  # USD / 30 days
PROMOTE_DOWNLOAD_THRESHOLD = int(os.getenv("PROMOTE_DOWNLOAD_THRESHOLD", "500"))


def pull_itchio_metrics() -> list[dict]:
    if not ITCHIO_API_KEY:
        print("[tracker] ITCHIO_API_KEY not set — skipping itch.io pull")
        return []
    r = requests.get(f"https://itch.io/api/1/{ITCHIO_API_KEY}/my-games", timeout=30)
    r.raise_for_status()
    return [
        {
            "store": "itchio",
            "slug": game.get("url", "").rsplit("/", 1)[-1],
            "title": game.get("title", ""),
            "views": game.get("views_count", 0),
            "downloads": game.get("downloads_count", 0),
            "purchases": game.get("purchases_count", 0),
        }
        for game in r.json().get("games", [])
    ]


def verdict(revenue_30d: float, downloads: int) -> str:
    if revenue_30d >= PROMOTE_REVENUE_THRESHOLD:
        return "PROMOTE — pays for itself; buy the $25 Google Play slot"
    if downloads >= PROMOTE_DOWNLOAD_THRESHOLD:
        return "WATCH — traction but revenue unproven; check ad placement"
    return "keep watching"


def snapshot() -> list[dict]:
    """Combine itch.io traffic with Unity Ads revenue, store, and return rows."""
    revenue_by_game = unity_ads.revenue_last_30d()
    rows = []
    for snap in pull_itchio_metrics():
        ads = revenue_by_game.get(snap["title"], {"revenue": 0.0, "impressions": 0})
        snap["revenue_30d"] = round(ads["revenue"], 2)
        snap["impressions_30d"] = ads["impressions"]
        snap["verdict"] = verdict(snap["revenue_30d"], snap["downloads"])
        store.add_store_metric(snap)
        rows.append(snap)
    return rows


def report() -> None:
    rows = snapshot()
    if not rows:
        print("[tracker] no data")
        return
    print(f"\n{'title':<28}{'downloads':>10}{'imps/30d':>10}{'rev/30d':>9}  verdict")
    for s in sorted(rows, key=lambda x: (-x["revenue_30d"], -x["downloads"])):
        print(
            f"{s['title'][:26]:<28}{s['downloads']:>10}{s['impressions_30d']:>10}"
            f"{'$' + str(s['revenue_30d']):>9}  {s['verdict']}"
        )


if __name__ == "__main__":
    report()
