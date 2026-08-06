from fastapi import APIRouter, HTTPException

from app.db.evaluation_repository import SQLEvaluationRepository
from app.schemas.evaluation import EvaluationRunDetail, EvaluationRunSummary


def create_evaluation_router(evaluation_repository: SQLEvaluationRepository) -> APIRouter:
    router = APIRouter(tags=["evaluation"])

    @router.get("/api/evaluations", response_model=list[EvaluationRunSummary])
    def list_evaluation_runs() -> list[EvaluationRunSummary]:
        return evaluation_repository.list_runs()

    @router.get("/api/evaluations/{run_id}", response_model=EvaluationRunDetail)
    def get_evaluation_run(run_id: str) -> EvaluationRunDetail:
        run = evaluation_repository.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Evaluation run not found.")
        return run

    return router
