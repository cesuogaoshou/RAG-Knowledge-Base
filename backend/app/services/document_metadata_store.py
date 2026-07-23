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
