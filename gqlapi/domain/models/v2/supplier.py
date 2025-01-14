from abc import ABC
from types import NoneType
from uuid import UUID
from typing import List, Optional, Union
from io import BytesIO, StringIO
from datetime import datetime, date

from strawberry import type as strawberry_type

from gqlapi.domain.models.v2.utils import (
    InvoiceConsolidation,
    InvoiceTriggerTime,
    InvoiceType,
    OrderSize,
    PayMethodType,
    SellingOption,
    ServiceDay,
    SupplierBusinessType,
)
from gqlapi.domain.models.v2 import (
    UOMType,
    NotificationChannelType,
    CurrencyType,
    SupplierRestaurantStatusType,
    VehicleType,
    Location,
    DeliveryTimeWindow,
)


@strawberry_type
class SupplierUser(ABC):
    id: UUID
    core_user_id: UUID
    role: str
    enabled: bool
    deleted: bool
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierUser":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierUser":
        raise NotImplementedError


@strawberry_type
class SupplierUserPermission(ABC):
    id: UUID
    supplier_user_id: UUID
    supplier_business_id: Optional[UUID] = None
    display_sales_section: bool
    display_routes_section: bool
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierUserPermission":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierUserPermission":
        raise NotImplementedError


@strawberry_type
class SupplierBusiness(ABC):
    id: UUID
    name: str
    country: str
    active: bool  # with an onboarded & active account in Alima
    notification_preference: NotificationChannelType
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    logo_url: Optional[str] = None

    def new(self, *args) -> "SupplierBusiness":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierBusiness":
        raise NotImplementedError


@strawberry_type
class SupplierUnit(ABC):
    id: UUID
    supplier_business_id: UUID
    unit_name: str
    full_address: str
    street: str
    external_num: str
    internal_num: str
    neighborhood: str
    city: str
    state: str
    country: str
    zip_code: str
    deleted: Optional[bool] = None
    created_at: datetime
    last_updated: datetime
    account_number: str
    allowed_payment_methods: List[str]


@strawberry_type
class InvoicingOptions(ABC):
    automated_invoicing: bool
    triggered_at: Optional[InvoiceTriggerTime] = None
    consolidation: Optional[InvoiceConsolidation] = None
    invoice_type: Optional[InvoiceType] = None


@strawberry_type
class SupplierRestaurantRelationMxInvoicingOptions(InvoicingOptions):
    supplier_restaurant_relation_id: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


@strawberry_type
class DeliveryOptions(ABC):
    selling_option: List[SellingOption]
    service_hours: List[ServiceDay]
    regions: List[str]
    delivery_time_window: int
    warning_time: int  # num of days before (1 -> day before)
    cutoff_time: int  # in 24hr format


@strawberry_type
class SupplierUnitDeliveryOptions(DeliveryOptions):
    supplier_unit_id: UUID


@strawberry_type
class MinimumOrderValue(ABC):
    measure: Optional[OrderSize] = None
    amount: Optional[float] = None


@strawberry_type
class SupplierBusinessCommertialConditions(ABC):
    minimum_order_value: MinimumOrderValue
    allowed_payment_methods: List[PayMethodType]
    policy_terms: str
    account_number: Optional[str] = None


@strawberry_type
class SupplierBusinessAccount(ABC):
    supplier_business_id: UUID
    business_type: Optional[SupplierBusinessType] = None
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
    mx_zip_code: Optional[str] = None
    default_commertial_conditions: Optional[SupplierBusinessCommertialConditions] = None
    requires_customer_validation: Optional[bool] = None  # deprecate
    displays_in_marketplace: Optional[bool] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierBusinessAccount":
        raise NotImplementedError

    def get(
        self, supplier_business_id: UUID | NoneType = None
    ) -> "SupplierBusinessAccount":
        raise NotImplementedError


@strawberry_type
class SupplierUnitCategory(ABC):
    supplier_unit_id: UUID
    supplier_category_id: UUID
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierUnitCategory":
        raise NotImplementedError

    def get(
        self,
        supplier_unit_id: UUID | NoneType = None,
        supplier_category_id: UUID | NoneType = None,
    ) -> "SupplierUnitCategory":
        raise NotImplementedError


@strawberry_type
class SupplierProduct(ABC):
    id: UUID
    product_id: Optional[UUID] = None  # (optional)
    supplier_business_id: UUID
    sku: str  # Internal supplier code
    upc: Optional[str] = None  # International UPC - Barcode (optional)
    description: str
    tax_id: str  # MX: SAT Unique Product tax id
    sell_unit: UOMType  # SellUOM
    tax_unit: str  # MX: SAT Unique Unit tax id
    tax: float  # percentage rate of the product value to apply for tax
    mx_ieps: Optional[float] = None
    conversion_factor: float
    buy_unit: UOMType  # BuyUOM
    unit_multiple: float
    min_quantity: float
    estimated_weight: Optional[float] = None
    is_active: bool
    long_description: Optional[str] = None
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierProduct":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierProduct":
        raise NotImplementedError


@strawberry_type
class SupplierProductTag(ABC):
    id: UUID
    supplier_product_id: UUID
    tag_key: Optional[str] = None
    tag_value: Optional[str] = None
    created_at: Optional[datetime] = None

    def new(self, *args) -> "SupplierProductTag":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierProductTag":
        raise NotImplementedError


@strawberry_type
class SupplierProductStock(ABC):
    id: UUID
    supplier_product_id: UUID
    supplier_unit_id: Optional[UUID] = None
    stock: float
    stock_unit: UOMType  # StockUOM
    keep_selling_without_stock: bool
    active: bool
    created_by: UUID
    created_at: Optional[datetime] = None

    def new(self, *args) -> "SupplierProductStock":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierProductStock":
        raise NotImplementedError


@strawberry_type
class SupplierProductPrice(ABC):
    id: UUID
    supplier_product_id: UUID
    price: float
    currency: CurrencyType
    valid_from: datetime
    valid_upto: datetime
    created_by: UUID
    created_at: Optional[datetime] = None

    def new(self, *args) -> "SupplierProductPrice":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierProductPrice":
        raise NotImplementedError


@strawberry_type
class SupplierPriceList(ABC):
    id: UUID
    name: str
    supplier_unit_id: UUID
    supplier_restaurant_relation_ids: List[UUID]
    supplier_product_price_ids: List[UUID]
    is_default: bool
    valid_from: datetime
    valid_upto: datetime
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierPriceList":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierPriceList":
        raise NotImplementedError


@strawberry_type
class SupplierProductImage(ABC):
    id: UUID
    supplier_product_id: UUID
    deleted: float
    image_url: str
    priority: int
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierProductPrice":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierProductPrice":
        raise NotImplementedError


@strawberry_type
class SupplierRestaurantRelation(ABC):
    id: UUID
    supplier_unit_id: UUID
    restaurant_branch_id: UUID
    approved: bool  # Validation flag to allow
    priority: int  # 1 is more, N is less important
    rating: Optional[int] = None  # ( 0 to 5, nullable)
    review: Optional[str] = None  # (nullable)
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "SupplierRestaurantRelation":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierRestaurantRelation":
        raise NotImplementedError


@strawberry_type
class SupplierRestaurantRelationStatus(ABC):
    id: UUID
    supplier_restaurant_relation_id: UUID
    status: SupplierRestaurantStatusType
    created_by: UUID
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierRestaurantRelationStatus":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierRestaurantRelationStatus":
        raise NotImplementedError


# [TO-REV] To review implementation
@strawberry_type
class SupplierRestaurantAgreement(ABC):
    supplier_restaurant_relation_id: UUID

    def new(self, *args) -> "SupplierRestaurantAgreement":
        raise NotImplementedError

    def get(
        self, supplier_restaurant_relation_id: UUID | NoneType = None
    ) -> "SupplierRestaurantAgreement":
        raise NotImplementedError


@strawberry_type
class SupplierRoute(ABC):
    id: UUID
    vehicle_id: UUID
    driver_user_id: UUID
    start_time: datetime
    actual_start_time: datetime
    route_distance: float  # in KMs
    route_total_time: int  # in seconds
    route_total_weight: float  # in KGs
    actual_end_time: datetime  # (nullable)
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierRoute":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierRoute":
        raise NotImplementedError


@strawberry_type
class SupplierRouteOrden(ABC):
    id: UUID
    supplier_route_id: UUID
    orden_id: UUID
    stop_number: int
    delivery_time: DeliveryTimeWindow
    actual_delivery_time: datetime
    estimated_weight: float
    source_location: Location
    destination_location: Location
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierRouteOrden":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierRouteOrden":
        raise NotImplementedError


@strawberry_type
class SupplierDeliveryEvidence(ABC):
    id: UUID
    supplier_route_orden_id: UUID
    receiver_name: str
    receiver_signature: Union[BytesIO, StringIO]  # Binary file  (nullable)
    evidence_picture: List[Union[BytesIO, StringIO]]  # Binary file array
    created_by: UUID
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierDeliveryEvidence":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierDeliveryEvidence":
        raise NotImplementedError


@strawberry_type
class SupplierVehicle(ABC):
    id: UUID
    supplier_business_id: UUID
    vehicle_type: VehicleType
    max_weight: float
    name: str
    plates: str
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierVehicle":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierVehicle":
        raise NotImplementedError


@strawberry_type
class SupplierDriverRelation(ABC):
    id: UUID
    supplier_unit_id: UUID
    driver_user_id: UUID
    license_img: Union[BytesIO, StringIO]  # (nullable)
    license_number: str  # (nullable)
    license_valid_until: date  # (nullable)
    created_by: UUID
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierDriverRelation":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierDriverRelation":
        raise NotImplementedError


@strawberry_type
class SupplierNotifications(ABC):
    id: UUID
    supplier_user_id: UUID
    notify_new_resturant_orden: bool
    notify_closing_day: bool
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "SupplierNotifications":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierNotifications":
        raise NotImplementedError


@strawberry_type
class SupplierCashbackTransaction(ABC):
    id: UUID
    supplier_unit_id: UUID
    restaurant_branch_id: UUID
    concept: str
    amount: float  # negative is a charge, positive is deposit
    created_by: UUID
    created_at: datetime

    def new(self, *args) -> "SupplierCashbackTransaction":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "SupplierCashbackTransaction":
        raise NotImplementedError
