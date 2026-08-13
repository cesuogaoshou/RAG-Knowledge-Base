import argparse
import json
import shutil
from pathlib import Path
from uuid import uuid4

from sqlalchemy.engine import make_url
from sqlalchemy import delete

from app.core.config import AppSettings
from app.db.database import create_session_factory, initialize_database
from app.db.models import DocumentRecord
from app.db.document_repository import SQLDocumentRepository
from app.schemas.document import UploadedDocument
from app.services.document_processor import DocumentProcessor
from app.services.embedding_service import EmbeddingService, SentenceTransformerEmbeddingService
from app.services.vector_store import ChromaVectorStore


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_DOCUMENTS_DIR = BACKEND_DIR / "evaluation" / "fixtures" / "documents"


def seed_demo_data(
    documents_dir: Path,
    upload_dir: Path,
    vector_store_dir: Path,
    database_url: str,
    embedding_service: EmbeddingService | None = None,
    chunk_size: int = 400,
    chunk_overlap: int = 0,
    reset_documents: bool = False,
) -> dict[str, object]:
    if reset_documents:
        _reset_local_document_storage(upload_dir=upload_dir, vector_store_dir=vector_store_dir, database_url=database_url)

    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)
    metadata_store = SQLDocumentRepository(session_factory)
    vector_store = ChromaVectorStore(vector_store_dir)
    processor = DocumentProcessor(
        vector_store=vector_store,
        embedding_service=embedding_service or SentenceTransformerEmbeddingService(),
        metadata_store=metadata_store,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    seeded_documents: list[dict[str, object]] = []
    for source_path in sorted(documents_dir.iterdir()):
        if not source_path.is_file() or source_path.suffix.lower() not in {".pdf", ".txt", ".md", ".markdown"}:
            continue

        document = _copy_fixture_document(source_path=source_path, upload_dir=upload_dir)
        metadata_store.add_document(document)
        processor.process(document)
        indexed = metadata_store.get_document(document.id)
        seeded_documents.append(
            {
                "filename": document.filename,
                "status": indexed.status if indexed else "deleted",
                "chunk_count": indexed.chunk_count if indexed else 0,
            }
        )

    return {
        "documents_dir": str(documents_dir),
        "upload_dir": str(upload_dir),
        "vector_store_dir": str(vector_store_dir),
        "database_url": database_url,
        "reset_documents": reset_documents,
        "document_count": len(seeded_documents),
        "chunk_count": sum(int(document["chunk_count"]) for document in seeded_documents),
        "documents": seeded_documents,
    }


def main(argv: list[str] | None = None) -> None:
    settings = AppSettings()
    parser = argparse.ArgumentParser(description="Seed local demo documents into SQLite and ChromaDB.")
    parser.add_argument("--documents-dir", type=Path, default=DEFAULT_DOCUMENTS_DIR)
    parser.add_argument("--upload-dir", type=Path, default=settings.upload_dir)
    parser.add_argument("--vector-store-dir", type=Path, default=settings.vector_store_dir)
    parser.add_argument("--database-url", default=settings.database_url)
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    parser.add_argument("--reset-documents", action="store_true")
    args = parser.parse_args(argv)

    summary = seed_demo_data(
        documents_dir=args.documents_dir,
        upload_dir=args.upload_dir,
        vector_store_dir=args.vector_store_dir,
        database_url=args.database_url,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        reset_documents=args.reset_documents,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def _copy_fixture_document(source_path: Path, upload_dir: Path) -> UploadedDocument:
    upload_dir.mkdir(parents=True, exist_ok=True)
    document_id = f"doc_{uuid4().hex}"
    extension = source_path.suffix.lower()
    saved_path = upload_dir / source_path.name
    shutil.copy2(source_path, saved_path)
    return UploadedDocument(
        id=document_id,
        filename=source_path.name,
        type="md" if extension == ".markdown" else extension.removeprefix("."),
        created_at=_utc_now_iso(),
        status="uploaded",
        saved_path=str(saved_path),
        text_length=0,
        page_count=0,
        chunk_count=0,
        pages=[],
    )


def _reset_local_document_storage(upload_dir: Path, vector_store_dir: Path, database_url: str) -> None:
    shutil.rmtree(upload_dir, ignore_errors=True)
    shutil.rmtree(vector_store_dir, ignore_errors=True)
    database_path = _sqlite_database_path(database_url)
    if database_path is not None:
        try:
            database_path.unlink(missing_ok=True)
        except PermissionError:
            session_factory = create_session_factory(database_url)
            initialize_database(session_factory)
            with session_factory() as session:
                session.execute(delete(DocumentRecord))
                session.commit()


def _sqlite_database_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        return None
    return Path(url.database)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
