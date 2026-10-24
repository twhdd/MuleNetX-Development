"""Local Ollama client (SRS §21.8): the only provider; structured output via `format`; 20 s timeout."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from mulenetx.core import error_codes as ec
from mulenetx.core.errors import AppError


@dataclass(frozen=True)
class Generation:
    content: str
    model: str
    model_digest: str | None
    output_tokens: int | None


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float,
        transport: httpx.BaseTransport | None = None,
        num_ctx: int = 9072,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.transport = transport
        # Ollama's default window (2,048) silently drops the start of a longer prompt, i.e. the system rules.
        self.num_ctx = num_ctx

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=self.transport)

    def digest(self, http: httpx.Client) -> str | None:
        try:
            tags = http.get("/api/tags").json().get("models", [])
        except (httpx.HTTPError, ValueError):
            return None
        for m in tags:
            if m.get("name") == self.model or m.get("model") == self.model:
                digest: str | None = m.get("digest")
                return digest
        return None

    def generate(self, messages: list[dict[str, str]], schema: dict[str, Any], max_tokens: int) -> Generation:
        body = {
            "model": self.model,
            "messages": messages,
            "format": schema,
            "stream": False,
            # num_predict is one past the limit so an over-long answer reaches validation rule 5 instead of
            # being cut off silently and then failing to parse
            "options": {"temperature": 0, "seed": 42, "num_predict": max_tokens + 1, "num_ctx": self.num_ctx},
        }
        try:
            with self._client() as http:
                resp = http.post("/api/chat", json=body)
                if resp.status_code >= 500 or resp.status_code == 404:
                    raise AppError(ec.COPILOT_UNAVAILABLE, details={"ollama_status": resp.status_code})
                resp.raise_for_status()
                data = resp.json()
                digest = self.digest(http)
        except httpx.TimeoutException as exc:
            raise AppError(ec.COPILOT_UNAVAILABLE, "The copilot timed out.", {"reason": "timeout"}) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise AppError(ec.COPILOT_UNAVAILABLE, details={"reason": type(exc).__name__}) from exc
        return Generation(
            content=str(data.get("message", {}).get("content", "")),
            model=str(data.get("model", self.model)),
            model_digest=digest,
            output_tokens=data.get("eval_count"),
        )
