from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class SearchRequest(BaseModel):
    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    top_k: int | None = Field(default=None, ge=1, le=20)


class SearchResult(BaseModel):
    filename: str
    page: int
    chunk_index: int
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    retrieval_query: str
    query_rewritten: bool
    top_k: int
    results: list[SearchResult]
