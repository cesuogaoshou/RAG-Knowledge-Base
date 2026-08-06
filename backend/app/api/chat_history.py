from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.chat_repository import SQLChatRepository
from app.schemas.chat_history import ChatSessionDetail, ChatSessionSummary


class DeleteChatSessionResponse(BaseModel):
    id: str
    deleted: bool


def create_chat_history_router(chat_repository: SQLChatRepository) -> APIRouter:
    router = APIRouter(tags=["chat-history"])

    @router.get("/api/chat/sessions", response_model=list[ChatSessionSummary])
    def list_chat_sessions() -> list[ChatSessionSummary]:
        return chat_repository.list_sessions()

    @router.get("/api/chat/sessions/{session_id}", response_model=ChatSessionDetail)
    def get_chat_session(session_id: str) -> ChatSessionDetail:
        session = chat_repository.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        return session

    @router.delete("/api/chat/sessions/{session_id}", response_model=DeleteChatSessionResponse)
    def delete_chat_session(session_id: str) -> DeleteChatSessionResponse:
        deleted = chat_repository.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Chat session not found.")
        return DeleteChatSessionResponse(id=session_id, deleted=True)

    return router
