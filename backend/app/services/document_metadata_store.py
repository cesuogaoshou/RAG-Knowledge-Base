from typing import Protocol

from app.schemas.document import DocumentStatus, DocumentSummary, UploadedDocument


class DocumentMetadataStore(Protocol):
    def list_documents(self, status: DocumentStatus = "indexed") -> list[DocumentSummary]:
        """Return stored document summaries with the selected status."""

    def list_active_documents(self) -> list[DocumentSummary]:
        """Return all non-deleted document summaries."""

    def get_document(self, document_id: str) -> DocumentSummary | None:
        """Return one non-deleted document summary by id."""

    def add_document(self, document: UploadedDocument) -> None:
        """Persist metadata for an uploaded document."""

    def update_document_status(
        self,
        document_id: str,
        status: DocumentStatus,
        chunk_count: int,
    ) -> bool:
        """Update processing status and indexed chunk count."""

    def delete_document(self, document_id: str) -> bool:
        """Mark one document metadata record as deleted."""
