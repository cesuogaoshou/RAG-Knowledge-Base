from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
from typing import Iterable

from app.schemas.search import SearchResult
from app.services.document_loader import parse_document
from app.services.embedding_service import EmbeddingService, SentenceTransformerEmbeddingService
from app.services.text_splitter import split_pages_into_chunks
from app.services.vector_store import ChromaVectorStore


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    question: str
    expected_filename: str | None
    expected_marker: str | None
    expect_refusal: bool


@dataclass(frozen=True)
class EvaluationOutcome:
    id: str
    question: str
    best_score: float | None
    source_hit: bool
    marker_hit: bool
    refusal_expected: bool
    refusal_actual: bool
    refusal_correct: bool


def load_cases(path: Path) -> list[EvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase(**item) for item in raw_cases]


def run_evaluation(
    cases_path: Path,
    documents_dir: Path,
    vector_store_dir: Path,
    embedding_service: EmbeddingService | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    top_k: int = 5,
    min_relevance_score: float = 0.5,
) -> dict[str, object]:
    if vector_store_dir.exists():
        shutil.rmtree(vector_store_dir)

    vector_store = ChromaVectorStore(persist_dir=vector_store_dir)
    embeddings = embedding_service or SentenceTransformerEmbeddingService()

    for document_path in sorted(documents_dir.iterdir()):
        if not document_path.is_file():
            continue
        pages = parse_document(document_path)
        chunks = split_pages_into_chunks(
            document_id=document_path.stem,
            filename=document_path.name,
            pages=pages,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        vector_store.add_chunks(chunks, embeddings.embed_texts([chunk.text for chunk in chunks]))

    cases = load_cases(cases_path)
    outcomes: list[EvaluationOutcome] = []
    for case in cases:
        query_embedding = embeddings.embed_texts([case.question])[0]
        results = vector_store.search(query_embedding=query_embedding, top_k=top_k)
        outcomes.append(evaluate_case(case, results, min_relevance_score=min_relevance_score))

    return {
        "summary": summarize_results(outcomes),
        "outcomes": [asdict(outcome) for outcome in outcomes],
    }


def evaluate_case(
    case: EvaluationCase,
    results: list[SearchResult],
    min_relevance_score: float,
) -> EvaluationOutcome:
    best_score = max((result.score for result in results), default=None)
    refusal_actual = best_score is None or best_score < min_relevance_score
    return EvaluationOutcome(
        id=case.id,
        question=case.question,
        best_score=best_score,
        source_hit=_source_hit(case, results),
        marker_hit=_marker_hit(case, results),
        refusal_expected=case.expect_refusal,
        refusal_actual=refusal_actual,
        refusal_correct=refusal_actual == case.expect_refusal,
    )


def summarize_results(outcomes: list[EvaluationOutcome]) -> dict[str, float | int]:
    case_count = len(outcomes)
    if case_count == 0:
        return {
            "case_count": 0,
            "source_hit_rate": 0.0,
            "marker_hit_rate": 0.0,
            "refusal_accuracy": 0.0,
        }
    return {
        "case_count": case_count,
        "source_hit_rate": _rate(outcome.source_hit for outcome in outcomes),
        "marker_hit_rate": _rate(outcome.marker_hit for outcome in outcomes),
        "refusal_accuracy": _rate(outcome.refusal_correct for outcome in outcomes),
    }


def _source_hit(case: EvaluationCase, results: list[SearchResult]) -> bool:
    if case.expected_filename is None:
        return True
    return any(result.filename == case.expected_filename for result in results)


def _marker_hit(case: EvaluationCase, results: list[SearchResult]) -> bool:
    if case.expected_marker is None:
        return True
    marker = case.expected_marker.lower()
    return any(marker in result.content.lower() for result in results)


def _rate(values: Iterable[bool]) -> float:
    items = list(values)
    return sum(1 for item in items if item) / len(items)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run offline RAG retrieval evaluation.")
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "cases.json",
    )
    parser.add_argument(
        "--documents",
        type=Path,
        default=Path(__file__).parent / "fixtures" / "documents",
    )
    parser.add_argument(
        "--vector-store",
        type=Path,
        default=Path(__file__).resolve().parents[2] / ".test-data" / "rag-evaluation-chroma",
    )
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-relevance-score", type=float, default=0.5)
    args = parser.parse_args(argv)

    report = run_evaluation(
        cases_path=args.cases,
        documents_dir=args.documents,
        vector_store_dir=args.vector_store,
        top_k=args.top_k,
        min_relevance_score=args.min_relevance_score,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
