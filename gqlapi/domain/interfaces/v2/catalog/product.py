from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID

from gqlapi.domain.models.v2.core import Product
from gqlapi.domain.models.v2.utils import UOMType
import strawberry


@strawberry.type
class ProductError:
    msg: str
    code: int


ProductResult = strawberry.union(
    "ProductResult",
    (
        ProductError,
        Product,
    ),
)


@strawberry.input
class ProductInput:
    product_family_id: UUID
    name: str
    description: str
    sku: str
    keywords: List[str]
    sell_unit: UOMType
    conversion_factor: float
    buy_unit: UOMType
    estimated_weight: float
    upc: Optional[str] = None


class ProductHandlerInterface(ABC):
    @abstractmethod
    async def new_product(
        self,
        product_family_id: UUID,
        name: str,
        description: str,
        sku: int,
        keywords: List[str],
        sell_unit: UOMType,
        conversion_factor: float,
        buy_unit: UOMType,
        estimated_weight: float,
        firebase_id: str,
        upc: Optional[str] = None,
    ) -> Product:
        raise NotImplementedError

    @abstractmethod
    async def edit_product(
        self,
        product_id: UUID,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sku: Optional[int] = None,
        keywords: Optional[List[str]] = None,
        sell_unit: Optional[UOMType] = None,
        conversion_factor: Optional[float] = None,
        buy_unit: Optional[UOMType] = None,
        estimated_weight: Optional[float] = None,
        upc: Optional[str] = None,
    ) -> Product:
        raise NotImplementedError

    @abstractmethod
    async def search_products(
        self,
        product_id: Optional[UUID] = None,
        name: Optional[str] = None,
        search: Optional[str] = None,
        product_family_id: Optional[UUID] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        current_page: int = 1,
        page_size: int = 10,
    ) -> List[Product]:
        raise NotImplementedError

    @abstractmethod
    async def new_batch_products(
        self, firebase_id: str, catalog: List[ProductInput]
    ) -> List[Product]:
        raise NotImplementedError


class ProductRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self, product: Product, validate_by: str, validate_against: Any
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        product_id: UUID,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sku: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        sell_unit: Optional[UOMType] = None,
        conversion_factor: Optional[float] = None,
        buy_unit: Optional[UOMType] = None,
        estimated_weight: Optional[float] = None,
        upc: Optional[str] = None,
        validate_by: Optional[str] = None,
        validate_agains: Optional[Any] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        product_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        product_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exist(
        self,
        product_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_products(
        self,
        product_id: Optional[UUID] = None,
        name: Optional[str] = None,
        search: Optional[str] = None,
        product_family_id: Optional[UUID] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        current_page: int = 1,
        page_size: int = 10,
    ) -> List[Product]:
        raise NotImplementedError

    @abstractmethod
    async def find(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        raise NotImplementedError
