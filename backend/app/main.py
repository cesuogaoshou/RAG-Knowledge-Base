from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import create_chat_router
from app.api.chat_history import create_chat_history_router
from app.api.documents import create_documents_router
from app.api.evaluation import create_evaluation_router
from app.api.search import create_search_router
from app.core.config import AppSettings
from app.db.database import create_session_factory, initialize_database
from app.db.chat_repository import SQLChatRepository
from app.db.document_repository import SQLDocumentRepository
from app.db.evaluation_repository import SQLEvaluationRepository
from app.services.chat_service import ChatService, DeepSeekChatService
from app.services.document_metadata_store import DocumentMetadataStore
from app.services.embedding_service import EmbeddingService, SentenceTransformerEmbeddingService
from app.services.vector_store import ChromaVectorStore


def create_app(
    settings: AppSettings | None = None,
    upload_dir: Path | None = None,
    vector_store_dir: Path | None = None,
    database_url: str | None = None,
    metadata_store: DocumentMetadataStore | None = None,
    vector_store: ChromaVectorStore | None = None,
    embedding_service: EmbeddingService | None = None,
    chat_service: ChatService | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> FastAPI:
    resolved_settings = settings or AppSettings()
    app = FastAPI(
        title=resolved_settings.app_title,
        version=resolved_settings.app_version,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins,
        allow_methods=resolved_settings.cors_methods,
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "rag-knowledge-base-api",
        }

    resolved_vector_store = vector_store or ChromaVectorStore(vector_store_dir or resolved_settings.vector_store_dir)
    session_factory = create_session_factory(database_url or resolved_settings.database_url)
    initialize_database(session_factory)
    resolved_metadata_store = metadata_store or SQLDocumentRepository(session_factory)
    chat_repository = SQLChatRepository(session_factory)
    evaluation_repository = SQLEvaluationRepository(session_factory)
    resolved_embedding_service = embedding_service or SentenceTransformerEmbeddingService()
    app.include_router(
        create_documents_router(
            upload_dir=upload_dir or resolved_settings.upload_dir,
            vector_store=resolved_vector_store,
            embedding_service=resolved_embedding_service,
            metadata_store=resolved_metadata_store,
            chunk_size=chunk_size if chunk_size is not None else resolved_settings.chunk_size,
            chunk_overlap=chunk_overlap if chunk_overlap is not None else resolved_settings.chunk_overlap,
        )
    )
    app.include_router(
        create_search_router(
            vector_store=resolved_vector_store,
            embedding_service=resolved_embedding_service,
            default_top_k=resolved_settings.default_top_k,
        )
    )
    app.include_router(
        create_chat_router(
            vector_store=resolved_vector_store,
            embedding_service=resolved_embedding_service,
            chat_service=chat_service or DeepSeekChatService(settings=resolved_settings),
            default_top_k=resolved_settings.default_top_k,
            min_relevance_score=resolved_settings.min_relevance_score,
            chat_repository=chat_repository,
        )
    )
    app.include_router(create_chat_history_router(chat_repository))
    app.include_router(create_evaluation_router(evaluation_repository))

    return app


app = create_app()
