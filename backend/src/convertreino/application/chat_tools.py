from datetime import datetime
from typing import Any
from uuid import UUID

from convertreino.application.llm.types import ToolDefinition
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.domain.services.pr_engine import PREngine
from convertreino.domain.services.volume_engine import VolumeEngine
from convertreino.infrastructure.tracing import set_span_attribute, start_span, truncate_attr
from convertreino.mcp.tools.pr import (
    GET_LONGEST_RIDE_DESCRIPTION,
    GET_LONGEST_RUN_DESCRIPTION,
    get_longest_ride,
    get_longest_run,
)
from convertreino.mcp.tools.volume import (
    GET_RIDE_VOLUME_DESCRIPTION,
    GET_RUN_VOLUME_DESCRIPTION,
    get_ride_volume,
    get_run_volume,
)

_DATE_PARAMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "start_date": {
            "type": "string",
            "description": "Data inicial em ISO 8601 UTC",
        },
        "end_date": {
            "type": "string",
            "description": "Data final em ISO 8601 UTC",
        },
    },
    "additionalProperties": False,
}

_TOOL_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("get_longest_run", GET_LONGEST_RUN_DESCRIPTION),
    ("get_longest_ride", GET_LONGEST_RIDE_DESCRIPTION),
    ("get_run_volume", GET_RUN_VOLUME_DESCRIPTION),
    ("get_ride_volume", GET_RIDE_VOLUME_DESCRIPTION),
)


class ChatToolRegistry:
    def __init__(self, activity_repo: ActivityRepository) -> None:
        self._activity_repo = activity_repo
        self._pr_engine = PREngine(activity_repo)
        self._volume_engine = VolumeEngine(activity_repo)

    def get_tool_definitions(self) -> list[ToolDefinition]:
        return [
            ToolDefinition(
                name=name,
                description=description,
                parameters=_DATE_PARAMS_SCHEMA,
            )
            for name, description in _TOOL_DEFINITIONS
        ]

    def execute(
        self,
        user_id: UUID,
        tool_name: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        with start_span(
            "chat.tool.execute",
            **{
                "tool.name": tool_name,
                "tool.arguments": truncate_attr(arguments),
            },
        ) as tool_span:
            result = self._execute_tool(user_id, tool_name, arguments)
            set_span_attribute(tool_span, "tool.result", truncate_attr(result))
            return result

    def _execute_tool(
        self,
        user_id: UUID,
        tool_name: str,
        arguments: dict[str, object],
    ) -> dict[str, object]:
        start_date = _parse_optional_date(arguments.get("start_date"))
        end_date = _parse_optional_date(arguments.get("end_date"))

        if tool_name == "get_longest_run":
            return get_longest_run(
                user_id,
                self._pr_engine,
                start_date=start_date,
                end_date=end_date,
            ).model_dump()
        if tool_name == "get_longest_ride":
            return get_longest_ride(
                user_id,
                self._pr_engine,
                start_date=start_date,
                end_date=end_date,
            ).model_dump()
        if tool_name == "get_run_volume":
            return get_run_volume(
                user_id,
                self._volume_engine,
                start_date=start_date,
                end_date=end_date,
            ).model_dump()
        if tool_name == "get_ride_volume":
            return get_ride_volume(
                user_id,
                self._volume_engine,
                start_date=start_date,
                end_date=end_date,
            ).model_dump()
        raise ValueError(f"Unknown tool: {tool_name}")


def _parse_optional_date(value: object | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)
