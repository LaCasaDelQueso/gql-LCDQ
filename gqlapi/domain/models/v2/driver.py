from abc import ABC
from types import NoneType
from uuid import UUID
from datetime import datetime

from strawberry import type as strawberry_type

from gqlapi.domain.models.v2 import (
    DriverStatusType,
    DeliveryStatusType
)


@strawberry_type
class DriverUser(ABC):
    id: UUID
    user_id: UUID
    enabled: bool
    deleted: bool
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> 'DriverUser':
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> 'DriverUser':
        raise NotImplementedError


# [TO-REV] To review implementation
@strawberry_type
class DriverInfo(ABC):
    driver_id: UUID

    def new(self, *args) -> 'DriverInfo':
        raise NotImplementedError

    def get(self, driver_id: UUID | NoneType = None) -> 'DriverInfo':
        raise NotImplementedError


@strawberry_type
class DriverStatus(ABC):
    id: UUID
    driver_user_id: UUID
    status: DriverStatusType
    created_at: datetime

    def new(self, *args) -> 'DriverStatus':
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> 'DriverStatus':
        raise NotImplementedError


@strawberry_type
class DriverNotifications(ABC):
    id: UUID
    driver_user_id: UUID
    notify_new_delivery_route: bool
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> 'DriverNotifications':
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> 'DriverNotifications':
        raise NotImplementedError


@strawberry_type
class DriverOrdenStatus(ABC):
    orden_id: UUID
    driver_user_id: UUID
    status: DeliveryStatusType
    created_at: datetime

    def new(self, *args) -> 'DriverOrdenStatus':
        raise NotImplementedError

    def get(self,
            orden_id: UUID | NoneType = None,
            driver_id: UUID | NoneType = None,
            status: DeliveryStatusType | NoneType = None
            ) -> 'DriverOrdenStatus':
        raise NotImplementedError
