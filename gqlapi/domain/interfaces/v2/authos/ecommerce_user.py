from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.authos.ecommerce_session import EcommerceSession

import strawberry
from gqlapi.domain.models.v2.authos import IEcommerceUser


@strawberry.type
class EcommerceUser(IEcommerceUser):
    ref_secret_key: str
    session: Optional[EcommerceSession] = None


@strawberry.type
class EcommerceUserError:
    msg: str
    code: int


@strawberry.type
class EcommerceUserMsg:
    ref_secret_key: str
    msg: str
    status: bool


EcommerceUserResult = strawberry.union(
    "EcommerceUserResult",
    (EcommerceUser, EcommerceUserError),
)

EcommerceUserGQLResult = strawberry.union(
    "EcommerceUserGQLResult",
    (IEcommerceUser, EcommerceUserError),
)

EcommerceUserMsgResult = strawberry.union(
    "EcommerceUserMsgResult",
    (EcommerceUserMsg, EcommerceUserError),
)


# handler interfaces
class EcommerceUserHandlerInterface(ABC):
    @abstractmethod
    async def login(
        self,
        email: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
        data: Dict[str, Any],
    ) -> EcommerceUser:
        raise NotImplementedError

    @abstractmethod
    async def is_logged(
        self,
        session_token: str,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def signup_email(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
        data: Dict[str, Any],
        business_name: Optional[str] = None,
    ) -> EcommerceUser:
        raise NotImplementedError

    @abstractmethod
    async def update_password(
        self,
        email: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def logout(
        self,
        session_token: str,
        data: Dict[str, Any],
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        id: UUID,
        ref_secret_key: str,
    ) -> EcommerceUser | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        id: UUID,
        session_token: str,
        data: Dict[str, Any],
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError


# Repository Interfaces
class EcommerceUserRepositoryInterface(ABC):
    @abstractmethod
    async def set_password(
        self,
        ecommerce_user_id: UUID,
        password: str,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        id: UUID,
        ref_secret_key: str,
    ) -> EcommerceUser | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch_by_email(
        self,
        email: str,
        ref_secret_key: str,
    ) -> EcommerceUser | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        ecommerce_user: IEcommerceUser,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        ecommerce_user: IEcommerceUser,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        id: UUID,
        ref_secret_key: str,
    ) -> bool:
        raise NotImplementedError
