import chromadb
from pathlib import Path

from app.cli.seed_demo_data import main, seed_demo_data
from app.db.database import create_session_factory, initialize_database
from app.db.document_repository import SQLDocumentRepository
from app.schemas.document import UploadedDocument


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


def test_seed_demo_data_indexes_fixture_documents(tmp_path) -> None:
    documents_dir = tmp_path / "fixtures"
    documents_dir.mkdir()
    (documents_dir / "phase7.md").write_text("Phase 7 keeps ChromaDB for the demo.", encoding="utf-8")
    upload_dir = tmp_path / "uploads"
    vector_store_dir = tmp_path / "chroma"
    database_url = f"sqlite:///{tmp_path / 'app.db'}"

    summary = seed_demo_data(
        documents_dir=documents_dir,
        upload_dir=upload_dir,
        vector_store_dir=vector_store_dir,
        database_url=database_url,
        embedding_service=FakeEmbeddingService(),
        chunk_size=400,
        chunk_overlap=0,
        reset_documents=False,
    )

    assert summary["document_count"] == 1
    assert summary["chunk_count"] == 1
    assert summary["documents"] == [{"filename": "phase7.md", "status": "indexed", "chunk_count": 1}]
    assert (upload_dir / "phase7.md").exists()

    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)
    documents = SQLDocumentRepository(session_factory).list_active_documents()
    assert len(documents) == 1
    assert documents[0].filename == "phase7.md"
    assert documents[0].status == "indexed"

    chroma_client = chromadb.PersistentClient(path=str(vector_store_dir))
    collection = chroma_client.get_collection("document_chunks")
    stored = collection.get()
    assert len(stored["ids"]) == 1
    assert stored["metadatas"][0]["filename"] == "phase7.md"


def test_seed_demo_data_reset_removes_stale_runtime_documents(tmp_path) -> None:
    documents_dir = tmp_path / "fixtures"
    documents_dir.mkdir()
    (documents_dir / "fresh.md").write_text("Fresh demo document.", encoding="utf-8")
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    (upload_dir / "stale.md").write_text("stale", encoding="utf-8")
    vector_store_dir = tmp_path / "chroma"
    database_url = f"sqlite:///{tmp_path / 'app.db'}"

    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)
    SQLDocumentRepository(session_factory).add_document(
        UploadedDocument(
            id="doc_stale",
            filename="stale.md",
            type="md",
            created_at="2026-08-14T00:00:00+00:00",
            status="indexed",
            saved_path=str(upload_dir / "stale.md"),
            text_length=5,
            page_count=1,
            chunk_count=1,
            pages=[],
        )
    )

    summary = seed_demo_data(
        documents_dir=documents_dir,
        upload_dir=upload_dir,
        vector_store_dir=vector_store_dir,
        database_url=database_url,
        embedding_service=FakeEmbeddingService(),
        chunk_size=400,
        chunk_overlap=0,
        reset_documents=True,
    )

    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)
    documents = SQLDocumentRepository(session_factory).list_active_documents()
    assert [document.filename for document in documents] == ["fresh.md"]
    assert not (upload_dir / "stale.md").exists()
    assert summary["reset_documents"] is True


def test_main_prints_seed_summary(monkeypatch, capsys, tmp_path) -> None:
    documents_dir = tmp_path / "fixtures"
    upload_dir = tmp_path / "uploads"
    vector_store_dir = tmp_path / "chroma"
    database_url = f"sqlite:///{tmp_path / 'app.db'}"

    def fake_seed_demo_data(**kwargs):
        assert kwargs["documents_dir"] == documents_dir
        assert kwargs["upload_dir"] == upload_dir
        assert kwargs["vector_store_dir"] == vector_store_dir
        assert kwargs["database_url"] == database_url
        assert kwargs["reset_documents"] is True
        return {"document_count": 0, "chunk_count": 0, "documents": [], "reset_documents": True}

    monkeypatch.setattr("app.cli.seed_demo_data.seed_demo_data", fake_seed_demo_data)

    main(
        [
            "--documents-dir",
            str(documents_dir),
            "--upload-dir",
            str(upload_dir),
            "--vector-store-dir",
            str(vector_store_dir),
            "--database-url",
            database_url,
            "--reset-documents",
        ]
    )

    assert '"document_count": 0' in capsys.readouterr().out


def test_readme_documents_demo_seed_command() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text(encoding="utf-8")

    assert "python.exe -m app.cli.seed_demo_data --reset-documents" in readme
