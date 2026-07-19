"""Publish builds to itch.io via the butler CLI.

itch.io is the best first target: free, no review queue, and butler makes
uploads fully scriptable. Auth: set BUTLER_API_KEY (from
https://itch.io/user/settings/api-keys) — butler reads it from the env.

The game page itself must be created once by hand on itch.io (butler can't
create pages), then every update is automated.

Env-only config (no engine imports) so this runs on the Nitro too.
"""

from __future__ import annotations

import os
import subprocess

BUTLER = os.getenv("BUTLER_PATH", "butler")
ITCHIO_USER = os.getenv("ITCHIO_USER", "")


def publish(artifact_dir: str, game_slug: str, channel: str = "windows") -> str:
    """Push a build directory to <user>/<slug>:<channel>. Returns a status line."""
    if not ITCHIO_USER:
        raise RuntimeError("set ITCHIO_USER in the environment")
    target = f"{ITCHIO_USER}/{game_slug}:{channel}"
    proc = subprocess.run(
        [BUTLER, "push", artifact_dir, target],
        capture_output=True, text=True, timeout=1800,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"butler push failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-500:]}")
    return f"published to https://{ITCHIO_USER}.itch.io/{game_slug} ({channel})"
