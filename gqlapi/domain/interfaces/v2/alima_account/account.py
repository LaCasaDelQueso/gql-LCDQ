from abc import ABC, abstractmethod
from datetime import date, datetime
from enum import Enum
from types import NoneType
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    EcommerceSellerHandlerInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import InvoiceStatus
from gqlapi.domain.interfaces.v2.supplier.supplier_business import SupplierBusinessGQL
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from gqlapi.domain.models.v2.utils import (
    AlimaCustomerType,
    InvoiceStatusType,
    InvoiceType,
    PayProviderType,
    PayStatusType,
)
import strawberry

from gqlapi.domain.models.v2.alima_business import (
    BillingInvoice,
    BillingInvoiceCharge,
    BillingInvoicePaystatus,
    BillingPaymentMethod,
    Charge,
    ChargeDiscount,
    PaidAccount,
    PaidAccountConfig,
)


@strawberry.type
class SupplierAlimaAccountError:
    msg: str
    code: int


@strawberry.enum
class LocalPaymentForm(Enum):
    CASH = "01"
    MONEY_ORDER = "02"
    TRANSFER = "03"
    CARD = "04"
    TBD = "99"


@strawberry.enum
class AlimaAccountPlan(Enum):
    ALIMA_COMERCIAL = "alima_comercial"
    ALIMA_PRO = "alima_pro"


ALIMA_PLANS_WITH_ECOMM = [AlimaAccountPlan.ALIMA_COMERCIAL, AlimaAccountPlan.ALIMA_PRO]


@strawberry.enum
class AlimaAccountPlanDiscount(Enum):
    SAAS_YEARLY = "saas_yearly"


@strawberry.type
class BillingPaymentMethodGQL(BillingPaymentMethod):
    provider_data: Optional[str] = None  # JSON formatted data


@strawberry.type
class BillingAccount:
    business: SupplierBusinessGQL
    paid_account: PaidAccount
    payment_method: BillingPaymentMethod


@strawberry.type
class BillingReport:
    paid_account_id: UUID
    supplier: Optional[str] = None
    invoice_name: Optional[str] = None
    status: bool
    reason: str
    execution_time: Optional[datetime] = None


@strawberry.type
class BillingTotalDue:
    charges: List[BillingInvoiceCharge]
    subtotal_due: float
    tax_due: float
    total_due: float


@strawberry.type
class SupplierAlimaAccount:
    supplier_business_id: UUID
    displayed_in_marketplace: Optional[bool] = None
    active_cedis: Optional[float] = None
    account: Optional[PaidAccount] = None
    charges: List[Charge]
    discounts: Optional[List[ChargeDiscount]] = None
    payment_methods: List[BillingPaymentMethodGQL]


@strawberry.type
class SupplierAlimaAccountConfig:
    supplier_business_id: UUID
    paid_account_id: Optional[UUID] = None
    config: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


@strawberry.type
class SupplerAlimaStripeIntentSecret:
    secret: str


@strawberry.type
class SupplerAlimaStripeResponse:
    status: bool
    msg: str
    data: Optional[str] = None


SupplierAlimaAccountResult = strawberry.union(
    "SupplierAlimaAccountResult", (SupplierAlimaAccount, SupplierAlimaAccountError)
)

SupplierAlimaAccountConfigResult = strawberry.union(
    "SupplierAlimaAccountConfigResult",
    (SupplierAlimaAccountConfig, SupplierAlimaAccountError),
)

SupplierAlimaStripeSetupIntentResult = strawberry.union(
    "SupplierAlimaStripeSetupIntentResult",
    (SupplerAlimaStripeIntentSecret, SupplierAlimaAccountError),
)

SupplierAlimaStripeResponseResult = strawberry.union(
    "SupplierAlimaStripeResponseResult",
    (SupplerAlimaStripeResponse, SupplierAlimaAccountError),
)


@strawberry.type
class SupplierAlimaBillingInvoice:
    invoice: BillingInvoice
    invoice_charges: List[BillingInvoiceCharge]
    invoice_paystatus: Optional[BillingInvoicePaystatus] = None


@strawberry.type
class SupplierAlimaHistoricInvoices:
    supplier_invoices: List[SupplierAlimaBillingInvoice]


SupplierAlimaBillingInvoiceResult = strawberry.union(
    "SupplierAlimaBillingInvoiceResult",
    (SupplierAlimaHistoricInvoices, SupplierAlimaAccountError),
)


# ------------------
# Handler Interface
# ------------------


class AlimaAccountHandlerInterface(ABC):
    @abstractmethod
    async def fetch_supplier_alima_account_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierAlimaAccount:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_alima_historic_invoices(
        self,
        firebase_id: str,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
    ) -> List[SupplierAlimaBillingInvoice]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_alima_account_config_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierAlimaAccountConfig:
        raise NotImplementedError

    @abstractmethod
    async def new_alima_invoice(
        self,
        billing_account: BillingAccount,
        invoice_month: str,  # MM-YYYY
        billing_charges_total: BillingTotalDue,
        currency: str,
        invoice_type: InvoiceType,
        is_paid: bool = False,
        payment_id: Optional[str] = None,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def new_alima_invoice_complement(
        self,
        supplier_business_id: UUID,
        payment_form: LocalPaymentForm,
        amount: float,
        active_invoice: BillingInvoice,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def cancel_alima_invoice(
        self,
        supplier_business_id: UUID,
        date: str,
        motive: str,
        uuid_replacement: Optional[str] = None,
    ) -> InvoiceStatus:
        raise NotImplementedError

    @abstractmethod
    async def fetch_billing_accounts(
        self,
        billing_period: Literal["monthly", "annual"],
    ) -> List[BillingAccount]:
        raise NotImplementedError

    @abstractmethod
    async def compute_total_due(
        self,
        billing_account: BillingAccount,
        date: datetime,
    ) -> BillingTotalDue:
        raise NotImplementedError

    @abstractmethod
    async def get_month_invoice_folio_count(
        self,
        paid_account: PaidAccount,
        until_date: Optional[datetime] = None,
    ) -> int | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def create_alima_account(
        self,
        supplier_business: SupplierBusiness,
        account_name: AlimaAccountPlan,
        payment_method: PayProviderType,
        active_cedis: int,
        firebase_id: str,
        discount: Optional[AlimaAccountPlanDiscount] = None,
    ) -> SupplierAlimaAccount:
        raise NotImplementedError

    @abstractmethod
    async def create_alima_account_config(
        self,
        supplier_business_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def disable_alima_account(self, supplier_business_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def reactivate_alima_account(self, supplier_business_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def change_alima_account_plan(
        self,
        paid_account: PaidAccount,
        charges: List[Charge],
        new_plan: AlimaAccountPlan,
    ) -> bool:
        raise NotImplementedError


class AlimaAccountListenerInterface:
    @staticmethod
    async def on_new_alima_supply_account_created(
        alima_account_handler: AlimaAccountHandlerInterface,
        ecommerce_seller_handler: EcommerceSellerHandlerInterface,
        supplier_business: SupplierBusinessGQL,
    ) -> bool:
        raise NotImplementedError


# ------------------
# Repository Interface
# ------------------


class AlimaAccountRepositoryInterface(ABC):
    @abstractmethod
    async def new_alima_account(self, paid_account: PaidAccount) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def new_billing_payment_method(
        self, payment_method: BillingPaymentMethod
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def deactivate_billing_payment_method(self, payment_method_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit_alima_account(
        self,
        paid_account_id: UUID,
        customer_type: AlimaCustomerType,
        account_name: str,
        active_cedis: int,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_alima_account(
        self, customer_business_id: UUID
    ) -> PaidAccount | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch_alima_account_by_id(
        self, paid_account_id: UUID
    ) -> PaidAccount | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch_discounts_charges(
        self, paid_account_id: UUID
    ) -> List[ChargeDiscount]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_charges(self, paid_account_id: UUID) -> List[Charge]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_payment_methods(
        self, paid_account_id: UUID, only_active: bool = True
    ) -> List[BillingPaymentMethod]:
        raise NotImplementedError

    @abstractmethod
    async def edit_payment_method(self, payment_method: BillingPaymentMethod) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_alima_account_config(
        self, paid_account_id: UUID
    ) -> PaidAccountConfig | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def new_charge(self, charge: Charge) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def new_discount_charge(
        self, charge_discount: ChargeDiscount
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def deactivate_charge(
        self, paid_account_id: UUID, charge_type: List[str]
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def verify_paid_account_config_exists(self, paid_account_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def create_paid_account_config(
        self,
        paid_account_id: UUID,
        config: Dict[str, Any],
    ) -> bool:
        raise NotImplementedError


class AlimaBillingInvoiceRepositoryInterface(ABC):
    @abstractmethod
    async def find(
        self, paid_account_id: UUID, date: Optional[str] = None
    ) -> List[BillingInvoice]:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self, billing_invoice_id: UUID, status: Optional[InvoiceStatusType] = None
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def raw_query(self, query: str, vals: Dict[str, Any]) -> List[Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_alima_invoices(
        self,
        paid_account_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
    ) -> List[BillingInvoice]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_alima_invoice_charges(
        self,
        invoice_ids: List[UUID],
    ) -> List[BillingInvoiceCharge]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_alima_invoice_paystatus(
        self,
        invoice_ids: List[UUID],
    ) -> List[BillingInvoicePaystatus]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_next_folio(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_last_invoice_date(self, paid_account_id: UUID) -> datetime | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add_alima_invoice(
        self,
        billing_invoice: BillingInvoice,
        billing_invoice_charges: List[BillingInvoiceCharge],
        paystatus: PayStatusType = PayStatusType.UNPAID,
        billing_payment_method_id: Optional[UUID] = None,
        transaction_id: Optional[str] = None,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit_alima_invoice(
        self,
        billing_invoice: BillingInvoice,
        paystatus: Optional[PayStatusType] = None,
        billing_payment_method_id: Optional[UUID] = None,
        transaction_id: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def add_alima_invoice_charge(
        self,
        billing_invoice_charge: BillingInvoiceCharge,
    ) -> UUID | NoneType:
        raise NotImplementedError


class AlimaBillingInvoiceComplementRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        billing_invoice_id: UUID,
        tax_invoice_id: str,
        sat_invoice_uuid: UUID,
        invoice_number: str,  # MONTH - YEAR (MM-YYYY)
        total: float,
        currency: str,
        status: InvoiceStatusType,
        result: str,
        pdf_file: Any,
        xml_file: Any,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def fetch_next_folio(self) -> int:
        raise NotImplementedError
