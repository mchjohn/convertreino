from convertreino.infrastructure.tracing import MAX_ATTR_LENGTH, truncate_attr


def test_truncate_attr_keeps_short_strings() -> None:
    assert truncate_attr("hello") == "hello"


def test_truncate_attr_truncates_long_payloads() -> None:
    payload = {"key": "x" * MAX_ATTR_LENGTH}

    truncated = truncate_attr(payload)

    assert len(truncated) == MAX_ATTR_LENGTH
    assert truncated.endswith("...")
