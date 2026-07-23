from pathlib import Path

from fastapi import FastAPI

from app.api.documents import create_documents_router


DEFAULT_UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"


def create_app(upload_dir: Path | None = None) -> FastAPI:
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

    app.include_router(create_documents_router(upload_dir or DEFAULT_UPLOAD_DIR))

    return app


app = create_app()
