import json
from pathlib import Path

from app.schemas.document import DocumentSummary, UploadedDocument


class JSONDocumentMetadataStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_documents(self) -> list[DocumentSummary]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [DocumentSummary.model_validate(item) for item in data]

    def get_document(self, document_id: str) -> DocumentSummary | None:
        for document in self.list_documents():
            if document.id == document_id:
                return document
        return None

    def add_document(self, document: UploadedDocument) -> None:
        documents = [item for item in self.list_documents() if item.id != document.id]
        documents.append(
            DocumentSummary(
                id=document.id,
                filename=document.filename,
                type=document.type,
                created_at=document.created_at,
                chunk_count=document.chunk_count,
            )
        )
        self.path.write_text(
            json.dumps([item.model_dump() for item in documents], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def delete_document(self, document_id: str) -> bool:
        documents = self.list_documents()
        remaining = [item for item in documents if item.id != document_id]
        if len(remaining) == len(documents):
            return False
        self.path.write_text(
            json.dumps([item.model_dump() for item in remaining], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return True
