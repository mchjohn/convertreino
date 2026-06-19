from typing import Protocol

from convertreino.application.llm.types import ChatMessage, LLMCompletion, ToolDefinition


class LLMClient(Protocol):
    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
    ) -> LLMCompletion: ...
