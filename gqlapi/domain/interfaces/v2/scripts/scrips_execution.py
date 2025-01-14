from abc import ABC, abstractmethod
import datetime
from types import NoneType
from typing import Optional
from uuid import UUID


class ScriptExecutionRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        id: UUID,
        status: Optional[str] = None,
        script_end: Optional[datetime.datetime] = None,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError
