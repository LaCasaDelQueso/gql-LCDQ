from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID

from gqlapi.domain.models.v2.core import MxSatProductCode, ProductFamily
from gqlapi.domain.models.v2.utils import UOMType
import strawberry


@strawberry.type
class ProductFamilyError:
    msg: str
    code: int


@strawberry.type
class MxSatProductCodeGQL(MxSatProductCode):
    sat_code_family: str


ProductFamilyResult = strawberry.union(
    "ProductFamilyResult",
    [
        ProductFamilyError,
        ProductFamily,
    ],
)

MxSatProductCodeResult = strawberry.union(
    "MxSatProductCodeResult",
    [
        ProductFamilyError,
        MxSatProductCodeGQL,
    ],
)


class ProductFamilyHandlerInterface(ABC):
    @abstractmethod
    async def new_product_family(
        self,
        alima_user_id: UUID,
        name: str,
        buy_unit: UOMType,
    ) -> ProductFamily:
        raise NotImplementedError

    @abstractmethod
    async def edit_product_family(
        self,
        product_family_id: UUID,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
    ) -> ProductFamily:
        raise NotImplementedError

    @abstractmethod
    async def search_product_families(
        self,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
        search: Optional[str] = None,
    ) -> List[ProductFamily]:
        raise NotImplementedError

    @abstractmethod
    async def find_mx_sat_product_codes(
        self,
        search: Optional[str] = None,
        current_page: Optional[int] = 1,
        page_size: Optional[int] = 200,
    ) -> List[MxSatProductCodeGQL]:
        raise NotImplementedError


class ProductFamilyRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        product_family: ProductFamily,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        product_family_id: UUID,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        product_family_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        product_family_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_product_families(
        self,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
        search: Optional[str] = None,
    ) -> List[ProductFamily]:
        raise NotImplementedError

    @abstractmethod
    async def exists_relation_buy_name(self, name: str, buy_unit: UOMType) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def find_mx_sat_product_codes(
        self,
        search: Optional[str] = None,
        current_page: int = 1,
        page_size: int = 200,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
