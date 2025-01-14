from abc import ABC
from datetime import datetime
from types import NoneType
from typing import Optional
from uuid import UUID
from strawberry import type as strawberry_type


@strawberry_type
class IEcommerceUser(ABC):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = ""
    password: str
    disabled: bool = False
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "IEcommerceUser":
        raise NotImplementedError

    @staticmethod
    def get(id: UUID | NoneType = None) -> "IEcommerceUser":
        raise NotImplementedError


@strawberry_type
class IUserSession(ABC):
    session_token: str
    ecommerce_user_id: Optional[UUID] = None
    session_data: Optional[str] = None  # json
    expiration: datetime
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "IUserSession":
        raise NotImplementedError

    @staticmethod
    def get(id: UUID | NoneType = None) -> "IUserSession":
        raise NotImplementedError


@strawberry_type
class IPwdRestore(ABC):
    restore_token: str
    ecommerce_user_id: UUID
    expiration: datetime

    def new(self, *args) -> "IEcommerceUser":
        raise NotImplementedError

    @staticmethod
    def get(id: UUID | NoneType = None) -> "IEcommerceUser":
        raise NotImplementedError
