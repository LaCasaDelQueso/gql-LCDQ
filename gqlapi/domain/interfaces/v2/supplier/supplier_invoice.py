from typing import Optional
from uuid import UUID
from gqlapi.domain.models.v2.core import MxInvoicingExecution

import strawberry

from gqlapi.lib.clients.clients.facturamaapi.facturama import PaymentForm
from gqlapi.domain.interfaces.v2.orden.invoice import CustomerMxInvoiceGQL
from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.models.v2.utils import OrdenStatusType, PayMethodType


INVOICE_PAYMENT_MAP = {
    PayMethodType.CASH: PaymentForm.CASH,
    PayMethodType.CARD: PaymentForm.CARD,
    PayMethodType.MONEY_ORDER: PaymentForm.MONEY_ORDER,
    PayMethodType.TRANSFER: PaymentForm.TRANSFER,
    PayMethodType.TBD: PaymentForm.TBD,
}


@strawberry.type
class SupplierInvoiceError:
    msg: str
    code: int


@strawberry.type
class SupplierInvoiceTriggerInfo(MxInvoicingExecution):
    customer_invoice: Optional[CustomerMxInvoiceGQL] = None


SupplierInvoiceTriggerResult = strawberry.union(
    "SupplierInvoiceTriggerResult", [SupplierInvoiceTriggerInfo, SupplierInvoiceError]
)

CustomerMxInvoiceGQLResult = strawberry.union(
    "CustomerMxInvoiceGQLResult", [CustomerMxInvoiceGQL, SupplierInvoiceError]
)


class SupplierInvoiceHandlerInterface:
    async def fetch_orden_details(self, orden_id: UUID) -> OrdenGQL:
        raise NotImplementedError

    async def trigger_supplier_invoice(
        self, firebase_id: str, orden: OrdenGQL
    ) -> SupplierInvoiceTriggerInfo:
        raise NotImplementedError

    async def fetch_supplier_invoice_exec_status(
        self, orden_id: UUID
    ) -> SupplierInvoiceTriggerInfo:
        raise NotImplementedError


class SupplierInvoiceHookListenerInterface:
    @staticmethod
    async def on_orden_status_changed(
        supplier_handler: SupplierInvoiceHandlerInterface,
        firebase_id: str,
        orden_id: UUID,
        status: OrdenStatusType,
    ) -> bool:
        raise NotImplementedError
