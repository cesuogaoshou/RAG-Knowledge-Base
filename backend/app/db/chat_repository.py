from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import ChatMessageRecord, ChatSessionRecord
from app.schemas.chat_history import (
    ChatMessageCreate,
    ChatMessageSummary,
    ChatSessionDetail,
    ChatSessionSummary,
)


class SQLChatRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    def create_session(self, title: str) -> ChatSessionSummary:
        now = _utc_now()
        record = ChatSessionRecord(id=uuid4().hex, title=title[:80], created_at=now, updated_at=now)
        with self.session_factory() as session:
            session.add(record)
            session.commit()
            return ChatSessionSummary(
                id=record.id,
                title=record.title,
                created_at=now,
                updated_at=now,
                message_count=0,
            )

    def list_sessions(self) -> list[ChatSessionSummary]:
        with self.session_factory() as session:
            rows = session.execute(
                select(ChatSessionRecord, func.count(ChatMessageRecord.id))
                .outerjoin(ChatMessageRecord)
                .group_by(ChatSessionRecord.id)
                .order_by(ChatSessionRecord.updated_at.desc())
            ).all()
            return [
                ChatSessionSummary(
                    id=record.id,
                    title=record.title,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    message_count=message_count,
                )
                for record, message_count in rows
            ]

    def get_session(self, session_id: str) -> ChatSessionDetail | None:
        with self.session_factory() as session:
            record = session.get(ChatSessionRecord, session_id)
            if record is None:
                return None
            messages = session.scalars(
                select(ChatMessageRecord)
                .where(ChatMessageRecord.session_id == session_id)
                .order_by(ChatMessageRecord.created_at)
            ).all()
            return ChatSessionDetail(
                id=record.id,
                title=record.title,
                created_at=record.created_at,
                updated_at=record.updated_at,
                message_count=len(messages),
                messages=[_message_to_summary(message) for message in messages],
            )

    def add_message(self, message: ChatMessageCreate) -> ChatMessageSummary:
        now = _utc_now()
        with self.session_factory() as session:
            parent = session.get(ChatSessionRecord, message.session_id)
            if parent is None:
                raise ValueError("Chat session not found.")
            record = ChatMessageRecord(
                id=uuid4().hex,
                session_id=message.session_id,
                role=message.role,
                content=message.content,
                created_at=now,
                top_k=message.top_k,
            )
            parent.updated_at = now
            session.add(record)
            session.commit()
            return _message_to_summary(record)

    def delete_session(self, session_id: str) -> bool:
        with self.session_factory() as session:
            record = session.get(ChatSessionRecord, session_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True


def _message_to_summary(record: ChatMessageRecord) -> ChatMessageSummary:
    return ChatMessageSummary(
        id=record.id,
        session_id=record.session_id,
        role=record.role,
        content=record.content,
        created_at=record.created_at,
        top_k=record.top_k,
    )


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
