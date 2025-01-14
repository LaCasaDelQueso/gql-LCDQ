from abc import ABC
from types import NoneType
from uuid import UUID
from typing import Optional, List
from datetime import datetime, date
from gqlapi.domain.models.v2.supplier import InvoicingOptions
from gqlapi.domain.models.v2.utils import (
    ExecutionStatusType,
    InvoiceType,
    OrdenSourceType,
    RegimenSat,
    SellingOption,
)

from strawberry import type as strawberry_type


from gqlapi.domain.models.v2 import (
    OrdenType,
    OrdenStatusType,
    PayStatusType,
    PayMethodType,
    InvoiceStatusType,
    DeliveryTimeWindow,
    UOMType,
    CategoryType,
)


@strawberry_type
class CoreUser(ABC):
    id: Optional[UUID] = None
    first_name: Optional[str] = ""
    last_name: Optional[str] = ""
    email: str
    phone_number: Optional[str] = ""
    firebase_id: str
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "CoreUser":
        raise NotImplementedError

    @staticmethod
    def get(id: UUID | NoneType = None) -> "CoreUser":
        raise NotImplementedError


@strawberry_type
class PermissionDict(ABC):
    key: str
    validation: bool


@strawberry_type
class RestaurantEmployeeInfoPermission(ABC):
    branch_id: UUID
    permissions: Optional[List[PermissionDict]] = None


@strawberry_type
class SupplierEmployeeInfoPermission(ABC):
    unit_id: UUID
    permissions: Optional[List[PermissionDict]] = None


@strawberry_type
class RestaurantEmployeeInfo(ABC):
    restaurant_user_id: UUID
    name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    branch_permissions: Optional[List[RestaurantEmployeeInfoPermission]] = None


@strawberry_type
class SupplierEmployeeInfo(ABC):
    supplier_user_id: UUID
    name: Optional[str] = None
    last_name: Optional[str] = None
    department: Optional[str] = None
    position: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    unit_permissions: Optional[List[SupplierEmployeeInfoPermission]] = None


@strawberry_type
class Orden(ABC):
    id: UUID
    orden_type: OrdenType
    orden_number: str
    created_by: UUID
    source_type: Optional[OrdenSourceType] = OrdenSourceType.AUTOMATION
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "Orden":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "Orden":
        raise NotImplementedError


@strawberry_type
class OrdenStatus(ABC):
    id: UUID
    orden_id: UUID
    status: Optional[OrdenStatusType] = None
    created_by: UUID
    created_at: Optional[datetime] = None

    def new(self, *args) -> "OrdenStatus":
        raise NotImplementedError

    def get(
        self,
        orden_id: UUID | NoneType = None,
        status: OrdenStatusType | NoneType = None,
    ) -> "OrdenStatus":
        raise NotImplementedError


@strawberry_type
class OrdenDetails(ABC):
    id: UUID
    orden_id: UUID
    version: int  # serial
    restaurant_branch_id: UUID
    supplier_unit_id: UUID
    cart_id: UUID
    delivery_date: Optional[date] = None
    delivery_time: Optional[DeliveryTimeWindow] = None  # Specified by supplier
    delivery_type: Optional[SellingOption] = None  # {pickup, delivery}
    subtotal_without_tax: Optional[float] = None
    tax: Optional[float] = None
    subtotal: Optional[float] = None  # subtotal_without_tax + tax
    discount: Optional[float] = None
    discount_code: Optional[str] = None
    cashback: Optional[float] = None
    cashback_transation_id: Optional[UUID] = None
    shipping_cost: Optional[float] = None
    packaging_cost: Optional[float] = None
    service_fee: Optional[float] = None
    total: Optional[
        float
    ] = None  # subtotal + shipping + packaging + service_fee - discount - cashback
    comments: Optional[str] = None
    payment_method: Optional[PayMethodType] = None
    created_by: UUID
    approved_by: Optional[UUID] = None
    created_at: Optional[datetime] = None

    def new(self, *args) -> "OrdenDetails":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "OrdenDetails":
        raise NotImplementedError


@strawberry_type
class OrdenPayStatus(ABC):
    id: UUID
    orden_id: UUID
    status: Optional[PayStatusType] = None
    created_by: UUID
    created_at: Optional[datetime] = None

    def new(self, *args) -> "OrdenPayStatus":
        raise NotImplementedError

    def get(
        self, orden_id: UUID | NoneType = None, status: PayStatusType | NoneType = None
    ) -> "OrdenPayStatus":
        raise NotImplementedError


@strawberry_type
class PaymentReceipt(ABC):
    id: UUID
    payment_value: float
    evidence_file: Optional[str] = None  # json encoded file
    comments: Optional[str] = None
    created_by: UUID
    payment_day: Optional[date] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "PaymentReceipt":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "PaymentReceipt":
        raise NotImplementedError


@strawberry_type
class MxInvoiceComplement(ABC):
    id: Optional[UUID] = None
    mx_invoice_id: UUID
    sat_invoice_uuid: UUID
    invoice_number: str  # folio (nullable)
    invoice_provider_id: Optional[str] = None
    invoice_provider: Optional[str] = None
    pdf_file: Optional[bytes] = None
    xml_file: Optional[bytes] = None
    total: float
    status: InvoiceStatusType
    result: Optional[str] = None
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "MxInvoiceComplement":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "MxInvoiceComplement":
        raise NotImplementedError


@strawberry_type
class PaymentReceiptOrden(ABC):
    id: UUID
    payment_receipt_id: UUID
    orden_id: UUID
    mx_invoice_complement_id: Optional[UUID] = None
    created_by: UUID
    deleted: bool = False
    created_at: Optional[datetime] = None

    def new(self, *args) -> "PaymentReceiptOrden":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "PaymentReceiptOrden":
        raise NotImplementedError


@strawberry_type
class MxInvoice(ABC):
    id: Optional[UUID | str] = None
    supplier_business_id: UUID
    restaurant_branch_id: UUID
    sat_invoice_uuid: UUID
    invoice_number: str  # folio (nullable)
    invoice_provider_id: Optional[str] = None
    invoice_provider: Optional[str] = None
    pdf_file: Optional[bytes] = None
    xml_file: Optional[bytes] = None
    total: float
    status: InvoiceStatusType
    result: Optional[str] = None
    cancel_result: Optional[str] = None
    payment_method: InvoiceType
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "MxInvoice":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "MxInvoice":
        raise NotImplementedError


@strawberry_type
class MxSatInvoicingCertificateInfo(ABC):
    rfc: str
    zip_code: str
    invoicing_options: InvoicingOptions
    legal_name: str
    cer_file: str  # binary file
    key_file: str  # binary file
    sat_pass_code: str
    sat_regime: RegimenSat
    supplier_unit_id: Optional[UUID] = None
    invoicing_provider_id: Optional[str] = None  # facturama id

    def new(self, *args) -> "MxInvoice":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "MxInvoice":
        raise NotImplementedError


@strawberry_type
class MxInvoicePayStatus(ABC):
    mx_invoice_id: UUID
    status: PayStatusType
    created_by: UUID
    created_at: datetime

    def new(self, *args) -> "MxInvoicePayStatus":
        raise NotImplementedError

    def get(
        self,
        mx_invoice_id: UUID | NoneType = None,
        status: PayStatusType | NoneType = None,
    ) -> "MxInvoicePayStatus":
        raise NotImplementedError


@strawberry_type
class MxInvoiceOrden(ABC):
    id: UUID
    mx_invoice_id: UUID
    orden_details_id: UUID
    created_by: UUID
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "MxInvoiceOrden":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "MxInvoiceOrden":
        raise NotImplementedError


@strawberry_type
class MxInvoicingExecution(ABC):
    id: UUID
    orden_details_id: UUID
    execution_start: datetime
    execution_end: Optional[datetime] = None
    status: Optional[ExecutionStatusType] = None
    result: str


@strawberry_type
class Cart(ABC):
    id: UUID
    active: bool
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    def new(self, *args) -> "Cart":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "Cart":
        raise NotImplementedError


@strawberry_type
class CartProduct(ABC):
    cart_id: Optional[UUID] = None
    supplier_product_id: UUID
    supplier_product_price_id: Optional[UUID] = None  # (nullable)
    quantity: float
    unit_price: Optional[float] = None
    subtotal: Optional[float] = None
    comments: Optional[str] = None
    sell_unit: UOMType  # SellUOM
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "CartProduct":
        raise NotImplementedError

    def get(
        self,
        cart_id: UUID | NoneType = None,
        supplier_product_id: UUID | NoneType = None,
    ) -> "CartProduct":
        raise NotImplementedError


@strawberry_type
class Product(ABC):
    id: UUID
    product_family_id: UUID
    sku: str  # serial
    upc: Optional[str]  # International UPC - Barcode (optional)
    name: str
    description: str
    keywords: List[str]  # related words, synonims, ...
    sell_unit: UOMType  # SellUOM
    conversion_factor: float
    buy_unit: UOMType  # BuyUOM
    estimated_weight: Optional[float] = None
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "Product":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "Product":
        raise NotImplementedError


@strawberry_type
class Category(ABC):
    id: UUID
    name: str
    category_type: CategoryType
    keywords: Optional[List[str]] = None
    parent_category_id: Optional[UUID] = None  # nullable
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "Category":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "Category":
        raise NotImplementedError


@strawberry_type
class ProductFamily(ABC):
    id: UUID
    name: str
    buy_unit: UOMType  # BuyUOM
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "ProductFamily":
        raise NotImplementedError

    def get(self, id: UUID | NoneType = None) -> "ProductFamily":
        raise NotImplementedError


@strawberry_type
class ProductFamilyCategory(ABC):
    product_family_id: UUID
    category_id: UUID
    created_by: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "ProductFamilyCategory":
        raise NotImplementedError

    def get(
        self,
        product_family_id: UUID | NoneType = None,
        category_id: UUID | NoneType = None,
    ) -> "ProductFamilyCategory":
        raise NotImplementedError


@strawberry_type
class MxSatProductCode(ABC):
    id: UUID
    sat_code: str
    sat_description: str
    created_at: datetime
