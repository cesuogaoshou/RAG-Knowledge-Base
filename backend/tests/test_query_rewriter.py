from app.services.query_rewriter import HeuristicQueryRewriter, NoopQueryRewriter, safe_rewrite_query


class ExplodingRewriter:
    def rewrite(self, question: str) -> str:
        raise RuntimeError("rewrite failed")


def test_noop_query_rewriter_keeps_original_question() -> None:
    rewriter = NoopQueryRewriter()

    result = rewriter.rewrite("向量库先保留哪个？")

    assert result == "向量库先保留哪个？"


def test_heuristic_query_rewriter_expands_vector_store_questions() -> None:
    rewriter = HeuristicQueryRewriter()

    result = rewriter.rewrite("这个向量数据库到底保留啥")

    assert "ChromaDB" in result
    assert "Qdrant" in result
    assert "migration evidence" in result


def test_heuristic_query_rewriter_expands_safe_reset_questions() -> None:
    rewriter = HeuristicQueryRewriter()

    result = rewriter.rewrite("那清理会不会删掉资料")

    assert "safe reset" in result
    assert "refuses document deletion" in result
    assert "explicit document delete path" in result


def test_heuristic_query_rewriter_expands_query_rewrite_timing_questions() -> None:
    rewriter = HeuristicQueryRewriter()

    result = rewriter.rewrite("什么时候才考虑 query rewrite？")

    assert "query rewrite" in result
    assert "ambiguous question failures are measured" in result


def test_heuristic_query_rewriter_keeps_unrelated_questions_unchanged() -> None:
    rewriter = HeuristicQueryRewriter()

    result = rewriter.rewrite("明天上海天气怎么样？")

    assert result == "明天上海天气怎么样？"


def test_safe_rewrite_query_reports_rewritten_metadata() -> None:
    result = safe_rewrite_query(HeuristicQueryRewriter(), "向量库先保留哪个？")

    assert result.original_query == "向量库先保留哪个？"
    assert result.retrieval_query != result.original_query
    assert result.query_rewritten is True


def test_safe_rewrite_query_falls_back_when_rewriter_fails() -> None:
    result = safe_rewrite_query(ExplodingRewriter(), "向量库先保留哪个？")

    assert result.original_query == "向量库先保留哪个？"
    assert result.retrieval_query == "向量库先保留哪个？"
    assert result.query_rewritten is False
