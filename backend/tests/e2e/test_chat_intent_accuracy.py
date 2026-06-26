import os
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
from convertreino.application.llm.factory import build_llm_client
from convertreino.infrastructure.config import ChatSettings
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from tests.e2e.accuracy import (
    AccuracyCollector,
    CaseOutcome,
    active_llm_provider_filter,
    has_real_api_key,
    provider_api_key,
)
from tests.e2e.intent_matrix import IntentCase, load_intent_matrix, load_intent_matrix_seed


def _jwt_service() -> JwtTokenService:
    return JwtTokenService(JwtSettings(secret="test-jwt-secret", expires_minutes=60))


def _auth_headers(user_id: UUID) -> dict[str, str]:
    token = _jwt_service().create_access_token(user_id)
    return {"Authorization": f"Bearer {token}"}


def _chat_settings(provider: str) -> ChatSettings:
    return ChatSettings(
        llm_provider=provider,
        openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
        openai_model=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        groq_api_key=os.environ.get("GROQ_API_KEY", ""),
        groq_model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        max_tool_iterations=int(os.environ.get("CHAT_MAX_TOOL_ITERATIONS", "5")),
    )


def _build_orchestrator(provider: str) -> ChatOrchestrator:
    seed = load_intent_matrix_seed()
    repo = InMemoryActivityRepository(list(seed.activities))
    llm_client = build_llm_client(_chat_settings(provider))
    return ChatOrchestrator(llm_client=llm_client, tool_registry=ChatToolRegistry(repo))


def _run_case(case: IntentCase, provider: str) -> CaseOutcome:
    seed = load_intent_matrix_seed()
    set_jwt_service_override(_jwt_service())
    set_chat_orchestrator_override(_build_orchestrator(provider))

    with TestClient(create_app()) as client:
        response = client.post(
            "/chat/messages",
            headers=_auth_headers(seed.user_id),
            json={"messages": [{"role": "user", "content": case.question}]},
        )

    if response.status_code != 200:
        return CaseOutcome(
            case_id=case.id,
            passed=False,
            detail=f"HTTP {response.status_code}: {response.json().get('detail', response.text)}",
        )

    payload = response.json()
    actual_tools = payload.get("tool_calls_made", [])
    expected_tools = list(case.expected_tools)

    if actual_tools != expected_tools:
        return CaseOutcome(
            case_id=case.id,
            passed=False,
            detail=f"expected {expected_tools}, got {actual_tools}",
        )

    if not case.expected_tools and not payload.get("message", {}).get("content"):
        return CaseOutcome(
            case_id=case.id,
            passed=False,
            detail="expected non-empty message.content for greeting",
        )

    return CaseOutcome(case_id=case.id, passed=True)


def _run_case_with_retry(case: IntentCase, provider: str) -> CaseOutcome:
    outcome = _run_case(case, provider)
    if outcome.passed:
        return outcome
    return _run_case(case, provider)


@pytest.fixture(autouse=True)
def reset_overrides() -> Generator[None, None, None]:
    set_jwt_service_override(None)
    set_chat_orchestrator_override(None)
    yield
    set_jwt_service_override(None)
    set_chat_orchestrator_override(None)


def _require_provider(provider: str) -> None:
    active = active_llm_provider_filter()
    if active is not None and provider != active:
        pytest.skip(f"LLM_PROVIDER={active}; skipping provider {provider!r}")

    if not has_real_api_key(provider):
        env_name = "OPENAI_API_KEY" if provider == "openai" else "GROQ_API_KEY"
        key = provider_api_key(provider)
        if not key:
            pytest.skip(f"{env_name} is required for E2E tests with provider {provider!r}")
        pytest.skip(
            f"{env_name} must be a real API key (not the pytest default) for provider {provider!r}",
        )


@pytest.mark.e2e
@pytest.mark.parametrize("provider", ["openai"])
@pytest.mark.parametrize("case", load_intent_matrix(), ids=lambda c: c.id)
def test_intent_routing_accuracy(
    case: IntentCase,
    provider: str,
    collector: AccuracyCollector,
) -> None:
    _require_provider(provider)
    outcome = _run_case_with_retry(case, provider)
    collector.record(provider, outcome)
