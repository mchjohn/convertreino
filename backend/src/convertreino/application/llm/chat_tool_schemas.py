import json
from typing import Any

from convertreino.application.llm.types import ToolDefinition

CHAT_GET_LONGEST_RUN_DESCRIPTION = (
    "Recorde Run: maior distância. Datas UTC opc. Não Ride/volume agregado."
)

CHAT_GET_LONGEST_RIDE_DESCRIPTION = (
    "Recorde Ride: maior distância. Datas UTC opc. Não Run/volume agregado."
)

CHAT_GET_RUN_VOLUME_DESCRIPTION = (
    "Volume agregado Run. Datas UTC opc. Não recorde individual/Ride."
)

CHAT_GET_RIDE_VOLUME_DESCRIPTION = (
    "Volume agregado Ride. Datas UTC opc. Não recorde individual/Run."
)

CHAT_DATE_PARAMS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "start_date": {"type": "string"},
        "end_date": {"type": "string"},
    },
    "additionalProperties": False,
}

_CHAT_TOOL_SPECS: tuple[tuple[str, str], ...] = (
    ("get_longest_run", CHAT_GET_LONGEST_RUN_DESCRIPTION),
    ("get_longest_ride", CHAT_GET_LONGEST_RIDE_DESCRIPTION),
    ("get_run_volume", CHAT_GET_RUN_VOLUME_DESCRIPTION),
    ("get_ride_volume", CHAT_GET_RIDE_VOLUME_DESCRIPTION),
)


def get_chat_tool_definitions() -> list[ToolDefinition]:
    return [
        ToolDefinition(
            name=name,
            description=description,
            parameters=CHAT_DATE_PARAMS_SCHEMA,
        )
        for name, description in _CHAT_TOOL_SPECS
    ]


def serialize_chat_tools_payload(definitions: list[ToolDefinition]) -> str:
    payload = [
        {
            "name": definition.name,
            "description": definition.description,
            "parameters": definition.parameters,
        }
        for definition in definitions
    ]
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
