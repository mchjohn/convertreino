import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import convertreino.infrastructure.load_env  # noqa: F401

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://convertreino:convertreino@localhost:5432/convertreino"
)


def get_database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def create_session_factory(database_url: str | None = None) -> sessionmaker[Session]:
    engine = create_engine(database_url or get_database_url())
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
