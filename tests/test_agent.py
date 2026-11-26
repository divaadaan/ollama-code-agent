import re

import pytest

from core.agents import BasicAgent
from core.tools import get_default_tools
from tests.conftest import FakeLLM


def make_agent(*replies):
    return BasicAgent(FakeLLM(*replies), tools=[])


def test_authorized_imports_are_separate_module_names():
    # Regression: 'uuid, re, chess' used to be one string, so none of the three could be imported.
    imports = make_agent().agent.additional_authorized_imports
    assert all("," not in name and " " not in name for name in imports)
    assert {"uuid", "re", "chess", "pandas"} <= set(imports)


def test_system_prompt_names_only_real_tools(monkeypatch):
    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setenv("OPEN_AI_KEY", "test-key")
    agent = BasicAgent(FakeLLM(), tools=get_default_tools())
    listed = set(re.findall(r"^\s*- (\w+)\(", agent.agent.system_prompt, re.MULTILINE))
    assert listed, "the system prompt should list the tools"
    assert listed <= set(agent.agent.tools), f"unknown tools in the prompt: {listed - set(agent.agent.tools)}"


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("FINAL ANSWER: Paris", "Paris"),
        ("  42 ", "42"),
        ("[a, b, c]", "a, b, c"),
        ("FINAL ANSWER: [3]", "3"),
    ],
)
def test_extract_final_answer(raw, expected):
    assert make_agent()._extract_final_answer(raw) == expected


@pytest.mark.parametrize(
    "reply, valid",
    [
        ("PASS - the code computes the sum.", True),
        ("FAIL - the API call errored.", False),
        ("PASS overall, but step 2 would FAIL", False),
        ({"error": "Request timed out"}, False),
    ],
)
def test_reasoning_check(reply, valid):
    assert make_agent(reply)._check_reasoning("q", "steps", "answer") is valid


def test_retries_until_the_review_passes(monkeypatch):
    agent = make_agent("FAIL - wrong", "PASS - right")
    answers = iter(["FINAL ANSWER: 41", "FINAL ANSWER: 42"])
    monkeypatch.setattr(agent.agent, "run", lambda question: next(answers))
    assert agent("What is 6*7?") == "42"


def test_returns_the_last_raw_answer_when_every_review_fails(monkeypatch):
    agent = make_agent("FAIL", "FAIL", "FAIL")
    monkeypatch.setattr(agent.agent, "run", lambda question: "FINAL ANSWER: maybe")
    assert agent("q") == "FINAL ANSWER: maybe"


def test_raises_after_three_crashes(monkeypatch):
    agent = make_agent()
    calls = []

    def crash(question):
        calls.append(question)
        raise ValueError("tool exploded")

    monkeypatch.setattr(agent.agent, "run", crash)
    with pytest.raises(ValueError, match="tool exploded"):
        agent("q")
    assert len(calls) == 3
