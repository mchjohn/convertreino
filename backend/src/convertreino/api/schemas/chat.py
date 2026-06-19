from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

ChatRoleRequest = Literal["user", "assistant"]


class ChatMessageRequest(BaseModel):
    role: ChatRoleRequest
    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("content must not be empty")
        return stripped


class ChatRequest(BaseModel):
    messages: list[ChatMessageRequest] = Field(min_length=1)

    @model_validator(mode="after")
    def last_message_is_user(self) -> Self:
        if self.messages[-1].role != "user":
            raise ValueError("last message must have role 'user'")
        return self


class AssistantMessageResponse(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: str


class ChatResponseSchema(BaseModel):
    message: AssistantMessageResponse
    tool_calls_made: list[str]
