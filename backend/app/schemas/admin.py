from pydantic import BaseModel


class LocalExportResponse(BaseModel):
    documents: list[dict[str, object]]
    chat_sessions: list[dict[str, object]]
    evaluation_runs: list[dict[str, object]]


class ResetRequest(BaseModel):
    reset_chat_history: bool = True
    reset_evaluations: bool = True
    reset_documents: bool = False


class ResetResponse(BaseModel):
    reset_chat_history: bool
    reset_evaluations: bool
    reset_documents: bool
