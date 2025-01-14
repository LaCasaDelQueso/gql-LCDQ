from abc import ABC
from types import NoneType
from uuid import UUID
from typing import List, Optional
from datetime import datetime

from strawberry import type as strawberry_type

from gqlapi.domain.models.v2.utils import (
    ChargeType,
    DiscountChargeType,
    InvoiceType,
    PayStatusType,
)
from gqlapi.domain.models.v2 import (
    PayMethodType,
    InvoiceStatusType,
    AlimaCustomerType,
    AlimaCustomerStatusType,
    PayProviderType,
)


@strawberry_type
class AlimaUser(ABC):
    id: UUID
    core_user_id: UUID
    role: str
    enabled: bool
    deleted: bool
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "AlimaUser":
        raise NotImplementedError

    def get(self, id: UUID) -> "AlimaUser":
        raise NotImplementedError


@strawberry_type
class AlimaUserPermission(ABC):
    id: UUID
    alima_user_id: UUID
    create_user: bool
    delegate_mode: bool
    created_by: UUID
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "AlimaUserPermission":
        raise NotImplementedError

    def get(self, id: UUID) -> "AlimaUserPermission":
        raise NotImplementedError


@strawberry_type
class PaidAccount(ABC):
    id: UUID
    customer_type: AlimaCustomerType
    customer_business_id: UUID
    account_name: str
    created_by: UUID
    created_at: datetime
    last_updated: datetime
    active_cedis: int
    invoicing_provider_id: Optional[str] = None

    def new(self, *args) -> "PaidAccount":
        raise NotImplementedError

    def get(self, id: UUID) -> "PaidAccount":
        raise NotImplementedError


@strawberry_type
class PaidAccountConfig(ABC):
    paid_account_id: UUID
    config: str
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "PaidAccountConfig":
        raise NotImplementedError

    def get(self, id: UUID) -> "PaidAccountConfig":
        raise NotImplementedError


@strawberry_type
class Charge(ABC):
    id: UUID
    paid_account_id: UUID
    charge_type: ChargeType
    charge_amount: float
    currency: str
    charge_amount_type: str  # $ or %
    created_at: datetime
    charge_description: Optional[str] = None
    last_updated: datetime
    active: bool

    def new(self, *args) -> "Charge":
        raise NotImplementedError

    def get(self, id: UUID) -> "Charge":
        raise NotImplementedError


@strawberry_type
class ChargeDiscount(ABC):
    id: UUID
    charge_id: UUID
    charge_discount_type: DiscountChargeType
    charge_discount_amount: float
    charge_discount_amount_type: str  # $ or %
    charge_discount_description: Optional[str] = None
    valid_upto: datetime
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "Charge":
        raise NotImplementedError

    def get(self, id: UUID) -> "Charge":
        raise NotImplementedError


@strawberry_type
class BillingPaymentMethod(ABC):
    id: UUID
    paid_account_id: UUID
    payment_type: PayMethodType
    payment_provider: PayProviderType
    payment_provider_id: str  # Id en Stripe
    account_number: Optional[str] = None
    account_name: Optional[str] = None
    bank_name: Optional[str] = None
    created_by: UUID
    created_at: datetime
    last_updated: datetime
    active: bool

    def new(self, *args) -> "BillingPaymentMethod":
        raise NotImplementedError

    def get(self, id: UUID) -> "BillingPaymentMethod":
        raise NotImplementedError


@strawberry_type
class BillingInvoice(ABC):
    id: UUID
    paid_account_id: UUID
    country: str
    invoice_month: str  # MONTH - YEAR (MM-YYYY)
    invoice_name: str
    sat_invoice_uuid: Optional[UUID] = None
    tax_invoice_id: str  # depending country, it can be SAT UUID or some other ID
    invoice_number: str  # (nullable) folio
    invoice_files: Optional[List[str]] = None  # json formated file
    total: float
    currency: str
    result: Optional[str] = None
    status: InvoiceStatusType
    payment_method: InvoiceType
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "BillingInvoice":
        raise NotImplementedError

    def get(self, id: UUID) -> "BillingInvoice":
        raise NotImplementedError


@strawberry_type
class BillingInvoiceComplement(ABC):
    id: UUID
    billing_invoice_id: UUID
    tax_invoice_id: str  # depending country, it can be SAT UUID or some other ID
    invoice_number: str  # (nullable) folio
    invoice_files: Optional[List[str]] = None  # json formated file
    sat_invoice_uuid: UUID
    total: float
    currency: str
    result: Optional[str] = None
    status: InvoiceStatusType
    created_at: datetime
    last_updated: datetime

    def new(self, *args) -> "BillingInvoice":
        raise NotImplementedError

    def get(self, id: UUID) -> "BillingInvoice":
        raise NotImplementedError


@strawberry_type
class BillingInvoiceCharge(ABC):
    id: UUID
    billing_invoice_id: UUID
    charge_id: UUID
    charge_type: str
    charge_base_quantity: float
    charge_amount: float
    charge_amount_type: str  # $ or %
    total_charge: float
    currency: str
    created_at: datetime

    def new(self, *args) -> "BillingInvoiceCharge":
        raise NotImplementedError

    def get(self, id: UUID) -> "BillingInvoiceCharge":
        raise NotImplementedError


@strawberry_type
class BillingInvoicePaystatus(ABC):
    id: UUID
    billing_invoice_id: UUID
    billing_payment_method_id: Optional[UUID] = None
    status: PayStatusType
    transaction_id: Optional[str] = None
    created_at: datetime

    def new(self, *args) -> "BillingInvoicePaystatus":
        raise NotImplementedError

    def get(self, id: UUID) -> "BillingInvoicePaystatus":
        raise NotImplementedError


@strawberry_type
class AlimaUserCustomerRelation(ABC):
    id: UUID
    alima_user_id: UUID
    customer_type: AlimaCustomerType
    customer_business_id: UUID
    created_by: UUID
    created_at: datetime

    def new(self, *args) -> "AlimaUserCustomerRelation":
        raise NotImplementedError

    def get(self, id: UUID) -> "AlimaUserCustomerRelation":
        raise NotImplementedError


@strawberry_type
class AlimaUserCustomerRelationStatus(ABC):
    alima_user_customer_relation_id: UUID
    status: AlimaCustomerStatusType
    created_at: datetime

    def new(self, *args) -> "AlimaUserCustomerRelationStatus":
        raise NotImplementedError

    def get(
        self,
        alima_user_customer_relation_id: UUID,
        status: AlimaCustomerStatusType | NoneType = None,
    ) -> "AlimaUserCustomerRelationStatus":
        raise NotImplementedError
