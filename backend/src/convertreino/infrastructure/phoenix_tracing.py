from __future__ import annotations

import logging

from convertreino.infrastructure.config import PhoenixSettings

logger = logging.getLogger(__name__)

_setup_done = False


def setup_phoenix_tracing(settings: PhoenixSettings) -> bool:
    global _setup_done
    if _setup_done:
        return settings.enabled
    _setup_done = True

    if not settings.enabled:
        return False

    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
        from phoenix.otel import register
    except ImportError:
        logger.warning(
            "PHOENIX_ENABLED=true but observability packages are not installed. "
            "Run: uv sync --extra observability --dev"
        )
        return False

    try:
        tracer_provider = register(
            project_name=settings.project_name,
            endpoint=settings.collector_endpoint,
        )
        OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception as exc:
        logger.warning("Failed to register Phoenix tracing: %s", exc)
        return False

    logger.info(
        "Phoenix tracing enabled (project=%s, endpoint=%s)",
        settings.project_name,
        settings.collector_endpoint,
    )
    return True
