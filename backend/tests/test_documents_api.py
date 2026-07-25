from pathlib import Path
import shutil
from uuid import uuid4

import fitz
from fastapi.testclient import TestClient
import chromadb

from app.main import create_app


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


def _client_with_upload_dir(
    upload_dir: Path,
    vector_store_dir: Path | None = None,
    metadata_store_path: Path | None = None,
) -> TestClient:
    return TestClient(
        create_app(
            upload_dir=upload_dir,
            vector_store_dir=vector_store_dir or upload_dir / "chroma_db",
            metadata_store_path=metadata_store_path or upload_dir / "documents.json",
            embedding_service=FakeEmbeddingService(),
            chunk_size=20,
            chunk_overlap=5,
        )
    )


def _workspace_upload_dir() -> Path:
    upload_dir = Path(".test-data") / f"uploads-{uuid4().hex}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _remove_tree(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _make_pdf_bytes(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    data = document.tobytes()
    document.close()
    return data


def test_upload_txt_document_saves_file_and_returns_metadata() -> None:
    upload_dir = _workspace_upload_dir()
    try:
        client = _client_with_upload_dir(upload_dir)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"RAG stores private document context.", "text/plain")},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["filename"] == "notes.txt"
        assert body["type"] == "txt"
        assert body["text_length"] == len("RAG stores private document context.")
        assert body["page_count"] == 1
        assert body["chunk_count"] == 3
        assert body["pages"] == [
            {
                "page": 1,
                "text": "RAG stores private document context.",
            }
        ]
        assert body["saved_path"].endswith(".txt")
        assert (upload_dir / Path(body["saved_path"]).name).read_text(encoding="utf-8") == (
            "RAG stores private document context."
        )
    finally:
        _remove_tree(upload_dir)


def test_upload_txt_document_persists_chunks_to_chroma() -> None:
    upload_dir = _workspace_upload_dir()
    vector_store_dir = upload_dir / "chroma_db"
    try:
        client = _client_with_upload_dir(upload_dir, vector_store_dir=vector_store_dir)

        response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "notes.txt",
                    b"RAG stores private context for grounded answers.",
                    "text/plain",
                )
            },
        )

        assert response.status_code == 201
        body = response.json()
        assert body["chunk_count"] == 4

        chroma_client = chromadb.PersistentClient(path=str(vector_store_dir))
        collection = chroma_client.get_collection("document_chunks")
        stored = collection.get(where={"document_id": body["id"]})

        assert len(stored["ids"]) == 4
        assert stored["metadatas"][0]["filename"] == "notes.txt"
        assert stored["metadatas"][0]["page"] == 1
        assert stored["metadatas"][0]["chunk_index"] == 0
        assert "RAG stores private" in stored["documents"][0]
    finally:
        _remove_tree(upload_dir)


def test_list_documents_returns_uploaded_document_metadata() -> None:
    upload_dir = _workspace_upload_dir()
    try:
        client = _client_with_upload_dir(upload_dir)

        upload_response = client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"RAG stores private document context.", "text/plain")},
        )
        assert upload_response.status_code == 201
        uploaded = upload_response.json()

        list_response = client.get("/api/documents")

        assert list_response.status_code == 200
        documents = list_response.json()
        assert documents == [
            {
                "id": uploaded["id"],
                "filename": "notes.txt",
                "type": "txt",
                "created_at": uploaded["created_at"],
                "chunk_count": uploaded["chunk_count"],
            }
        ]
    finally:
        _remove_tree(upload_dir)


def test_delete_document_removes_metadata_file_and_vectors() -> None:
    upload_dir = _workspace_upload_dir()
    vector_store_dir = upload_dir / "chroma_db"
    try:
        client = _client_with_upload_dir(upload_dir, vector_store_dir=vector_store_dir)
        upload_response = client.post(
            "/api/documents/upload",
            files={
                "file": (
                    "notes.txt",
                    b"RAG stores private context for grounded answers.",
                    "text/plain",
                )
            },
        )
        assert upload_response.status_code == 201
        uploaded = upload_response.json()
        saved_path = Path(uploaded["saved_path"])
        assert saved_path.exists()

        delete_response = client.delete(f"/api/documents/{uploaded['id']}")

        assert delete_response.status_code == 200
        assert delete_response.json() == {"id": uploaded["id"], "deleted": True}
        assert client.get("/api/documents").json() == []
        assert not saved_path.exists()

        chroma_client = chromadb.PersistentClient(path=str(vector_store_dir))
        collection = chroma_client.get_collection("document_chunks")
        stored = collection.get(where={"document_id": uploaded["id"]})
        assert stored["ids"] == []
    finally:
        _remove_tree(upload_dir)


def test_delete_unknown_document_returns_404() -> None:
    upload_dir = _workspace_upload_dir()
    try:
        client = _client_with_upload_dir(upload_dir)

        response = client.delete("/api/documents/missing-doc")

        assert response.status_code == 404
        assert response.json()["detail"] == "Document not found."
    finally:
        _remove_tree(upload_dir)


def test_document_metadata_persists_across_app_restarts() -> None:
    workspace = _workspace_upload_dir()
    metadata_store_path = workspace / "documents.json"
    vector_store_dir = workspace / "chroma_db"
    try:
        first_client = _client_with_upload_dir(
            workspace / "uploads",
            vector_store_dir=vector_store_dir,
            metadata_store_path=metadata_store_path,
        )
        upload_response = first_client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"RAG persists document metadata.", "text/plain")},
        )
        assert upload_response.status_code == 201

        second_client = _client_with_upload_dir(
            workspace / "uploads",
            vector_store_dir=vector_store_dir,
            metadata_store_path=metadata_store_path,
        )
        list_response = second_client.get("/api/documents")

        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) == 1
        assert documents[0]["filename"] == "notes.txt"
        assert documents[0]["chunk_count"] == upload_response.json()["chunk_count"]
    finally:
        _remove_tree(workspace)


def test_upload_markdown_document_is_parsed_as_text() -> None:
    upload_dir = _workspace_upload_dir()
    try:
        client = _client_with_upload_dir(upload_dir)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("guide.md", b"# RAG\n\nUse citations.", "text/markdown")},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["filename"] == "guide.md"
        assert body["type"] == "md"
        assert body["pages"][0]["text"] == "# RAG\n\nUse citations."
    finally:
        _remove_tree(upload_dir)


def test_upload_pdf_document_preserves_page_text() -> None:
    upload_dir = _workspace_upload_dir()
    try:
        client = _client_with_upload_dir(upload_dir)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("paper.pdf", _make_pdf_bytes("PDF page about RAG"), "application/pdf")},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["filename"] == "paper.pdf"
        assert body["type"] == "pdf"
        assert body["page_count"] == 1
        assert "PDF page about RAG" in body["pages"][0]["text"]
    finally:
        _remove_tree(upload_dir)


def test_upload_rejects_unsupported_file_type() -> None:
    upload_dir = _workspace_upload_dir()
    try:
        client = _client_with_upload_dir(upload_dir)

        response = client.post(
            "/api/documents/upload",
            files={"file": ("image.png", b"not a document", "image/png")},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Unsupported file type: .png"
    finally:
        _remove_tree(upload_dir)
