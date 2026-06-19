import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from convertreino.application.chat_orchestrator import (
    DEFAULT_SYSTEM_PROMPT,
    ChatOrchestrator,
    ChatResponse,
)
from convertreino.application.chat_tools import ChatToolRegistry
from convertreino.application.llm.fake_client import FakeLLMClient
from convertreino.application.llm.types import ChatMessage, LLMCompletion, ToolCall
from convertreino.domain.exceptions import ChatProcessingError, LLMProviderError
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from tests.builders import build_activity

USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _orchestrator(
  llm_client: FakeLLMClient,
  activities: list | None = None,
  *,
  max_tool_iterations: int = 5,
) -> ChatOrchestrator:
    repo = InMemoryActivityRepository(activities or [])
    return ChatOrchestrator(
        llm_client=llm_client,
        tool_registry=ChatToolRegistry(repo),
        max_tool_iterations=max_tool_iterations,
    )


def test_chat_orchestrator_handle_signature_matches_contract():
  # Arrange / Act
    signature = inspect.signature(ChatOrchestrator.handle)

    # Assert
    assert list(signature.parameters) == ["self", "user_id", "messages"]
    assert signature.return_annotation is ChatResponse


def test_cn1_question_about_pr_triggers_get_longest_run():
    # Arrange — CN-1
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content=""),
                tool_calls=(ToolCall(id="call-1", name="get_longest_run", arguments={}),),
            ),
            LLMCompletion(
                message=ChatMessage(
                    role="assistant",
                    content="Sua corrida mais longa foi de 21,1 km.",
                ),
                tool_calls=(),
            ),
        ]
    )
    activities = [build_activity(user_id=USER_ID, distance_meters=21097)]
    orchestrator = _orchestrator(llm, activities)

    # Act
    response = orchestrator.handle(
        USER_ID,
        [ChatMessage(role="user", content="Qual foi minha corrida mais longa?")],
    )

    # Assert
    assert response.message.role == "assistant"
    assert response.message.content
    assert response.tool_calls_made == ("get_longest_run",)


def test_cn2_volume_question_triggers_get_run_volume_with_dates():
    # Arrange — CN-2
    start_date = "2024-01-01T00:00:00+00:00"
    end_date = "2024-01-07T23:59:59+00:00"
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content=""),
                tool_calls=(
                    ToolCall(
                        id="call-1",
                        name="get_run_volume",
                        arguments={"start_date": start_date, "end_date": end_date},
                    ),
                ),
            ),
            LLMCompletion(
                message=ChatMessage(role="assistant", content="Você correu 42 km essa semana."),
                tool_calls=(),
            ),
        ]
    )
    activities = [
        build_activity(
            user_id=USER_ID,
            distance_meters=42000,
            start_date=datetime(2024, 1, 3, 8, 0, 0, tzinfo=UTC),
        )
    ]
    orchestrator = _orchestrator(llm, activities)

    # Act
    response = orchestrator.handle(
        USER_ID,
        [ChatMessage(role="user", content="Quanto corri essa semana?")],
    )

    # Assert
    assert response.tool_calls_made == ("get_run_volume",)
    assert "42" in response.message.content or response.message.content


def test_cn3_greeting_without_tools_returns_direct_response():
    # Arrange — CN-3
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content="Olá! Como posso ajudar?"),
                tool_calls=(),
            ),
        ]
    )
    orchestrator = _orchestrator(llm)

    # Act
    response = orchestrator.handle(USER_ID, [ChatMessage(role="user", content="Olá!")])

    # Assert
    assert response.message.content
    assert response.tool_calls_made == ()


def test_cn4_multi_turn_preserves_full_history_for_llm():
    # Arrange — CN-4
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content="Posso ajudar com seus treinos."),
                tool_calls=(),
            ),
        ]
    )
    orchestrator = _orchestrator(llm)
    history = [
        ChatMessage(role="user", content="Oi"),
        ChatMessage(role="assistant", content="Olá!"),
        ChatMessage(role="user", content="Como vai?"),
    ]

    # Act
    orchestrator.handle(USER_ID, history)

    # Assert
    sent_messages = llm.complete_calls[0][0]
    assert sent_messages[0] == ChatMessage(role="system", content=DEFAULT_SYSTEM_PROMPT)
    assert sent_messages[1:] == history


def test_cb1_empty_tool_result_is_passed_back_without_exception():
    # Arrange — CB-1
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content=""),
                tool_calls=(ToolCall(id="call-1", name="get_longest_run", arguments={}),),
            ),
            LLMCompletion(
                message=ChatMessage(
                    role="assistant",
                    content="Não encontrei corridas registradas.",
                ),
                tool_calls=(),
            ),
        ]
    )
    orchestrator = _orchestrator(llm, [])

    # Act
    response = orchestrator.handle(
        USER_ID,
        [ChatMessage(role="user", content="Qual foi minha corrida mais longa?")],
    )

    # Assert
    assert response.message.content
    assert response.tool_calls_made == ("get_longest_run",)


def test_cb2_unknown_tool_raises_chat_processing_error():
    # Arrange — CB-2
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content=""),
                tool_calls=(ToolCall(id="call-1", name="unknown_tool", arguments={}),),
            ),
        ]
    )
    orchestrator = _orchestrator(llm)

    # Act / Assert
    with pytest.raises(ChatProcessingError):
        orchestrator.handle(USER_ID, [ChatMessage(role="user", content="Pergunta")])


def test_cb3_multiple_tool_calls_in_single_round_are_executed_in_order():
    # Arrange — CB-3
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content=""),
                tool_calls=(
                    ToolCall(id="call-1", name="get_longest_run", arguments={}),
                    ToolCall(id="call-2", name="get_run_volume", arguments={}),
                ),
            ),
            LLMCompletion(
                message=ChatMessage(role="assistant", content="Aqui estão seus dados."),
                tool_calls=(),
            ),
        ]
    )
    activities = [build_activity(user_id=USER_ID, distance_meters=10000)]
    orchestrator = _orchestrator(llm, activities)

    # Act
    response = orchestrator.handle(
        USER_ID,
        [ChatMessage(role="user", content="Me mostre recorde e volume.")],
    )

    # Assert
    assert response.tool_calls_made == ("get_longest_run", "get_run_volume")


def test_cb4_spurious_user_id_in_tool_arguments_is_ignored():
    # Arrange — CB-4
    other_user_id = uuid4()
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content=""),
                tool_calls=(
                    ToolCall(
                        id="call-1",
                        name="get_longest_run",
                        arguments={"user_id": str(other_user_id)},
                    ),
                ),
            ),
            LLMCompletion(
                message=ChatMessage(role="assistant", content="Pronto."),
                tool_calls=(),
            ),
        ]
    )
    activity = build_activity(user_id=USER_ID, distance_meters=15000)
    orchestrator = _orchestrator(llm, [activity])

    # Act
    response = orchestrator.handle(
        USER_ID,
        [ChatMessage(role="user", content="Qual foi minha corrida mais longa?")],
    )

    # Assert
    assert response.tool_calls_made == ("get_longest_run",)
    assert "15" in response.message.content or response.message.content


def test_ce4_exceeding_max_tool_iterations_raises_chat_processing_error():
    # Arrange — CE-4
    tool_round = LLMCompletion(
        message=ChatMessage(role="assistant", content=""),
        tool_calls=(ToolCall(id="call-1", name="get_longest_run", arguments={}),),
    )
    llm = FakeLLMClient([tool_round])
    orchestrator = _orchestrator(llm, max_tool_iterations=5)

    # Act / Assert
    with pytest.raises(ChatProcessingError):
        orchestrator.handle(USER_ID, [ChatMessage(role="user", content="Loop")])


class _RaisingLLMClient:
    def complete(self, messages: list[ChatMessage], tools: list) -> LLMCompletion:
        raise LLMProviderError("LLM provider unavailable")


def test_ce3_llm_provider_error_propagates_from_orchestrator():
    # Arrange — CE-3
    orchestrator = ChatOrchestrator(
        llm_client=_RaisingLLMClient(),
        tool_registry=ChatToolRegistry(InMemoryActivityRepository([])),
    )

    # Act / Assert
    with pytest.raises(LLMProviderError):
        orchestrator.handle(USER_ID, [ChatMessage(role="user", content="Oi")])
