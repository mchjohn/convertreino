from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

import yaml

from convertreino.domain.entities.activity import Activity
from tests.builders import build_activity

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chat_intent_matrix.yaml"


@dataclass(frozen=True, slots=True)
class IntentCase:
    id: str
    question: str
    expected_tools: tuple[str, ...]
    boundary: str


@dataclass(frozen=True, slots=True)
class IntentMatrixSeed:
    user_id: UUID
    activities: tuple[Activity, ...]


@dataclass(frozen=True, slots=True)
class IntentMatrix:
    version: int
    seed: IntentMatrixSeed
    cases: tuple[IntentCase, ...]


def _parse_start_date(raw: str) -> datetime:
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def load_intent_matrix(path: Path = FIXTURE_PATH) -> tuple[IntentCase, ...]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    user_id = UUID(data["seed"]["user_id"])
    activities = tuple(
        build_activity(
            user_id=user_id,
            activity_type=item["activity_type"],
            distance_meters=item["distance_meters"],
            start_date=_parse_start_date(item["start_date"]),
        )
        for item in data["seed"]["activities"]
    )
    seed = IntentMatrixSeed(user_id=user_id, activities=activities)
    cases = tuple(
        IntentCase(
            id=item["id"],
            question=item["question"],
            expected_tools=tuple(item["expected_tools"]),
            boundary=item["boundary"],
        )
        for item in data["cases"]
    )
    matrix = IntentMatrix(version=data["version"], seed=seed, cases=cases)
    return matrix.cases


def load_intent_matrix_seed(path: Path = FIXTURE_PATH) -> IntentMatrixSeed:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    user_id = UUID(data["seed"]["user_id"])
    activities = tuple(
        build_activity(
            user_id=user_id,
            activity_type=item["activity_type"],
            distance_meters=item["distance_meters"],
            start_date=_parse_start_date(item["start_date"]),
        )
        for item in data["seed"]["activities"]
    )
    return IntentMatrixSeed(user_id=user_id, activities=activities)
