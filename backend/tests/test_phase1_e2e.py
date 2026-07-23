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
                    1.0 if "retrieval" in normalized else 0.0,
                    1.0 if "unrelated" in normalized else 0.0,
                ]
            )
        return embeddings


class FakeChatService:
    def answer(self, question: str, sources: list[SearchResult]) -> str:
        return f"Answer for '{question}' using {len(sources)} retrieved source(s)."


def test_phase1_backend_rag_flow() -> None:
    workspace = Path(".test-data") / f"phase1-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                metadata_store_path=workspace / "documents.json",
                embedding_service=KeywordEmbeddingService(),
                chat_service=FakeChatService(),
                chunk_size=200,
                chunk_overlap=0,
            )
        )

        health = client.get("/health")
        assert health.status_code == 200

        upload = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "rag-notes.txt",
                    b"RAG uses retrieval before generation.",
                    "text/plain",
                )
            },
        )
        assert upload.status_code == 201
        uploaded = upload.json()
        assert uploaded["chunk_count"] == 1

        documents = client.get("/api/documents")
        assert documents.status_code == 200
        assert documents.json()[0]["id"] == uploaded["id"]

        search = client.post("/api/search", json={"question": "What does RAG use?", "top_k": 1})
        assert search.status_code == 200
        assert search.json()["results"][0]["filename"] == "rag-notes.txt"

        chat = client.post("/api/chat", json={"question": "What does RAG use?", "top_k": 1})
        assert chat.status_code == 200
        assert chat.json()["answer"] == "Answer for 'What does RAG use?' using 1 retrieved source(s)."
        assert chat.json()["sources"][0]["filename"] == "rag-notes.txt"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
