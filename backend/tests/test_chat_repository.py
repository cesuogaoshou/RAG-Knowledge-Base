from pathlib import Path
from uuid import uuid4

from app.db.chat_repository import SQLChatRepository
from app.db.database import create_session_factory, initialize_database
from app.schemas.chat_history import ChatMessageCreate
from app.schemas.search import SearchResult


def _repository() -> SQLChatRepository:
    workspace = Path(".test-data") / f"chat-repo-{uuid4().hex}"
    workspace.mkdir(parents=True, exist_ok=True)
    session_factory = create_session_factory(f"sqlite:///{workspace / 'app.db'}")
    initialize_database(session_factory)
    return SQLChatRepository(session_factory)


def test_chat_repository_creates_session_and_messages() -> None:
    repository = _repository()

    session = repository.create_session(title="RAG 的回答来源如何展示？")
    repository.add_message(
        ChatMessageCreate(
            session_id=session.id,
            role="user",
            content="RAG 的回答来源如何展示？",
            top_k=3,
        )
    )
    repository.add_message(
        ChatMessageCreate(
            session_id=session.id,
            role="assistant",
            content="前端会展示答案和来源。",
            top_k=3,
        )
    )

    sessions = repository.list_sessions()
    loaded = repository.get_session(session.id)

    assert sessions[0].id == session.id
    assert sessions[0].title == "RAG 的回答来源如何展示？"
    assert sessions[0].message_count == 2
    assert loaded is not None
    assert [message.role for message in loaded.messages] == ["user", "assistant"]
    assert loaded.messages[1].content == "前端会展示答案和来源。"


def test_chat_repository_persists_answer_sources() -> None:
    repository = _repository()
    session = repository.create_session(title="RAG 的来源是什么？")
    repository.add_message(
        ChatMessageCreate(
            session_id=session.id,
            role="user",
            content="RAG 的来源是什么？",
            top_k=3,
        )
    )

    repository.add_message(
        ChatMessageCreate(
            session_id=session.id,
            role="assistant",
            content="答案来自 rag.md。",
            top_k=3,
        ),
        sources=[
            SearchResult(
                filename="rag.md",
                page=1,
                chunk_index=0,
                content="RAG answer source.",
                score=0.91,
            )
        ],
    )

    loaded = repository.get_session(session.id)

    assert loaded is not None
    assert loaded.messages[1].sources[0].filename == "rag.md"
    assert loaded.messages[1].sources[0].chunk_index == 0
    assert loaded.messages[1].sources[0].score == 0.91
