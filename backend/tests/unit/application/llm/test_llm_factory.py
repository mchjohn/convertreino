import pytest

from convertreino.application.llm.factory import build_llm_client
from convertreino.application.llm.openai_client import GROQ_BASE_URL, OpenAICompatibleLLMClient
from convertreino.infrastructure.config import ChatSettings


def _settings(**overrides: object) -> ChatSettings:
    defaults = {
        "llm_provider": "openai",
        "openai_api_key": "test-openai-key",
        "openai_model": "gpt-4o-mini",
        "groq_api_key": "test-groq-key",
        "groq_model": "llama-3.3-70b-versatile",
        "max_tool_iterations": 5,
    }
    defaults.update(overrides)
    return ChatSettings(**defaults)  # type: ignore[arg-type]


def test_build_llm_client_openai_uses_default_endpoint():
    # Arrange / Act
    client = build_llm_client(_settings(llm_provider="openai"))

    # Assert — CN
    assert isinstance(client, OpenAICompatibleLLMClient)
    assert client._client.base_url.host == "api.openai.com"  # type: ignore[union-attr]
    assert client._model == "gpt-4o-mini"


def test_build_llm_client_groq_uses_groq_base_url_and_model():
    # Arrange / Act
    client = build_llm_client(_settings(llm_provider="groq"))

    # Assert — CN
    assert isinstance(client, OpenAICompatibleLLMClient)
    assert str(client._client.base_url).rstrip("/") == GROQ_BASE_URL
    assert client._model == "llama-3.3-70b-versatile"


def test_build_llm_client_groq_requires_api_key():
    # Arrange / Act / Assert — CE
    with pytest.raises(ValueError, match="GROQ_API_KEY is required"):
        build_llm_client(_settings(llm_provider="groq", groq_api_key=""))


def test_build_llm_client_rejects_invalid_provider():
    # Arrange / Act / Assert — CE
    with pytest.raises(ValueError, match="Invalid LLM_PROVIDER"):
        build_llm_client(_settings(llm_provider="anthropic"))
