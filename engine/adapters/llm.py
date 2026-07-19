"""LLM adapters.

Two backends, one interface:

- CloudLLM  -> Claude API. Used for anything quality-sensitive: writing code,
               build specs, final opportunity analysis.
- LocalLLM  -> Ollama running on the Nitro's GPU. Used for cheap bulk work
               (clustering reviews, summarizing signals) to keep API spend in
               lean-mode range.

``bulk()`` prefers the local model and silently falls back to the cloud when
the Nitro is offline, so the pipeline never depends on the Nitro being up.
"""

from __future__ import annotations

import json

import anthropic
import requests

from engine.config import settings


class CloudLLM:
    def __init__(self, model: str = settings.CLOUD_MODEL):
        self.model = model
        self.client = anthropic.Anthropic()

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 16000) -> str:
        kwargs: dict = {}
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        return next(b.text for b in response.content if b.type == "text")

    def complete_json(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        kwargs: dict = {}
        if system:
            kwargs["system"] = system
        response = self.client.messages.create(
            model=self.model,
            max_tokens=16000,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
            **kwargs,
        )
        text = next(b.text for b in response.content if b.type == "text")
        return json.loads(text)


class LocalLLM:
    """Ollama on the Nitro (OpenAI-ish local API, plain HTTP)."""

    def __init__(self, model: str = settings.LOCAL_MODEL, base_url: str = settings.OLLAMA_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def is_online(self) -> bool:
        try:
            requests.get(f"{self.base_url}/api/tags", timeout=2)
            return True
        except requests.RequestException:
            return False

    def complete(self, prompt: str, system: str | None = None, max_tokens: int = 2048) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        if system:
            payload["system"] = system
        r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=300)
        r.raise_for_status()
        return r.json()["response"]


_cloud = None
_local = None


def cloud() -> CloudLLM:
    global _cloud
    if _cloud is None:
        _cloud = CloudLLM()
    return _cloud


def local() -> LocalLLM:
    global _local
    if _local is None:
        _local = LocalLLM()
    return _local


def bulk(prompt: str, system: str | None = None) -> str:
    """Cheap bulk completion: Nitro's GPU if it's on, cloud otherwise."""
    if local().is_online():
        return local().complete(prompt, system=system)
    return cloud().complete(prompt, system=system, max_tokens=2048)
