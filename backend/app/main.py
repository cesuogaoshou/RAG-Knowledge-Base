from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import create_chat_router
from app.api.documents import create_documents_router
from app.api.search import create_search_router
from app.services.chat_service import ChatService, DeepSeekChatService
from app.services.document_metadata_store import JSONDocumentMetadataStore
from app.services.embedding_service import EmbeddingService, SentenceTransformerEmbeddingService
from app.services.vector_store import ChromaVectorStore


DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
DEFAULT_VECTOR_STORE_DIR = Path(__file__).resolve().parents[1] / "data" / "chroma_db"
DEFAULT_METADATA_STORE_PATH = Path(__file__).resolve().parents[1] / "data" / "documents.json"


def create_app(
    upload_dir: Path | None = None,
    vector_store_dir: Path | None = None,
    metadata_store_path: Path | None = None,
    embedding_service: EmbeddingService | None = None,
    chat_service: ChatService | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> FastAPI:
    app = FastAPI(
        title="RAG Knowledge Base API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "rag-knowledge-base-api",
        }

    vector_store = ChromaVectorStore(vector_store_dir or DEFAULT_VECTOR_STORE_DIR)
    metadata_store = JSONDocumentMetadataStore(metadata_store_path or DEFAULT_METADATA_STORE_PATH)
    resolved_embedding_service = embedding_service or SentenceTransformerEmbeddingService()
    app.include_router(
        create_documents_router(
            upload_dir=upload_dir or DEFAULT_UPLOAD_DIR,
            vector_store=vector_store,
            embedding_service=resolved_embedding_service,
            metadata_store=metadata_store,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    )
    app.include_router(
        create_search_router(
            vector_store=vector_store,
            embedding_service=resolved_embedding_service,
        )
    )
    app.include_router(
        create_chat_router(
            vector_store=vector_store,
            embedding_service=resolved_embedding_service,
            chat_service=chat_service or DeepSeekChatService(),
        )
    )

    return app


app = create_app()
