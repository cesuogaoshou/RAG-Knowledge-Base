from fastapi import APIRouter, HTTPException

from app.db.chat_repository import SQLChatRepository
from app.db.evaluation_repository import SQLEvaluationRepository
from app.schemas.admin import LocalExportResponse, ResetRequest, ResetResponse
from app.services.document_metadata_store import DocumentMetadataStore


def create_admin_router(
    metadata_store: DocumentMetadataStore,
    chat_repository: SQLChatRepository,
    evaluation_repository: SQLEvaluationRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/admin", tags=["admin"])

    @router.get("/export", response_model=LocalExportResponse)
    def export_local_data() -> LocalExportResponse:
        chat_sessions = [
            detail.model_dump()
            for session in chat_repository.list_sessions()
            if (detail := chat_repository.get_session(session.id)) is not None
        ]
        evaluation_runs = [
            detail.model_dump()
            for run in evaluation_repository.list_runs()
            if (detail := evaluation_repository.get_run(run.id)) is not None
        ]
        return LocalExportResponse(
            documents=[document.model_dump() for document in metadata_store.list_active_documents()],
            chat_sessions=chat_sessions,
            evaluation_runs=evaluation_runs,
        )

    @router.post("/reset", response_model=ResetResponse)
    def reset_local_data(request: ResetRequest) -> ResetResponse:
        if request.reset_documents:
            raise HTTPException(
                status_code=400,
                detail="Document reset is not available from the safe local reset endpoint.",
            )
        if request.reset_chat_history:
            chat_repository.clear_all()
        if request.reset_evaluations:
            evaluation_repository.clear_all()
        return ResetResponse(
            reset_chat_history=request.reset_chat_history,
            reset_evaluations=request.reset_evaluations,
            reset_documents=False,
        )

    return router
