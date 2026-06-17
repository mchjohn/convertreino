from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from convertreino.domain.entities.activity import Activity
from convertreino.domain.exceptions import DomainIntegrityError
from convertreino.domain.repositories.activity_repository import ActivityRepository
from convertreino.infrastructure.db.models import ActivityModel


def _to_domain(model: ActivityModel) -> Activity:
    return Activity(
        id=model.id,
        user_id=model.user_id,
        distance_meters=model.distance_meters,
        elapsed_time_seconds=model.elapsed_time_seconds,
        start_date=model.start_date,
        activity_type=model.activity_type,
        external_id=model.external_id,
    )


def _to_model(activity: Activity) -> ActivityModel:
    return ActivityModel(
        id=activity.id,
        user_id=activity.user_id,
        distance_meters=activity.distance_meters,
        elapsed_time_seconds=activity.elapsed_time_seconds,
        start_date=activity.start_date,
        activity_type=activity.activity_type,
        external_id=activity.external_id,
    )


class SqlAlchemyActivityRepository(ActivityRepository):
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_all(self, user_id: UUID) -> list[Activity]:
        stmt = select(ActivityModel).where(ActivityModel.user_id == user_id)
        models = self._session.scalars(stmt).all()
        return [_to_domain(model) for model in models]

    def save(self, activity: Activity) -> Activity:
        self._session.add(_to_model(activity))
        try:
            self._session.flush()
        except IntegrityError as exc:
            raise DomainIntegrityError(
                f"Cannot save activity for unknown user_id: {activity.user_id}"
            ) from exc
        return activity
