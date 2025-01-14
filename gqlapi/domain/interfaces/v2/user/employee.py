from abc import ABC, abstractmethod
from types import NoneType
from typing import Dict, Any
from uuid import UUID

from gqlapi.domain.models.v2.core import RestaurantEmployeeInfo, SupplierEmployeeInfo
from gqlapi.lib.future.future.deprecation import deprecated


class EmployeeRepositoryInterface(ABC):
    @abstractmethod
    async def new_restaurant_employee(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def new_supplier_employee(
        self,
        core_element_collection: str,
        employee: SupplierEmployeeInfo,
    ) -> UUID:
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    async def get(
        self,
        core_element_collection: str,
        user_id_key: str,
        user_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        core_element_collection: str,
        user_id_key: str,
        user_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exist(
        self,
        core_element_collection: str,
        user_id_key: str,
        user_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    async def update(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo,
        user_id_key: str,
        user_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo | SupplierEmployeeInfo,
        user_id_key: str,
        user_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @deprecated("Use find() instead", "domain")
    @abstractmethod
    async def search(
        self,
        core_element_collection: str,
        core_element_name: str,
        query: Dict[Any, Any],
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
    ) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def upsert(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo | SupplierEmployeeInfo,
        user_id_key: str,
        user_id: UUID,
    ) -> bool:
        raise NotImplementedError
