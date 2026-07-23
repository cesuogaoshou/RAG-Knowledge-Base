from pydantic import BaseModel


class DocumentPage(BaseModel):
    page: int
    text: str


class DocumentSummary(BaseModel):
    id: str
    filename: str
    type: str
    created_at: str
    chunk_count: int


class UploadedDocument(BaseModel):
    id: str
    filename: str
    type: str
    created_at: str
    saved_path: str
    text_length: int
    page_count: int
    chunk_count: int = 0
    pages: list[DocumentPage]
