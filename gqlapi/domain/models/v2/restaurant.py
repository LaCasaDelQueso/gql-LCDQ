from abc import ABC
from types import NoneType
from typing import Optional
from uuid import UUID
from datetime import datetime
from gqlapi.domain.models.v2.utils import CFDIUse, RegimenSat, RestaurantBusinessType

from strawberry import type as strawberry_type


@strawberry_type
class RestaurantUser(ABC):
    id: UUID
    core_user_id: UUID
    role: Optional[str]
    enabled: bool
    deleted: bool
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "RestaurantUser":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantUser":
        raise NotImplementedError


@strawberry_type
class RestaurantUserPermission(ABC):
    id: UUID
    restaurant_user_id: UUID
    restaurant_business_id: UUID
    display_orders_section: bool
    display_suppliers_section: bool
    display_products_section: bool
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "RestaurantUserPermission":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantUserPermission":
        raise NotImplementedError


@strawberry_type
class RestaurantBusiness(ABC):
    id: UUID
    name: str
    country: str
    active: bool  # with an onboarded & active account in Alima
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "RestaurantBusiness":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantBusiness":
        raise NotImplementedError


@strawberry_type
class RestaurantBusinessAccount(ABC):
    restaurant_business_id: UUID
    business_type: Optional[RestaurantBusinessType] = None
    legal_business_name: Optional[str] = None
    incorporation_file: Optional[str] = None
    legal_rep_name: Optional[str] = None
    legal_rep_id: Optional[str] = None
    legal_address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    mx_sat_regimen: Optional[str] = None
    mx_sat_rfc: Optional[str] = None
    mx_sat_csf: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "RestaurantBusinessAccount":
        raise NotImplementedError

    def get(
        self, restaurant_business_id: UUID | NoneType = None
    ) -> "RestaurantBusinessAccount":
        raise NotImplementedError


@strawberry_type
class RestaurantBranch(ABC):
    id: UUID
    restaurant_business_id: UUID
    branch_name: str
    full_address: str
    street: str
    external_num: str
    internal_num: str
    neighborhood: str
    city: str
    state: str
    country: str
    zip_code: str
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    deleted: Optional[bool] = None

    def new(self, *args) -> "RestaurantBranch":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantBranch":
        raise NotImplementedError


@strawberry_type
class RestaurantBranchTag(ABC):
    id: UUID
    restaurant_branch_id: UUID
    tag_key: str
    tag_value: str
    created_at: Optional[datetime] = None

    def new(self, *args) -> "RestaurantBranchTag":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantBranchTag":
        raise NotImplementedError


@strawberry_type
class RestaurantBranchCategory(ABC):
    restaurant_branch_id: UUID
    restaurant_category_id: UUID
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "RestaurantBranchCategory":
        raise NotImplementedError

    def get(
        self,
        restaurant_unit_id: UUID | NoneType = None,
        restaurant_category_id: UUID | NoneType = None,
    ) -> "RestaurantBranchCategory":
        raise NotImplementedError


@strawberry_type
class RestaurantBranchMxInvoiceInfo(ABC):
    branch_id: UUID
    mx_sat_id: str  # rfc
    email: str
    legal_name: str
    full_address: str
    zip_code: str
    sat_regime: RegimenSat
    cfdi_use: CFDIUse
    invoicing_provider_id: Optional[str] = None
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "RestaurantBranchMxInvoiceInfo":
        raise NotImplementedError

    def get(
        self,
        restaurant_branch_id: UUID | NoneType = None,
        mx_sat_id: UUID | NoneType = None,
    ) -> "RestaurantBranchMxInvoiceInfo":
        raise NotImplementedError


@strawberry_type
class RestaurantNotifications(ABC):
    id: UUID
    restaurant_user_id: UUID
    notify_new_supplier_delivery: bool
    notify_reminder_to_buy: bool
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "RestaurantNotifications":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantNotifications":
        raise NotImplementedError


@strawberry_type
class RestaurantSupplierRelation(ABC):
    id: UUID
    restaurant_branch_id: UUID
    supplier_business_id: UUID
    rating: Optional[int] = None  # ( 0 to 5, nullable)
    review: Optional[str] = None
    created_by: UUID
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "RestaurantSupplierRelation":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "RestaurantSupplierRelation":
        raise NotImplementedError
