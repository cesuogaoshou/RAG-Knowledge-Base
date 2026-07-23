from pathlib import Path

from fastapi import FastAPI

from app.api.documents import create_documents_router
from app.services.embedding_service import EmbeddingService, SentenceTransformerEmbeddingService
from app.services.vector_store import ChromaVectorStore


DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"
DEFAULT_VECTOR_STORE_DIR = Path(__file__).resolve().parents[1] / "data" / "chroma_db"


def create_app(
    upload_dir: Path | None = None,
    vector_store_dir: Path | None = None,
    embedding_service: EmbeddingService | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> FastAPI:
    app = FastAPI(
        title="RAG Knowledge Base API",
        version="0.1.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "rag-knowledge-base-api",
        }

    vector_store = ChromaVectorStore(vector_store_dir or DEFAULT_VECTOR_STORE_DIR)
    app.include_router(
        create_documents_router(
            upload_dir=upload_dir or DEFAULT_UPLOAD_DIR,
            vector_store=vector_store,
            embedding_service=embedding_service or SentenceTransformerEmbeddingService(),
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    )

    return app


app = create_app()
