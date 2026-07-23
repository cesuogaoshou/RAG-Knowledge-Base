from app.schemas.document import DocumentPage
from app.services.text_splitter import split_pages_into_chunks


def test_split_pages_into_overlapping_chunks_with_metadata() -> None:
    pages = [
        DocumentPage(page=1, text="abcdefghijklmnopqrstuvwxyz"),
        DocumentPage(page=2, text="short"),
    ]

    chunks = split_pages_into_chunks(
        document_id="doc_123",
        filename="notes.txt",
        pages=pages,
        chunk_size=10,
        chunk_overlap=3,
    )

    assert [chunk.text for chunk in chunks] == [
        "abcdefghij",
        "hijklmnopq",
        "opqrstuvwx",
        "vwxyz",
        "short",
    ]
    assert chunks[0].document_id == "doc_123"
    assert chunks[0].filename == "notes.txt"
    assert chunks[0].page == 1
    assert chunks[0].chunk_index == 0
    assert chunks[-1].page == 2
    assert chunks[-1].chunk_index == 4
