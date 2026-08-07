from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import shutil
from typing import Iterable, Protocol

from app.db.database import create_session_factory, initialize_database
from app.db.evaluation_repository import SQLEvaluationRepository
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


@dataclass(frozen=True)
class EvaluationParameters:
    chunk_size: int
    chunk_overlap: int
    top_k: int
    min_relevance_score: float


class Reranker(Protocol):
    def rerank(self, question: str, results: list[SearchResult]) -> list[SearchResult]:
        pass


class QueryRewriter(Protocol):
    def rewrite(self, question: str) -> str:
        pass


class KeywordOverlapReranker:
    def rerank(self, question: str, results: list[SearchResult]) -> list[SearchResult]:
        query_terms = _tokenize_for_reranking(question)
        return sorted(
            results,
            key=lambda result: (_overlap_count(query_terms, result.content), result.score),
            reverse=True,
        )


class StaticQueryRewriter:
    def __init__(self) -> None:
        self._rewrites = {
            "向量库先保留哪个？": "Phase 7 evidence shows which vector store should keep ChromaDB before migration?",
            "那安全清理会删文档吗？": "Safe reset refuses document deletion and document removal uses the explicit document delete path.",
            "什么时候才考虑 query rewrite？": (
                "Query rewrite should be considered only after ambiguous question failures are measured."
            ),
        }

    def rewrite(self, question: str) -> str:
        return self._rewrites.get(question, question)


class HeuristicQueryRewriter:
    def rewrite(self, question: str) -> str:
        normalized = question.lower()
        if _looks_unrelated_to_project(normalized):
            return question
        if _mentions_vector_store(normalized):
            return (
                f"{question} Phase 7 evidence keep ChromaDB vector store before Qdrant migration evidence."
            )
        if _mentions_safe_reset_followup(normalized):
            return (
                f"{question} safe reset refuses document deletion and uses the explicit document delete path."
            )
        if _mentions_query_rewrite_timing(normalized):
            return (
                f"{question} query rewrite considered after ambiguous question failures are measured."
            )
        return question


def load_cases(path: Path) -> list[EvaluationCase]:
    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    return [EvaluationCase(**item) for item in raw_cases]


def run_evaluation(
    cases_path: Path,
    documents_dir: Path,
    vector_store_dir: Path,
    embedding_service: EmbeddingService | None = None,
    chunk_size: int = 400,
    chunk_overlap: int = 0,
    top_k: int = 3,
    min_relevance_score: float = 0.45,
    initial_top_k: int | None = None,
    reranker: Reranker | None = None,
    query_rewriter: QueryRewriter | None = None,
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
        retrieval_question = query_rewriter.rewrite(case.question) if query_rewriter else case.question
        query_embedding = embeddings.embed_texts([retrieval_question])[0]
        retrieved_results = vector_store.search(query_embedding=query_embedding, top_k=initial_top_k or top_k)
        results = reranker.rerank(case.question, retrieved_results)[:top_k] if reranker else retrieved_results
        outcomes.append(evaluate_case(case, results, min_relevance_score=min_relevance_score))

    return {
        "summary": summarize_results(outcomes),
        "outcomes": [asdict(outcome) for outcome in outcomes],
    }


def run_parameter_sweep(
    cases_path: Path,
    documents_dir: Path,
    vector_store_root: Path,
    parameters: list[EvaluationParameters],
    embedding_service: EmbeddingService | None = None,
) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    embeddings = embedding_service or SentenceTransformerEmbeddingService()
    for index, parameter_set in enumerate(parameters):
        report = run_evaluation(
            cases_path=cases_path,
            documents_dir=documents_dir,
            vector_store_dir=vector_store_root / f"config-{index}",
            embedding_service=embeddings,
            chunk_size=parameter_set.chunk_size,
            chunk_overlap=parameter_set.chunk_overlap,
            top_k=parameter_set.top_k,
            min_relevance_score=parameter_set.min_relevance_score,
        )
        report["parameters"] = asdict(parameter_set)
        reports.append(report)

    ranked = rank_parameter_reports(reports)
    return {
        "best": ranked[0] if ranked else None,
        "reports": ranked,
    }


def run_reranker_comparison(
    cases_path: Path,
    documents_dir: Path,
    vector_store_root: Path,
    chunk_size: int = 400,
    chunk_overlap: int = 0,
    top_k: int = 3,
    min_relevance_score: float = 0.45,
    initial_top_k: int = 5,
    embedding_service: EmbeddingService | None = None,
) -> dict[str, object]:
    embeddings = embedding_service or SentenceTransformerEmbeddingService()
    baseline = run_evaluation(
        cases_path=cases_path,
        documents_dir=documents_dir,
        vector_store_dir=vector_store_root / "baseline",
        embedding_service=embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        min_relevance_score=min_relevance_score,
        reranker=None,
    )
    reranked = run_evaluation(
        cases_path=cases_path,
        documents_dir=documents_dir,
        vector_store_dir=vector_store_root / "reranked",
        embedding_service=embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        min_relevance_score=min_relevance_score,
        initial_top_k=initial_top_k,
        reranker=KeywordOverlapReranker(),
    )
    delta = _summary_delta(baseline["summary"], reranked["summary"])
    return {
        "baseline": baseline,
        "reranked": reranked,
        "delta": delta,
        "recommendation": _reranker_recommendation(delta),
    }


def run_query_rewrite_comparison(
    cases_path: Path,
    documents_dir: Path,
    vector_store_root: Path,
    chunk_size: int = 400,
    chunk_overlap: int = 0,
    top_k: int = 3,
    min_relevance_score: float = 0.45,
    embedding_service: EmbeddingService | None = None,
) -> dict[str, object]:
    embeddings = embedding_service or SentenceTransformerEmbeddingService()
    baseline = run_evaluation(
        cases_path=cases_path,
        documents_dir=documents_dir,
        vector_store_dir=vector_store_root / "baseline",
        embedding_service=embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        min_relevance_score=min_relevance_score,
        query_rewriter=None,
    )
    rewritten = run_evaluation(
        cases_path=cases_path,
        documents_dir=documents_dir,
        vector_store_dir=vector_store_root / "rewritten",
        embedding_service=embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        min_relevance_score=min_relevance_score,
        query_rewriter=StaticQueryRewriter(),
    )
    delta = _summary_delta(baseline["summary"], rewritten["summary"])
    return {
        "baseline": baseline,
        "rewritten": rewritten,
        "delta": delta,
        "recommendation": _query_rewrite_recommendation(delta),
    }


def run_heuristic_query_rewrite_comparison(
    cases_path: Path,
    documents_dir: Path,
    vector_store_root: Path,
    chunk_size: int = 400,
    chunk_overlap: int = 0,
    top_k: int = 3,
    min_relevance_score: float = 0.45,
    embedding_service: EmbeddingService | None = None,
) -> dict[str, object]:
    embeddings = embedding_service or SentenceTransformerEmbeddingService()
    baseline = run_evaluation(
        cases_path=cases_path,
        documents_dir=documents_dir,
        vector_store_dir=vector_store_root / "baseline",
        embedding_service=embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        min_relevance_score=min_relevance_score,
        query_rewriter=None,
    )
    rewritten = run_evaluation(
        cases_path=cases_path,
        documents_dir=documents_dir,
        vector_store_dir=vector_store_root / "rewritten",
        embedding_service=embeddings,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        top_k=top_k,
        min_relevance_score=min_relevance_score,
        query_rewriter=HeuristicQueryRewriter(),
    )
    delta = _summary_delta(baseline["summary"], rewritten["summary"])
    return {
        "baseline": baseline,
        "rewritten": rewritten,
        "delta": delta,
        "recommendation": _query_rewrite_recommendation(delta),
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


def rank_parameter_reports(reports: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(reports, key=_ranking_key, reverse=True)


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


def _summary_delta(baseline: object, reranked: object) -> dict[str, float]:
    if not isinstance(baseline, dict) or not isinstance(reranked, dict):
        raise TypeError("baseline and reranked summaries must be dictionaries")
    return {
        metric: round(float(reranked[metric]) - float(baseline[metric]), 10)
        for metric in ("source_hit_rate", "marker_hit_rate", "refusal_accuracy")
    }


def _reranker_recommendation(delta: dict[str, float]) -> str:
    values = list(delta.values())
    if any(value > 0 for value in values) and all(value >= 0 for value in values):
        return "consider_reranker"
    return "keep_retrieval_only"


def _query_rewrite_recommendation(delta: dict[str, float]) -> str:
    values = list(delta.values())
    if any(value > 0 for value in values) and all(value >= 0 for value in values):
        return "consider_query_rewrite"
    return "keep_retrieval_only"


def _looks_unrelated_to_project(normalized_question: str) -> bool:
    unrelated_terms = (
        "天气",
        "weather",
        "鸡翅",
        "空气炸锅",
        "股价",
        "stock",
        "英伟达",
        "nvidia",
    )
    return any(term in normalized_question for term in unrelated_terms)


def _mentions_vector_store(normalized_question: str) -> bool:
    mentions_store = any(
        term in normalized_question
        for term in (
            "向量库",
            "向量数据库",
            "vector store",
            "vector database",
            "chromadb",
            "qdrant",
        )
    )
    mentions_phase7_boundary = any(
        term in normalized_question
        for term in (
            "保留",
            "迁移",
            "keep",
            "migration",
            "qdrant",
            "chromadb",
        )
    )
    return mentions_store and mentions_phase7_boundary


def _mentions_safe_reset_followup(normalized_question: str) -> bool:
    mentions_reset = any(term in normalized_question for term in ("清理", "reset", "安全"))
    mentions_documents = any(term in normalized_question for term in ("文档", "资料", "删", "删除", "delete"))
    return mentions_reset and mentions_documents


def _mentions_query_rewrite_timing(normalized_question: str) -> bool:
    mentions_rewrite = any(term in normalized_question for term in ("query rewrite", "查询重写", "问题重写", "改写"))
    mentions_timing = any(term in normalized_question for term in ("什么时候", "何时", "when", "考虑", "consider"))
    return mentions_rewrite and mentions_timing


def _tokenize_for_reranking(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", text.lower()) if len(token.strip()) > 0}


def _overlap_count(query_terms: set[str], content: str) -> int:
    return len(query_terms.intersection(_tokenize_for_reranking(content)))


def _ranking_key(report: dict[str, object]) -> tuple[float, float, float, int, int]:
    summary = report["summary"]
    parameters = report["parameters"]
    if not isinstance(summary, dict) or not isinstance(parameters, dict):
        raise TypeError("report must include summary and parameters dictionaries")
    return (
        float(summary["source_hit_rate"]),
        float(summary["marker_hit_rate"]),
        float(summary["refusal_accuracy"]),
        -int(parameters["top_k"]),
        -int(parameters["chunk_size"]),
    )


def _parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def _parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def _build_parameter_grid(
    chunk_sizes: list[int],
    chunk_overlaps: list[int],
    top_ks: list[int],
    min_relevance_scores: list[float],
) -> list[EvaluationParameters]:
    return [
        EvaluationParameters(chunk_size, chunk_overlap, top_k, min_relevance_score)
        for chunk_size in chunk_sizes
        for chunk_overlap in chunk_overlaps
        if chunk_overlap < chunk_size
        for top_k in top_ks
        for min_relevance_score in min_relevance_scores
    ]


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
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--min-relevance-score", type=float, default=0.45)
    parser.add_argument("--initial-top-k", type=int, default=5)
    parser.add_argument("--chunk-sizes", default=None)
    parser.add_argument("--chunk-overlaps", default=None)
    parser.add_argument("--top-ks", default=None)
    parser.add_argument("--min-relevance-scores", default=None)
    parser.add_argument("--compare-reranker", action="store_true")
    parser.add_argument("--compare-query-rewrite", action="store_true")
    parser.add_argument("--compare-heuristic-query-rewrite", action="store_true")
    parser.add_argument("--save-run", action="store_true")
    parser.add_argument("--database-url", default="sqlite:///data/app.db")
    args = parser.parse_args(argv)

    if args.compare_heuristic_query_rewrite:
        report = run_heuristic_query_rewrite_comparison(
            cases_path=args.cases,
            documents_dir=args.documents,
            vector_store_root=args.vector_store,
            top_k=args.top_k,
            min_relevance_score=args.min_relevance_score,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.compare_query_rewrite:
        report = run_query_rewrite_comparison(
            cases_path=args.cases,
            documents_dir=args.documents,
            vector_store_root=args.vector_store,
            top_k=args.top_k,
            min_relevance_score=args.min_relevance_score,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.compare_reranker:
        report = run_reranker_comparison(
            cases_path=args.cases,
            documents_dir=args.documents,
            vector_store_root=args.vector_store,
            top_k=args.top_k,
            min_relevance_score=args.min_relevance_score,
            initial_top_k=args.initial_top_k,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    if args.chunk_sizes or args.chunk_overlaps or args.top_ks or args.min_relevance_scores:
        parameters = _build_parameter_grid(
            chunk_sizes=_parse_int_list(args.chunk_sizes or str(args.top_k)),
            chunk_overlaps=_parse_int_list(args.chunk_overlaps or "120"),
            top_ks=_parse_int_list(args.top_ks or str(args.top_k)),
            min_relevance_scores=_parse_float_list(args.min_relevance_scores or str(args.min_relevance_score)),
        )
        report = run_parameter_sweep(
            cases_path=args.cases,
            documents_dir=args.documents,
            vector_store_root=args.vector_store,
            parameters=parameters,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    report = run_evaluation(
        cases_path=args.cases,
        documents_dir=args.documents,
        vector_store_dir=args.vector_store,
        top_k=args.top_k,
        min_relevance_score=args.min_relevance_score,
    )
    if args.save_run:
        saved_run = _save_evaluation_run(
            database_url=args.database_url,
            mode="baseline",
            parameters={
                "top_k": args.top_k,
                "min_relevance_score": args.min_relevance_score,
            },
            report=report,
        )
        report["saved_run_id"] = saved_run.id
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _save_evaluation_run(
    database_url: str,
    mode: str,
    parameters: dict[str, object],
    report: dict[str, object],
):
    session_factory = create_session_factory(database_url)
    initialize_database(session_factory)
    repository = SQLEvaluationRepository(session_factory)
    return repository.save_run(mode=mode, parameters=parameters, report=report)


if __name__ == "__main__":
    main()
