"""Builder agent — writes project code on the Acer via the Claude API.

Uses the SDK tool runner: the model calls write_file/read_file/list_files and
the loop runs until the MVP scaffold is complete. All file operations are
confined to WORKSPACE_DIR/<project_name>. No GPU needed — this is API calls
plus file I/O.
"""

from __future__ import annotations

import json
from pathlib import Path

import anthropic
from anthropic import beta_tool

from engine.config import settings

_project_root: Path | None = None


def _safe_path(relative_path: str) -> Path:
    assert _project_root is not None
    p = (_project_root / relative_path).resolve()
    if not p.is_relative_to(_project_root):
        raise ValueError(f"path escapes project root: {relative_path}")
    return p


@beta_tool
def write_file(path: str, content: str) -> str:
    """Write a file inside the project directory.

    Args:
        path: Relative path within the project (e.g. "src/main.py").
        content: Full file contents.
    """
    try:
        p = _safe_path(path)
    except ValueError as e:
        return f"ERROR: {e}"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {path} ({len(content)} bytes)"


@beta_tool
def read_file(path: str) -> str:
    """Read a file from the project directory.

    Args:
        path: Relative path within the project.
    """
    try:
        p = _safe_path(path)
    except ValueError as e:
        return f"ERROR: {e}"
    if not p.exists():
        return "ERROR: file does not exist"
    return p.read_text()[:20000]


@beta_tool
def list_files(subdir: str = ".") -> str:
    """List files in the project directory.

    Args:
        subdir: Relative subdirectory to list (default: project root).
    """
    try:
        p = _safe_path(subdir)
    except ValueError as e:
        return f"ERROR: {e}"
    if not p.exists():
        return "(empty)"
    return "\n".join(
        str(f.relative_to(_project_root)) for f in sorted(p.rglob("*")) if f.is_file()
    ) or "(empty)"


SYSTEM = """You are a builder agent on a small app studio team. Build the MVP
described in the spec by writing real, runnable code with the file tools.

Work file by file. Include a README with run instructions. Keep the scaffold
minimal but complete — every MVP feature in the spec gets working code, nothing
outside the spec does. Finish with a short summary of what you built."""


def build(spec: dict) -> Path:
    global _project_root
    _project_root = (settings.WORKSPACE_DIR / spec["project_name"]).resolve()
    _project_root.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model=settings.CLOUD_MODEL,
        max_tokens=32000,
        system=SYSTEM,
        tools=[write_file, read_file, list_files],
        messages=[{"role": "user", "content": f"Build spec:\n{json.dumps(spec, indent=2)}"}],
    )
    for message in runner:
        for block in message.content:
            if block.type == "text" and block.text.strip():
                print(f"[builder] {block.text.strip()[:300]}")

    print(f"[builder] project written to {_project_root}")
    return _project_root
