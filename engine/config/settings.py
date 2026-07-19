"""Central configuration, loaded from environment / .env file."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

REPO_ROOT = Path(__file__).resolve().parents[2]

# --- Models ---------------------------------------------------------------
# Cloud model writes production code and specs; local model (on the Nitro via
# Ollama) does cheap bulk work: clustering reviews, summarizing signals.
CLOUD_MODEL = os.getenv("CLOUD_MODEL", "claude-opus-4-8")
LOCAL_MODEL = os.getenv("LOCAL_MODEL", "llama3.1:8b")

# Ollama server on the Nitro. When unreachable, adapters fall back to cloud.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://nitro.local:11434")

# --- Storage --------------------------------------------------------------
DB_PATH = Path(os.getenv("DB_PATH", REPO_ROOT / "engine" / "database" / "engine.db"))

# --- Scoring (Blended Scoring Formula V2) ---------------------------------
SCORING_WEIGHTS = {
    "pain_intensity": 0.25,
    "market_gap": 0.20,
    "monetization_clarity": 0.15,
    "implementation_ease": 0.15,
    "distribution_fit": 0.15,
    "competitive_weakness": 0.10,
}
MIN_BUILD_THRESHOLD = float(os.getenv("MIN_BUILD_THRESHOLD", "8.2"))

# --- Signal ingestion -----------------------------------------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")  # optional, raises rate limits
GITHUB_SEARCH_QUERIES = [
    q.strip()
    for q in os.getenv(
        "GITHUB_SEARCH_QUERIES",
        "label:bug frustrating,wish this existed,no good tool for",
    ).split(",")
]
APP_STORE_APP_IDS = [
    a.strip() for a in os.getenv("APP_STORE_APP_IDS", "").split(",") if a.strip()
]

# --- Builder output -------------------------------------------------------
WORKSPACE_DIR = Path(os.getenv("WORKSPACE_DIR", REPO_ROOT / "workspace"))
