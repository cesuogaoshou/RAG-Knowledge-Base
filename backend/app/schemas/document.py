from pydantic import BaseModel


class DocumentPage(BaseModel):
    page: int
    text: str


class UploadedDocument(BaseModel):
    id: str
    filename: str
    type: str
    saved_path: str
    text_length: int
    page_count: int
    pages: list[DocumentPage]
