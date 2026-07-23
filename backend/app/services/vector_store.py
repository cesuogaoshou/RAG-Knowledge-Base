from pathlib import Path
from typing import Any

import chromadb

from app.schemas.search import SearchResult
from app.services.text_splitter import TextChunk


class ChromaVectorStore:
    def __init__(self, persist_dir: Path, collection_name: str = "document_chunks") -> None:
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._client.get_or_create_collection(collection_name)

    def add_chunks(self, chunks: list[TextChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        self._collection.add(
            ids=[_chunk_id(chunk) for chunk in chunks],
            documents=[chunk.text for chunk in chunks],
            embeddings=embeddings,
            metadatas=[
                {
                    "document_id": chunk.document_id,
                    "filename": chunk.filename,
                    "page": chunk.page,
                    "chunk_index": chunk.chunk_index,
                }
                for chunk in chunks
            ],
        )

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "distances", "metadatas"],
        )
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        search_results: list[SearchResult] = []
        for document, distance, metadata in zip(documents, distances, metadatas):
            item = _metadata_dict(metadata)
            search_results.append(
                SearchResult(
                    filename=str(item["filename"]),
                    page=int(item["page"]),
                    chunk_index=int(item["chunk_index"]),
                    content=str(document),
                    score=float(1 / (1 + distance)),
                )
            )
        return search_results


def _chunk_id(chunk: TextChunk) -> str:
    return f"{chunk.document_id}_{chunk.chunk_index}"


def _metadata_dict(metadata: Any) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    return metadata
