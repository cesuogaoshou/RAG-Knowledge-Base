from dataclasses import dataclass

from app.schemas.document import DocumentPage


@dataclass(frozen=True)
class TextChunk:
    document_id: str
    filename: str
    page: int
    chunk_index: int
    text: str


def split_pages_into_chunks(
    document_id: str,
    filename: str,
    pages: list[DocumentPage],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater than or equal to 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        start = 0
        step = chunk_size - chunk_overlap
        while start < len(text):
            chunk_text = text[start : start + chunk_size]
            chunks.append(
                TextChunk(
                    document_id=document_id,
                    filename=filename,
                    page=page.page,
                    chunk_index=chunk_index,
                    text=chunk_text,
                )
            )
            chunk_index += 1
            start += step

    return chunks
