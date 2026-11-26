import pytest

from core.smolagents_adapter import SmolOllamaAdapter
from tests.conftest import FakeLLM


def test_messages_are_flattened_with_roles():
    adapter = SmolOllamaAdapter(FakeLLM())
    prompt = adapter._format_messages(
        [{"role": "system", "content": "Be brief."}, {"role": "user", "content": "Hi"}, {"text": "raw"}, "plain"]
    )
    assert prompt == "system: Be brief.\nuser: Hi\nraw\nplain"


def test_generate_wraps_the_reply_for_smolagents():
    llm = FakeLLM("final_answer('42')")
    response = SmolOllamaAdapter(llm).generate([{"role": "user", "content": "6*7?"}], temperature=0.3)
    assert response.content == "final_answer('42')"
    assert response.token_usage.input_tokens == 3 and response.token_usage.output_tokens == 2
    assert response.usage["total_tokens"] == 5
    assert llm.prompts == ["user: 6*7?"]


def test_generation_errors_raise():
    adapter = SmolOllamaAdapter(FakeLLM({"error": "Request timed out"}))
    with pytest.raises(RuntimeError, match="Request timed out"):
        adapter([{"role": "user", "content": "x"}])
