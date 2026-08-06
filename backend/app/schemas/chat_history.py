from typing import Literal

from pydantic import BaseModel, Field


ChatRole = Literal["user", "assistant"]


class ChatSessionSummary(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    message_count: int


class AnswerSourceSummary(BaseModel):
    id: str
    message_id: str
    filename: str
    page: int
    chunk_index: int
    content: str
    score: float


class ChatMessageSummary(BaseModel):
    id: str
    session_id: str
    role: ChatRole
    content: str
    created_at: str
    top_k: int | None = None
    sources: list[AnswerSourceSummary] = Field(default_factory=list)


class ChatSessionDetail(ChatSessionSummary):
    messages: list[ChatMessageSummary]


class ChatMessageCreate(BaseModel):
    session_id: str
    role: ChatRole
    content: str
    top_k: int | None = Field(default=None, ge=1, le=20)
