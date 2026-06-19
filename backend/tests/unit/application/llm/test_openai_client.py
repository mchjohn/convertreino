import inspect
import json
from unittest.mock import MagicMock, patch

import pytest
from openai import APIStatusError, RateLimitError

from convertreino.application.llm.client import LLMClient
from convertreino.application.llm.openai_client import GROQ_BASE_URL, OpenAICompatibleLLMClient
from convertreino.application.llm.types import ChatMessage, ToolDefinition
from convertreino.domain.exceptions import LLMProviderError


def test_llm_client_complete_signature_matches_contract():
    # Arrange / Act
    signature = inspect.signature(LLMClient.complete)

    # Assert
    assert list(signature.parameters) == ["self", "messages", "tools"]


def test_openai_compatible_llm_client_requires_api_key():
    # Arrange / Act / Assert — CE-5
    with pytest.raises(ValueError, match="OPENAI_API_KEY is required"):
        OpenAICompatibleLLMClient(api_key="")


def test_openai_compatible_llm_client_requires_groq_api_key():
    # Arrange / Act / Assert
    with pytest.raises(ValueError, match="GROQ_API_KEY is required"):
        OpenAICompatibleLLMClient(api_key="", provider_name="groq")


def test_openai_compatible_llm_client_maps_messages_tools_and_response():
    # Arrange
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Resposta final"
    mock_function = MagicMock()
    mock_function.name = "get_longest_run"
    mock_function.arguments = '{"start_date":"2024-01-01"}'
    mock_response.choices[0].message.tool_calls = [
        MagicMock(id="call-1", function=mock_function),
    ]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("convertreino.application.llm.openai_client.OpenAI", return_value=mock_client):
        client = OpenAICompatibleLLMClient(api_key="test-key", model="gpt-4o-mini")

    messages = [
        ChatMessage(role="system", content="system"),
        ChatMessage(role="user", content="pergunta"),
    ]
    tools = [
        ToolDefinition(
            name="get_longest_run",
            description="desc",
            parameters={"type": "object", "properties": {}},
        )
    ]

    # Act
    completion = client.complete(messages, tools)

    # Assert
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o-mini"
    assert call_kwargs["tool_choice"] == "auto"
    assert call_kwargs["messages"][0]["role"] == "system"
    assert completion.tool_calls[0].name == "get_longest_run"
    assert completion.tool_calls[0].arguments == {"start_date": "2024-01-01"}
    assert completion.message is not None
    assert completion.message.role == "assistant"


def test_openai_compatible_llm_client_uses_custom_base_url():
    # Arrange
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"
    mock_response.choices[0].message.tool_calls = []

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response
    mock_openai_ctor = MagicMock(return_value=mock_client)

    with patch("convertreino.application.llm.openai_client.OpenAI", mock_openai_ctor):
        client = OpenAICompatibleLLMClient(
            api_key="test-key",
            model="llama-3.3-70b-versatile",
            base_url=GROQ_BASE_URL,
            provider_name="groq",
        )

    # Act
    client.complete([ChatMessage(role="user", content="oi")], [])

    # Assert
    mock_openai_ctor.assert_called_once_with(api_key="test-key", base_url=GROQ_BASE_URL)


def test_openai_compatible_llm_client_maps_assistant_message_with_tool_calls_for_follow_up():
    # Arrange
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""
    mock_response.choices[0].message.tool_calls = []

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("convertreino.application.llm.openai_client.OpenAI", return_value=mock_client):
        client = OpenAICompatibleLLMClient(api_key="test-key")

    conversation = [
        ChatMessage(role="assistant", content="", tool_calls=()),
        ChatMessage(role="tool", content=json.dumps({"distance_km": 10}), tool_call_id="call-1"),
    ]

    # Act
    client.complete(conversation, [])

    # Assert
    sent_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert sent_messages[-1]["role"] == "tool"
    assert sent_messages[-1]["tool_call_id"] == "call-1"


def test_openai_compatible_llm_client_raises_llm_provider_error_on_api_failure():
    # Arrange
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APIStatusError(
        "error",
        response=MagicMock(status_code=500),
        body=None,
    )

    with patch("convertreino.application.llm.openai_client.OpenAI", return_value=mock_client):
        client = OpenAICompatibleLLMClient(api_key="test-key")

    # Act / Assert
    with pytest.raises(LLMProviderError, match="LLM provider unavailable"):
        client.complete([ChatMessage(role="user", content="oi")], [])


def test_openai_compatible_llm_client_raises_rate_limit_error():
    # Arrange
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RateLimitError(
        "rate limit",
        response=MagicMock(status_code=429),
        body=None,
    )

    with patch("convertreino.application.llm.openai_client.OpenAI", return_value=mock_client):
        client = OpenAICompatibleLLMClient(api_key="test-key")

    # Act / Assert — CE-3
    with pytest.raises(LLMProviderError, match="LLM rate limit exceeded"):
        client.complete([ChatMessage(role="user", content="oi")], [])


def test_openai_compatible_llm_client_raises_quota_error():
    # Arrange
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RateLimitError(
        "insufficient_quota",
        response=MagicMock(status_code=429),
        body=None,
    )

    with patch("convertreino.application.llm.openai_client.OpenAI", return_value=mock_client):
        client = OpenAICompatibleLLMClient(api_key="test-key")

    # Act / Assert — CE-4
    with pytest.raises(LLMProviderError, match="LLM quota exceeded"):
        client.complete([ChatMessage(role="user", content="oi")], [])
