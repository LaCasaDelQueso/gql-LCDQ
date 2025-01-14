from abc import ABC, abstractmethod
from datetime import date, datetime
from types import NoneType
from typing import List, Dict, Any, Optional, Sequence
from uuid import UUID
from gqlapi.domain.interfaces.v2.integrations.integrations import (
    IntegrationWebhookHandlerInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import MxInvoiceGQL
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitGQL

import strawberry

from gqlapi.domain.interfaces.v2.orden.cart import CartProductGQL
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import RestaurantBranchGQL
from gqlapi.domain.models.v2.core import (
    CartProduct,
    CoreUser,
    Orden,
    OrdenDetails,
    OrdenPayStatus,
    OrdenStatus,
    PaymentReceipt,
    PaymentReceiptOrden,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
    SupplierBusinessAccount,
)
from gqlapi.domain.models.v2.utils import (
    DeliveryTimeWindow,
    OrdenStatusType,
    OrdenType,
    PayMethodType,
    PayStatusType,
    SellingOption,
)


@strawberry.type
class OrdenError:
    msg: str
    code: int


@strawberry.type
class OrdenStatusConfirmMsg:
    msg: str
    status: bool


@strawberry.input
class CartProductInput(CartProduct):
    pass


@strawberry.input
class PaymentAmountInput:
    orden_id: UUID
    amount: float


@strawberry.type
class OrdenSupplierGQL:
    supplier_business: Optional[SupplierBusiness] = None
    supplier_business_account: Optional[SupplierBusinessAccount] = None
    supplier_unit: Optional[SupplierUnitGQL] = None


@strawberry.type
class OrdenGQL(Orden):
    status: Optional[OrdenStatus] = None
    details: Optional[OrdenDetails] = None
    paystatus: Optional[OrdenPayStatus] = None
    cart: Optional[List[CartProductGQL]] = None
    supplier: Optional[OrdenSupplierGQL] = None
    branch: Optional[RestaurantBranchGQL] = None


@strawberry.type
class MxInvoiceComplementGQL:
    id: UUID
    sat_invoice_uuid: UUID
    pdf_file: Optional[str] = None
    xml_file: Optional[str] = None
    total: float


@strawberry.type
class PaymentReceiptOrdenGQL(PaymentReceiptOrden):
    payment_complement: Optional[MxInvoiceComplementGQL] = None
    pass


@strawberry.type
class PaymentReceiptGQL(PaymentReceipt):
    ordenes: Optional[List[PaymentReceiptOrdenGQL]] = None


@strawberry.type
class OrdenPaystatusGQL:
    paystatus: Optional[OrdenPayStatus] = None
    core_user: Optional[CoreUser] = None
    pay_receipts: Optional[List[PaymentReceiptGQL]] = None


@strawberry.type
class ExportOrdenGQL:
    file: str  # encoded file
    extension: str = "csv"  # {csv, xlsx} default = csv


OrdenResult = strawberry.union(
    "OrdenResult",
    (
        OrdenError,
        OrdenGQL,
    ),
)

OrdenStatusResult = strawberry.union(
    "OrdenStatusResult",
    (
        OrdenError,
        OrdenStatus,
    ),
)

OrdenPaystatusResult = strawberry.union(
    "OrdenPaystatusResult",
    (
        OrdenError,
        OrdenPaystatusGQL,
    ),
)

ExportOrdenResult = strawberry.union(
    "ExportOrdenResult",
    (
        OrdenError,
        ExportOrdenGQL,
    ),
)

OrdenStatusExternalResult = strawberry.union(
    "OrdenStatusExternalResult",
    (
        OrdenError,
        OrdenStatusConfirmMsg,
    ),
)

PaymentReceiptResult = strawberry.union(
    "PaymentReceiptResult",
    (
        PaymentReceiptGQL,
        OrdenError,
    ),
)


@strawberry.input
class DeliveryTimeWindowInput(DeliveryTimeWindow):
    pass


class OrdenHandlerInterface(ABC):
    @abstractmethod
    async def new_orden(
        self,
        orden_type: OrdenType,
        firebase_id: str,
        restaurant_branch_id: UUID,
        cart_products: List[CartProduct],
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        raise NotImplementedError

    @abstractmethod
    async def new_orden_marketplace(
        self,
        orden_type: OrdenType,
        firebase_id: str,
        restaurant_branch_id: UUID,
        cart_products: List[CartProduct],
        supplier_unit_id: Optional[UUID] = None,
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        raise NotImplementedError

    @abstractmethod
    async def new_orden_ecommerce(
        self,
        orden_type: OrdenType,
        restaurant_branch_id: UUID,
        cart_products: List[CartProduct],
        supplier_unit_id: UUID,
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,  # noqa
        cashback_transation_id: Optional[UUID] = None,  # noqa
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_orden(
        self,
        firebase_id: str,
        orden_id: UUID,
        orden_type: Optional[OrdenType] = None,
        cart_products: Optional[List[CartProductInput]] = None,
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[date] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_orden_status(self, orden_id: UUID) -> OrdenStatus:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def add_payment_receipt(
        self,
        firebase_id: str,
        orden_ids: List[UUID],
        payment_value: float,
        payment_day: date,
        comments: Optional[str] = None,
        receipt_file: Optional[str] = None,
    ) -> PaymentReceiptGQL:
        raise NotImplementedError

    @abstractmethod
    async def edit_payment_receipt(
        self,
        firebase_id: str,
        payment_receipt_id: UUID,
        payment_value: Optional[float] = None,
        comments: Optional[str] = None,
        payment_day: Optional[datetime] = None,
        receipt_file: Optional[str] = None,
        orden_ids: Optional[List[UUID]] = None,
    ) -> PaymentReceiptGQL:
        raise NotImplementedError

    @abstractmethod
    async def search_orden(
        self,
        orden_id: Optional[UUID] = None,
        orden_type: Optional[OrdenType] = None,
        status: Optional[OrdenStatusType] = None,
        paystatus: Optional[PayStatusType] = None,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        payment_method: Optional[PayMethodType] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[OrdenGQL]:
        raise NotImplementedError

    @abstractmethod
    async def find_orden(
        self,
        orden_id: Optional[UUID] = None,
        orden_type: Optional[OrdenType] = None,
        status: Optional[OrdenStatusType] = None,
        paystatus: Optional[PayStatusType] = None,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        payment_method: Optional[PayMethodType] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[OrdenGQL]:
        raise NotImplementedError

    @abstractmethod
    async def search_ordens_with_many(self, orden_ids: List[UUID]) -> List[OrdenGQL]:
        raise NotImplementedError

    @abstractmethod
    async def merge_ordenes_invoices(
        self, ordenes: List[OrdenGQL], invoices: List[MxInvoiceGQL]
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def get_customer_payments_by_dates(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        comments: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[PaymentReceiptGQL]:
        raise NotImplementedError

    @abstractmethod
    async def count_daily_ordenes(self, supplier_business_id: UUID) -> int:
        raise NotImplementedError


class OrdenRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, orden: Orden) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(self, orden: Orden) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(self, orden_id: UUID, orden_type: OrdenType) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        orden_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_orders(
        self, filter_values: str | None, info_values_view: Dict[Any, Any]
    ) -> Sequence:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def find_orders(
        self, filter_values: str | None, info_values_view: Dict[Any, Any]
    ) -> Sequence:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        orden_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def validation(
        self,
        orden_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def count_by_supplier_business(self, supplier_business_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_by_created_at_range(
        self, supplier_business_id: UUID, from_date: datetime, until_date: datetime
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError


class OrdenStatusRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, orden_status: OrdenStatus) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        orden_status: OrdenStatus,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def update(self, orden_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_last(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    async def fetch_last(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exist(
        self,
        orden_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        orden_id: UUID,
    ) -> List[OrdenStatus]:
        raise NotImplementedError


class OrdenDetailsRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, orden_details: OrdenDetails) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(self, orden_details: OrdenDetails) -> NoneType | UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(self, orden_details_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, orden_details_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        orden_details_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_last(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_last(
        self,
        orden_details_id: UUID,
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        orden_details_id: UUID,
    ) -> NoneType:
        raise NotImplementedError


class OrdenPaymentStatusRepositoryInterface(ABC):
    @abstractmethod
    async def new(self, orden_paystatus: OrdenPayStatus) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add(self, orden_paystatus: OrdenPayStatus) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update(self, orden_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_last(self, orden_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        orden_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        orden_id: UUID,
    ) -> List[OrdenPayStatus]:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        orden_id: UUID,
    ) -> List[OrdenPayStatus]:
        raise NotImplementedError

    @abstractmethod
    async def find_payment_receipts(
        self,
        orden_id: UUID,
    ) -> List[PaymentReceiptGQL]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_payment_receipt(
        self, payment_receipt_id: UUID
    ) -> PaymentReceipt | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add_payment_receipt(self, receipt: PaymentReceipt) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_payment_receipt_association(
        self,
        receipt_orden: PaymentReceiptOrden,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit_payment_receipt(self, receipt: PaymentReceipt) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit_payment_receipt_association(
        self,
        receipt_ordens: List[PaymentReceiptOrden],
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_payment_complement_receipt_association(
        self, payment_receipt_orden_id: UUID, mx_invoice_complement_id: UUID
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def find_payment_receipts_by_dates(
        self,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        comments: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError


class OrdenHookListenerInterface:
    @staticmethod
    async def on_orden_created(
        webhook_handler: IntegrationWebhookHandlerInterface,
        orden_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        restaurant_business_id: Optional[UUID] = None,
    ) -> bool:
        raise NotImplementedError
