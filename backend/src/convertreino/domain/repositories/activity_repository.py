from abc import ABC, abstractmethod
from uuid import UUID

from convertreino.domain.entities.activity import Activity


class ActivityRepository(ABC):
    @abstractmethod
    def get_all(self, user_id: UUID) -> list[Activity]:
        ...

    @abstractmethod
    def save(self, activity: Activity) -> Activity:
        ...
