from datetime import UTC, datetime
import json
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import EvaluationRunRecord
from app.schemas.evaluation import EvaluationRunDetail, EvaluationRunSummary


class SQLEvaluationRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def save_run(
        self,
        mode: str,
        parameters: dict[str, object],
        report: dict[str, object],
    ) -> EvaluationRunSummary:
        summary = _report_summary(report)
        record = EvaluationRunRecord(
            id=uuid4().hex,
            created_at=_utc_now(),
            mode=mode,
            case_count=int(summary["case_count"]),
            source_hit_rate=float(summary["source_hit_rate"]),
            marker_hit_rate=float(summary["marker_hit_rate"]),
            refusal_accuracy=float(summary["refusal_accuracy"]),
            recommendation=_recommendation(report),
            parameters_json=json.dumps(parameters, ensure_ascii=False),
            report_json=json.dumps(report, ensure_ascii=False),
        )
        with self.session_factory() as session:
            session.add(record)
            session.commit()
            return _record_to_summary(record)

    def list_runs(self) -> list[EvaluationRunSummary]:
        with self.session_factory() as session:
            records = session.scalars(
                select(EvaluationRunRecord).order_by(EvaluationRunRecord.created_at.desc())
            ).all()
            return [_record_to_summary(record) for record in records]

    def get_run(self, run_id: str) -> EvaluationRunDetail | None:
        with self.session_factory() as session:
            record = session.get(EvaluationRunRecord, run_id)
            if record is None:
                return None
            return EvaluationRunDetail(
                **_record_to_summary(record).model_dump(),
                report=json.loads(record.report_json),
            )

    def clear_all(self) -> None:
        with self.session_factory() as session:
            records = session.scalars(select(EvaluationRunRecord)).all()
            for record in records:
                session.delete(record)
            session.commit()


def _record_to_summary(record: EvaluationRunRecord) -> EvaluationRunSummary:
    return EvaluationRunSummary(
        id=record.id,
        created_at=record.created_at,
        mode=record.mode,
        case_count=record.case_count,
        source_hit_rate=record.source_hit_rate,
        marker_hit_rate=record.marker_hit_rate,
        refusal_accuracy=record.refusal_accuracy,
        recommendation=record.recommendation,
        parameters=json.loads(record.parameters_json),
    )


def _report_summary(report: dict[str, object]) -> dict[str, object]:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Evaluation report must include a summary object.")
    return summary


def _recommendation(report: dict[str, object]) -> str | None:
    recommendation = report.get("recommendation")
    return recommendation if isinstance(recommendation, str) else None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
