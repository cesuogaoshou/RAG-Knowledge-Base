from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="indexed")


class ChatSessionRecord(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[str] = mapped_column(String, nullable=False)
    messages: Mapped[list["ChatMessageRecord"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class ChatMessageRecord(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, nullable=False)
    top_k: Mapped[int | None] = mapped_column(Integer, nullable=True)
    session: Mapped[ChatSessionRecord] = relationship(back_populates="messages")
    sources: Mapped[list["AnswerSourceRecord"]] = relationship(
        back_populates="message",
        cascade="all, delete-orphan",
    )


class AnswerSourceRecord(Base):
    __tablename__ = "answer_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(ForeignKey("chat_messages.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    page: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[ChatMessageRecord] = relationship(back_populates="sources")
