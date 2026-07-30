from pydantic import BaseModel
from typing import Literal


DocumentStatus = Literal["uploaded", "indexed", "failed", "deleted"]


class DocumentPage(BaseModel):
    page: int
    text: str


class DocumentSummary(BaseModel):
    id: str
    filename: str
    type: str
    created_at: str
    chunk_count: int
    status: DocumentStatus = "indexed"


class DeletedDocument(BaseModel):
    id: str
    deleted: bool


class UploadedDocument(BaseModel):
    id: str
    filename: str
    type: str
    created_at: str
    status: DocumentStatus = "indexed"
    saved_path: str
    text_length: int
    page_count: int
    chunk_count: int = 0
    pages: list[DocumentPage]
