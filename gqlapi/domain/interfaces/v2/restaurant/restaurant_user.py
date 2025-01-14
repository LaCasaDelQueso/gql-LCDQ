from abc import ABC, abstractmethod
from types import NoneType
from typing import Optional, List, Dict, Any
from uuid import UUID
from gqlapi.lib.future.future.deprecation import deprecated
import strawberry
from gqlapi.domain.models.v2.core import (
    CoreUser,
    PermissionDict,
    RestaurantEmployeeInfo,
    RestaurantEmployeeInfoPermission,
)
from gqlapi.domain.models.v2.restaurant import (
    RestaurantUser,
    RestaurantUserPermission,
)


# GraphQL Schema Error Types
@strawberry.type
class RestaurantUserError:
    msg: str
    code: int


# GraphQL Schema Result Types
@strawberry.type
class RestaurantUserGQL(RestaurantUser):
    user: Optional[CoreUser] = None


@strawberry.type
class RestaurantUserEmployeeGQL:
    restaurant_user: Optional[RestaurantUserGQL] = None
    employee: Optional[RestaurantEmployeeInfo] = None
    permission: Optional[RestaurantUserPermission] = None


@strawberry.type
class RestaurantUserStatus:
    enabled: Optional[bool] = None
    deleted: Optional[bool] = None


@strawberry.type
class RestaurantUserPermCont(RestaurantUser):
    contact_info_user: Optional[CoreUser] = None
    permission: Optional[RestaurantUserPermission] = None
    employee: Optional[RestaurantEmployeeInfo] = None


@strawberry.input
class PermissionDictInput(PermissionDict):
    pass


@strawberry.input
class RestaurantEmployeeInfoPermissionInput(RestaurantEmployeeInfoPermission):
    permissions: Optional[List[PermissionDictInput]] = None


@strawberry.input
class RestaurantDisplayPermissionsInput:
    display_orders_section: Optional[bool] = None
    display_suppliers_section: Optional[bool] = None
    display_products_section: Optional[bool] = None


# Result : getRestaurantUser, newRestaurantUser, editRestaurantUser
RestaurantUserResult = strawberry.union(
    "RestaurantUserResult",
    (
        RestaurantUserGQL,
        RestaurantUserError,
    ),
)

RestaurantUserPermContResult = strawberry.union(
    "RestaurantUserPermContResult",
    (
        RestaurantUserPermCont,
        RestaurantUserError,
    ),
)

# Result : changeRestaurantUserStatus, eraseRestaurantUser
RestaurantUserStatusResult = strawberry.union(
    "RestaurantUserStatusResult",
    (
        RestaurantUserStatus,
        RestaurantUserError,
    ),
)

RestaurantUserPermissionResult = strawberry.union(
    "RestaurantUserPermissionResult",
    (
        RestaurantUserError,
        RestaurantUserPermission,
    ),
)

RestaurantUserEmployeeResult = strawberry.union(
    "RestaurantUserEmployeeResult",
    (RestaurantUserError, RestaurantEmployeeInfo),
)

RestaurantUserEmployeeGQLResult = strawberry.union(
    "RestaurantUserEmployeeGQLResult",
    (RestaurantUserError, RestaurantUserEmployeeGQL),
)


# Handler Interfaces
class RestaurantUserHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> RestaurantUserGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_user(
        self,
        restaurant_user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
    ) -> RestaurantUserGQL:
        raise NotImplementedError

    @abstractmethod
    async def change_restaurant_user_status(
        self, restaurant_user_id: UUID, enabled: bool
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def erase_restaurant_user(
        self, restaurant_user_id: UUID, deleted: bool
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_user(
        self, restaurant_user_id: UUID
    ) -> RestaurantUserGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_user_by_firebase_id(
        self, firebase_id: str
    ) -> RestaurantUserGQL | NoneType:
        raise NotImplementedError


class RestaurantUserPermissionHandlerInterface(ABC):
    @abstractmethod
    async def fetch_restaurant_users_contact_and_permission_from_business(
        self,
        restaurant_business_id: UUID,
    ) -> List[RestaurantUserPermCont]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_user_contact_and_permission(
        self,
        firebase_id: str,
    ) -> RestaurantUserPermCont:
        raise NotImplementedError


class RestaurantEmployeeHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_employee(
        self,
        restaurant_business_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        position: str,
        display_perms: Dict[str, bool],
        department: Optional[str] = None,
        permission: Optional[List[RestaurantEmployeeInfoPermission]] = None,
    ) -> RestaurantUserEmployeeGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_employee(
        self,
        restaurant_business_id: UUID,
        restaurant_user_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        display_perms: Optional[Dict[str, bool]] = None,
        permission: Optional[List[RestaurantEmployeeInfoPermission]] = None,
    ) -> RestaurantUserPermission:
        raise NotImplementedError


# Repository Interfaces
class RestaurantUserRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        core_user_id: UUID,
        role: str,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        core_user_id: UUID,
        role: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    async def get(self, core_user_id: UUID) -> RestaurantUserGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, core_user_id: UUID) -> RestaurantUserGQL | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def activate_desactivate(self, core_user_id: UUID, enabled: bool) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, core_id: UUID, deleted: bool) -> bool:
        raise NotImplementedError

    @deprecated("Use exists() instead", "domain")
    @abstractmethod
    async def exist(
        self,
        restaurant_user_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        restaurant_user_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, restaurant_user_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError


class RestaurantUserPermissionRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        restaurant_user_id: UUID,
        restaurant_business_id: UUID,
        display_orders_section: bool,
        display_suppliers_section: bool,
        display_products_section: bool,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        restaurant_user_id: UUID,
        display_orders_section: Optional[bool] = None,
        display_suppliers_section: Optional[bool] = None,
        display_products_section: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        restaurant_user_id: UUID,
        display_orders_section: Optional[bool] = None,
        display_suppliers_section: Optional[bool] = None,
        display_products_section: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, restaurant_user_id: UUID) -> RestaurantUserPermission:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self, restaurant_user_id: UUID
    ) -> RestaurantUserPermission | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_restaurant_user_contact_and_permission(
        self,
        filter_values: str | None,
        rest_user_info_values_view: Dict[Any, Any],
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
