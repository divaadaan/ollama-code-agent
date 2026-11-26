import json

import pytest
import requests

from core.llm_client import LLMClient


class FakeResponse:
    def __init__(self, chunks, status=200):
        self._lines = [json.dumps(c).encode("utf-8") for c in chunks]
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.exceptions.HTTPError()
            err.response = self
            raise err

    def iter_lines(self):
        return iter(self._lines)


@pytest.fixture
def client():
    return LLMClient("http://fake-ollama/api/generate", default_model="test-model")


def test_generate_joins_streamed_chunks(client, monkeypatch):
    sent = {}

    def fake_post(url, json, stream, timeout):
        sent.update(json)
        return FakeResponse([{"response": "Hello "}, {"response": "there"}, {"done": True}])

    monkeypatch.setattr(requests, "post", fake_post)
    result = client.generate("say hi", max_tokens=5, temperature=0.1)
    assert result["content"] == "Hello there"
    assert result["model"] == "test-model"
    assert result["completion_tokens"] == 2 and result["prompt_tokens"] == 2
    assert sent["options"] == {"num_predict": 5, "temperature": 0.1}


def test_error_chunk_is_returned_as_error(client, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse([{"error": "model not found"}]))
    assert client.generate("x") == {"error": "model not found"}


@pytest.mark.parametrize(
    "exc, message",
    [
        (requests.exceptions.Timeout(), "Request timed out"),
        (requests.exceptions.ConnectionError(), "Failed to connect to LLM API"),
    ],
)
def test_transport_failures_become_error_dicts(client, monkeypatch, exc, message):
    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(requests, "post", boom)
    assert client.generate("x") == {"error": message}


def test_http_error_reports_status(client, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse([], status=503))
    assert client.generate("x") == {"error": "HTTP error: 503"}


def test_health_check(client, monkeypatch):
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse([{"response": "hi"}]))
    assert client.health_check()["status"] == "healthy"
    monkeypatch.setattr(requests, "post", lambda *a, **k: FakeResponse([{"error": "down"}]))
    unhealthy = client.health_check()
    assert unhealthy["status"] == "unhealthy" and unhealthy["error"] == "down"
