from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from types import NoneType
from typing import Any, Dict

import strawberry
from gqlapi.domain.models.v2.authos import IPwdRestore


@strawberry.type
class EcommercePassword(IPwdRestore):
    ref_secret_key: str
    status: bool
    msg: str


@strawberry.type
class EcommercePasswordError:
    msg: str
    code: int


@strawberry.type
class EcommercePasswordResetMsg:
    ref_secret_key: str
    msg: str
    status: bool


EcommercePasswordResult = strawberry.union(
    "EcommercePasswordResult",
    (EcommercePassword, EcommercePasswordError),
)

EcommercePasswordResetResult = strawberry.union(
    "EcommercePasswordResetResult",
    (EcommercePasswordResetMsg, EcommercePasswordError),
)


# handler interfaces
class EcommercePasswordHandlerInterface(ABC):
    @abstractmethod
    async def create_restore_token(
        self,
        email: str,
        ref_secret_key: str,
        expires_delta: timedelta = timedelta(hours=48),
    ) -> EcommercePassword:
        raise NotImplementedError

    @abstractmethod
    async def is_restore_token_valid(
        self,
        restore_token: str,
        ref_secret_key: str,
        with_expiration: bool = True,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def reset_password(
        self,
        password: str,
        restore_token: str,
        ref_secret_key: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError


# Repository Interfaces
class PwdRestoreRepositoryInterface(ABC):
    @abstractmethod
    async def delete_pwd_restore(
        self,
        email: str,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_pwd_restore(
        self,
        pwd_restore: IPwdRestore,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_pwd_restore(
        self,
        restore_token: str,
        ref_secret_key: str,
        expires_after: datetime = datetime.utcnow(),
    ) -> IPwdRestore | NoneType:
        raise NotImplementedError
