# Video Game / App Builder

An AI builder team plus an Opportunity Intelligence Engine, designed to run on a
two-machine home setup:

- **Acer laptop (Ubuntu, always on)** — the brain *and* the hands. Runs the
  intelligence engine (signal ingestion, pain clustering, scoring, routing),
  the builder orchestrator, and the code-writing agents (Claude API). Also
  hosts the job queue API.
- **Acer Nitro (GPU, on when available)** — the muscle. Polls the Acer's job
  queue and handles the two jobs that need a GPU: local LLM inference (Ollama)
  and Unity builds/playtesting. Nothing breaks when it's offline — GPU jobs
  just wait in the queue.

## How it flows

```
signals (GitHub issues, app store reviews)
        │  engine/signals
        ▼
pain clustering ──► scoring (blended formula, ship at ≥ 8.2) ──► router (mobile/saas/ai tool)
        engine/analysis        engine/scoring                      engine/routing
                                                                        │
                                                                        ▼
                                                       orchestrator: task spec ──► builder agent
                                                                        │        (writes code, pushes
                                                                        │         to GitHub)
                                                                        ▼
                                                            GPU job queue (FastAPI on Acer)
                                                                        │  polled over LAN
                                                                        ▼
                                                            workers/gpu_worker.py (Nitro)
                                                            - Ollama inference batches
                                                            - Unity batch builds
```

## Layout

| Path | What it is | Runs on |
|---|---|---|
| `engine/` | Opportunity Intelligence Engine (signals, analysis, scoring, routing, learning, adapters, database, config) | Acer |
| `engine/api.py` | JSON API: ranked opportunity list, feedback endpoint, job queue | Acer |
| `orchestrator/` | Turns the top opportunity into a build spec and drives the builder agents | Acer |
| `workers/gpu_worker.py` | GPU worker: polls the queue, runs Ollama + Unity jobs | Nitro |
| `docs/` | Setup guides for each machine | — |

## Quick start (Acer)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY etc.
uvicorn engine.api:app --host 0.0.0.0 --port 8000
```

Run one intelligence pass (ingest → cluster → score → route):

```bash
python -m engine.pipeline
```

Dispatch the top-ranked opportunity to the builder team:

```bash
python -m orchestrator.dispatcher
```

## Quick start (Nitro)

```bash
pip install requests
# Ollama installed + a small model pulled, e.g.: ollama pull llama3.1:8b
ACER_URL=http://<acer-ip>:8000 python workers/gpu_worker.py
```

See `docs/SETUP-ACER.md` and `docs/SETUP-NITRO.md` for full setup.
