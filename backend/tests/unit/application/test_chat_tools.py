import inspect
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from convertreino.application.chat_tools import ChatToolRegistry
from convertreino.domain.services.pr_engine import PREngine
from convertreino.domain.services.volume_engine import VolumeEngine
from convertreino.infrastructure.repositories.in_memory_activity_repository import (
    InMemoryActivityRepository,
)
from convertreino.mcp.tools.pr import GET_LONGEST_RUN_DESCRIPTION
from convertreino.mcp.tools.volume import GET_RUN_VOLUME_DESCRIPTION
from tests.builders import build_activity

USER_ID = UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
OTHER_USER_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def test_chat_tool_registry_execute_signature_matches_contract():
    # Arrange / Act
    signature = inspect.signature(ChatToolRegistry.execute)

    # Assert
    assert list(signature.parameters) == ["self", "user_id", "tool_name", "arguments"]


def test_tool_definitions_do_not_include_user_id():
    # Arrange
    registry = ChatToolRegistry(InMemoryActivityRepository([]))

    # Act
    definitions = registry.get_tool_definitions()

    # Assert
    assert len(definitions) == 4
    for definition in definitions:
        assert "user_id" not in definition.parameters.get("properties", {})
        assert definition.parameters.get("additionalProperties") is False


def test_tool_definitions_reuse_mcp_descriptions():
    # Arrange
    registry = ChatToolRegistry(InMemoryActivityRepository([]))

    # Act
    definitions = {tool.name: tool.description for tool in registry.get_tool_definitions()}

    # Assert
    assert definitions["get_longest_run"] == GET_LONGEST_RUN_DESCRIPTION
    assert definitions["get_run_volume"] == GET_RUN_VOLUME_DESCRIPTION


def test_execute_get_longest_run_uses_injected_user_id():
    # Arrange
    activity = build_activity(user_id=USER_ID, distance_meters=21097)
    other_activity = build_activity(user_id=OTHER_USER_ID, distance_meters=50000)
    registry = ChatToolRegistry(InMemoryActivityRepository([activity, other_activity]))

    # Act
    result = registry.execute(USER_ID, "get_longest_run", {})

    # Assert
    assert result["distance_km"] == 21.097
    assert result["activity_id"] == str(activity.id)


def test_execute_get_run_volume_passes_dates_to_volume_engine():
    # Arrange
    activity = build_activity(
        user_id=USER_ID,
        distance_meters=10000,
        start_date=datetime(2024, 6, 1, 8, 0, 0, tzinfo=UTC),
    )
    registry = ChatToolRegistry(InMemoryActivityRepository([activity]))

    # Act
    result = registry.execute(
        USER_ID,
        "get_run_volume",
        {
            "start_date": "2024-06-01T00:00:00+00:00",
            "end_date": "2024-06-30T23:59:59+00:00",
        },
    )

    # Assert
    assert result["total_distance_km"] == 10.0
    assert result["activities_count"] == 1


def test_execute_unknown_tool_raises_value_error():
    # Arrange
    registry = ChatToolRegistry(InMemoryActivityRepository([]))

    # Act / Assert
    with pytest.raises(ValueError, match="Unknown tool"):
        registry.execute(USER_ID, "unknown_tool", {})


def test_execute_ignores_spurious_user_id_argument():
    # Arrange — CB-4
    activity = build_activity(user_id=USER_ID, distance_meters=12000)
    registry = ChatToolRegistry(InMemoryActivityRepository([activity]))

    # Act
    result = registry.execute(
        USER_ID,
        "get_longest_run",
        {"user_id": str(uuid4()), "extra": "ignored"},
    )

    # Assert
    assert result["distance_km"] == 12.0


def test_registry_uses_pr_and_volume_engines_with_activity_repository():
    # Arrange
    repo = InMemoryActivityRepository([build_activity(user_id=USER_ID)])
    registry = ChatToolRegistry(repo)

    # Act
    longest = registry.execute(USER_ID, "get_longest_run", {})
    volume = registry.execute(USER_ID, "get_run_volume", {})

    # Assert
    assert longest["activity_id"] is not None
    assert volume["activities_count"] == 1
    assert isinstance(PREngine(repo).get_longest_run(USER_ID), object)
    assert isinstance(VolumeEngine(repo).get_run_volume(USER_ID).activities_count, int)
