import os
from collections import defaultdict
from dataclasses import dataclass, field

ACCURACY_THRESHOLD = 0.90
TEST_OPENAI_KEY = "test-openai-key"
TEST_GROQ_KEY = "test-groq-key"


@dataclass(frozen=True, slots=True)
class CaseOutcome:
    case_id: str
    passed: bool
    detail: str | None = None


@dataclass
class AccuracyCollector:
    outcomes: dict[str, list[CaseOutcome]] = field(default_factory=lambda: defaultdict(list))
    active: bool = False

    def reset(self) -> None:
        self.outcomes.clear()
        self.active = False

    def record(self, provider: str, outcome: CaseOutcome) -> None:
        self.active = True
        self.outcomes[provider].append(outcome)

    def report(self) -> list[str]:
        lines: list[str] = []
        for provider in sorted(self.outcomes):
            outcomes = self.outcomes[provider]
            passed = sum(1 for item in outcomes if item.passed)
            total = len(outcomes)
            pct = (passed / total * 100) if total else 0.0
            lines.append(f"Chat intent accuracy [{provider}]: {passed}/{total} ({pct:.1f}%)")
            failures = [item for item in outcomes if not item.passed]
            if failures:
                lines.append("Failures:")
                for item in failures:
                    lines.append(f"  - {item.case_id}: {item.detail}")
        return lines

    def below_threshold_providers(self) -> list[str]:
        failing: list[str] = []
        for provider, outcomes in self.outcomes.items():
            if not outcomes:
                continue
            passed = sum(1 for item in outcomes if item.passed)
            if passed / len(outcomes) < ACCURACY_THRESHOLD:
                failing.append(provider)
        return failing


accuracy_collector = AccuracyCollector()


def e2e_enabled() -> bool:
    return os.environ.get("E2E_LLM", "").strip() in {"1", "true", "yes", "on"}


def provider_api_key(provider: str) -> str:
    if provider == "openai":
        return os.environ.get("OPENAI_API_KEY", "")
    if provider == "groq":
        return os.environ.get("GROQ_API_KEY", "")
    raise ValueError(f"Unknown provider: {provider}")


def has_real_api_key(provider: str) -> bool:
    key = provider_api_key(provider)
    if not key:
        return False
    if provider == "openai" and key == TEST_OPENAI_KEY:
        return False
    if provider == "groq" and key == TEST_GROQ_KEY:
        return False
    return True


def active_llm_provider_filter() -> str | None:
    raw = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if raw in {"openai", "groq"}:
        return raw
    return None
