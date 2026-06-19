import json
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from convertreino.application.llm.types import ChatMessage, LLMCompletion, ToolCall, ToolDefinition
from convertreino.domain.exceptions import LLMProviderError


class OpenAILLMClient:
    def __init__(self, *, api_key: str, model: str = "gpt-4o-mini") -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required")
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
    ) -> LLMCompletion:
        openai_tools = _to_openai_tools(tools)
        request_kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": _to_openai_messages(messages),
        }
        if openai_tools:
            request_kwargs["tools"] = openai_tools
            request_kwargs["tool_choice"] = "auto"
        try:
            response = self._client.chat.completions.create(**request_kwargs)
        except (APIConnectionError, APITimeoutError, APIStatusError) as exc:
            error_message = "LLM provider unavailable"
            if type(exc).__name__ == "RateLimitError" and "insufficient_quota" in str(exc):
                error_message = "LLM quota exceeded"
            raise LLMProviderError(error_message) from exc

        choice = response.choices[0]
        raw_tool_calls = choice.message.tool_calls or []
        tool_calls = tuple(
            ToolCall(
                id=call.id,
                name=call.function.name,
                arguments=_parse_arguments(call.function.arguments),
            )
            for call in raw_tool_calls
        )
        content = choice.message.content or ""
        message = ChatMessage(
            role="assistant",
            content=content,
            tool_calls=tool_calls or None,
        )
        return LLMCompletion(message=message, tool_calls=tool_calls)


def _parse_arguments(raw: str) -> dict[str, object]:
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _to_openai_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "tool":
            result.append(
                {
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.tool_call_id,
                }
            )
            continue
        payload: dict[str, Any] = {"role": message.role, "content": message.content}
        if message.role == "assistant" and message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in message.tool_calls
            ]
        result.append(payload)
    return result


def _to_openai_tools(tools: list[ToolDefinition]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]
