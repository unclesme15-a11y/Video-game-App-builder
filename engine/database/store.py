"""SQLite persistence for signals, opportunities, feedback, and the GPU job queue."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager

from engine.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,            -- github | app_store
    external_id TEXT,
    text TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    created_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_signals_dedupe ON signals (source, external_id);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    pain_summary TEXT NOT NULL,
    scores TEXT NOT NULL,            -- json of the six factor scores
    total_score REAL NOT NULL,
    channel TEXT,                    -- mobile | saas | ai_tool
    status TEXT DEFAULT 'ranked',    -- ranked | dispatched | built | shipped | rejected
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    notes TEXT DEFAULT '',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,          -- llm_batch | unity_build
    payload TEXT NOT NULL,
    status TEXT DEFAULT 'queued',    -- queued | claimed | done | failed
    result TEXT,
    created_at REAL NOT NULL,
    claimed_at REAL,
    finished_at REAL
);
"""


@contextmanager
def conn():
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    try:
        yield c
        c.commit()
    finally:
        c.close()


# --- signals ---------------------------------------------------------------

def add_signal(source: str, external_id: str, text: str, metadata: dict | None = None) -> bool:
    with conn() as c:
        try:
            c.execute(
                "INSERT INTO signals (id, source, external_id, text, metadata, created_at) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), source, external_id, text, json.dumps(metadata or {}), time.time()),
            )
            return True
        except sqlite3.IntegrityError:
            return False  # already ingested


def recent_signals(limit: int = 200) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# --- opportunities ---------------------------------------------------------

def add_opportunity(title: str, pain_summary: str, scores: dict, total: float, channel: str) -> str:
    oid = str(uuid.uuid4())
    with conn() as c:
        c.execute(
            "INSERT INTO opportunities (id, title, pain_summary, scores, total_score, channel, created_at) VALUES (?,?,?,?,?,?,?)",
            (oid, title, pain_summary, json.dumps(scores), total, channel, time.time()),
        )
    return oid


def ranked_opportunities(min_score: float = 0.0) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM opportunities WHERE total_score >= ? ORDER BY total_score DESC",
            (min_score,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["scores"] = json.loads(d["scores"])
        out.append(d)
    return out


def set_opportunity_status(opportunity_id: str, status: str) -> None:
    with conn() as c:
        c.execute("UPDATE opportunities SET status = ? WHERE id = ?", (status, opportunity_id))


# --- feedback --------------------------------------------------------------

def add_feedback(opportunity_id: str, outcome: str, notes: str = "") -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO feedback (id, opportunity_id, outcome, notes, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), opportunity_id, outcome, notes, time.time()),
        )


# --- job queue (Nitro polls these over the API) ----------------------------

def enqueue_job(job_type: str, payload: dict) -> str:
    jid = str(uuid.uuid4())
    with conn() as c:
        c.execute(
            "INSERT INTO jobs (id, job_type, payload, created_at) VALUES (?,?,?,?)",
            (jid, job_type, json.dumps(payload), time.time()),
        )
    return jid


def claim_next_job() -> dict | None:
    with conn() as c:
        row = c.execute(
            "SELECT * FROM jobs WHERE status = 'queued' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        c.execute(
            "UPDATE jobs SET status = 'claimed', claimed_at = ? WHERE id = ?",
            (time.time(), row["id"]),
        )
    d = dict(row)
    d["payload"] = json.loads(d["payload"])
    return d


def finish_job(job_id: str, ok: bool, result: str) -> None:
    with conn() as c:
        c.execute(
            "UPDATE jobs SET status = ?, result = ?, finished_at = ? WHERE id = ?",
            ("done" if ok else "failed", result, time.time(), job_id),
        )
