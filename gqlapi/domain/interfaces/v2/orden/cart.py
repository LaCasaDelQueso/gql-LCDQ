from abc import ABC, abstractmethod
from datetime import datetime
from types import NoneType
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID

from gqlapi.domain.models.v2.core import Cart, CartProduct
from gqlapi.domain.models.v2.supplier import SupplierProduct, SupplierProductPrice
import strawberry


@strawberry.type
class CartProductGQL(CartProduct):
    supp_prod: Optional[SupplierProduct] = None
    supp_prod_price: Optional[SupplierProductPrice] = None


@strawberry.type
class TaxGQL:
    tax: Optional[float] = None


class CartRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, cart: Cart) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        cart_id: UUID,
        active: Optional[bool] = None,
        closed_at: Optional[datetime] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, cart_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        cart_id: UUID,
    ) -> NoneType:
        raise NotImplementedError


class CartProductRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, cart_product: CartProduct) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def search(self, cart_id: UUID) -> List[CartProduct]:
        raise NotImplementedError

    @abstractmethod
    async def find(self, cart_id: UUID) -> List[CartProduct]:
        raise NotImplementedError

    @abstractmethod
    async def find_many(
        self,
        cols: List[str],
        filter_values: List[Dict[str, str]],
        tablename: str = "cart_product",
        filter_type: str = "AND",
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def search_with_tax(self, cart_id: Optional[UUID] = None) -> Sequence:
        raise NotImplementedError

    @abstractmethod
    async def find_with_tax(
        self, cart_id: Optional[UUID] = None
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError
