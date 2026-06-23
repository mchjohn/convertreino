import os
from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from convertreino.api.main import create_app
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.infrastructure.db.models import Base
from convertreino.infrastructure.repositories.sqlalchemy_activity_repository import (
    SqlAlchemyActivityRepository,
)
from convertreino.infrastructure.repositories.sqlalchemy_user_repository import (
    SqlAlchemyUserRepository,
)
from tests.builders import build_activity, build_user

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://convertreino:convertreino@localhost:5432/convertreino_test",
)


def _postgres_available() -> bool:
    try:
        engine = create_engine(TEST_DATABASE_URL)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def db_session() -> Generator[Session, None, None]:
    if not _postgres_available():
        pytest.skip("PostgreSQL not available for integration tests")

    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_sql_get_all_returns_two_activities(db_session: Session):
    # Arrange
    user_repo = SqlAlchemyUserRepository(db_session)
    activity_repo = SqlAlchemyActivityRepository(db_session)
    user = build_user()
    user_repo.save(user)
    activity_repo.save(build_activity(user_id=user.id, distance_meters=5000))
    activity_repo.save(build_activity(user_id=user.id, distance_meters=10000))

    # Act
    result = activity_repo.get_all(user.id)

    # Assert
    assert len(result) == 2
    assert {activity.distance_meters for activity in result} == {5000.0, 10000.0}


def test_sql_save_activity_fails_for_unknown_user(db_session: Session):
    # Arrange
    activity_repo = SqlAlchemyActivityRepository(db_session)
    activity = build_activity(user_id=uuid4())

    # Act / Assert
    with pytest.raises(DomainIntegrityError, match="unknown user_id"):
        activity_repo.save(activity)


def test_health_endpoint_returns_ok():
    # Arrange
    client = TestClient(create_app())

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
