from pathlib import Path

from fastapi import APIRouter, File, UploadFile, status

from app.schemas.document import UploadedDocument
from app.services.document_loader import save_and_parse_document


def create_documents_router(upload_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/documents", tags=["documents"])

    @router.post("/upload", response_model=UploadedDocument, status_code=status.HTTP_201_CREATED)
    async def upload_document(file: UploadFile = File(...)) -> UploadedDocument:
        return await save_and_parse_document(file, upload_dir)

    return router
