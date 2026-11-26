"""Shared fixtures. Every test runs offline: Ollama, the network and the hosted APIs are replaced with fakes."""

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TELEMETRY_ENABLED", "false")

FIXTURES = ROOT / "core" / "test"


class FakeLLM:
    """Stands in for LLMClient: returns queued replies and records the prompts it was given."""

    telemetry_enabled = False
    api_url = "http://fake-ollama/api/generate"
    default_model = "fake-model"

    def __init__(self, *replies):
        self.replies = list(replies)
        self.prompts = []

    def generate(self, prompt, **kwargs):
        self.prompts.append(prompt)
        reply = self.replies.pop(0) if self.replies else "PASS"
        if isinstance(reply, dict):
            return reply
        return {"content": reply, "model": self.default_model, "prompt_tokens": 3, "completion_tokens": 2,
                "total_tokens": 5, "finish_reason": "stop"}

    def health_check(self):
        return {"status": "healthy", "api_url": self.api_url}


@pytest.fixture
def fake_llm():
    return FakeLLM()


@pytest.fixture
def fixtures_dir():
    return FIXTURES
