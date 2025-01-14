from abc import ABC, abstractmethod
from datetime import datetime
from types import NoneType
from typing import Optional, List, Dict, Any
from uuid import UUID
from gqlapi.domain.interfaces.v2.services.image import ImageRoute
from gqlapi.domain.interfaces.v2.supplier.supplier_product import SupplierProductStockWithAvailability
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
    SupplierBusinessAccount,
    SupplierProduct,
    SupplierProductPrice,
    SupplierUnit,
    SupplierUnitCategory,
    SupplierUnitDeliveryOptions,
)
from gqlapi.domain.models.v2.utils import CurrencyType, NotificationChannelType, UOMType
import strawberry
from gqlapi.domain.models.v2.restaurant import (
    RestaurantSupplierRelation,
)


# GraphQL Schema Error Types
@strawberry.type
class RestaurantSupplierError:
    msg: str
    code: int


@strawberry.type
class RestaurantBusinessSupplierBusinessRelation:
    restaurant_business_id: UUID
    supplier_business_id: UUID


@strawberry.input
class SupplierProductInput:
    id: Optional[UUID] = None  # (optional)
    product_id: Optional[UUID] = None  # (optional)
    sku: str  # Internal supplier code
    upc: Optional[str] = None  # International UPC - Barcode (optional)
    description: str
    tax_id: str  # MX: SAT Unique Product tax id
    sell_unit: UOMType  # SellUOM
    tax_unit: str  # MX: SAT Unique Unit tax id
    tax: float  # percentage rate of the product value to apply for tax
    conversion_factor: float
    buy_unit: UOMType  # BuyUOM
    unit_multiple: float
    min_quantity: float
    estimated_weight: float
    is_active: bool


@strawberry.input
class SupplierProductPriceInput:
    price: float
    currency: CurrencyType
    valid_from: datetime
    valid_upto: datetime


@strawberry.input
class SupplierProductCreationInput:
    product: SupplierProductInput
    price: Optional[SupplierProductPriceInput] = None
    pass


@strawberry.type
class SupplierProductCreation:
    product: SupplierProduct
    price: Optional[SupplierProductPrice] = None
    images: Optional[List[ImageRoute]] = None
    stock: Optional[SupplierProductStockWithAvailability] = None


@strawberry.type
class SupplierUnitRestoGQL:
    supplier_unit: SupplierUnit
    category: SupplierUnitCategory
    delivery_info: Optional[SupplierUnitDeliveryOptions] = None


@strawberry.type
class SupplierBatchGQL:
    uuid: Optional[UUID] = None
    name: str
    status: bool
    msg: str


@strawberry.type
class ProductsBatchGQL:
    supplier_name: str
    supplier_product_id: Optional[UUID] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    status: bool
    msg: str


@strawberry.type
class RestaurantSupplierBatchGQL:
    suppliers: Optional[List[SupplierBatchGQL]] = None
    products: Optional[List[ProductsBatchGQL]] = None
    msg: str


@strawberry.type
class RestaurantSupplierCreationGQL:
    supplier_business: Optional[SupplierBusiness] = None
    supplier_business_account: Optional[SupplierBusinessAccount] = None
    relation: Optional[RestaurantSupplierRelation] = None
    unit: Optional[List[SupplierUnitRestoGQL]] = None
    products: Optional[List[SupplierProductCreation]] = None


# Result : getRestaurantUser, newRestaurantUser, editRestaurantUser
RestaurantSupplierAssignationResult = strawberry.union(
    "RestaurantSupplierAssignation",
    (
        RestaurantSupplierRelation,
        RestaurantSupplierError,
    ),
)

RestaurantSupplierBatchResult = strawberry.union(
    "RestaurantSupplierBatchResult",
    (
        RestaurantSupplierBatchGQL,
        RestaurantSupplierError,
    ),
)

RestaurantSupplierCreationResult = strawberry.union(
    "RestaurantSupplierCreation",
    (
        RestaurantSupplierCreationGQL,
        RestaurantSupplierError,
    ),
)

RestaurantSuppliersResult = strawberry.union(
    "RestaurantSuppliers",
    (
        RestaurantSupplierCreationGQL,
        RestaurantSupplierError,
    ),
)

RestaurantSuppliersResult = strawberry.union(
    "RestaurantSuppliers",
    (
        RestaurantSupplierCreationGQL,
        RestaurantSupplierError,
    ),
)

RestaurantSupplierProductsResult = strawberry.union(
    "RestaurantSupplierProducts",
    (
        SupplierProduct,
        RestaurantSupplierError,
    ),
)


# Handler Interfaces
class RestaurantSupplierAssignationHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_supplier_assignation(
        self,
        restaurant_branch_id: UUID,
        supplier_business_id: UUID,
        firebase_id: str,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> RestaurantSupplierRelation:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_supplier_assignation(
        self,
        rest_supp_assig_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> RestaurantSupplierRelation:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_suppliers_assignation(
        self, restaurant_branch_id: Optional[UUID] = None
    ) -> List[RestaurantSupplierRelation]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_suppliers(
        self,
        firebase_id: str,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        with_products: bool = False,
    ) -> List[RestaurantSupplierCreationGQL]:
        raise NotImplementedError

    @abstractmethod
    async def search_restaurant_business_supplier(
        self,
        restaurant_business_id: UUID,
        supplier_unit_name: Optional[str] = None,
        supplier_unit_id: Optional[UUID] = None,
    ) -> List[RestaurantBusinessSupplierBusinessRelation]:
        raise NotImplementedError


class RestaurantSupplierHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_supplier_creation(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
        category_id: UUID,  # For supplier category
        restaurant_branch_id: UUID,
        email: str,
        phone_number: str,
        contact_name: str,
        firebase_id: str,
        unit_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        catalog: Optional[List[SupplierProductCreationInput]] = None,
    ) -> RestaurantSupplierCreationGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_supplier_creation(
        self,
        supplier_business_id: UUID,
        firebase_id: str,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        category_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        contact_name: Optional[str] = None,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        catalog: Optional[List[SupplierProductCreationInput]] = None,
    ) -> RestaurantSupplierCreationGQL:
        raise NotImplementedError

    @abstractmethod
    async def search_restaurant_branch_supplier(
        self,
        restaurant_branch_id: UUID,
        supplier_business_name: UUID,
    ) -> List[RestaurantBusinessSupplierBusinessRelation]:
        raise NotImplementedError

    @abstractmethod
    async def find_restaurant_supplier_products(
        self,
        supplier_business_ids: List[UUID],
    ) -> List[SupplierProduct]:
        raise NotImplementedError

    @abstractmethod
    async def find_available_marketplace_suppliers(
        self,
        restaurant_branch_id: UUID,
    ) -> List[RestaurantSupplierCreationGQL]:
        raise NotImplementedError


# Repository Interfaces
class RestaurantSupplierAssignationRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        restaurant_branch_id: UUID,
        supplier_business_id: UUID,
        core_user_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        rest_supp_assig_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
    ) -> List[RestaurantSupplierRelation]:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, restaurant_branch_id: UUID) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_product_supplier_assignation(
        self,
        restaurant_business_id: UUID,
        supplier_business_name: str,
    ) -> List[RestaurantBusinessSupplierBusinessRelation]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_restaurant_business(
        self,
        restaurant_business_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
    ) -> List[RestaurantSupplierRelation]:
        raise NotImplementedError

    # @abstractmethod
    # async def unassign(self, restaurant_branch_id, supplier_unit_id):
    #     raise NotImplementedError

    @abstractmethod
    async def raw_query(
        self, query: str, vals: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
