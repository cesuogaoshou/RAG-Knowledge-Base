from pathlib import Path
from sqlalchemy import create_engine, inspect, text
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
    assert documents[0].status == "indexed"


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


def test_sql_document_repository_marks_deleted_document_and_hides_it_from_active_reads() -> None:
    session_factory = create_session_factory(_database_url())
    initialize_database(session_factory)
    repository = SQLDocumentRepository(session_factory)
    repository.add_document(_uploaded_document(document_id="doc-1"))

    found = repository.get_document("doc-1")
    deleted = repository.delete_document("doc-1")
    missing = repository.get_document("doc-1")
    deleted_documents = repository.list_documents(status="deleted")

    assert found is not None
    assert found.filename == "notes.txt"
    assert deleted is True
    assert missing is None
    assert repository.list_documents() == []
    assert len(deleted_documents) == 1
    assert deleted_documents[0].id == "doc-1"
    assert deleted_documents[0].status == "deleted"
    assert repository.delete_document("doc-1") is False


def test_sql_document_repository_lists_uploaded_indexed_and_failed_documents() -> None:
    session_factory = create_session_factory(_database_url())
    initialize_database(session_factory)
    repository = SQLDocumentRepository(session_factory)

    uploaded = _uploaded_document(document_id="uploaded-doc")
    uploaded.status = "uploaded"
    uploaded.chunk_count = 0
    indexed = _uploaded_document(document_id="indexed-doc")
    indexed.status = "indexed"
    failed = _uploaded_document(document_id="failed-doc")
    failed.status = "failed"
    failed.chunk_count = 0
    deleted = _uploaded_document(document_id="deleted-doc")
    deleted.status = "deleted"

    repository.add_document(uploaded)
    repository.add_document(indexed)
    repository.add_document(failed)
    repository.add_document(deleted)

    documents = repository.list_active_documents()

    assert [document.id for document in documents] == [
        "uploaded-doc",
        "indexed-doc",
        "failed-doc",
    ]
    assert [document.status for document in documents] == ["uploaded", "indexed", "failed"]


def test_sql_document_repository_updates_status_and_chunk_count() -> None:
    session_factory = create_session_factory(_database_url())
    initialize_database(session_factory)
    repository = SQLDocumentRepository(session_factory)
    uploaded = _uploaded_document(document_id="doc-1")
    uploaded.status = "uploaded"
    uploaded.chunk_count = 0
    repository.add_document(uploaded)

    updated = repository.update_document_status("doc-1", status="indexed", chunk_count=7)
    missing = repository.update_document_status("missing-doc", status="failed", chunk_count=0)
    document = repository.get_document("doc-1")

    assert updated is True
    assert missing is False
    assert document is not None
    assert document.status == "indexed"
    assert document.chunk_count == 7


def test_initialize_database_adds_status_column_to_existing_documents_table() -> None:
    workspace = Path(".test-data") / f"sqlite-migrate-status-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    database_path = workspace / "app.db"
    database_url = f"sqlite:///{database_path}"
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE documents ("
                "id VARCHAR PRIMARY KEY, "
                "filename VARCHAR NOT NULL, "
                "type VARCHAR NOT NULL, "
                "created_at VARCHAR NOT NULL, "
                "chunk_count INTEGER NOT NULL"
                ")"
            )
        )
        connection.execute(
            text(
                "INSERT INTO documents (id, filename, type, created_at, chunk_count) "
                "VALUES ('legacy-doc', 'legacy.txt', 'txt', '2026-07-31T10:00:00Z', 1)"
            )
        )

    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)

    columns = {column["name"] for column in inspect(session_factory.kw["bind"]).get_columns("documents")}
    repository = SQLDocumentRepository(session_factory)
    documents = repository.list_documents()

    assert "status" in columns
    assert documents[0].id == "legacy-doc"
    assert documents[0].status == "indexed"
