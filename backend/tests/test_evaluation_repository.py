from pathlib import Path
from uuid import uuid4

from app.db.database import create_session_factory, initialize_database
from app.db.evaluation_repository import SQLEvaluationRepository


def _repository() -> SQLEvaluationRepository:
    workspace = Path(".test-data") / f"evaluation-repo-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    session_factory = create_session_factory(f"sqlite:///{workspace / 'app.db'}")
    initialize_database(session_factory)
    return SQLEvaluationRepository(session_factory)


def test_evaluation_repository_saves_and_lists_run_summary() -> None:
    repository = _repository()

    saved = repository.save_run(
        mode="baseline",
        parameters={"top_k": 3, "min_relevance_score": 0.45},
        report={
            "summary": {
                "case_count": 15,
                "source_hit_rate": 1.0,
                "marker_hit_rate": 1.0,
                "refusal_accuracy": 1.0,
            },
            "outcomes": [{"id": "rag_upload_chunking"}],
        },
    )

    runs = repository.list_runs()
    loaded = repository.get_run(saved.id)

    assert runs[0].id == saved.id
    assert runs[0].case_count == 15
    assert runs[0].source_hit_rate == 1.0
    assert runs[0].parameters["top_k"] == 3
    assert loaded is not None
    assert loaded.report["outcomes"][0]["id"] == "rag_upload_chunking"
