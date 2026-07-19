"""Dispatcher — the handoff from intelligence to execution.

Takes the top-ranked opportunity at or above the build threshold, writes a
spec, runs the builder agent on the Acer, and queues any GPU work (Unity
builds) for the Nitro worker.

Run:  python -m orchestrator.dispatcher
"""

from __future__ import annotations

from engine.config import settings
from engine.database import store
from engine.learning import feedback_log
from orchestrator import builder_agent, task_spec


def dispatch_next() -> None:
    ranked = [
        o
        for o in store.ranked_opportunities(min_score=settings.MIN_BUILD_THRESHOLD)
        if o["status"] == "ranked"
    ]
    if not ranked:
        print(f"[dispatcher] nothing at or above {settings.MIN_BUILD_THRESHOLD} — "
              "run `python -m engine.pipeline` first")
        return

    top = ranked[0]
    print(f"[dispatcher] dispatching {top['title']!r} ({top['total_score']}, {top['channel']})")
    feedback_log.record(top["id"], "dispatched", "picked by dispatcher")

    spec = task_spec.create(top)
    project_dir = builder_agent.build(spec)

    if spec["needs_gpu_jobs"]:
        job_id = store.enqueue_job(
            "unity_build",
            {"project_dir": str(project_dir), "opportunity_id": top["id"]},
        )
        print(f"[dispatcher] queued GPU job {job_id} — Nitro will pick it up when online")

    feedback_log.record(top["id"], "built", f"scaffold at {project_dir}")


if __name__ == "__main__":
    dispatch_next()
