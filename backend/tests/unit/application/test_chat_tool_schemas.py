import json

from convertreino.application.llm.chat_tool_schemas import (
    CHAT_DATE_PARAMS_SCHEMA,
    CHAT_GET_LONGEST_RIDE_DESCRIPTION,
    CHAT_GET_LONGEST_RUN_DESCRIPTION,
    CHAT_GET_RIDE_VOLUME_DESCRIPTION,
    CHAT_GET_RUN_VOLUME_DESCRIPTION,
    get_chat_tool_definitions,
    serialize_chat_tools_payload,
)
from convertreino.mcp.tools.pr import GET_LONGEST_RIDE_DESCRIPTION, GET_LONGEST_RUN_DESCRIPTION
from convertreino.mcp.tools.volume import GET_RIDE_VOLUME_DESCRIPTION, GET_RUN_VOLUME_DESCRIPTION

CHAT_DESCRIPTIONS = (
    CHAT_GET_LONGEST_RUN_DESCRIPTION,
    CHAT_GET_LONGEST_RIDE_DESCRIPTION,
    CHAT_GET_RUN_VOLUME_DESCRIPTION,
    CHAT_GET_RIDE_VOLUME_DESCRIPTION,
)

MCP_DESCRIPTIONS = (
    GET_LONGEST_RUN_DESCRIPTION,
    GET_LONGEST_RIDE_DESCRIPTION,
    GET_RUN_VOLUME_DESCRIPTION,
    GET_RIDE_VOLUME_DESCRIPTION,
)

MAX_TOTAL_DESCRIPTION_CHARS = 800
MAX_SCHEMA_JSON_CHARS = 121
MAX_TOOLS_PAYLOAD_CHARS = 1000


def test_chat_descriptions_differ_from_mcp_descriptions():
    # Arrange
    definitions = {tool.name: tool.description for tool in get_chat_tool_definitions()}

    # Assert
    assert definitions["get_longest_run"] == CHAT_GET_LONGEST_RUN_DESCRIPTION
    assert definitions["get_longest_run"] != GET_LONGEST_RUN_DESCRIPTION
    assert definitions["get_longest_ride"] == CHAT_GET_LONGEST_RIDE_DESCRIPTION
    assert definitions["get_longest_ride"] != GET_LONGEST_RIDE_DESCRIPTION
    assert definitions["get_run_volume"] == CHAT_GET_RUN_VOLUME_DESCRIPTION
    assert definitions["get_run_volume"] != GET_RUN_VOLUME_DESCRIPTION
    assert definitions["get_ride_volume"] == CHAT_GET_RIDE_VOLUME_DESCRIPTION
    assert definitions["get_ride_volume"] != GET_RIDE_VOLUME_DESCRIPTION
    assert set(CHAT_DESCRIPTIONS).isdisjoint(set(MCP_DESCRIPTIONS))


def test_chat_descriptions_preserve_sport_type_and_record_vs_volume():
    # Arrange
    definitions = {tool.name: tool.description for tool in get_chat_tool_definitions()}

    # Assert
    assert "Run" in definitions["get_longest_run"]
    assert "recorde" in definitions["get_longest_run"].lower() or "maior distância" in definitions["get_longest_run"]
    assert "Ride" in definitions["get_longest_ride"]
    assert "Run" in definitions["get_run_volume"]
    assert "volume agregado" in definitions["get_run_volume"].lower()
    assert "Ride" in definitions["get_ride_volume"]
    assert "volume agregado" in definitions["get_ride_volume"].lower()


def test_chat_descriptions_state_sibling_tool_boundaries():
    # Arrange
    definitions = {tool.name: tool.description for tool in get_chat_tool_definitions()}

    # Assert
    assert "volume agregado" in definitions["get_longest_run"].lower()
    assert "Ride" in definitions["get_longest_run"]
    assert "Run" in definitions["get_longest_ride"]
    assert "volume agregado" in definitions["get_longest_ride"].lower()
    assert "recorde individual" in definitions["get_run_volume"].lower()
    assert "Ride" in definitions["get_run_volume"]
    assert "recorde individual" in definitions["get_ride_volume"].lower()
    assert "Run" in definitions["get_ride_volume"]


def test_chat_date_params_schema_is_minified_without_user_id():
    # Assert
    assert CHAT_DATE_PARAMS_SCHEMA["additionalProperties"] is False
    assert set(CHAT_DATE_PARAMS_SCHEMA["properties"]) == {"start_date", "end_date"}
    assert CHAT_DATE_PARAMS_SCHEMA["properties"]["start_date"] == {"type": "string"}
    assert CHAT_DATE_PARAMS_SCHEMA["properties"]["end_date"] == {"type": "string"}
    assert "user_id" not in CHAT_DATE_PARAMS_SCHEMA["properties"]
    assert "description" not in CHAT_DATE_PARAMS_SCHEMA["properties"]["start_date"]


def test_chat_tool_payload_respects_character_ceilings():
    # Arrange
    definitions = get_chat_tool_definitions()
    descriptions_total = sum(len(description) for description in CHAT_DESCRIPTIONS)
    schema_json = json.dumps(CHAT_DATE_PARAMS_SCHEMA, separators=(",", ":"), ensure_ascii=False)
    payload = serialize_chat_tools_payload(definitions)

    # Assert
    assert descriptions_total <= MAX_TOTAL_DESCRIPTION_CHARS
    assert len(schema_json) <= MAX_SCHEMA_JSON_CHARS
    assert len(payload) <= MAX_TOOLS_PAYLOAD_CHARS
