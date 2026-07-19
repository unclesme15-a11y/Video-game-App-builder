"""One full intelligence pass: ingest -> cluster -> score -> route -> store.

Run on the Acer (cron or manual):  python -m engine.pipeline
"""

from __future__ import annotations

from engine.analysis import pain_clustering
from engine.config import settings
from engine.database import store
from engine.routing import distribution_router
from engine.scoring import heuristic_v1
from engine.signals import app_store_reviews, github_signals


def run() -> None:
    github_signals.ingest()
    app_store_reviews.ingest()

    for pain_point in pain_clustering.cluster():
        scores, total = heuristic_v1.score(pain_point)
        channel = distribution_router.route(pain_point)
        store.add_opportunity(
            title=pain_point["title"],
            pain_summary=pain_point["summary"],
            scores=scores,
            total=total,
            channel=channel,
        )

    buildable = store.ranked_opportunities(min_score=settings.MIN_BUILD_THRESHOLD)
    print(f"\n[pipeline] done — {len(buildable)} opportunities at or above "
          f"{settings.MIN_BUILD_THRESHOLD}:")
    for o in buildable:
        print(f"  {o['total_score']:>5}  [{o['channel']}]  {o['title']}")


if __name__ == "__main__":
    run()
