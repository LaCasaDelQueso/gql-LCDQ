from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from gqlapi.domain.models.v2.core import CoreUser

import strawberry

from gqlapi.domain.models.v2.supplier import (
    SupplierProduct,
    SupplierProductImage,
    SupplierProductPrice,
    SupplierProductStock,
    SupplierProductTag,
)
from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.lib.future.future.deprecation import deprecated


@strawberry.input
class SupplierProductTagInput:
    tag: str
    value: str


@strawberry.type
class SupplierProductError:
    msg: str
    code: int


@strawberry.type
class ExportProductGQL:
    file: str  # encoded file
    extension: str = "csv"  # {csv, xlsx} default = csv


@strawberry.type
class SupplierProductsBatch:
    product_id: Optional[UUID] = None
    supplier_product_id: Optional[UUID] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    status: bool
    msg: str


@strawberry.type
class SupplierProductsStockBatch:
    supplier_product_id: Optional[UUID] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    stock: Optional[float] = None
    keep_selling_without_stock: Optional[bool] = None
    status: bool
    msg: str


@strawberry.input
class SupplierProductStockInput:
    supplier_product_id: UUID
    stock: float | None
    keep_selling_without_stock: bool
    active: bool
    sku: str


@strawberry.type
class SupplierProductsBatchGQL:
    products: List[SupplierProductsBatch]
    msg: str


@strawberry.type
class SupplierProductsBatchStockGQL:
    stock: List[SupplierProductsStockBatch]
    msg: str


@strawberry.type
class SupplierProductStockWithAvailability(SupplierProductStock):
    availability: float = 0.0


@strawberry.type
class SupplierProductDetails(SupplierProduct):
    last_price: Optional[SupplierProductPrice] = None
    stock: Optional[SupplierProductStockWithAvailability] = None
    tags: Optional[List[SupplierProductTag]] = None
    images: Optional[List[str]] = None


# Model overload - for GQL and priority rearrangement
@strawberry.type
class SupplierProductDetailsGQL(SupplierProductDetails):
    images: Optional[List[SupplierProductImage]] = None


@strawberry.type
class SupplierProductStockGQL:
    stock: SupplierProductStock
    supplier_product: SupplierProduct


@strawberry.type
class SupplierProductsDetailsListGQL:
    products: List[SupplierProductDetailsGQL]


@strawberry.type
class SupplierProductsStockListGQL:
    stock_list: List[SupplierProductStockGQL]


SupplierProductsBatchResult = strawberry.union(
    "SupplierProductsBatchResult", (SupplierProductsBatchGQL, SupplierProductError)
)

SupplierProductsStockBatchResult = strawberry.union(
    "SupplierProductsBatchStockResult",
    (SupplierProductsBatchStockGQL, SupplierProductError),
)

SupplierProductDetailsListResult = strawberry.union(
    "SupplierProductDetailsResult",
    (SupplierProductsDetailsListGQL, SupplierProductError),
)

ExportSupplierProductResult = strawberry.union(
    "ExportSupplierProductResult",
    (
        SupplierProductError,
        ExportProductGQL,
    ),
)

SupplierProductStockListResult = strawberry.union(
    "SupplierProductStockResult",
    (SupplierProductsStockListGQL, SupplierProductError),
)


class SupplierProductHandlerInterface(ABC):
    @abstractmethod
    async def upsert_supplier_products_file(
        self,
        firebase_id: str,
        product_file: bytes | str,
    ) -> List[SupplierProductsBatch]:
        raise NotImplementedError

    @abstractmethod
    async def add_supplier_product(
        self,
        firebase_id: str,
        supplier_business_id: UUID,
        sku: str,  # Internal supplier code
        description: str,
        tax_id: str,  # MX: SAT Unique Product tax id
        sell_unit: UOMType,  # SellUOM
        tax: float,  # percentage rate of the product value to apply for tax
        conversion_factor: float,
        buy_unit: UOMType,  # BuyUOM
        unit_multiple: float,
        min_quantity: float,
        product_id: Optional[UUID] = None,
        upc: Optional[str] = None,  # International UPC - Barcode (optional)
        estimated_weight: Optional[float] = None,
        default_price: Optional[float] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
        long_description: Optional[str] = None,
        mx_ieps: Optional[float] = None,
    ) -> SupplierProductDetails:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_product(
        self,
        firebase_id: str,
        supplier_product_id: UUID,
        sku: Optional[str] = None,  # Internal supplier code
        description: Optional[str] = None,
        tax_id: Optional[str] = None,  # MX: SAT Unique Product tax id
        sell_unit: Optional[UOMType] = None,  # SellUOM
        tax: Optional[
            float
        ] = None,  # percentage rate of the product value to apply for tax
        conversion_factor: Optional[float] = None,
        buy_unit: Optional[UOMType] = None,  # BuyUOM
        unit_multiple: Optional[float] = None,
        min_quantity: Optional[float] = None,
        product_id: Optional[UUID] = None,
        upc: Optional[str] = None,  # International UPC - Barcode (optional)
        estimated_weight: Optional[float] = None,
        default_price: Optional[float] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
        long_description: Optional[str] = None,
        mx_ieps: Optional[float] = None,
    ) -> SupplierProductDetails:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_products(
        self,
        firebase_id: str,
    ) -> List[SupplierProductDetails]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_product(
        self,
        firebase_id: str,
        supplier_product_id: UUID,
    ) -> SupplierProductDetails:
        raise NotImplementedError

    @abstractmethod
    def validate_cols_supplier_products_file(self, df: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_business(
        self, firebase_id: str
    ) -> Tuple[CoreUser, Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_customer_products_to_export(
        self,
        supplier_business_id: UUID,
        receiver: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_products_stock(
        self, firebase_id: str, supplier_unit_id: UUID
    ) -> List[SupplierProductDetailsGQL]:
        raise NotImplementedError

    @abstractmethod
    async def upsert_supplier_products_stock_file(
        self,
        firebase_id: str,
        product_stock_file: bytes | str,
        supplier_units: List[UUID],
    ) -> List[SupplierProductsStockBatch]:
        raise NotImplementedError

    @abstractmethod
    async def get_customer_products_stock_to_export(
        self, supplier_unit_id: UUID
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError


class SupplierProductRepositoryInterface(ABC):
    @deprecated("Use add() instead", "domain")
    @abstractmethod
    async def new(
        self,
        supplier_product: SupplierProduct,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        supplier_product: SupplierProduct,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        supplier_product: SupplierProduct,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        id: UUID,
        product_id: Optional[UUID] = None,  # (optional)
        supplier_business_id: Optional[UUID] = None,  # (optional)
        sku: Optional[str] = None,  # (optional)
        upc: Optional[str] = None,  # (optional)
        description: Optional[str] = None,  # (optional)
        tax_id: Optional[str] = None,  # (optional)
        sell_unit: Optional[UOMType] = None,  # (optional)
        tax_unit: Optional[str] = None,  # (optional)
        tax: Optional[float] = None,  # (optional)
        conversion_factor: Optional[float] = None,  # (optional)
        buy_unit: Optional[UOMType] = None,  # (optional)
        unit_multiple: Optional[float] = None,  # (optional)
        min_quantity: Optional[float] = None,  # (optional)
        estimated_weight: Optional[float] = None,  # (optional)
        is_active: Optional[bool] = None,  # (optional)
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        supplier_product_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        supplier_product_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        supplier_product_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def validate(
        self,
        supplier_product_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @deprecated("Use find() instead", "domain")
    @abstractmethod
    async def search(
        self,
        supplier_business_id: Optional[UUID] = None,
        supplier_product_id: Optional[UUID] = None,
        description: Optional[str] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> List[SupplierProduct]:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        supplier_business_id: Optional[UUID] = None,
        supplier_product_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        description: Optional[str] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def find_many(
        self,
        cols: List[str],
        filter_values: List[Dict[str, str]],
        tablename: str = "supplier_product",
        filter_type: str = "AND",
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def raw_query(
        self,
        query: str,
        values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def add_file_tags(
        self,
        supplier_product_id: UUID,
        tags: List[SupplierProductTag],
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_tags(
        self,
        supplier_product_id: UUID,
        tags: List[SupplierProductTag],
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_tags(
        self,
        supplier_product_id: UUID,
    ) -> List[SupplierProductTag]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_tags_from_many(
        self,
        supplier_product_ids: List[UUID],
    ) -> List[SupplierProductTag]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_products_to_export(
        self,
        supplier_business_id: UUID,
        receiver: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError


class SupplierProductPriceRepositoryInterface(ABC):
    @deprecated("Use add() instead", "domain")
    @abstractmethod
    async def new(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @deprecated("Use edit() instead", "domain")
    @abstractmethod
    async def update(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        supp_prod_price_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        supp_prod_price_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_latest_active(
        self, supplier_product_id: UUID
    ) -> SupplierProductPrice | NoneType:
        raise NotImplementedError


class SupplierProductStockRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        supp_prod_stock: SupplierProductStock,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch_latest(
        self, supplier_product_id: UUID, supplier_unit_id: UUID
    ) -> SupplierProductStock | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch_latest_by_unit(
        self, supplier_unit_id: UUID
    ) -> List[SupplierProductStock]:
        raise NotImplementedError

    @abstractmethod
    async def find_availability(
        self,
        supplier_unit_id: UUID,
        stock_products: List[SupplierProductStock],
    ) -> List[SupplierProductStockWithAvailability]:
        raise NotImplementedError
