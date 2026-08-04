from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4

import fitz
from fastapi import HTTPException, UploadFile

from app.schemas.document import DocumentPage, UploadedDocument


SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}
TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}


async def save_and_parse_document(file: UploadFile, upload_dir: Path) -> UploadedDocument:
    document = await save_uploaded_file(file, upload_dir)
    parsed_document = parse_saved_document(document)
    parsed_document.status = "indexed"
    return parsed_document


async def save_uploaded_file(file: UploadFile, upload_dir: Path) -> UploadedDocument:
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    upload_dir.mkdir(parents=True, exist_ok=True)
    document_id = f"doc_{uuid4().hex}"
    saved_path = upload_dir / f"{document_id}{extension}"
    saved_path.write_bytes(content)

    return UploadedDocument(
        id=document_id,
        filename=original_filename,
        type=_document_type(extension),
        created_at=datetime.now(timezone.utc).isoformat(),
        status="uploaded",
        saved_path=str(saved_path),
        text_length=0,
        page_count=0,
        chunk_count=0,
        pages=[],
    )


def parse_saved_document(document: UploadedDocument) -> UploadedDocument:
    saved_path = Path(document.saved_path)
    pages = _parse_document(saved_path, saved_path.suffix.lower())
    text_length = sum(len(page.text) for page in pages)
    if text_length == 0:
        raise HTTPException(status_code=400, detail="Uploaded file contains no readable text")

    document.pages = pages
    document.text_length = text_length
    document.page_count = len(pages)
    return document


def parse_document(path: Path) -> list[DocumentPage]:
    return _parse_document(path, path.suffix.lower())


def _parse_document(path: Path, extension: str) -> list[DocumentPage]:
    if extension == ".pdf":
        return _parse_pdf(path)
    if extension in TEXT_EXTENSIONS:
        return [DocumentPage(page=1, text=path.read_text(encoding="utf-8"))]
    raise HTTPException(status_code=400, detail=f"Unsupported file type: {extension}")


def _parse_pdf(path: Path) -> list[DocumentPage]:
    pages: list[DocumentPage] = []
    with fitz.open(path) as document:
        for index, page in enumerate(document, start=1):
            pages.append(DocumentPage(page=index, text=page.get_text().strip()))
    return pages


def _document_type(extension: str) -> str:
    if extension == ".markdown":
        return "md"
    return extension.removeprefix(".")
