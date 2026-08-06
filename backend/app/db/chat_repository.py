from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import AnswerSourceRecord, ChatMessageRecord, ChatSessionRecord
from app.schemas.chat_history import (
    AnswerSourceSummary,
    ChatMessageCreate,
    ChatMessageSummary,
    ChatSessionDetail,
    ChatSessionSummary,
)
from app.schemas.search import SearchResult


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
            sources_by_message_id = _load_sources_by_message_id(session, [message.id for message in messages])
            return ChatSessionDetail(
                id=record.id,
                title=record.title,
                created_at=record.created_at,
                updated_at=record.updated_at,
                message_count=len(messages),
                messages=[
                    _message_to_summary(message, sources=sources_by_message_id.get(message.id, []))
                    for message in messages
                ],
            )

    def add_message(
        self,
        message: ChatMessageCreate,
        sources: list[SearchResult] | None = None,
    ) -> ChatMessageSummary:
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
            source_records = [
                AnswerSourceRecord(
                    id=uuid4().hex,
                    message_id=record.id,
                    filename=source.filename,
                    page=source.page,
                    chunk_index=source.chunk_index,
                    content=source.content,
                    score=source.score,
                )
                for source in (sources or [])
            ]
            session.add_all(source_records)
            session.commit()
            return _message_to_summary(record, sources=source_records)

    def delete_session(self, session_id: str) -> bool:
        with self.session_factory() as session:
            record = session.get(ChatSessionRecord, session_id)
            if record is None:
                return False
            session.delete(record)
            session.commit()
            return True


def _message_to_summary(
    record: ChatMessageRecord,
    sources: list[AnswerSourceRecord] | None = None,
) -> ChatMessageSummary:
    return ChatMessageSummary(
        id=record.id,
        session_id=record.session_id,
        role=record.role,
        content=record.content,
        created_at=record.created_at,
        top_k=record.top_k,
        sources=[_source_to_summary(source) for source in (sources or [])],
    )


def _source_to_summary(record: AnswerSourceRecord) -> AnswerSourceSummary:
    return AnswerSourceSummary(
        id=record.id,
        message_id=record.message_id,
        filename=record.filename,
        page=record.page,
        chunk_index=record.chunk_index,
        content=record.content,
        score=record.score,
    )


def _load_sources_by_message_id(
    session: Session,
    message_ids: list[str],
) -> dict[str, list[AnswerSourceRecord]]:
    if not message_ids:
        return {}
    sources = session.scalars(
        select(AnswerSourceRecord)
        .where(AnswerSourceRecord.message_id.in_(message_ids))
        .order_by(AnswerSourceRecord.page, AnswerSourceRecord.chunk_index)
    ).all()
    grouped: dict[str, list[AnswerSourceRecord]] = {}
    for source in sources:
        grouped.setdefault(source.message_id, []).append(source)
    return grouped


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
