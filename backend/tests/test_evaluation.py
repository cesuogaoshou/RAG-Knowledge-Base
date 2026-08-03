import json
from pathlib import Path

from app.schemas.search import SearchResult
from evaluation.evaluate_retrieval import (
    EvaluationCase,
    evaluate_case,
    main,
    run_evaluation,
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
