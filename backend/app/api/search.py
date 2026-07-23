from fastapi import APIRouter

from app.schemas.search import SearchRequest, SearchResponse
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import ChromaVectorStore


def create_search_router(
    vector_store: ChromaVectorStore,
    embedding_service: EmbeddingService,
) -> APIRouter:
    router = APIRouter(tags=["search"])

    @router.post("/api/search", response_model=SearchResponse)
    def search(request: SearchRequest) -> SearchResponse:
        query_embedding = embedding_service.embed_texts([request.question])[0]
        results = vector_store.search(query_embedding=query_embedding, top_k=request.top_k)
        return SearchResponse(query=request.question, top_k=request.top_k, results=results)

    return router
