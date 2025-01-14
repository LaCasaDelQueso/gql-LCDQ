from abc import ABC, abstractmethod
from types import NoneType
from typing import Optional, List, Dict, Any
from uuid import UUID
from gqlapi.domain.models.v2.core import Category, RestaurantEmployeeInfo
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranch,
    RestaurantBranchCategory,
    RestaurantBranchMxInvoiceInfo,
    RestaurantBranchTag,
)
from gqlapi.domain.models.v2.supplier import SupplierRestaurantRelationMxInvoicingOptions
from gqlapi.domain.models.v2.utils import (
    CFDIUse,
    InvoiceConsolidation,
    InvoiceTriggerTime,
    InvoiceType,
    RegimenSat,
)
from gqlapi.lib.future.future.deprecation import deprecated
import strawberry


@strawberry.input
class RestaurantBranchTagInput:
    tag: str
    value: str


@strawberry.type
class RestaurantBranchError:
    msg: str
    code: int


@strawberry.type
class RestaurantBranchContactInfo:
    business_name: Optional[str] = None
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None


@strawberry.type
class RestaurantBranchGQL(RestaurantBranch):
    branch_category: Optional[RestaurantBranchCategory] = None
    tax_info: Optional[RestaurantBranchMxInvoiceInfo] = None
    contact_info: Optional[RestaurantBranchContactInfo] = None
    invoice_options: Optional[SupplierRestaurantRelationMxInvoicingOptions] = None
    tags: Optional[List[RestaurantBranchTag]] = None


RestaurantBranchResult = strawberry.union(
    "RestaurantBranchResult",
    (RestaurantBranchGQL, RestaurantBranchError),
)


@strawberry.type
class RestaurantCategories:
    categories: List[Category]


RestaurantCategoryResult = strawberry.union(
    "RestaurantCategoryResult",
    (RestaurantCategories, RestaurantBranchError),
)

RestaurantBranchTaxResult = strawberry.union(
    "RestaurantBranchTaxResult",
    (
        RestaurantBranchError,
        RestaurantBranchMxInvoiceInfo,
    ),
)

RestaurantBranchEmployeeResult = strawberry.union(
    "RestaurantBranchEmployeeResult",
    (
        RestaurantBranchError,
        RestaurantEmployeeInfo,
    ),
)


class RestaurantBranchHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_branch(
        self,
        restaurant_business_id: UUID,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        firebase_id: str,
        category_id: UUID,
    ) -> RestaurantBranchGQL:
        raise NotImplementedError

    @abstractmethod
    async def new_ecommerce_restaurant_address(
        self,
        restaurant_business_id: UUID,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        category_id: Optional[UUID] = None,
    ) -> RestaurantBranchGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_ecommerce_restaurant_branch(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        category_id: Optional[UUID] = None,
        deleted: Optional[bool] = None,
    ) -> RestaurantBranchGQL:
        raise NotImplementedError

    @abstractmethod
    async def new_restaurant_branch_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: str,
        email: str,
        legal_name: str,
        full_address: str,
        zip_code: str,
        sat_regime: RegimenSat,
        cfdi_use: CFDIUse,
    ) -> RestaurantBranchMxInvoiceInfo:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_branch(
        self,
        restaurant_branch_id=UUID,
        branch_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        category_id: Optional[UUID] = None,
    ) -> RestaurantBranchGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_branch_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> RestaurantBranchMxInvoiceInfo:  # type: ignore
        raise NotImplementedError

    async def fetch_restaurant_branches(
        self,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchGQL]:  # type: ignore
        raise NotImplementedError


class RestaurantBranchRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        restaurant_business_id: UUID,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        restaurant_branch: RestaurantBranch,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        deleted: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        deleted: Optional[bool] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def new_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: str,
        email: str,
        legal_name: str,
        full_address: str,
        zip_code: str,
        sat_regime: RegimenSat,
        cfdi_use: CFDIUse,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get_tax_info(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_tax_info(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError
    
    @abstractmethod
    async def fetch_tax_info_from_many(self, restaurant_branch_id_list: List[UUID]) -> List[RestaurantBranchMxInvoiceInfo]:
        raise NotImplementedError

    @abstractmethod
    async def get_restaurant_branches(
        self,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchGQL]:  # type: ignore
        raise NotImplementedError

    @deprecated("Use exists() instead", "domain")
    @abstractmethod
    async def exist(
        self,
        rest_branch_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        rest_branch_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def exist_relation_rest_supp(
        self, restaurant_branch_id: UUID, supplier_business_id: UUID
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add_tags(
        self,
        restaurant_branch_id: UUID,
        tags: List[RestaurantBranchTag],
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_tags(
        self,
        restaurant_branch_id: UUID,
    ) -> List[RestaurantBranchTag]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_tags_from_many(
        self,
        restaurant_branch_ids: List[UUID],
    ) -> List[RestaurantBranchTag]:
        raise NotImplementedError


class RestaurantBranchInvoicingOptionsRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        branch_invoicing_options: SupplierRestaurantRelationMxInvoicingOptions,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        supplier_restaurant_relation_id: UUID,
        automated_invoicing: bool,
        invoice_type: InvoiceType,
        triggered_at: Optional[InvoiceTriggerTime] = None,
        consolidation: Optional[InvoiceConsolidation] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self, supplier_restaurant_relation_id: UUID
    ) -> SupplierRestaurantRelationMxInvoicingOptions | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, supplier_restaurant_relation_id: UUID) -> NoneType:
        raise NotImplementedError


class RestaurantBranchEmployeeHandlerInterface(ABC):
    @abstractmethod
    async def new_restaurant_branch_employee(
        self,
        restaurant_business_id: UUID,
        restaurant_branch_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        department: Optional[str] = None,
        position: Optional[str] = None,
    ) -> RestaurantEmployeeInfo:
        raise NotImplementedError

    @abstractmethod
    async def edit_restaurant_branch_employee(
        self,
        restaurant_business_id: UUID,
        id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
    ) -> RestaurantEmployeeInfo:
        raise NotImplementedError
