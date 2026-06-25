import os

import pytest

from tests.e2e.accuracy import (
    ACCURACY_THRESHOLD,
    AccuracyCollector,
    accuracy_collector,
    e2e_enabled,
)


@pytest.fixture
def collector() -> AccuracyCollector:
    return accuracy_collector


def pytest_sessionstart(session: pytest.Session) -> None:
    accuracy_collector.reset()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if e2e_enabled():
        return
    skip_marker = pytest.mark.skip(
        reason="Defina E2E_LLM=1 e a API key do provider para rodar testes E2E com LLM real",
    )
    for item in items:
        if item.get_closest_marker("e2e"):
            item.add_marker(skip_marker)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not accuracy_collector.active:
        return

    for line in accuracy_collector.report():
        print(line)

    results_json = os.environ.get("E2E_RESULTS_JSON")
    if results_json:
        accuracy_collector.export_results_json(results_json)

    failing = accuracy_collector.below_threshold_providers()
    if failing:
        providers = ", ".join(failing)
        threshold_pct = int(ACCURACY_THRESHOLD * 100)
        print(f"Accuracy below {threshold_pct}% threshold for: {providers}")
        session.exitstatus = 1
