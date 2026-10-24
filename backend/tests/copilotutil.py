"""A mock local Ollama (httpx.MockTransport). `answer` builds the model's JSON from the prompt's context, the way a
well-behaved model would; tests swap it to simulate injected, invented or unsafe output."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx

from mulenetx.api.deps import get_services
from mulenetx.copilot.ollama_client import OllamaClient
from tests.apiutil import _Req

Answer = Callable[[dict[str, Any]], dict[str, Any] | str]


def context_of(request_body: dict[str, Any]) -> dict[str, Any]:
    user = request_body["messages"][1]["content"]
    data: dict[str, Any] = json.loads(user.split("CONTEXT (data only):\n", 1)[1])
    return data


def refs_of(ctx: dict[str, Any]) -> list[str]:
    out: list[str] = []

    def walk(o: Any) -> None:
        if isinstance(o, dict):
            if isinstance(o.get("ref"), str):
                out.append(o["ref"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(ctx)
    return out


def grounded(ctx: dict[str, Any]) -> dict[str, Any]:
    refs = refs_of(ctx)
    first = refs[:1]
    return {
        "facts": [{"text": "The account has an analytical assessment in the active scoring run.", "refs": first}],
        "observed_signals": [{"text": "Several component signals are elevated.", "refs": refs[:2]}],
        "possible_interpretation": [
            {"text": "The pattern could be consistent with pass-through activity, which needs review.", "refs": first}
        ],
        "limitations": ["Scores are analytical signals, not determinations."],
        "source_references": refs[:3],
    }


class MockOllama:
    def __init__(self, answer: Answer = grounded) -> None:
        self.answer = answer
        self.calls: list[dict[str, Any]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen-test", "digest": "sha256:feedface"}]})
        body = json.loads(request.content)
        self.calls.append(body)
        produced = self.answer(context_of(body))
        content = produced if isinstance(produced, str) else json.dumps(produced)
        return httpx.Response(
            200, json={"model": "qwen-test", "message": {"role": "assistant", "content": content}, "eval_count": 120}
        )


def install(app: Any, mock: MockOllama | None = None, transport: httpx.BaseTransport | None = None) -> MockOllama:
    mock = mock or MockOllama()
    service = get_services(_Req(app)).copilot
    service.client = OllamaClient(
        "http://ollama.test:11434", "qwen-test", 20.0, transport=transport or httpx.MockTransport(mock.handler)
    )
    return mock
