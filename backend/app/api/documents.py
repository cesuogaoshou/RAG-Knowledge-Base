from pathlib import Path

from fastapi import APIRouter, File, UploadFile, status

from app.schemas.document import UploadedDocument
from app.services.embedding_service import EmbeddingService
from app.services.document_loader import save_and_parse_document
from app.services.text_splitter import split_pages_into_chunks
from app.services.vector_store import ChromaVectorStore


def create_documents_router(
    upload_dir: Path,
    vector_store: ChromaVectorStore,
    embedding_service: EmbeddingService,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> APIRouter:
    router = APIRouter(prefix="/api/documents", tags=["documents"])

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
        return document

    return router
