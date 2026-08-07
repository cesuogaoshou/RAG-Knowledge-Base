from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class QueryRewriteResult:
    original_query: str
    retrieval_query: str
    query_rewritten: bool


class QueryRewriter(Protocol):
    def rewrite(self, question: str) -> str:
        pass


class NoopQueryRewriter:
    def rewrite(self, question: str) -> str:
        return question


class HeuristicQueryRewriter:
    def rewrite(self, question: str) -> str:
        normalized = question.lower()
        if _looks_unrelated_to_project(normalized):
            return question
        if _mentions_vector_store(normalized):
            return f"{question} Phase 7 evidence keep ChromaDB vector store before Qdrant migration evidence."
        if _mentions_safe_reset_followup(normalized):
            return f"{question} safe reset refuses document deletion and uses the explicit document delete path."
        if _mentions_query_rewrite_timing(normalized):
            return f"{question} query rewrite considered after ambiguous question failures are measured."
        return question


def safe_rewrite_query(rewriter: QueryRewriter, question: str) -> QueryRewriteResult:
    try:
        retrieval_query = rewriter.rewrite(question).strip()
    except Exception:
        retrieval_query = question

    if not retrieval_query:
        retrieval_query = question

    return QueryRewriteResult(
        original_query=question,
        retrieval_query=retrieval_query,
        query_rewritten=retrieval_query != question,
    )


def _looks_unrelated_to_project(normalized_question: str) -> bool:
    unrelated_terms = (
        "天气",
        "weather",
        "菜谱",
        "recipe",
        "股票",
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
