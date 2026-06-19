from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from convertreino.api.dependencies import (
    set_chat_orchestrator_override,
    set_jwt_service_override,
)
from convertreino.api.main import create_app
from convertreino.application.chat_orchestrator import ChatOrchestrator
from convertreino.application.chat_tools import ChatToolRegistry
from convertreino.application.jwt_token_service import JwtSettings, JwtTokenService
from convertreino.application.llm.fake_client import FakeLLMClient
from convertreino.application.llm.types import ChatMessage, LLMCompletion, ToolCall
from convertreino.domain.exceptions import ChatProcessingError, LLMProviderError
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from tests.builders import build_activity

USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")


def _jwt_service() -> JwtTokenService:
    return JwtTokenService(JwtSettings(secret="test-jwt-secret", expires_minutes=60))


def _auth_headers(user_id: UUID = USER_ID) -> dict[str, str]:
    token = _jwt_service().create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _build_orchestrator(
    llm: FakeLLMClient,
    *,
    user_id: UUID = USER_ID,
    distance_meters: float = 21097,
) -> ChatOrchestrator:
    activities = [build_activity(user_id=user_id, distance_meters=distance_meters)]
    repo = InMemoryActivityRepository(activities)
    return ChatOrchestrator(llm_client=llm, tool_registry=ChatToolRegistry(repo))


@pytest.fixture(autouse=True)
def reset_overrides() -> Generator[None, None, None]:
    set_jwt_service_override(None)
    set_chat_orchestrator_override(None)
    yield
    set_jwt_service_override(None)
    set_chat_orchestrator_override(None)


def test_cn1_post_chat_messages_triggers_get_longest_run():
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
    set_jwt_service_override(_jwt_service())
    set_chat_orchestrator_override(_build_orchestrator(llm))

    # Act
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat/messages",
            headers=_auth_headers(),
            json={"messages": [{"role": "user", "content": "Qual foi minha corrida mais longa?"}]},
        )

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"]["role"] == "assistant"
    assert payload["message"]["content"]
    assert payload["tool_calls_made"] == ["get_longest_run"]


def test_cn3_greeting_returns_200_without_tools():
    # Arrange — CN-3
    llm = FakeLLMClient(
        [
            LLMCompletion(
                message=ChatMessage(role="assistant", content="Olá! Como posso ajudar?"),
                tool_calls=(),
            ),
        ]
    )
    set_jwt_service_override(_jwt_service())
    set_chat_orchestrator_override(_build_orchestrator(llm))

    # Act
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat/messages",
            headers=_auth_headers(),
            json={"messages": [{"role": "user", "content": "Olá!"}]},
        )

    # Assert
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"]["content"]
    assert payload["tool_calls_made"] == []


def test_ce1_missing_authorization_returns_401():
    # Arrange — CE-1
    set_jwt_service_override(_jwt_service())

    # Act
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat/messages",
            json={"messages": [{"role": "user", "content": "Oi"}]},
        )

    # Assert
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_ce2_invalid_messages_return_422():
    # Arrange — CE-2
    set_jwt_service_override(_jwt_service())

    # Act
    with TestClient(create_app()) as client:
        empty_response = client.post(
            "/chat/messages",
            headers=_auth_headers(),
            json={"messages": []},
        )
        assistant_last_response = client.post(
            "/chat/messages",
            headers=_auth_headers(),
            json={
                "messages": [
                    {"role": "user", "content": "Oi"},
                    {"role": "assistant", "content": "Olá"},
                ]
            },
        )

    # Assert
    assert empty_response.status_code == 422
    assert assistant_last_response.status_code == 422


class _RaisingOrchestrator:
    def handle(self, user_id: UUID, messages: list[ChatMessage]):
        raise LLMProviderError("LLM provider unavailable")


def test_ce3_llm_provider_error_returns_502():
    # Arrange — CE-3
    set_jwt_service_override(_jwt_service())
    set_chat_orchestrator_override(_RaisingOrchestrator())  # type: ignore[arg-type]

    # Act
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat/messages",
            headers=_auth_headers(),
            json={"messages": [{"role": "user", "content": "Oi"}]},
        )

    # Assert
    assert response.status_code == 502
    assert response.json()["detail"] == "LLM provider unavailable"


class _FailingOrchestrator:
    def handle(self, user_id: UUID, messages: list[ChatMessage]):
        raise ChatProcessingError("Exceeded max tool iterations")


def test_ce4_chat_processing_error_returns_500():
    # Arrange — CE-4
    set_jwt_service_override(_jwt_service())
    set_chat_orchestrator_override(_FailingOrchestrator())  # type: ignore[arg-type]

    # Act
    with TestClient(create_app()) as client:
        response = client.post(
            "/chat/messages",
            headers=_auth_headers(),
            json={"messages": [{"role": "user", "content": "Loop"}]},
        )

    # Assert
    assert response.status_code == 500
    assert response.json()["detail"] == "Chat processing failed"
