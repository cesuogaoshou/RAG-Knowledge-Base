from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app
from app.schemas.search import SearchResult


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class FakeVectorStore:
    def __init__(self) -> None:
        self.last_top_k: int | None = None

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        self.last_top_k = top_k
        return [
            SearchResult(
                filename="notes.txt",
                page=1,
                chunk_index=0,
                content="RAG configuration is centralized.",
                score=0.2,
            )
        ]


class FakeChatService:
    def __init__(self) -> None:
        self.call_count = 0

    def answer(self, question: str, sources: list[SearchResult]) -> str:
        self.call_count += 1
        return "configured answer"


def test_app_settings_reads_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("RAG_CHUNK_SIZE", "512")
    monkeypatch.setenv("RAG_CHUNK_OVERLAP", "64")
    monkeypatch.setenv("RAG_CORS_ORIGINS", "http://127.0.0.1:5173,http://localhost:4173")
    monkeypatch.setenv("RAG_MIN_RELEVANCE_SCORE", "0.75")
    monkeypatch.setenv("RAG_UPLOAD_DIR", "custom/uploads")

    settings = AppSettings()

    assert settings.deepseek_model == "deepseek-v4-pro"
    assert settings.chunk_size == 512
    assert settings.chunk_overlap == 64
    assert settings.cors_origins == ["http://127.0.0.1:5173", "http://localhost:4173"]
    assert settings.min_relevance_score == 0.75
    assert settings.upload_dir == Path("custom/uploads")


def test_create_app_uses_centralized_settings() -> None:
    chat_service = FakeChatService()
    vector_store = FakeVectorStore()
    settings = AppSettings(
        cors_origins=["http://example.local"],
        min_relevance_score=0.1,
        chunk_size=400,
        chunk_overlap=0,
        default_top_k=7,
    )
    client = TestClient(
        create_app(
            settings=settings,
            vector_store=vector_store,
            embedding_service=FakeEmbeddingService(),
            chat_service=chat_service,
        )
    )

    cors_response = client.options(
        "/health",
        headers={
            "Origin": "http://example.local",
            "Access-Control-Request-Method": "GET",
        },
    )
    chat_response = client.post("/api/chat", json={"question": "How is config managed?"})

    assert cors_response.status_code == 200
    assert cors_response.headers["access-control-allow-origin"] == "http://example.local"
    assert chat_response.status_code == 200
    assert chat_response.json()["answer"] == "configured answer"
    assert vector_store.last_top_k == 7
    assert chat_service.call_count == 1
