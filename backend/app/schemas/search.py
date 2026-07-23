from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class SearchRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    filename: str
    page: int
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchResult]
