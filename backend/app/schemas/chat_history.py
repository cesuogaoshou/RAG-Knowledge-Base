from typing import Literal

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant"]


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class ChatMessageSummary(BaseModel):
    id: str
    session_id: str
    role: ChatRole
    content: str
    created_at: str
    top_k: int | None = None


class ChatSessionDetail(ChatSessionSummary):
    messages: list[ChatMessageSummary]


class ChatMessageCreate(BaseModel):
    session_id: str
    role: ChatRole
    content: str
    top_k: int | None = Field(default=None, ge=1, le=20)
