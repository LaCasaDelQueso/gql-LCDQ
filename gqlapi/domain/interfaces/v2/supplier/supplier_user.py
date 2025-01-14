from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import PermissionDictInput

import strawberry

from gqlapi.domain.models.v2.core import (
    CoreUser,
    SupplierEmployeeInfo,
    SupplierEmployeeInfoPermission,
)
from gqlapi.domain.models.v2.supplier import SupplierUser, SupplierUserPermission


@strawberry.input
class SupplierEmployeeInfoPermissionInput(SupplierEmployeeInfoPermission):
    permissions: Optional[List[PermissionDictInput]] = None


@strawberry.input
class SupplierDisplayPermissionsInput:
    display_sales_section: Optional[bool] = None
    display_routes_section: Optional[bool] = None


# GraphQL Schema Error Types
@strawberry.type
class SupplierUserError:
    msg: str
    code: int


# GraphQL Schema Result Types
@strawberry.type
class SupplierUserGQL(SupplierUser):
    user: Optional[CoreUser] = None


@strawberry.type
class SupplierUserEmployeeGQL:
    supplier_user: Optional[SupplierUserGQL] = None
    employee: Optional[SupplierEmployeeInfo] = None
    permission: Optional[SupplierUserPermission] = None


@strawberry.type
class SupplierUserStatus:
    enabled: Optional[bool] = None
    deleted: Optional[bool] = None


SupplierUserResult = strawberry.union(
    "SupplierUserResult",
    (
        SupplierUserGQL,
        SupplierUserError,
    ),
)

SupplierUserEmployeeGQLResult = strawberry.union(
    "SupplierUserEmployeeGQLResult",
    (SupplierUserEmployeeGQL, SupplierUserError),
)

SupplierUserStatusResult = strawberry.union(
    "SupplierUserStatusResult",
    (
        SupplierUserStatus,
        SupplierUserError,
    ),
)


# Handler Interfaces
class SupplierUserHandlerInterface(ABC):
    @abstractmethod
    async def new_supplier_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> SupplierUserGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_user(
        self,
        supplier_user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
    ) -> SupplierUserGQL:
        raise NotImplementedError

    @abstractmethod
    async def erase_supplier_user(self, supplier_user_id: UUID, deleted: bool) -> bool:
        raise NotImplementedError

    # @abstractmethod
    # async def change_supplier_user_status(
    #     self, supplier_user_id: UUID, enabled: bool
    # ) -> bool:
    #     raise NotImplementedError

    # @abstractmethod
    # async def fetch_supplier_user(self, supplier_user_id: UUID) -> SupplierUserGQL:
    #     raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_user_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierUserGQL:
        raise NotImplementedError


class SupplierUserPermissionHandlerInterface(ABC):
    @abstractmethod
    async def fetch_supplier_user_contact_and_permission(
        self,
        firebase_id: str,
    ) -> SupplierUserEmployeeGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_user_permission(
        self, firebase_id: str
    ) -> SupplierUserPermission:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_users_contact_and_permission_from_business(
        self,
        supplier_business_id: UUID,
    ) -> List[SupplierUserEmployeeGQL]:
        raise NotImplementedError


class SupplierEmployeeHandlerInterface(ABC):
    @abstractmethod
    async def new_supplier_employee(
        self,
        supplier_business_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        position: str,
        display_perms: Dict[str, bool],
        department: Optional[str] = None,
        permission: Optional[List[SupplierEmployeeInfoPermission]] = None,
    ) -> SupplierUserEmployeeGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_employee(
        self,
        supplier_business_id: UUID,
        supplier_user_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        display_perms: Optional[Dict[str, bool]] = None,
        permission: Optional[List[SupplierEmployeeInfoPermission]] = None,
    ) -> SupplierUserPermission:
        raise NotImplementedError


# Repository Interfaces
class SupplierUserRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        core_user_id: UUID,
        role: str,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        core_user_id: UUID,
        role: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, core_user_id: UUID) -> Dict[Any, Any] | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def activate_desactivate(self, core_user_id: UUID, enabled: bool) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, core_user_id: UUID, deleted: bool) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        supplier_user_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(
        self, supplier_user_id: UUID
    ) -> Sequence | Dict[Any, Any] | NoneType:
        raise NotImplementedError


class SupplierUserPermissionRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        supplier_user_id: UUID,
        supplier_business_id: UUID,
        display_sales_section: bool,
        display_routes_section: bool,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        supplier_user_id: UUID,
        supplier_business_id: UUID,
        display_sales_section: Optional[bool] = None,
        display_routes_section: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, supplier_user_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    async def fetch_by_supplier_business(
        self, supplier_business_id: UUID
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_user_contact_and_permission(
        self,
        filter_str: str | None,
        filter_values: Dict[Any, Any],
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
