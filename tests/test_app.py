"""API tests. The app's startup (Ollama health checks) is skipped: TestClient is used without its lifespan, and the
module-level clients are replaced with fakes."""

import pytest
from fastapi.testclient import TestClient

import app as app_module
from core.test_toolkit import ToolCase, contains
from tests.conftest import FakeLLM


class FakeAgent:
    telemetry_enabled = False

    def __init__(self, answer="42", error=None):
        self.answer = answer
        self.error = error
        self.agent = type("Inner", (), {"tools": {}})()

    def __call__(self, prompt):
        if self.error:
            raise self.error
        return self.answer

    def health_check(self):
        return {"status": "healthy"}

    def get_stats(self):
        return {"tools": 0}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "llm_client", FakeLLM("Hello from the model"))
    monkeypatch.setattr(app_module, "basic_agent", FakeAgent())
    return TestClient(app_module.app)


def test_ask(client):
    body = client.get("/ask", params={"prompt": "hi"}).json()
    assert body["content"] == "Hello from the model"


def test_empty_prompt_is_rejected(client):
    assert client.get("/ask", params={"prompt": "  "}).status_code == 400
    assert client.post("/generate", json={"prompt": ""}).status_code == 400


def test_llm_errors_become_500(client, monkeypatch):
    monkeypatch.setattr(app_module, "llm_client", FakeLLM({"error": "Failed to connect to LLM API"}))
    response = client.post("/generate", json={"prompt": "hi"})
    assert response.status_code == 500 and "Failed to connect" in response.json()["detail"]


def test_code_agent(client, monkeypatch):
    assert client.post("/code-agent", json={"prompt": "6*7?"}).json() == {"response": "42"}
    monkeypatch.setattr(app_module, "basic_agent", FakeAgent(error=RuntimeError("tool exploded")))
    response = client.post("/code-agent", json={"prompt": "6*7?"})
    assert response.status_code == 500 and "tool exploded" in response.json()["detail"]


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"
    simple = client.get("/health/simple").json()
    assert simple["components"]["agent_initialized"] is True


def test_toolkit_test_offline(client, monkeypatch):
    tool = type("T", (), {"name": "good", "forward": lambda self, **k: "42"})()
    agent = FakeAgent()
    agent.agent.tools = {"good": tool}
    monkeypatch.setattr(app_module, "basic_agent", agent)

    from core import test_toolkit

    cases = [
        ToolCase("file", "good", "ok", {}, contains("42")),
        ToolCase("web", "good", "online", {}, contains("42"), needs_network=True),
    ]
    monkeypatch.setattr(test_toolkit, "default_cases", lambda test_dir=None: cases)
    body = client.get("/toolkit-test", params={"network": "false"}).json()
    assert body["status"] == "completed"
    assert body["summary"]["pass"] == 1 and body["summary"]["skipped"] == 1
