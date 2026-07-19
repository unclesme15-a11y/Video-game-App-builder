"""Store performance tracker — the "is this app worth real money?" signal.

Pulls views/downloads for every published game from the itch.io server API
and stores a snapshot. Apps that clear PROMOTE_DOWNLOAD_THRESHOLD get flagged
as worth the $25 Google Play registration (and, if they keep earning, the
$99/yr Apple account).

Runs on the Acer (cron):  python -m publisher.tracker
"""

from __future__ import annotations

import os

import requests

from engine.database import store

ITCHIO_API_KEY = os.getenv("ITCHIO_API_KEY", "")
PROMOTE_DOWNLOAD_THRESHOLD = int(os.getenv("PROMOTE_DOWNLOAD_THRESHOLD", "500"))


def pull_itchio_metrics() -> list[dict]:
    if not ITCHIO_API_KEY:
        print("[tracker] ITCHIO_API_KEY not set — skipping itch.io pull")
        return []
    r = requests.get(f"https://itch.io/api/1/{ITCHIO_API_KEY}/my-games", timeout=30)
    r.raise_for_status()
    snapshots = []
    for game in r.json().get("games", []):
        snap = {
            "store": "itchio",
            "slug": game.get("url", "").rsplit("/", 1)[-1],
            "title": game.get("title", ""),
            "views": game.get("views_count", 0),
            "downloads": game.get("downloads_count", 0),
            "purchases": game.get("purchases_count", 0),
        }
        store.add_store_metric(snap)
        snapshots.append(snap)
    return snapshots


def report() -> None:
    snapshots = pull_itchio_metrics()
    if not snapshots:
        print("[tracker] no data")
        return
    print(f"\n{'title':<32}{'views':>8}{'downloads':>11}  verdict")
    for s in sorted(snapshots, key=lambda x: -x["downloads"]):
        verdict = (
            "PROMOTE -> worth $25 Google Play"
            if s["downloads"] >= PROMOTE_DOWNLOAD_THRESHOLD
            else "keep watching"
        )
        print(f"{s['title'][:30]:<32}{s['views']:>8}{s['downloads']:>11}  {verdict}")


if __name__ == "__main__":
    report()
