from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from types import NoneType
from typing import Any, Dict, Optional
from uuid import UUID

import strawberry
from gqlapi.domain.models.v2.authos import IUserSession


@strawberry.type
class EcommerceSession(IUserSession):
    ref_secret_key: str
    status: bool
    msg: str


@strawberry.type
class EcommerceSessionError:
    msg: str
    code: int


EcommerceSessionResult = strawberry.union(
    "EcommerceSessionResult",
    (EcommerceSession, EcommerceSessionError),
)


# handler interfaces
class AuthosTokenHandlerInterface(ABC):
    @abstractmethod
    async def verify_token(
        self,
        session_token: str,
        ref_secret_key: str,
        with_expiration: bool = True,
    ) -> Dict[str, Any]:
        raise NotImplementedError


class EcommerceSessionHandlerInterface(ABC):
    @abstractmethod
    async def get_session_token(
        self,
        session_token: str,
        data: Dict[str, Any],
        ref_secret_key: str,
        refresh: bool = False,
    ) -> EcommerceSession:
        raise NotImplementedError

    @abstractmethod
    async def is_session_valid(
        self,
        session_token: str,
        ref_secret_key: str,
        with_expiration: bool = True,
    ) -> EcommerceSession | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def is_token_expired(
        self,
        session_token: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def create_session_token(
        self,
        data: Dict[str, Any],
        ref_secret_key: str,
        expires_delta: timedelta = timedelta(hours=48),
        ecommerce_user_id: Optional[UUID] = None,
    ) -> EcommerceSession:
        raise NotImplementedError

    @abstractmethod
    async def set_login_session_token(
        self,
        session_token: str,
        ecommerce_user_id: UUID,
        data: Dict[str, Any],
        ref_secret_key: str,
        expires_delta: timedelta = timedelta(hours=48),
    ) -> EcommerceSession:
        raise NotImplementedError

    @abstractmethod
    async def set_logout_session_token(
        self,
        session_token: str,
        ref_secret_key: str,
        data: Dict[str, Any],
    ) -> EcommerceSession:
        raise NotImplementedError


# Repository Interfaces
class UserSessionRepositoryInterface(ABC):
    @abstractmethod
    async def fetch_session(
        self,
        session_token: str,
        ref_secret_key: str,
        expires_after: datetime = datetime.utcnow(),
    ) -> IUserSession | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def create_session(
        self,
        session: IUserSession,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update_session(
        self,
        session: IUserSession,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def clear_session(
        self,
        session_token: str,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError
