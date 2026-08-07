from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.config import AppSettings
from app.main import create_app
from app.schemas.search import SearchResult


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


class FakeChatService:
    def __init__(self) -> None:
        self.call_count = 0
        self.last_question = ""
        self.last_sources: list[SearchResult] = []

    def answer(self, question: str, sources: list[SearchResult]) -> str:
        self.call_count += 1
        self.last_question = question
        self.last_sources = sources
        return f"RAG answer using {len(sources)} source(s)."

    def stream_answer(self, question: str, sources: list[SearchResult]):
        self.call_count += 1
        self.last_question = question
        self.last_sources = sources
        yield "RAG "
        yield f"stream using {len(sources)} source(s)."


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


def test_chat_returns_deduplicated_sources_by_file_and_page() -> None:
    workspace = _workspace_dir()
    chat_service = FakeChatService()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
                chat_service=chat_service,
                chunk_size=30,
                chunk_overlap=0,
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "memory.md",
                    b"RAG project memory rules. RAG project direction. RAG progress log.",
                    "text/markdown",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post("/api/chat", json={"question": "What does RAG memory cover?", "top_k": 3})

        assert response.status_code == 200
        body = response.json()
        assert len(chat_service.last_sources) == 3
        assert len(body["sources"]) == 1
        assert body["sources"][0]["filename"] == "memory.md"
        assert body["sources"][0]["page"] == 1
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_refuses_low_relevance_without_calling_llm() -> None:
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

        response = client.post("/api/chat", json={"question": "How do I improve this recipe?", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "根据当前知识库资料无法确定。"
        assert body["sources"] == []
        assert chat_service.call_count == 0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_refuses_when_no_sources_without_calling_llm() -> None:
    workspace = _workspace_dir()
    chat_service = FakeChatService()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
                chat_service=chat_service,
            )
        )

        response = client.post("/api/chat", json={"question": "What does the knowledge base say?", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["answer"] == "根据当前知识库资料无法确定。"
        assert body["sources"] == []
        assert chat_service.call_count == 0
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_streams_answer_tokens_and_deduplicated_sources() -> None:
    workspace = _workspace_dir()
    chat_service = FakeChatService()
    try:
        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=KeywordEmbeddingService(),
                chat_service=chat_service,
                chunk_size=30,
                chunk_overlap=0,
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "memory.md",
                    b"RAG project memory rules. RAG project direction. RAG progress log.",
                    "text/markdown",
                )
            },
        )
        assert upload_response.status_code == 201

        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "What does RAG memory cover?", "top_k": 3},
        ) as response:
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")
            body = response.read().decode("utf-8")

        assert 'event: token\ndata: {"delta": "RAG "}' in body
        assert 'event: token\ndata: {"delta": "stream using 3 source(s)."}' in body
        assert '"filename": "memory.md"' in body
        assert body.count('"filename": "memory.md"') == 1
        assert "event: done\ndata: {}" in body
        assert chat_service.last_question == "What does RAG memory cover?"
        assert len(chat_service.last_sources) == 3
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_stream_refuses_low_relevance_without_calling_llm() -> None:
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

        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "How do I improve this recipe?", "top_k": 1},
        ) as response:
            assert response.status_code == 200
            body = response.read().decode("utf-8")

        assert "event: token" in body
        assert "根据当前知识库资料无法确定。" in body
        assert "event: sources\ndata: {\"sources\": []}" in body
        assert chat_service.call_count == 0
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


def test_chat_uses_rewritten_retrieval_query_but_keeps_original_llm_question() -> None:
    workspace = _workspace_dir()
    embedding_service = KeywordEmbeddingService()
    chat_service = FakeChatService()
    try:
        client = TestClient(
            create_app(
                settings=AppSettings(query_rewrite_enabled=True, min_relevance_score=0.0),
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                embedding_service=embedding_service,
                chat_service=chat_service,
                chunk_size=200,
                chunk_overlap=0,
            )
        )
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "phase7.md",
                    b"Phase 7 evidence says keep ChromaDB before Qdrant migration.",
                    "text/markdown",
                )
            },
        )
        assert upload_response.status_code == 201

        response = client.post("/api/chat", json={"question": "向量库先保留哪个？", "top_k": 1})

        assert response.status_code == 200
        body = response.json()
        assert body["query_rewritten"] is True
        assert "ChromaDB" in body["retrieval_query"]
        assert chat_service.last_question == "向量库先保留哪个？"
        assert any("ChromaDB" in text for text in embedding_service.embedded_texts)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def test_chat_stream_emits_retrieval_metadata_event() -> None:
    workspace = _workspace_dir()
    chat_service = FakeChatService()
    try:
        client = TestClient(
            create_app(
                settings=AppSettings(query_rewrite_enabled=True, min_relevance_score=0.0),
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
                    "phase7.md",
                    b"Phase 7 evidence says keep ChromaDB before Qdrant migration.",
                    "text/markdown",
                )
            },
        )
        assert upload_response.status_code == 201

        with client.stream(
            "POST",
            "/api/chat/stream",
            json={"question": "向量库先保留哪个？", "top_k": 1},
        ) as response:
            assert response.status_code == 200
            body = response.read().decode("utf-8")

        assert "event: retrieval" in body
        assert '"query": "向量库先保留哪个？"' in body
        assert '"query_rewritten": true' in body
        assert "ChromaDB" in body
        assert chat_service.last_question == "向量库先保留哪个？"
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
