from pathlib import Path
from uuid import uuid4

from app.db.database import create_session_factory, initialize_database
from app.db.document_repository import SQLDocumentRepository
from app.schemas.document import UploadedDocument


def _database_url() -> str:
    workspace = Path(".test-data") / f"sqlite-repo-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{workspace / 'app.db'}"


def _uploaded_document(document_id: str = "doc-1") -> UploadedDocument:
    return UploadedDocument(
        id=document_id,
        filename="notes.txt",
        type="txt",
        created_at="2026-07-31T10:00:00Z",
        saved_path="uploads/doc-1.txt",
        text_length=18,
        page_count=1,
        chunk_count=3,
        pages=[{"page": 1, "text": "RAG stores metadata."}],
    )


def test_sql_document_repository_persists_document_metadata_across_instances() -> None:
    database_url = _database_url()
    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)
    repository = SQLDocumentRepository(session_factory)

    repository.add_document(_uploaded_document())

    second_repository = SQLDocumentRepository(create_session_factory(database_url))
    documents = second_repository.list_documents()

    assert len(documents) == 1
    assert documents[0].id == "doc-1"
    assert documents[0].filename == "notes.txt"
    assert documents[0].type == "txt"
    assert documents[0].created_at == "2026-07-31T10:00:00Z"
    assert documents[0].chunk_count == 3


def test_initialize_database_creates_sqlite_parent_directory() -> None:
    workspace = Path(".test-data") / f"sqlite-missing-parent-{uuid4().hex}"
    database_path = workspace / "nested" / "app.db"
    database_url = f"sqlite:///{database_path}"

    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)

    assert database_path.exists()


def test_sql_document_repository_replaces_existing_document_by_id() -> None:
    session_factory = create_session_factory(_database_url())
    initialize_database(session_factory)
    repository = SQLDocumentRepository(session_factory)

    repository.add_document(_uploaded_document(document_id="doc-1"))
    updated = _uploaded_document(document_id="doc-1")
    updated.chunk_count = 5
    repository.add_document(updated)

    documents = repository.list_documents()

    assert len(documents) == 1
    assert documents[0].chunk_count == 5


def test_sql_document_repository_gets_and_deletes_document() -> None:
    session_factory = create_session_factory(_database_url())
    initialize_database(session_factory)
    repository = SQLDocumentRepository(session_factory)
    repository.add_document(_uploaded_document(document_id="doc-1"))

    found = repository.get_document("doc-1")
    deleted = repository.delete_document("doc-1")
    missing = repository.get_document("doc-1")

    assert found is not None
    assert found.filename == "notes.txt"
    assert deleted is True
    assert missing is None
    assert repository.delete_document("doc-1") is False
