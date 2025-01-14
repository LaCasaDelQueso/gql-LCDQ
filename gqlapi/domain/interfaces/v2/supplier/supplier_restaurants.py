from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.authos.ecommerce_user import EcommerceUser
from gqlapi.domain.interfaces.v2.supplier.supplier_product import SupplierProductDetails

import strawberry

from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranch,
    RestaurantBranchCategory,
    RestaurantBranchMxInvoiceInfo,
    RestaurantBranchTag,
    RestaurantBusiness,
    RestaurantBusinessAccount,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierRestaurantRelation,
    SupplierRestaurantRelationMxInvoicingOptions,
)


@strawberry.type
class ExportSupplierRestaurantGQL:
    file: str  # encoded file
    extension: str = "csv"  # {csv, xlsx} default = csv


@strawberry.type
class SupplierRestaurantError:
    msg: str
    code: int


@strawberry.type
class RestaurantBranchSupGQL:
    restaurant_branch: RestaurantBranch
    category: RestaurantBranchCategory
    tax_info: Optional[RestaurantBranchMxInvoiceInfo] = None
    invoicing_options: Optional[SupplierRestaurantRelationMxInvoicingOptions] = None
    tags: Optional[List[RestaurantBranchTag]] = None


@strawberry.type
class SupplierRestaurantCreationGQL:
    relation: SupplierRestaurantRelation
    restaurant_business: Optional[RestaurantBusiness] = None
    restaurant_business_account: Optional[RestaurantBusinessAccount] = None
    branch: Optional[RestaurantBranchSupGQL] = None
    products: List[SupplierProductDetails]
    ecommerce_user: Optional[EcommerceUser] = None
    price_list_name: Optional[str] = None


SupplierRestaurantAssignationResult = strawberry.union(
    "SupplierRestaurantAssignationResult",
    (
        SupplierRestaurantRelation,
        SupplierRestaurantError,
    ),
)


SupplierRestaurantCreationResult = strawberry.union(
    "SupplierRestaurantCreationResult",
    (
        SupplierRestaurantCreationGQL,
        SupplierRestaurantError,
    ),
)

ExportSupplierRestaurantResult = strawberry.union(
    "ExportSupplierRestaurantResult",
    (
        ExportSupplierRestaurantGQL,
        SupplierRestaurantError,
    ),
)


# Handler Interfaces
class SupplierRestaurantsHandlerInterface(ABC):
    @abstractmethod
    async def new_supplier_restaurant_creation(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        name: str,
        country: str,
        email: str,
        phone_number: str,
        contact_name: str,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        zip_code: str,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> SupplierRestaurantCreationGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_restaurant_creation(
        self,
        firebase_id: str,
        supplier_restaurant_relation_id: UUID,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        # Rest Branch Data
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        contact_name: Optional[str] = None,
        branch_name: Optional[str] = None,
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
    ) -> SupplierRestaurantCreationGQL:
        raise NotImplementedError

    @abstractmethod
    async def search_supplier_business_restaurant(
        self,
        supplier_business_id: UUID,
        restaurant_branch_name: Optional[str] = None,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> List[SupplierRestaurantRelation]:
        raise NotImplementedError

    @abstractmethod
    async def find_supplier_restaurants(
        self,
        firebase_id: str,
        supplier_unit_ids: List[UUID],
    ) -> List[SupplierRestaurantCreationGQL]:
        raise NotImplementedError

    @abstractmethod
    async def find_supplier_restaurant_products(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
    ) -> SupplierRestaurantCreationGQL:
        raise NotImplementedError

    @abstractmethod
    async def add_supplier_restaurant_relation(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        created_by: UUID,
        approved: bool,
        priority: int,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> SupplierRestaurantRelation:
        raise NotImplementedError

    @abstractmethod
    async def find_business_specific_price_ids(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        skip_specific: bool = False,
    ) -> List[UUID]:
        raise NotImplementedError

    @abstractmethod
    async def get_ecommerce_supplier_restaurant_products(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> List[SupplierProductDetails]:
        raise NotImplementedError

    @abstractmethod
    async def get_ecommerce_default_supplier_products(
        self,
        supplier_unit_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> List[SupplierProductDetails]:
        raise NotImplementedError

    @abstractmethod
    async def get_ecommerce_categories(
        self,
        supplier_unit_id: UUID,
    ) -> List[str]:
        raise NotImplementedError

    @abstractmethod
    async def count_ecommerce_supplier_restaurant_products(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        search: str,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def count_ecommerce_default_supplier_products(
        self,
        supplier_unit_id: UUID,
        search: str,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_ecommerce_supplier_restaurant_product_details(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        supplier_product_id: UUID,
    ) -> SupplierProductDetails | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_ecommerce_default_supplier_product_detail(
        self,
        supplier_unit_id: UUID,
        supplier_product_id: UUID,
    ) -> SupplierProductDetails | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def assigned_supplier_restaurant(
        self,
        firebase_id: str,
        restaurant_branch_id: UUID,
        actual_supplier_product_id: UUID,
        set_supplier_product_id: UUID,
    ) -> SupplierRestaurantRelation:
        raise NotImplementedError

    @abstractmethod
    async def get_clients_to_export(
        self,
        firebase_id: str,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_restaurant_branch_infocing_options(
        self, supplier_business_id: UUID, restaurant_branch_id: UUID
    ) -> SupplierRestaurantRelationMxInvoicingOptions | NoneType:
        raise NotImplementedError
    
    @abstractmethod
    async def find_business_specific_price_list_name(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
    ) -> str:
        raise NotImplementedError
    
    @abstractmethod
    async def find_business_default_price_list_name(
        self,
        supplier_unit_id: UUID,
    ) -> str | NoneType:
        raise NotImplementedError


# Repository Interfaces
class SupplierRestaurantsRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self, supplier_restaurant_relation: SupplierRestaurantRelation
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self, supplier_restaurant_relation: SupplierRestaurantRelation
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        supplier_restaurant_relation_id: UUID,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def reasign(
        self,
        restaurant_branch_id: UUID,
        supplier_unit_id: UUID,
        set_supplier_unit_id: UUID,
    ):
        raise NotImplementedError

    @abstractmethod
    async def raw_query(
        self,
        query: str,
        values: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def search_supplier_business_restaurant(
        self,
        supplier_business_id: UUID,
        restaurant_branch_name: Optional[str] = None,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> List[SupplierRestaurantRelation]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_clients_to_export(
        self,
        supplier_business_id: UUID,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError
