from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import ChromaVectorStore
from app.schemas.search import SearchResult


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

    return router


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
