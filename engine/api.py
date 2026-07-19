"""JSON API served from the Acer.

- Ranked Opportunity List (the Phase 1 deliverable)
- Feedback logging endpoint
- GPU job queue endpoints that the Nitro worker polls over the LAN

Run:  uvicorn engine.api:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from engine.config import settings
from engine.database import store
from engine.learning import feedback_log

app = FastAPI(title="Opportunity Intelligence Engine")


# --- opportunities ---------------------------------------------------------

@app.get("/opportunities")
def opportunities(min_score: float = 0.0):
    return store.ranked_opportunities(min_score=min_score)


@app.get("/opportunities/buildable")
def buildable():
    return store.ranked_opportunities(min_score=settings.MIN_BUILD_THRESHOLD)


class Feedback(BaseModel):
    opportunity_id: str
    outcome: str
    notes: str = ""


@app.post("/feedback")
def feedback(body: Feedback):
    try:
        feedback_log.record(body.opportunity_id, body.outcome, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {"ok": True}


# --- GPU job queue (polled by workers/gpu_worker.py on the Nitro) ----------

class NewJob(BaseModel):
    job_type: str  # llm_batch | unity_build
    payload: dict


@app.post("/jobs")
def create_job(body: NewJob):
    return {"id": store.enqueue_job(body.job_type, body.payload)}


@app.get("/jobs/next")
def next_job():
    job = store.claim_next_job()
    return job or {}


class JobResult(BaseModel):
    ok: bool
    result: str = ""


@app.post("/jobs/{job_id}/complete")
def complete_job(job_id: str, body: JobResult):
    store.finish_job(job_id, body.ok, body.result)
    return {"ok": True}
