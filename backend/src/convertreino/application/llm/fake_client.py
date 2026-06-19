from collections.abc import Sequence

from convertreino.application.llm.types import ChatMessage, LLMCompletion, ToolDefinition


class FakeLLMClient:
    def __init__(self, completions: Sequence[LLMCompletion]) -> None:
        if not completions:
            raise ValueError("FakeLLMClient requires at least one completion")
        self._completions = list(completions)
        self._index = 0
        self.complete_calls: list[tuple[list[ChatMessage], list[ToolDefinition]]] = []

    def complete(
        self,
        messages: list[ChatMessage],
        tools: list[ToolDefinition],
    ) -> LLMCompletion:
        self.complete_calls.append((list(messages), list(tools)))
        if self._index < len(self._completions):
            completion = self._completions[self._index]
            self._index += 1
            return completion
        return self._completions[-1]
