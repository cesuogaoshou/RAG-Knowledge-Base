import json
from collections.abc import Iterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.search import SearchResult
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import ChromaVectorStore


INSUFFICIENT_EVIDENCE_ANSWER = "根据当前知识库资料无法确定。"
DEFAULT_MIN_RELEVANCE_SCORE = 0.5


def create_chat_router(
    vector_store: ChromaVectorStore,
    embedding_service: EmbeddingService,
    chat_service: ChatService,
    default_top_k: int = 5,
    min_relevance_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
) -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        query_embedding = embedding_service.embed_texts([request.question])[0]
        top_k = request.top_k if request.top_k is not None else default_top_k
        sources = vector_store.search(query_embedding=query_embedding, top_k=top_k)
        if _has_insufficient_evidence(sources, min_relevance_score):
            return ChatResponse(answer=INSUFFICIENT_EVIDENCE_ANSWER, sources=[])

        answer = chat_service.answer(question=request.question, sources=sources)
        return ChatResponse(answer=answer, sources=_deduplicate_sources_by_file_page(sources))

    @router.post("/api/chat/stream")
    def chat_stream(request: ChatRequest) -> StreamingResponse:
        query_embedding = embedding_service.embed_texts([request.question])[0]
        top_k = request.top_k if request.top_k is not None else default_top_k
        sources = vector_store.search(query_embedding=query_embedding, top_k=top_k)
        if _has_insufficient_evidence(sources, min_relevance_score):
            return StreamingResponse(
                _stream_refusal_events(),
                media_type="text/event-stream",
            )

        display_sources = _deduplicate_sources_by_file_page(sources)
        return StreamingResponse(
            _stream_chat_events(
                tokens=chat_service.stream_answer(question=request.question, sources=sources),
                sources=display_sources,
            ),
            media_type="text/event-stream",
        )

    return router


def _stream_refusal_events() -> Iterator[str]:
    yield _format_sse("token", {"delta": INSUFFICIENT_EVIDENCE_ANSWER})
    yield _format_sse("sources", {"sources": []})
    yield _format_sse("done", {})


def _stream_chat_events(tokens: Iterator[str], sources: list[SearchResult]) -> Iterator[str]:
    for token in tokens:
        yield _format_sse("token", {"delta": token})
    yield _format_sse("sources", {"sources": [source.model_dump() for source in sources]})
    yield _format_sse("done", {})


def _format_sse(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _has_insufficient_evidence(sources: list[SearchResult], min_relevance_score: float) -> bool:
    if not sources:
        return True
    best_score = max(source.score for source in sources)
    return best_score < min_relevance_score


def _deduplicate_sources_by_file_page(sources: list[SearchResult]) -> list[SearchResult]:
    deduplicated: dict[tuple[str, int], SearchResult] = {}
    for source in sources:
        key = (source.filename, source.page)
        current = deduplicated.get(key)
        if current is None or source.score > current.score:
            deduplicated[key] = source
    return list(deduplicated.values())
