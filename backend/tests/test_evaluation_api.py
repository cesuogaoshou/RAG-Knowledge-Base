from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.database import create_session_factory, initialize_database
from app.db.evaluation_repository import SQLEvaluationRepository
from app.main import create_app


def _workspace_dir() -> Path:
    path = Path(".test-data") / f"evaluation-api-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_evaluation_api_lists_and_reads_saved_runs() -> None:
    workspace = _workspace_dir()
    database_url = f"sqlite:///{workspace / 'app.db'}"
    try:
        session_factory = create_session_factory(database_url)
        initialize_database(session_factory)
        repository = SQLEvaluationRepository(session_factory)
        saved = repository.save_run(
            mode="baseline",
            parameters={"top_k": 3},
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

        client = TestClient(
            create_app(
                upload_dir=workspace / "uploads",
                vector_store_dir=workspace / "chroma_db",
                database_url=database_url,
            )
        )

        list_response = client.get("/api/evaluations")
        detail_response = client.get(f"/api/evaluations/{saved.id}")
        missing_response = client.get("/api/evaluations/missing-run")

        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == saved.id
        assert list_response.json()[0]["parameters"]["top_k"] == 3
        assert detail_response.status_code == 200
        assert detail_response.json()["report"]["outcomes"][0]["id"] == "rag_upload_chunking"
        assert missing_response.status_code == 404
        assert missing_response.json()["detail"] == "Evaluation run not found."
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
