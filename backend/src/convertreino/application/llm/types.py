from dataclasses import dataclass
from typing import Any, Literal

ChatRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str
    tool_call_id: str | None = None
    tool_calls: tuple["ToolCall", ...] | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class LLMCompletion:
    message: ChatMessage | None
    tool_calls: tuple[ToolCall, ...]
