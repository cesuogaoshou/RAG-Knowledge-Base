from fastapi import APIRouter

from app.schemas.search import SearchRequest, SearchResponse
from app.services.embedding_service import EmbeddingService
from app.services.query_rewriter import NoopQueryRewriter, QueryRewriter, safe_rewrite_query
from app.services.vector_store import ChromaVectorStore


def create_search_router(
    vector_store: ChromaVectorStore,
    embedding_service: EmbeddingService,
    default_top_k: int = 5,
    query_rewriter: QueryRewriter | None = None,
) -> APIRouter:
    router = APIRouter(tags=["search"])
    resolved_query_rewriter = query_rewriter or NoopQueryRewriter()

    @router.post("/api/search", response_model=SearchResponse)
    def search(request: SearchRequest) -> SearchResponse:
        rewrite_result = safe_rewrite_query(resolved_query_rewriter, request.question)
        query_embedding = embedding_service.embed_texts([rewrite_result.retrieval_query])[0]
        top_k = request.top_k if request.top_k is not None else default_top_k
        results = vector_store.search(query_embedding=query_embedding, top_k=top_k)
        return SearchResponse(
            query=rewrite_result.original_query,
            retrieval_query=rewrite_result.retrieval_query,
            query_rewritten=rewrite_result.query_rewritten,
            top_k=top_k,
            results=results,
        )

    return router
