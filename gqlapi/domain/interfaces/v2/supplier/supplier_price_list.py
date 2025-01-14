from abc import ABC, abstractmethod
from datetime import date
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.domain.models.v2.utils import UOMType

import strawberry

from gqlapi.domain.models.v2.supplier import (
    SupplierPriceList,
    SupplierProductImage,
    SupplierProductPrice,
    SupplierUnit,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBranch


@strawberry.type
class SupplierPriceListError:
    msg: str
    code: int


@strawberry.input
class SupplierPriceInput:
    supplier_product_id: UUID
    price: float


@strawberry.type
class SupplierPriceListBatch:
    product_id: Optional[UUID] = None
    supplier_product_id: Optional[UUID] = None
    supplier_product_price_id: Optional[UUID] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    status: bool
    msg: str


@strawberry.type
class SupplierPriceListBatchGQL:
    prices: List[SupplierPriceListBatch]
    msg: str


@strawberry.type
class PriceListItemDetails:
    description: str
    sell_unit: UOMType
    sku: str
    price: SupplierProductPrice
    images: Optional[List[SupplierProductImage]] = None


@strawberry.type
class SupplierPriceListDetails(SupplierPriceList):
    prices_details: List[PriceListItemDetails]
    clients: List[RestaurantBranch]


@strawberry.type
class SupplierPriceListsGQL:
    price_lists: List[SupplierPriceListDetails]


@strawberry.type
class SupplierUnitDefaultPriceListsGQL:
    unit: SupplierUnit | NoneType
    price_list: SupplierPriceList
    price: SupplierProductPrice
    
    
@strawberry.type
class DeleteSupplierPriceListStatus:
    msg: str


@strawberry.type
class UpdateOneSupplierPriceListStatus:
    msg: str



SupplierPriceListBatchResult = strawberry.union(
    "SupplierPriceListBatchResult", [SupplierPriceListBatchGQL, SupplierPriceListError]
)

SupplierPriceListsResult = strawberry.union(
    "SupplierPriceListsResult",
    [SupplierPriceListsGQL, SupplierPriceListError],
)

SupplierUnitsDefaultPriceListsResult = strawberry.union(
    "SupplierUnitsDefaultPriceListsResult",
    [SupplierUnitDefaultPriceListsGQL, SupplierPriceListError],
)

DeleteSupplierPriceListResult = strawberry.union(
    "DeleteSupplierPriceListResult",
    [DeleteSupplierPriceListStatus, SupplierPriceListError],
)

UpdateOneSupplierPriceListResult = strawberry.union(
    "UpdateOneSupplierPriceListResult",
    [UpdateOneSupplierPriceListStatus, SupplierPriceListError],
)


class SupplierPriceListHandlerInterface(ABC):
    @abstractmethod
    async def upsert_supplier_price_list_file(
        self,
        firebase_id: str,
        name: str,
        supplier_unit_ids: List[UUID],
        price_list_file: bytes | str,
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
        supplier_price_list_id: Optional[UUID] = None,
    ) -> List[SupplierPriceListBatch]:
        raise NotImplementedError

    @abstractmethod
    async def new_supplier_price_list(
        self,
        firebase_id: str,
        name: str,
        supplier_unit_ids: List[UUID],
        supplier_prices: List[Dict[str, Any]],
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
    ) -> List[SupplierPriceListBatch]:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_price_list(
        self,
        firebase_id: str,
        name: str,
        supplier_unit_ids: List[UUID],
        supplier_prices: List[Dict[str, Any]],
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
    ) -> List[SupplierPriceListBatch]:
        raise NotImplementedError

    @abstractmethod
    async def add_price_to_price_list(
        self,
        firebase_id: str,
        price_list_id: UUID,
        supplier_product_id: UUID,
        price: float,
        valid_until: Optional[date] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_price_to_default_price_lists(
        self,
        firebase_id: str,
        supplier_business_id: UUID,
        supplier_product_id: UUID,
        price: float,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_customer_product_price_list_to_export(
        self, product_price_list: UUID
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_all_product_price_lists_to_export(
        self, supplier_business_id: UUID
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_product_default_price_list(
        self, supplier_product_id: UUID, supplier_business_id: UUID
    ) -> List[SupplierUnit]:
        raise NotImplementedError


class SupplierPriceListRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        supplier_price_list: SupplierPriceList,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        supplier_price_list_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def raw_query(
        self,
        query: str,
        vals: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_price_list_to_export(
        self, supplier_product_price_list_id: UUID, supplier_business_id: UUID
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_all_price_list_to_export(
        self, supplier_business_id: UUID
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self, supplier_price_list_name: str, supplier_business_id: UUID
    ) -> bool | NoneType:
        raise NotImplementedError