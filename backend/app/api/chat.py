from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import ChromaVectorStore


def create_chat_router(
    vector_store: ChromaVectorStore,
    embedding_service: EmbeddingService,
    chat_service: ChatService,
) -> APIRouter:
    router = APIRouter(tags=["chat"])

    @router.post("/api/chat", response_model=ChatResponse)
    def chat(request: ChatRequest) -> ChatResponse:
        query_embedding = embedding_service.embed_texts([request.question])[0]
        sources = vector_store.search(query_embedding=query_embedding, top_k=request.top_k)
        answer = chat_service.answer(question=request.question, sources=sources)
        return ChatResponse(answer=answer, sources=sources)

    return router
