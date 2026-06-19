from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from convertreino.api.dependencies import get_chat_orchestrator, get_current_user_id
from convertreino.api.schemas.chat import (
    AssistantMessageResponse,
    ChatRequest,
    ChatResponseSchema,
)
from convertreino.application.chat_orchestrator import ChatOrchestrator
from convertreino.application.llm.types import ChatMessage
from convertreino.domain.exceptions import ChatProcessingError, LLMProviderError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/messages")
def send_chat_message(
    body: ChatRequest,
    current_user_id: UUID = Depends(get_current_user_id),  # noqa: B008
    orchestrator: ChatOrchestrator = Depends(get_chat_orchestrator),  # noqa: B008
) -> ChatResponseSchema:
    messages = [
        ChatMessage(role=message.role, content=message.content) for message in body.messages
    ]
    try:
        response = orchestrator.handle(current_user_id, messages)
    except LLMProviderError as exc:
        raise HTTPException(status_code=502, detail="LLM provider unavailable") from exc
    except ChatProcessingError as exc:
        raise HTTPException(status_code=500, detail="Chat processing failed") from exc

    return ChatResponseSchema(
        message=AssistantMessageResponse(content=response.message.content),
        tool_calls_made=list(response.tool_calls_made),
    )
