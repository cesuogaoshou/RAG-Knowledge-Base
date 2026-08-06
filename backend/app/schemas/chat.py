from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.schemas.search import SearchResult


class ChatRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    top_k: int | None = Field(default=None, ge=1, le=20)


class ChatResponse(BaseModel):
    answer: str
    sources: list[SearchResult]
    session_id: str | None = None
