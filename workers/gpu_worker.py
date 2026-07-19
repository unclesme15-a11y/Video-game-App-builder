"""GPU worker — runs on the Nitro.

Polls the Acer's job queue over the LAN and handles the two job types that
need a GPU:

- llm_batch:   run a batch of prompts through the local Ollama model
- unity_build: run a Unity batch-mode build of a project directory

Deliberately dependency-light (stdlib + requests) so setup on the Nitro is
just `pip install requests`. Safe to Ctrl-C or close the lid — unclaimed jobs
stay queued on the Acer.

Usage:  ACER_URL=http://<acer-ip>:8000 python workers/gpu_worker.py
"""

from __future__ import annotations

import json
import os
import subprocess
import time

import requests

ACER_URL = os.getenv("ACER_URL", "http://localhost:8000").rstrip("/")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3.1:8b")
UNITY_PATH = os.getenv("UNITY_PATH", "Unity")  # e.g. C:/Program Files/Unity/Hub/Editor/<ver>/Editor/Unity.exe
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "10"))


def handle_llm_batch(payload: dict) -> str:
    results = []
    for prompt in payload.get("prompts", []):
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": LOCAL_MODEL, "prompt": prompt, "stream": False},
            timeout=600,
        )
        r.raise_for_status()
        results.append(r.json()["response"])
    return json.dumps(results)


def handle_unity_build(payload: dict) -> str:
    project_dir = payload["project_dir"]
    cmd = [
        UNITY_PATH,
        "-batchmode", "-nographics", "-quit",
        "-projectPath", project_dir,
        "-executeMethod", payload.get("build_method", "BuildScript.PerformBuild"),
        "-logFile", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if proc.returncode != 0:
        raise RuntimeError(f"unity build failed:\n{proc.stdout[-3000:]}\n{proc.stderr[-1000:]}")
    return f"unity build ok for {project_dir}"


HANDLERS = {
    "llm_batch": handle_llm_batch,
    "unity_build": handle_unity_build,
}


def main() -> None:
    print(f"[worker] polling {ACER_URL} every {POLL_SECONDS}s")
    while True:
        try:
            job = requests.get(f"{ACER_URL}/jobs/next", timeout=10).json()
        except requests.RequestException as e:
            print(f"[worker] Acer unreachable ({e}); retrying")
            time.sleep(POLL_SECONDS)
            continue

        if not job:
            time.sleep(POLL_SECONDS)
            continue

        job_id, job_type = job["id"], job["job_type"]
        print(f"[worker] claimed {job_type} job {job_id}")
        handler = HANDLERS.get(job_type)
        try:
            if handler is None:
                raise ValueError(f"unknown job type: {job_type}")
            result, ok = handler(job["payload"]), True
        except Exception as e:  # report failure back rather than crashing the loop
            result, ok = str(e), False
        requests.post(
            f"{ACER_URL}/jobs/{job_id}/complete",
            json={"ok": ok, "result": result[:10000]},
            timeout=10,
        )
        print(f"[worker] job {job_id} {'done' if ok else 'FAILED'}")


if __name__ == "__main__":
    main()
