import os

import pytest

from convertreino.infrastructure.config import get_phoenix_settings


def test_phoenix_settings_default_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PHOENIX_ENABLED", raising=False)
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.delenv("PHOENIX_PROJECT_NAME", raising=False)

    settings = get_phoenix_settings()

    assert settings.enabled is False
    assert settings.collector_endpoint == "http://localhost:6006/v1/traces"
    assert settings.project_name == "convertreino-dev"


def test_phoenix_settings_enabled_when_env_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PHOENIX_ENABLED", "true")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://collector:6006/v1/traces")
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "my-project")
    monkeypatch.setattr("convertreino.infrastructure.config._is_test_runtime", lambda: False)

    settings = get_phoenix_settings()

    assert settings.enabled is True
    assert settings.collector_endpoint == "http://collector:6006/v1/traces"
    assert settings.project_name == "my-project"


@pytest.mark.parametrize("raw_value", ["TRUE", "Yes", "1", "on"])
def test_phoenix_settings_enabled_case_insensitive(
    monkeypatch: pytest.MonkeyPatch,
    raw_value: str,
) -> None:
    monkeypatch.setenv("PHOENIX_ENABLED", raw_value)
    monkeypatch.setattr("convertreino.infrastructure.config._is_test_runtime", lambda: False)

    settings = get_phoenix_settings()

    assert settings.enabled is True


def test_phoenix_settings_disabled_under_pytest_even_when_env_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PHOENIX_ENABLED", "true")

    settings = get_phoenix_settings()

    assert settings.enabled is False
    assert "pytest" in os.environ.get("PYTEST_CURRENT_TEST", "")
