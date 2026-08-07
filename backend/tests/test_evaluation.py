import json
from pathlib import Path

from app.schemas.search import SearchResult
from evaluation.evaluate_retrieval import (
    EvaluationCase,
    EvaluationParameters,
    HeuristicQueryRewriter,
    KeywordOverlapReranker,
    StaticQueryRewriter,
    evaluate_case,
    load_cases,
    main,
    rank_parameter_reports,
    run_evaluation,
    run_heuristic_query_rewrite_comparison,
    run_parameter_sweep,
    run_query_rewrite_comparison,
    run_reranker_comparison,
    summarize_results,
)


class KeywordEmbeddingService:
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            normalized = text.lower()
            vectors.append(
                [
                    1.0 if "rag" in normalized or "向量" in normalized else 0.0,
                    1.0 if "docker" in normalized or "compose" in normalized else 0.0,
                    1.0 if "weather" in normalized or "天气" in normalized else 0.0,
                ]
            )
        return vectors


def test_evaluate_case_counts_expected_source_hit() -> None:
    case = EvaluationCase(
        id="rag_upload_chunking",
        question="How are documents indexed?",
        expected_filename="rag_baseline.md",
        expected_marker="split into overlapping chunks",
        expect_refusal=False,
    )
    results = [
        SearchResult(
            filename="rag_baseline.md",
            page=1,
            chunk_index=0,
            content="Documents are split into overlapping chunks before embedding.",
            score=0.91,
        )
    ]

    outcome = evaluate_case(case, results, min_relevance_score=0.5)

    assert outcome.source_hit is True
    assert outcome.marker_hit is True
    assert outcome.refusal_correct is True
    assert outcome.best_score == 0.91


def test_evaluate_case_counts_expected_refusal() -> None:
    case = EvaluationCase(
        id="unrelated_weather",
        question="Will it rain tomorrow?",
        expected_filename=None,
        expected_marker=None,
        expect_refusal=True,
    )

    outcome = evaluate_case(case, [], min_relevance_score=0.5)

    assert outcome.source_hit is True
    assert outcome.marker_hit is True
    assert outcome.refusal_correct is True
    assert outcome.best_score is None


def test_summarize_results_reports_rates() -> None:
    cases = [
        EvaluationCase("a", "q1", "one.md", "needle", False),
        EvaluationCase("b", "q2", None, None, True),
    ]
    outcomes = [
        evaluate_case(
            cases[0],
            [
                SearchResult(
                    filename="one.md",
                    page=1,
                    chunk_index=0,
                    content="needle",
                    score=0.9,
                )
            ],
            min_relevance_score=0.5,
        ),
        evaluate_case(cases[1], [], min_relevance_score=0.5),
    ]

    summary = summarize_results(outcomes)

    assert summary["case_count"] == 2
    assert summary["source_hit_rate"] == 1.0
    assert summary["marker_hit_rate"] == 1.0
    assert summary["refusal_accuracy"] == 1.0


def test_run_evaluation_returns_summary_for_fixture_documents(tmp_path: Path) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    (document_dir / "rag_baseline.md").write_text(
        "RAG documents are split into overlapping chunks before embedding.",
        encoding="utf-8",
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        """
[
  {
    "id": "rag",
    "question": "RAG 怎么索引文档？",
    "expected_filename": "rag_baseline.md",
    "expected_marker": "overlapping chunks",
    "expect_refusal": false
  }
]
""".strip(),
        encoding="utf-8",
    )

    report = run_evaluation(
        cases_path=cases_path,
        documents_dir=document_dir,
        vector_store_dir=tmp_path / "chroma",
        embedding_service=KeywordEmbeddingService(),
        chunk_size=400,
        chunk_overlap=0,
        top_k=3,
        min_relevance_score=0.5,
    )

    assert report["summary"]["case_count"] == 1
    assert report["summary"]["source_hit_rate"] == 1.0
    assert report["outcomes"][0]["id"] == "rag"


def test_default_evaluation_fixture_covers_core_project_behaviors() -> None:
    cases = load_cases(Path(__file__).parents[1] / "evaluation" / "fixtures" / "cases.json")
    case_ids = {case.id for case in cases}
    filenames = {case.expected_filename for case in cases if case.expected_filename is not None}

    assert len(cases) >= 14
    assert {
        "rag_upload_chunking",
        "sqlite_deleted_documents_hidden",
        "frontend_retrieval_debug_panel",
        "reranker_deferred_until_evaluation",
        "english_question_sqlite_lifecycle",
        "unrelated_weather",
    }.issubset(case_ids)
    assert {
        "rag_baseline.md",
        "deployment_notes.md",
        "phase3_hardening.md",
        "frontend_behavior.md",
        "roadmap_boundaries.md",
    }.issubset(filenames)
    assert sum(1 for case in cases if case.expect_refusal) >= 3


def test_default_evaluation_fixture_includes_phase7_advanced_rag_pressure_cases() -> None:
    cases = load_cases(Path(__file__).parents[1] / "evaluation" / "fixtures" / "cases.json")
    case_ids = {case.id for case in cases}
    filenames = {case.expected_filename for case in cases if case.expected_filename is not None}

    assert len(cases) >= 20
    assert {
        "short_ambiguous_vector_store",
        "keyword_exact_bge_m3",
        "conversational_followup_reset",
        "similar_document_interference",
        "query_rewrite_scope_boundary",
    }.issubset(case_ids)
    assert "phase7_advanced_rag.md" in filenames


def test_main_prints_json_report(monkeypatch, capsys, tmp_path: Path) -> None:
    cases_path = tmp_path / "cases.json"
    documents_dir = tmp_path / "documents"
    vector_store_dir = tmp_path / "chroma"

    def fake_run_evaluation(**kwargs):
        assert kwargs["cases_path"] == cases_path
        assert kwargs["documents_dir"] == documents_dir
        assert kwargs["vector_store_dir"] == vector_store_dir
        assert kwargs["top_k"] == 2
        assert kwargs["min_relevance_score"] == 0.4
        return {"summary": {"case_count": 0}, "outcomes": []}

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    main(
        [
            "--cases",
            str(cases_path),
            "--documents",
            str(documents_dir),
            "--vector-store",
            str(vector_store_dir),
            "--top-k",
            "2",
            "--min-relevance-score",
            "0.4",
        ]
    )

    assert json.loads(capsys.readouterr().out)["summary"]["case_count"] == 0


def test_main_defaults_to_ignored_root_test_data(monkeypatch, capsys) -> None:
    expected_vector_store = Path(__file__).resolve().parents[2] / ".test-data" / "rag-evaluation-chroma"

    def fake_run_evaluation(**kwargs):
        assert kwargs["vector_store_dir"] == expected_vector_store
        return {"summary": {"case_count": 0}, "outcomes": []}

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    main([])

    assert json.loads(capsys.readouterr().out)["summary"]["case_count"] == 0


def test_rank_parameter_reports_orders_by_quality_then_smaller_context() -> None:
    reports = [
        {
            "parameters": {
                "chunk_size": 800,
                "chunk_overlap": 120,
                "top_k": 5,
                "min_relevance_score": 0.5,
            },
            "summary": {
                "case_count": 4,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 0.75,
                "refusal_accuracy": 1.0,
            },
            "outcomes": [],
        },
        {
            "parameters": {
                "chunk_size": 500,
                "chunk_overlap": 80,
                "top_k": 3,
                "min_relevance_score": 0.5,
            },
            "summary": {
                "case_count": 4,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 1.0,
                "refusal_accuracy": 1.0,
            },
            "outcomes": [],
        },
    ]

    ranked = rank_parameter_reports(reports)

    assert ranked[0]["parameters"]["chunk_size"] == 500
    assert ranked[0]["summary"]["marker_hit_rate"] == 1.0


def test_run_parameter_sweep_evaluates_each_parameter_set(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_evaluation(**kwargs):
        calls.append(kwargs)
        return {
            "summary": {
                "case_count": 1,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 1.0,
                "refusal_accuracy": 1.0,
            },
            "outcomes": [],
        }

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)
    parameters = [
        EvaluationParameters(chunk_size=400, chunk_overlap=0, top_k=3, min_relevance_score=0.5),
        EvaluationParameters(chunk_size=800, chunk_overlap=120, top_k=5, min_relevance_score=0.45),
    ]

    report = run_parameter_sweep(
        cases_path=tmp_path / "cases.json",
        documents_dir=tmp_path / "documents",
        vector_store_root=tmp_path / "chroma-sweep",
        parameters=parameters,
        embedding_service=KeywordEmbeddingService(),
    )

    assert len(calls) == 2
    assert calls[0]["chunk_size"] == 400
    assert calls[1]["min_relevance_score"] == 0.45
    assert report["best"]["parameters"]["top_k"] == 3
    assert len(report["reports"]) == 2


def test_run_parameter_sweep_reuses_default_embedding_service(monkeypatch, tmp_path: Path) -> None:
    created_embeddings: list[object] = []
    used_embeddings: list[object] = []

    class FakeDefaultEmbeddingService:
        def __init__(self) -> None:
            created_embeddings.append(self)

    def fake_run_evaluation(**kwargs):
        used_embeddings.append(kwargs["embedding_service"])
        return {
            "summary": {
                "case_count": 1,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 1.0,
                "refusal_accuracy": 1.0,
            },
            "outcomes": [],
        }

    monkeypatch.setattr("evaluation.evaluate_retrieval.SentenceTransformerEmbeddingService", FakeDefaultEmbeddingService)
    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    run_parameter_sweep(
        cases_path=tmp_path / "cases.json",
        documents_dir=tmp_path / "documents",
        vector_store_root=tmp_path / "chroma-sweep",
        parameters=[
            EvaluationParameters(chunk_size=400, chunk_overlap=0, top_k=3, min_relevance_score=0.5),
            EvaluationParameters(chunk_size=800, chunk_overlap=120, top_k=5, min_relevance_score=0.45),
        ],
    )

    assert len(created_embeddings) == 1
    assert used_embeddings == [created_embeddings[0], created_embeddings[0]]


def test_keyword_overlap_reranker_prioritizes_query_terms() -> None:
    reranker = KeywordOverlapReranker()
    results = [
        SearchResult(
            filename="deployment_notes.md",
            page=1,
            chunk_index=0,
            content="Docker Compose exposes local ports for the demo.",
            score=0.95,
        ),
        SearchResult(
            filename="phase3_hardening.md",
            page=1,
            chunk_index=0,
            content="Normal document list and repository reads hide deleted status records.",
            score=0.7,
        ),
    ]

    reranked = reranker.rerank("How does the app hide deleted documents from normal reads?", results)

    assert reranked[0].filename == "phase3_hardening.md"


def test_run_reranker_comparison_reports_metric_deltas(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_evaluation(**kwargs):
        calls.append(kwargs)
        summary = {
            "case_count": 2,
            "source_hit_rate": 1.0,
            "marker_hit_rate": 1.0,
            "refusal_accuracy": 1.0,
        }
        return {"summary": summary, "outcomes": []}

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    report = run_reranker_comparison(
        cases_path=tmp_path / "cases.json",
        documents_dir=tmp_path / "documents",
        vector_store_root=tmp_path / "chroma-reranker",
        chunk_size=400,
        chunk_overlap=0,
        top_k=3,
        min_relevance_score=0.45,
        initial_top_k=5,
        embedding_service=KeywordEmbeddingService(),
    )

    assert calls[0]["top_k"] == 3
    assert calls[0]["reranker"] is None
    assert calls[1]["top_k"] == 3
    assert calls[1]["initial_top_k"] == 5
    assert isinstance(calls[1]["reranker"], KeywordOverlapReranker)
    assert report["delta"] == {
        "source_hit_rate": 0.0,
        "marker_hit_rate": 0.0,
        "refusal_accuracy": 0.0,
    }
    assert report["recommendation"] == "keep_retrieval_only"


def test_static_query_rewriter_expands_known_phase7_pressure_question() -> None:
    rewriter = StaticQueryRewriter()

    rewritten = rewriter.rewrite("向量库先保留哪个？")

    assert rewritten == "Phase 7 evidence shows which vector store should keep ChromaDB before migration?"


def test_heuristic_query_rewriter_expands_project_retrieval_questions_without_exact_match() -> None:
    rewriter = HeuristicQueryRewriter()

    rewritten = rewriter.rewrite("这个向量数据库到底保留啥")

    assert "ChromaDB" in rewritten
    assert "Phase 7" in rewritten
    assert "migration evidence" in rewritten


def test_heuristic_query_rewriter_expands_safe_reset_followups_without_exact_match() -> None:
    rewriter = HeuristicQueryRewriter()

    rewritten = rewriter.rewrite("那清理会不会删掉资料")

    assert "safe reset" in rewritten
    assert "refuses document deletion" in rewritten
    assert "explicit document delete path" in rewritten


def test_heuristic_query_rewriter_keeps_unrelated_questions_unchanged() -> None:
    rewriter = HeuristicQueryRewriter()

    question = "明天上海天气怎么样？"

    assert rewriter.rewrite(question) == question


def test_run_query_rewrite_comparison_reports_metric_deltas(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_evaluation(**kwargs):
        calls.append(kwargs)
        summary = (
            {
                "case_count": 20,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 1.0,
                "refusal_accuracy": 1.0,
            }
            if kwargs["query_rewriter"] is not None
            else {
                "case_count": 20,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 0.85,
                "refusal_accuracy": 1.0,
            }
        )
        return {"summary": summary, "outcomes": []}

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    report = run_query_rewrite_comparison(
        cases_path=tmp_path / "cases.json",
        documents_dir=tmp_path / "documents",
        vector_store_root=tmp_path / "chroma-query-rewrite",
        chunk_size=400,
        chunk_overlap=0,
        top_k=3,
        min_relevance_score=0.45,
        embedding_service=KeywordEmbeddingService(),
    )

    assert calls[0]["query_rewriter"] is None
    assert isinstance(calls[1]["query_rewriter"], StaticQueryRewriter)
    assert report["delta"] == {
        "source_hit_rate": 0.0,
        "marker_hit_rate": 0.15,
        "refusal_accuracy": 0.0,
    }
    assert report["recommendation"] == "consider_query_rewrite"


def test_run_heuristic_query_rewrite_comparison_reports_metric_deltas(monkeypatch, tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def fake_run_evaluation(**kwargs):
        calls.append(kwargs)
        summary = (
            {
                "case_count": 20,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 0.95,
                "refusal_accuracy": 1.0,
            }
            if kwargs["query_rewriter"] is not None
            else {
                "case_count": 20,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 0.85,
                "refusal_accuracy": 1.0,
            }
        )
        return {"summary": summary, "outcomes": []}

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    report = run_heuristic_query_rewrite_comparison(
        cases_path=tmp_path / "cases.json",
        documents_dir=tmp_path / "documents",
        vector_store_root=tmp_path / "chroma-heuristic-query-rewrite",
        chunk_size=400,
        chunk_overlap=0,
        top_k=3,
        min_relevance_score=0.45,
        embedding_service=KeywordEmbeddingService(),
    )

    assert calls[0]["query_rewriter"] is None
    assert isinstance(calls[1]["query_rewriter"], HeuristicQueryRewriter)
    assert report["delta"] == {
        "source_hit_rate": 0.0,
        "marker_hit_rate": 0.1,
        "refusal_accuracy": 0.0,
    }
    assert report["recommendation"] == "consider_query_rewrite"


def test_main_runs_parameter_sweep_when_multiple_values_are_passed(monkeypatch, capsys, tmp_path: Path) -> None:
    captured_parameters: list[EvaluationParameters] = []

    def fake_run_parameter_sweep(**kwargs):
        captured_parameters.extend(kwargs["parameters"])
        return {"best": None, "reports": []}

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_parameter_sweep", fake_run_parameter_sweep)

    main(
        [
            "--cases",
            str(tmp_path / "cases.json"),
            "--documents",
            str(tmp_path / "documents"),
            "--vector-store",
            str(tmp_path / "chroma"),
            "--chunk-sizes",
            "400,800",
            "--chunk-overlaps",
            "0,120",
            "--top-ks",
            "3,5",
            "--min-relevance-scores",
            "0.45,0.5",
        ]
    )

    assert len(captured_parameters) == 16
    assert captured_parameters[0] == EvaluationParameters(400, 0, 3, 0.45)
    assert json.loads(capsys.readouterr().out)["reports"] == []


def test_main_runs_reranker_comparison(monkeypatch, capsys, tmp_path: Path) -> None:
    def fake_run_reranker_comparison(**kwargs):
        assert kwargs["top_k"] == 3
        assert kwargs["initial_top_k"] == 5
        return {
            "baseline": {"summary": {"case_count": 0}, "outcomes": []},
            "reranked": {"summary": {"case_count": 0}, "outcomes": []},
            "delta": {},
            "recommendation": "keep_retrieval_only",
        }

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_reranker_comparison", fake_run_reranker_comparison)

    main(
        [
            "--cases",
            str(tmp_path / "cases.json"),
            "--documents",
            str(tmp_path / "documents"),
            "--vector-store",
            str(tmp_path / "chroma"),
            "--compare-reranker",
            "--top-k",
            "3",
            "--initial-top-k",
            "5",
        ]
    )

    assert json.loads(capsys.readouterr().out)["recommendation"] == "keep_retrieval_only"


def test_main_runs_query_rewrite_comparison(monkeypatch, capsys, tmp_path: Path) -> None:
    def fake_run_query_rewrite_comparison(**kwargs):
        assert kwargs["top_k"] == 3
        return {
            "baseline": {"summary": {"case_count": 0}, "outcomes": []},
            "rewritten": {"summary": {"case_count": 0}, "outcomes": []},
            "delta": {},
            "recommendation": "keep_retrieval_only",
        }

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_query_rewrite_comparison", fake_run_query_rewrite_comparison)

    main(
        [
            "--cases",
            str(tmp_path / "cases.json"),
            "--documents",
            str(tmp_path / "documents"),
            "--vector-store",
            str(tmp_path / "chroma"),
            "--compare-query-rewrite",
            "--top-k",
            "3",
        ]
    )

    assert json.loads(capsys.readouterr().out)["recommendation"] == "keep_retrieval_only"


def test_main_runs_heuristic_query_rewrite_comparison(monkeypatch, capsys, tmp_path: Path) -> None:
    def fake_run_heuristic_query_rewrite_comparison(**kwargs):
        assert kwargs["top_k"] == 3
        return {
            "baseline": {"summary": {"case_count": 0}, "outcomes": []},
            "rewritten": {"summary": {"case_count": 0}, "outcomes": []},
            "delta": {},
            "recommendation": "keep_retrieval_only",
        }

    monkeypatch.setattr(
        "evaluation.evaluate_retrieval.run_heuristic_query_rewrite_comparison",
        fake_run_heuristic_query_rewrite_comparison,
    )

    main(
        [
            "--cases",
            str(tmp_path / "cases.json"),
            "--documents",
            str(tmp_path / "documents"),
            "--vector-store",
            str(tmp_path / "chroma"),
            "--compare-heuristic-query-rewrite",
            "--top-k",
            "3",
        ]
    )

    assert json.loads(capsys.readouterr().out)["recommendation"] == "keep_retrieval_only"


def test_main_saves_evaluation_run_when_requested(monkeypatch, capsys, tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'app.db'}"

    def fake_run_evaluation(**kwargs):
        return {
            "summary": {
                "case_count": 1,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 1.0,
                "refusal_accuracy": 1.0,
            },
            "outcomes": [{"id": "rag"}],
        }

    monkeypatch.setattr("evaluation.evaluate_retrieval.run_evaluation", fake_run_evaluation)

    main(
        [
            "--database-url",
            database_url,
            "--save-run",
        ]
    )

    output = json.loads(capsys.readouterr().out)

    assert output["saved_run_id"]
    assert output["summary"]["case_count"] == 1
