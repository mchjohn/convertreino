import pytest
from fastmcp.client import Client

from convertreino.infrastructure.repositories.sqlalchemy_activity_repository import (
    SqlAlchemyActivityRepository,
)
from convertreino.mcp.server import (
    _activity_repo_scope,
    create_mcp_app,
    create_mcp_server,
    set_activity_repo_factory,
)
from convertreino.mcp.tools.pr import GET_LONGEST_RIDE_DESCRIPTION, GET_LONGEST_RUN_DESCRIPTION


@pytest.fixture(autouse=True)
def reset_activity_repo_factory():
    set_activity_repo_factory(None)
    yield
    set_activity_repo_factory(None)


@pytest.mark.anyio
async def test_get_longest_run_tool_is_registered_with_boundary_description():
    # Arrange
    server = create_mcp_server()

    # Act
    async with Client(server) as client:
        tools = await client.list_tools()

    # Assert
    tool = next(tool for tool in tools if tool.name == "get_longest_run")
    assert tool.description is not None
    assert "corrida" in tool.description.lower()
    assert "get_longest_ride" in tool.description
    assert tool.description == GET_LONGEST_RUN_DESCRIPTION


@pytest.mark.anyio
async def test_get_longest_ride_tool_is_registered_with_boundary_description():
    # Arrange
    server = create_mcp_server()

    # Act
    async with Client(server) as client:
        tools = await client.list_tools()

    # Assert
    tool = next(tool for tool in tools if tool.name == "get_longest_ride")
    assert tool.description is not None
    assert "pedal" in tool.description.lower()
    assert "get_longest_run" in tool.description
    assert tool.description == GET_LONGEST_RIDE_DESCRIPTION


def test_create_mcp_app_returns_http_application():
    # Arrange / Act
    app = create_mcp_app()

    # Assert
    assert app is not None
    assert any(route.path == "/" for route in app.routes)


def test_activity_repo_scope_uses_sqlalchemy_when_factory_not_set(monkeypatch):
    # Arrange
    class FakeSession:
        def __init__(self) -> None:
            self.committed = False
            self.rolled_back = False
            self.closed = False

        def commit(self) -> None:
            self.committed = True

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    fake_session = FakeSession()
    monkeypatch.setattr(
        "convertreino.mcp.server.create_session_factory",
        lambda: (lambda: fake_session),
    )

    # Act
    with _activity_repo_scope() as repo:
        assert isinstance(repo, SqlAlchemyActivityRepository)

    # Assert
    assert fake_session.committed is True
    assert fake_session.closed is True


def test_activity_repo_scope_rolls_back_on_error(monkeypatch):
    # Arrange
    class FakeSession:
        def __init__(self) -> None:
            self.rolled_back = False
            self.closed = False

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            self.rolled_back = True

        def close(self) -> None:
            self.closed = True

    fake_session = FakeSession()
    monkeypatch.setattr(
        "convertreino.mcp.server.create_session_factory",
        lambda: (lambda: fake_session),
    )

    # Act / Assert
    with pytest.raises(RuntimeError, match="boom"):
        with _activity_repo_scope():
            raise RuntimeError("boom")

    assert fake_session.rolled_back is True
    assert fake_session.closed is True
