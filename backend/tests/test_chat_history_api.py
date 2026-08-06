from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import create_app
from app.schemas.search import SearchResult


class KeywordEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0 if "rag" in text.lower() else 0.0] for text in texts]


class FakeChatService:
    def answer(self, question: str, sources: list[SearchResult]) -> str:
        return "RAG answer with persisted history."

    def stream_answer(self, question: str, sources: list[SearchResult]):
        yield "RAG stream answer."


def _workspace_dir() -> Path:
    path = Path(".test-data") / f"chat-history-api-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_chat_history_api_lists_reads_and_deletes_sessions() -> None:
    workspace = _workspace_dir()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                database_url=f"sqlite:///{workspace / 'app.db'}",
                embedding_service=KeywordEmbeddingService(),
                chat_service=FakeChatService(),
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

        chat_response = client.post("/api/chat", json={"question": "How does RAG answer?", "top_k": 1})
        assert chat_response.status_code == 200
        session_id = chat_response.json()["session_id"]

        list_response = client.get("/api/chat/sessions")
        detail_response = client.get(f"/api/chat/sessions/{session_id}")
        delete_response = client.delete(f"/api/chat/sessions/{session_id}")
        missing_response = client.get(f"/api/chat/sessions/{session_id}")

        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == session_id
        assert list_response.json()[0]["message_count"] == 2
        assert detail_response.status_code == 200
        assert [message["role"] for message in detail_response.json()["messages"]] == ["user", "assistant"]
        assert delete_response.json() == {"id": session_id, "deleted": True}
        assert missing_response.status_code == 404
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_history_api_returns_404_for_unknown_session() -> None:
    workspace = _workspace_dir()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                database_url=f"sqlite:///{workspace / 'app.db'}",
                embedding_service=KeywordEmbeddingService(),
                chat_service=FakeChatService(),
            )
        )

        response = client.delete("/api/chat/sessions/missing-session")

        assert response.status_code == 404
        assert response.json()["detail"] == "Chat session not found."
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
