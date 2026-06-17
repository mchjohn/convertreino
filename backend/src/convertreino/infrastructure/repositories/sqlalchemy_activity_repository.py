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

    def get_by_external_id(self, user_id: UUID, external_id: str) -> Activity | None:
        stmt = select(ActivityModel).where(
            ActivityModel.user_id == user_id,
            ActivityModel.external_id == external_id,
        )
        model = self._session.scalar(stmt)
        return _to_domain(model) if model is not None else None

    def upsert(self, activity: Activity) -> Activity:
        if activity.external_id is None:
            return self.save(activity)

        existing = self.get_by_external_id(activity.user_id, activity.external_id)
        if existing is not None:
            stmt = select(ActivityModel).where(ActivityModel.id == existing.id)
            model = self._session.scalar(stmt)
            if model is None:
                raise DomainIntegrityError(
                    f"Activity with external_id {activity.external_id} disappeared during upsert"
                )
            model.distance_meters = activity.distance_meters
            model.elapsed_time_seconds = activity.elapsed_time_seconds
            model.start_date = activity.start_date
            model.activity_type = activity.activity_type
            try:
                self._session.flush()
            except IntegrityError as exc:
                raise DomainIntegrityError(
                    f"Cannot upsert activity for user_id: {activity.user_id}"
                ) from exc
            return Activity(
                id=existing.id,
                user_id=activity.user_id,
                distance_meters=activity.distance_meters,
                elapsed_time_seconds=activity.elapsed_time_seconds,
                start_date=activity.start_date,
                activity_type=activity.activity_type,
                external_id=activity.external_id,
            )

        return self.save(activity)

    def delete_by_external_id(self, user_id: UUID, external_id: str) -> bool:
        stmt = select(ActivityModel).where(
            ActivityModel.user_id == user_id,
            ActivityModel.external_id == external_id,
        )
        model = self._session.scalar(stmt)
        if model is None:
            return False
        self._session.delete(model)
        self._session.flush()
        return True
