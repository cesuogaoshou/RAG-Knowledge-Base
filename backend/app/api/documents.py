from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.document import DeletedDocument, DocumentSummary, UploadedDocument
from app.services.embedding_service import EmbeddingService
from app.services.document_loader import save_and_parse_document
from app.services.document_metadata_store import JSONDocumentMetadataStore
from app.services.text_splitter import split_pages_into_chunks
from app.services.vector_store import ChromaVectorStore


def create_documents_router(
    upload_dir: Path,
    vector_store: ChromaVectorStore,
    embedding_service: EmbeddingService,
    metadata_store: JSONDocumentMetadataStore,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> APIRouter:
    router = APIRouter(prefix="/api/documents", tags=["documents"])

    @router.get("", response_model=list[DocumentSummary])
    def list_documents() -> list[DocumentSummary]:
        return metadata_store.list_documents()

    @router.post("/upload", response_model=UploadedDocument, status_code=status.HTTP_201_CREATED)
    async def upload_document(file: UploadFile = File(...)) -> UploadedDocument:
        document = await save_and_parse_document(file, upload_dir)
        chunks = split_pages_into_chunks(
            document_id=document.id,
            filename=document.filename,
            pages=document.pages,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        embeddings = embedding_service.embed_texts([chunk.text for chunk in chunks])
        vector_store.add_chunks(chunks, embeddings)
        document.chunk_count = len(chunks)
        metadata_store.add_document(document)
        return document

    @router.delete("/{document_id}", response_model=DeletedDocument)
    def delete_document(document_id: str) -> DeletedDocument:
        document = metadata_store.get_document(document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found.")

        metadata_store.delete_document(document_id)
        _delete_uploaded_file(upload_dir=upload_dir, document_id=document_id)
        vector_store.delete_document(document_id)
        return DeletedDocument(id=document_id, deleted=True)

    return router


def _delete_uploaded_file(upload_dir: Path, document_id: str) -> None:
    resolved_upload_dir = upload_dir.resolve()
    if not resolved_upload_dir.exists():
        return

    for candidate in resolved_upload_dir.glob(f"{document_id}.*"):
        resolved_candidate = candidate.resolve()
        if resolved_candidate.parent == resolved_upload_dir and resolved_candidate.is_file():
            resolved_candidate.unlink()
