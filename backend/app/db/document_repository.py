from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import DocumentRecord
from app.schemas.document import DocumentStatus, DocumentSummary, UploadedDocument


class SQLDocumentRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def list_documents(self, status: DocumentStatus = "indexed") -> list[DocumentSummary]:
        with self.session_factory() as session:
            records = session.scalars(
                select(DocumentRecord)
                .where(DocumentRecord.status == status)
                .order_by(DocumentRecord.created_at)
            ).all()
            return [_record_to_summary(record) for record in records]

    def get_document(self, document_id: str) -> DocumentSummary | None:
        with self.session_factory() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None or record.status == "deleted":
                return None
            return _record_to_summary(record)

    def add_document(self, document: UploadedDocument) -> None:
        with self.session_factory() as session:
            record = session.get(DocumentRecord, document.id)
            if record is None:
                record = DocumentRecord(id=document.id)
                session.add(record)

            record.filename = document.filename
            record.type = document.type
            record.created_at = document.created_at
            record.chunk_count = document.chunk_count
            record.status = document.status
            session.commit()

    def delete_document(self, document_id: str) -> bool:
        with self.session_factory() as session:
            record = session.get(DocumentRecord, document_id)
            if record is None or record.status == "deleted":
                return False
            record.status = "deleted"
            session.commit()
            return True


def _record_to_summary(record: DocumentRecord) -> DocumentSummary:
    return DocumentSummary(
        id=record.id,
        filename=record.filename,
        type=record.type,
        created_at=record.created_at,
        chunk_count=record.chunk_count,
        status=record.status,
    )
