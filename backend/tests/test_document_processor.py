from pathlib import Path

from app.schemas.document import DocumentStatus, DocumentSummary, UploadedDocument
from app.services.document_processor import DocumentProcessor
from app.services.text_splitter import TextChunk


class FakeVectorStore:
    def __init__(self) -> None:
        self.added_chunks: list[TextChunk] = []
        self.deleted_document_ids: list[str] = []

    def add_chunks(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> None:
        self.added_chunks.extend(chunks)

    def delete_document(self, document_id: str) -> None:
        self.deleted_document_ids.append(document_id)


class FakeEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


class FakeMetadataStore:
    def __init__(self, current_document: DocumentSummary | None, update_result: bool = True) -> None:
        self.current_document = current_document
        self.update_result = update_result
        self.updated_statuses: list[tuple[str, DocumentStatus, int]] = []

    def list_documents(self, status: DocumentStatus = "indexed") -> list[DocumentSummary]:
        return []

    def list_active_documents(self) -> list[DocumentSummary]:
        return []

    def get_document(self, document_id: str) -> DocumentSummary | None:
        return self.current_document

    def add_document(self, document: UploadedDocument) -> None:
        return None

    def update_document_status(
        self,
        document_id: str,
        status: DocumentStatus,
        chunk_count: int,
    ) -> bool:
        self.updated_statuses.append((document_id, status, chunk_count))
        return self.update_result

    def delete_document(self, document_id: str) -> bool:
        return False


def _uploaded_document(saved_path: Path, document_id: str = "doc-processor") -> UploadedDocument:
    return UploadedDocument(
        id=document_id,
        filename="notes.txt",
        type="txt",
        created_at="2026-08-05T00:00:00Z",
        status="uploaded",
        saved_path=str(saved_path),
        text_length=0,
        page_count=0,
        chunk_count=0,
        pages=[],
    )


def _document_summary(document_id: str = "doc-processor") -> DocumentSummary:
    return DocumentSummary(
        id=document_id,
        filename="notes.txt",
        type="txt",
        created_at="2026-08-05T00:00:00Z",
        chunk_count=0,
        status="uploaded",
    )


def test_document_processor_skips_vector_write_when_document_was_deleted(tmp_path: Path) -> None:
    saved_path = tmp_path / "doc-processor.txt"
    saved_path.write_text("RAG background processing should respect deletes.", encoding="utf-8")
    vector_store = FakeVectorStore()
    metadata_store = FakeMetadataStore(current_document=None)
    processor = DocumentProcessor(
        vector_store=vector_store,
        embedding_service=FakeEmbeddingService(),
        metadata_store=metadata_store,
        chunk_size=80,
        chunk_overlap=0,
    )

    processor.process(_uploaded_document(saved_path))

    assert vector_store.added_chunks == []
    assert metadata_store.updated_statuses == []


def test_document_processor_cleans_vectors_when_status_update_fails(tmp_path: Path) -> None:
    saved_path = tmp_path / "doc-processor.txt"
    saved_path.write_text("RAG background processing should clean stale vectors.", encoding="utf-8")
    vector_store = FakeVectorStore()
    metadata_store = FakeMetadataStore(current_document=_document_summary(), update_result=False)
    processor = DocumentProcessor(
        vector_store=vector_store,
        embedding_service=FakeEmbeddingService(),
        metadata_store=metadata_store,
        chunk_size=80,
        chunk_overlap=0,
    )

    processor.process(_uploaded_document(saved_path))

    assert len(vector_store.added_chunks) == 1
    assert vector_store.deleted_document_ids == ["doc-processor"]


def test_document_processor_marks_failed_when_processing_raises(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.txt"
    vector_store = FakeVectorStore()
    metadata_store = FakeMetadataStore(current_document=_document_summary())
    processor = DocumentProcessor(
        vector_store=vector_store,
        embedding_service=FakeEmbeddingService(),
        metadata_store=metadata_store,
        chunk_size=80,
        chunk_overlap=0,
    )

    processor.process(_uploaded_document(missing_path))

    assert vector_store.deleted_document_ids == ["doc-processor"]
    assert metadata_store.updated_statuses == [("doc-processor", "failed", 0)]
