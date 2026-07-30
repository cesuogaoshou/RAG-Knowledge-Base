from typing import Protocol

from app.schemas.document import DocumentSummary, UploadedDocument


class DocumentMetadataStore(Protocol):
    def list_documents(self) -> list[DocumentSummary]:
        """Return stored document summaries."""

    def get_document(self, document_id: str) -> DocumentSummary | None:
        """Return one document summary by id."""

    def add_document(self, document: UploadedDocument) -> None:
        """Persist metadata for an uploaded document."""

    def delete_document(self, document_id: str) -> bool:
        """Delete one document metadata record by id."""
