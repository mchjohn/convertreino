import builtins

import pytest

from convertreino.infrastructure.config import PhoenixSettings
from convertreino.infrastructure.phoenix_tracing import setup_phoenix_tracing


@pytest.fixture(autouse=True)
def reset_phoenix_setup_state() -> None:
    import convertreino.infrastructure.phoenix_tracing as phoenix_tracing_module

    phoenix_tracing_module._setup_done = False
    yield
    phoenix_tracing_module._setup_done = False


def test_setup_phoenix_tracing_noop_when_disabled() -> None:
    settings = PhoenixSettings(
        enabled=False,
        collector_endpoint="http://localhost:6006/v1/traces",
        project_name="convertreino-dev",
    )

    assert setup_phoenix_tracing(settings) is False


def test_setup_phoenix_tracing_is_idempotent() -> None:
    settings = PhoenixSettings(
        enabled=False,
        collector_endpoint="http://localhost:6006/v1/traces",
        project_name="convertreino-dev",
    )

    assert setup_phoenix_tracing(settings) is False
    assert setup_phoenix_tracing(settings) is False


def test_setup_phoenix_tracing_warns_when_packages_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    settings = PhoenixSettings(
        enabled=True,
        collector_endpoint="http://localhost:6006/v1/traces",
        project_name="convertreino-dev",
    )

    original_import = builtins.__import__

    def _missing_import(name: str, *args: object, **kwargs: object) -> object:
        if name in {"phoenix.otel", "openinference.instrumentation.openai"}:
            raise ImportError("missing observability packages")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _missing_import)

    with caplog.at_level("WARNING"):
        assert setup_phoenix_tracing(settings) is False

    assert any(
        "observability packages are not installed" in record.message
        for record in caplog.records
    )
