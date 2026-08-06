from pydantic import BaseModel


class EvaluationRunSummary(BaseModel):
    id: str
    created_at: str
    mode: str
    case_count: int
    source_hit_rate: float
    marker_hit_rate: float
    refusal_accuracy: float
    recommendation: str | None
    parameters: dict[str, object]


class EvaluationRunDetail(EvaluationRunSummary):
    report: dict[str, object]
