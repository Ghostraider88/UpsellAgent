"""Database engine, session factory and base model.

Uses a synchronous SQLAlchemy engine. The default SQLite URL keeps tests and
local runs dependency-free; production uses PostgreSQL via ``DATABASE_URL``.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped DB session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db() -> None:
    """Create all tables. Used for SQLite/dev; production uses Alembic."""
    from app import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
