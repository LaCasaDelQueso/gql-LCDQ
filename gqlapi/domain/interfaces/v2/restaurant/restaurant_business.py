from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Optional, List, Dict
from uuid import UUID
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBusiness,
    RestaurantBusinessAccount,
    RestaurantUserPermission,
)
from gqlapi.domain.models.v2.utils import RestaurantBusinessType
import strawberry
from strawberry.file_uploads import Upload


@strawberry.type
class RestaurantBusinessError:
    msg: str
    code: int


@strawberry.input
class RestaurantBusinessAccountInput:
    business_type: Optional[RestaurantBusinessType] = None
    legal_business_name: Optional[str] = None
    incorporation_file: Optional[Upload] = None
    legal_rep_name: Optional[str] = None
    legal_rep_id: Optional[Upload] = None
    legal_address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    mx_sat_regimen: Optional[str] = None
    mx_sat_rfc: Optional[str] = None
    mx_sat_csf: Optional[Upload] = None


@strawberry.type
class RestaurantBusinessGQL(RestaurantBusiness):
    account: Optional[RestaurantBusinessAccount] = None


@strawberry.type
class RestaurantBusinessAccountDeleteGQL:
    delete: bool


@strawberry.type
class RestaurantBusinessAdminGQL(RestaurantBusiness):
    account: Optional[RestaurantBusinessAccount] = None
    permission: Optional[RestaurantUserPermission] = None


RestaurantBusinessGQLResult = strawberry.union(
    "RestaurantBusinessGQLResult",
    (
        RestaurantBusinessError,
        RestaurantBusinessGQL,
    ),
)

RestaurantBusinessAccountDeleteGQLResult = strawberry.union(
    "RestaurantBusinessAccountDeleteGQLResult",
    (
        RestaurantBusinessError,
        RestaurantBusinessAccountDeleteGQL,
    ),
)

RestaurantBusinessAdminGQLResult = strawberry.union(
    "RestaurantBusinessAdminGQLResult",
    (
        RestaurantBusinessError,
        RestaurantBusinessAdminGQL,
    ),
)

RestaurantBusinessResult = strawberry.union(
    "RestaurantBusinessResult",
    (
        RestaurantBusinessError,
        RestaurantBusinessGQL,
    ),
)


class RestaurantBusinessHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_business(
        self,
        name: str,
        country: str,
        firebase_id: str,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessGQL:
        raise NotImplementedError

    @abstractmethod
    async def new_ecommerce_restaurant_business(
        self,
        name: str,
        country: str,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessAdminGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_business(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_business(
        self,
        id: Optional[UUID] = None,
    ) -> RestaurantBusiness:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_business_by_firebase_id(
        self,
        firebase_id: str,
    ) -> RestaurantBusiness:
        raise NotImplementedError

    @abstractmethod
    async def delete_restaurant_business_account(
        self,
        restaurant_business_id: UUID,
    ) -> bool | NoneType:
        raise NotImplementedError


class RestaurantBusinessRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, name: str, country: str, active: bool = True) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self, name: str, country: str, active: bool = True
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> bool:
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

    @abstractmethod
    async def get(self, id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_restaurant_businesses(
        self,
        id: Optional[UUID] = None,
    ) -> List[RestaurantBusiness]:
        raise NotImplementedError

    @abstractmethod
    async def exist(
        self,
        restaurant_business_id: UUID,
    ) -> NoneType:
        raise NotImplementedError


class RestaurantBusinessAccountRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        restaurant_business_id: UUID,
        account: Optional[RestaurantBusinessAccount] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        account: RestaurantBusinessAccount,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        restaurant_business_id: UUID,
        account: Optional[RestaurantBusinessAccount] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        restaurant_business_id: UUID,
        account: RestaurantBusinessAccount,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, id: UUID) -> RestaurantBusinessAccount:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, id: UUID) -> RestaurantBusinessAccount | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exist(
        self,
        id_key: str,
        restaurant_business_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        restaurant_business_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        query: Dict[Any, Any],
    ) -> List[Any]:
        raise NotImplementedError
