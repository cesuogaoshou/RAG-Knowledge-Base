from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.search import SearchResult


class KeywordEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            embeddings.append(
                [
                    1.0 if "rag" in normalized else 0.0,
                    1.0 if "database" in normalized else 0.0,
                    1.0 if "recipe" in normalized else 0.0,
                ]
            )
        return embeddings


class FakeChatService:
    def __init__(self) -> None:
        self.last_question = ""
        self.last_sources: list[SearchResult] = []

    def answer(self, question: str, sources: list[SearchResult]) -> str:
        self.last_question = question
        self.last_sources = sources
        return f"RAG answer using {len(sources)} source(s)."


def _workspace_dir() -> Path:
    path = Path(".test-data") / f"chat-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_chat_answers_with_retrieved_sources() -> None:
    workspace = _workspace_dir()
    chat_service = FakeChatService()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
                chat_service=chat_service,
                chunk_size=200,
                chunk_overlap=0,
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "notes.txt",
                    b"RAG retrieves relevant chunks before generation.",
                    "text/plain",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post("/api/chat", json={"question": "How does RAG answer?", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "RAG answer using 1 source(s)."
        assert len(body["sources"]) == 1
        assert body["sources"][0]["filename"] == "notes.txt"
        assert "RAG retrieves relevant chunks" in body["sources"][0]["content"]
        assert chat_service.last_question == "How does RAG answer?"
        assert chat_service.last_sources[0].filename == "notes.txt"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_rejects_blank_question() -> None:
    workspace = _workspace_dir()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
                chat_service=FakeChatService(),
            )
        )

        response = client.post("/api/chat", json={"question": " ", "top_k": 1})

        assert response.status_code == 422
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
