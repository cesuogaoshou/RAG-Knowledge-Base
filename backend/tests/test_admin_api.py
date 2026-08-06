from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.database import create_session_factory, initialize_database
from app.db.evaluation_repository import SQLEvaluationRepository
from app.main import create_app
from app.schemas.search import SearchResult


class KeywordEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0 if "rag" in text.lower() else 0.0] for text in texts]


class FakeChatService:
    def answer(self, question: str, sources: list[SearchResult]) -> str:
        return "RAG answer for export."

    def stream_answer(self, question: str, sources: list[SearchResult]):
        yield "RAG answer for export."


def _workspace_dir() -> Path:
    path = Path(".test-data") / f"admin-api-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_admin_export_returns_local_demo_data() -> None:
    workspace = _workspace_dir()
    database_url = f"sqlite:///{workspace / 'app.db'}"
    try:
        session_factory = create_session_factory(database_url)
        initialize_database(session_factory)
        SQLEvaluationRepository(session_factory).save_run(
            mode="baseline",
            parameters={"top_k": 3},
            report={
                "summary": {
                    "case_count": 1,
                    "source_hit_rate": 1.0,
                    "marker_hit_rate": 1.0,
                    "refusal_accuracy": 1.0,
                },
                "outcomes": [{"id": "rag"}],
            },
        )
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                database_url=database_url,
                embedding_service=KeywordEmbeddingService(),
                chat_service=FakeChatService(),
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"RAG retrieves relevant chunks.", "text/plain")},
        )
        assert upload_response.status_code == 201
        chat_response = client.post("/api/chat", json={"question": "How does RAG answer?", "top_k": 1})
        assert chat_response.status_code == 200

        response = client.get("/api/admin/export")

        assert response.status_code == 200
        body = response.json()
        assert body["documents"][0]["filename"] == "notes.txt"
        assert body["chat_sessions"][0]["messages"][1]["sources"][0]["filename"] == "notes.txt"
        assert body["evaluation_runs"][0]["case_count"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_admin_reset_clears_chat_and_evaluations_but_preserves_documents_by_default() -> None:
    workspace = _workspace_dir()
    database_url = f"sqlite:///{workspace / 'app.db'}"
    try:
        session_factory = create_session_factory(database_url)
        initialize_database(session_factory)
        SQLEvaluationRepository(session_factory).save_run(
            mode="baseline",
            parameters={"top_k": 3},
            report={
                "summary": {
                    "case_count": 1,
                    "source_hit_rate": 1.0,
                    "marker_hit_rate": 1.0,
                    "refusal_accuracy": 1.0,
                },
                "outcomes": [{"id": "rag"}],
            },
        )
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                database_url=database_url,
                embedding_service=KeywordEmbeddingService(),
                chat_service=FakeChatService(),
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"RAG retrieves relevant chunks.", "text/plain")},
        )
        assert upload_response.status_code == 201
        chat_response = client.post("/api/chat", json={"question": "How does RAG answer?", "top_k": 1})
        assert chat_response.status_code == 200

        reset_response = client.post(
            "/api/admin/reset",
            json={"reset_chat_history": True, "reset_evaluations": True},
        )
        export_response = client.get("/api/admin/export")

        assert reset_response.status_code == 200
        assert reset_response.json()["reset_chat_history"] is True
        assert reset_response.json()["reset_evaluations"] is True
        assert reset_response.json()["reset_documents"] is False
        assert export_response.json()["chat_sessions"] == []
        assert export_response.json()["evaluation_runs"] == []
        assert export_response.json()["documents"][0]["filename"] == "notes.txt"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
