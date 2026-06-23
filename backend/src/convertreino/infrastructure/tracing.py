from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.trace import Span

TRACER_NAME = "convertreino"
MAX_ATTR_LENGTH = 4096


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(TRACER_NAME)


def truncate_attr(value: object, max_length: int = MAX_ATTR_LENGTH) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def set_span_attribute(span: Span, key: str, value: object) -> None:
    if value is None:
        return
    if isinstance(value, bool):
        span.set_attribute(key, value)
        return
    if isinstance(value, int):
        span.set_attribute(key, value)
        return
    if isinstance(value, float):
        span.set_attribute(key, value)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        span.set_attribute(key, tuple(str(item) for item in value))
        return
    if isinstance(value, (dict, list, tuple, set)):
        span.set_attribute(key, truncate_attr(value))
        return
    span.set_attribute(key, str(value))


@contextmanager
def start_span(name: str, **attributes: object) -> Iterator[Span]:
    tracer = get_tracer()
    with tracer.start_as_current_span(name) as span:
        for key, attr_value in attributes.items():
            set_span_attribute(span, key, attr_value)
        yield span
