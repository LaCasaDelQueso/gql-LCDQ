from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict
from uuid import UUID

from gqlapi.domain.models.v2.alima_business import AlimaUser


class AlimaUserRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        alima_user: AlimaUser,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        alima_user_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        alima_user_id: UUID,
    ) -> NoneType:
        raise NotImplementedError
