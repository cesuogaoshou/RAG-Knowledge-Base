import logging

from app.schemas.document import UploadedDocument
from app.services.document_loader import parse_saved_document
from app.services.document_metadata_store import DocumentMetadataStore
from app.services.embedding_service import EmbeddingService
from app.services.text_splitter import split_pages_into_chunks
from app.services.vector_store import ChromaVectorStore


logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedding_service: EmbeddingService,
        metadata_store: DocumentMetadataStore,
        chunk_size: int,
        chunk_overlap: int,
    ) -> None:
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.metadata_store = metadata_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def process(self, document: UploadedDocument) -> None:
        try:
            parsed_document = parse_saved_document(document)
            chunks = split_pages_into_chunks(
                document_id=parsed_document.id,
                filename=parsed_document.filename,
                pages=parsed_document.pages,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            embeddings = self.embedding_service.embed_texts([chunk.text for chunk in chunks])
            if self.metadata_store.get_document(parsed_document.id) is None:
                return

            self.vector_store.add_chunks(chunks, embeddings)
            updated = self.metadata_store.update_document_status(
                parsed_document.id,
                status="indexed",
                chunk_count=len(chunks),
            )
            if not updated:
                self.vector_store.delete_document(parsed_document.id)
        except Exception:
            self.vector_store.delete_document(document.id)
            self.metadata_store.update_document_status(document.id, status="failed", chunk_count=0)
            logger.exception("Document processing failed for %s", document.id)
