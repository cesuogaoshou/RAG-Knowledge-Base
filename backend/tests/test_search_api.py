from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app


class KeywordEmbeddingService:
    def __init__(self) -> None:
        self.embedded_texts: list[str] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.embedded_texts.extend(texts)
        embeddings: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            embeddings.append(
                [
                    1.0 if "rag" in normalized else 0.0,
                    1.0 if "database" in normalized else 0.0,
                    1.0 if "recipe" in normalized else 0.0,
                    1.0 if "chromadb" in normalized else 0.0,
                ]
            )
        return embeddings


def _workspace_dir() -> Path:
    path = Path(".test-data") / f"search-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_search_returns_top_k_chunks_from_uploaded_documents() -> None:
    workspace = _workspace_dir()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
                chunk_size=200,
                chunk_overlap=0,
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "notes.txt",
                    b"RAG retrieves document chunks.\n\nA recipe explains cooking steps.",
                    "text/plain",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post("/api/search", json={"question": "How does RAG work?", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "How does RAG work?"
        assert body["top_k"] == 1
        assert len(body["results"]) == 1
        result = body["results"][0]
        assert result["filename"] == "notes.txt"
        assert result["page"] == 1
        assert result["chunk_index"] == 0
        assert "RAG retrieves document chunks" in result["content"]
        assert isinstance(result["score"], float)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_search_rejects_blank_question() -> None:
    workspace = _workspace_dir()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
            )
        )

        response = client.post("/api/search", json={"question": "   ", "top_k": 3})

        assert response.status_code == 422
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_search_reports_unmodified_query_when_rewrite_is_disabled() -> None:
    workspace = _workspace_dir()
    embedding_service = KeywordEmbeddingService()
    try:
        client = TestClient(
            create_app(
                settings=AppSettings(query_rewrite_enabled=False),
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=embedding_service,
                chunk_size=200,
                chunk_overlap=0,
            )
        )

        response = client.post("/api/search", json={"question": "向量库先保留哪个？", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "向量库先保留哪个？"
        assert body["retrieval_query"] == "向量库先保留哪个？"
        assert body["query_rewritten"] is False
        assert "向量库先保留哪个？" in embedding_service.embedded_texts
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_search_uses_rewritten_query_when_rewrite_is_enabled() -> None:
    workspace = _workspace_dir()
    embedding_service = KeywordEmbeddingService()
    try:
        client = TestClient(
            create_app(
                settings=AppSettings(query_rewrite_enabled=True),
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=embedding_service,
                chunk_size=200,
                chunk_overlap=0,
            )
        )

        response = client.post("/api/search", json={"question": "向量库先保留哪个？", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "向量库先保留哪个？"
        assert "ChromaDB" in body["retrieval_query"]
        assert body["query_rewritten"] is True
        assert any("ChromaDB" in text for text in embedding_service.embedded_texts)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
