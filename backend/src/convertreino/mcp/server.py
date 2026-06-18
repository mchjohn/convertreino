from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.server.http import StarletteWithLifespan

from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.services.pr_engine import PREngine
from convertreino.infrastructure.db.session import create_session_factory
from convertreino.infrastructure.repositories.sqlalchemy_activity_repository import (
    SqlAlchemyActivityRepository,
)
from convertreino.mcp.tools.pr import GET_LONGEST_RUN_DESCRIPTION, get_longest_run

_activity_repo_factory: Callable[[], ActivityRepository] | None = None


def set_activity_repo_factory(factory: Callable[[], ActivityRepository] | None) -> None:
    global _activity_repo_factory
    _activity_repo_factory = factory


@contextmanager
def _activity_repo_scope() -> Generator[ActivityRepository, None, None]:
    if _activity_repo_factory is not None:
        yield _activity_repo_factory()
        return

    session_factory = create_session_factory()
    session = session_factory()
    try:
        yield SqlAlchemyActivityRepository(session)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_mcp_server() -> FastMCP:
    mcp = FastMCP("ConverTreino")

    @mcp.tool(name="get_longest_run", description=GET_LONGEST_RUN_DESCRIPTION)
    def get_longest_run_tool(user_id: UUID) -> dict[str, Any]:
        with _activity_repo_scope() as activity_repo:
            result = get_longest_run(user_id, PREngine(activity_repo))
        return result.model_dump()

    return mcp


def create_mcp_app() -> StarletteWithLifespan:
    return create_mcp_server().http_app(path="/")
