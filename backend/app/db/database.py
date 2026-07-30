from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base


def create_session_factory(database_url: str) -> sessionmaker[Session]:
    _ensure_sqlite_parent_directory(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def initialize_database(session_factory: sessionmaker[Session]) -> None:
    engine = session_factory.kw["bind"]
    Base.metadata.create_all(bind=engine)
    _ensure_document_status_column(engine)


def _ensure_sqlite_parent_directory(database_url: str) -> None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        return
    Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def _ensure_document_status_column(engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("documents"):
        return

    column_names = {column["name"] for column in inspector.get_columns("documents")}
    if "status" in column_names:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE documents ADD COLUMN status VARCHAR NOT NULL DEFAULT 'indexed'"))
