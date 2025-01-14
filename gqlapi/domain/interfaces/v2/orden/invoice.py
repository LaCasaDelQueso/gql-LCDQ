from abc import abstractmethod
from datetime import datetime, date
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID

# from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.models.v2.restaurant import RestaurantBranch
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
)
from gqlapi.domain.models.v2.utils import InvoiceStatusType, InvoiceType, RegimenSat
import strawberry
from gqlapi.domain.models.v2.core import (
    CoreUser,
    MxInvoice,
    MxInvoiceComplement,
    MxInvoiceOrden,
    MxInvoicingExecution,
    MxSatInvoicingCertificateInfo,
    OrdenDetails,
)


# Types
@strawberry.type
class MxUploadInvoiceMsg:
    msg: str
    success: bool


@strawberry.type
class MxUploadInvoice:
    upload_msg: MxUploadInvoiceMsg
    orden_id: UUID
    orden_delivery_date: date
    restaurant_branch: RestaurantBranch
    orden_total: Optional[float] = None


@strawberry.type
class MxInvoiceGQL:
    id: UUID
    orden_id: Optional[UUID] = None
    sat_invoice_uuid: UUID
    invoice_number: str  # folio (nullable)
    total: float
    status: InvoiceStatusType
    created_by: UUID
    created_at: datetime
    orden: MxInvoiceOrden
    supplier: SupplierBusiness
    restaurant_branch: RestaurantBranch
    pdf_file: Optional[str] = None
    xml_file: Optional[str] = None
    invoice_type: Optional[str] = None
    cancel_result: Optional[str] = None


@strawberry.type
class IssuerGQL:
    rfc: str
    business_name: str


@strawberry.type
class ReceiverGQL:
    rfc: str
    business_name: str


@strawberry.type
class CustomerMxInvoiceGQL:
    sat_id: Optional[str]
    total: float
    issue_date: datetime
    issuer: IssuerGQL
    receiver: ReceiverGQL
    pdf: Optional[str] = None
    xml: Optional[str] = None
    cancel_result: Optional[str] = None


@strawberry.type
class CustomerMxInvoiceDetailsGQL:
    id: UUID
    sat_invoice_uuid: str
    status: str
    legal_name: str
    total: float
    xml_file: str
    pdf_file: str


@strawberry.type
class FacturamaData:
    Rfc: str
    Certificate: str
    PrivateKey: str
    PrivateKeyPassword: str
    CsdExpirationDate: str
    UploadDate: str


@strawberry.type
class MxInvoiceError:
    msg: str
    code: int


@strawberry.type
class MxSatCertificateError:
    msg: str
    code: int


@strawberry.type
class InvoiceStatus:
    id: str
    canceled: bool


@strawberry.type
class ExportMxInvoiceGQL:
    file: str  # encoded file
    extension: str = "csv"  # {csv, xlsx} default = csv


@strawberry.type
class MxSatCertificateGQL:
    mx_sat_certificate: Optional[MxSatInvoicingCertificateInfo] = None
    facturama_response: Optional[FacturamaData] = None


MxUploadInvoiceResult = strawberry.union(
    "MxUploadInvoiceResult", (MxUploadInvoiceMsg, MxInvoiceError)
)

MxUploadInvoiceCheckResult = strawberry.union(
    "MxUploadInvoiceCheckResult", (MxUploadInvoice, MxInvoiceError)
)

MxUpsertCustomerSatCertificateResult = strawberry.union(
    "MxUpsertCustomerSatCertificateResult", (MxSatCertificateGQL, MxSatCertificateError)
)

MxInvoiceResult = strawberry.union("MxInvoiceResult", (MxInvoiceGQL, MxInvoiceError))

MxInvoiceStatusResult = strawberry.union(
    "MxInvoiceStatusResult", (InvoiceStatus, MxInvoiceError)
)

ExportMxInvoiceResult = strawberry.union(
    "ExportMxInvoiceResult",
    (
        MxInvoiceError,
        ExportMxInvoiceGQL,
    ),
)

CustomerMxInvoiceResult = strawberry.union(
    "CustomerMxInvoiceResult", (CustomerMxInvoiceGQL, MxInvoiceError)
)


# Handlers
class MxInvoiceHandlerInterface:
    @abstractmethod
    async def upload_invoice(
        self, pdf_file: bytes, xml_file: bytes, orden_id: UUID
    ) -> MxUploadInvoiceMsg:
        raise NotImplementedError

    @abstractmethod
    async def get_invoice(self, orden_id: UUID) -> MxInvoiceGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_invoices(self, orden_ids: List[UUID]) -> List[MxInvoiceGQL]:
        raise NotImplementedError

    @abstractmethod
    async def get_invoice_external(self, order_id: UUID) -> MxUploadInvoiceMsg:
        raise NotImplementedError

    @abstractmethod
    async def get_customer_invoices_by_orden(self, order_id: UUID):
        raise NotImplementedError

    @abstractmethod
    async def new_customer_invoice(
        self,
        orden_details_id: UUID,
        cfdi_type: str,
        payment_form: str,
        expedition_place: str,
        issue_date: datetime,
        payment_method: str,
        firebase_id: Optional[str] = None,
        core_user: Optional[CoreUser] = None,
    ) -> CustomerMxInvoiceGQL:
        raise NotImplementedError

    @abstractmethod
    async def new_consolidated_customer_invoice(
        self,
        ordenes: List[Any],
        public_general_invoice_flag: bool,
        firebase_id: Optional[str] = None,
        core_user: Optional[CoreUser] = None,
    ):
        raise NotImplementedError

    @abstractmethod
    async def get_customer_invoices_by_dates(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        receiver: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[MxInvoiceGQL]:
        raise NotImplementedError

    @abstractmethod
    async def format_invoices_to_export(
        self, invoices: List[MxInvoiceGQL]
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def new_customer_invoice_complement(
        self,
        orden_details_id: UUID,
        amount: float,
        payment_receipt_orden_id: UUID,
        firebase_id: Optional[str] = None,
        core_user: Optional[CoreUser] = None,
    ) -> CustomerMxInvoiceGQL:
        raise NotImplementedError

    @abstractmethod
    async def get_invoice_type(self, orden_details_id) -> InvoiceType | None:
        raise NotImplementedError

    @abstractmethod
    async def re_invoice(
        self,
        old_ordn_det: OrdenDetails,
        motive: str,
        orden_id: UUID,
    ) -> InvoiceStatus:
        raise NotImplementedError

    @abstractmethod
    async def validate_complements_by_orders(self, orden_ids: List[UUID]) -> bool:
        raise NotImplementedError


class MxSatCertificateHandlerInterface:
    @abstractmethod
    async def upsert_customer_certificate(
        self,
        rfc: str,
        legal_name: str,
        zip_code: str,
        sat_regime: RegimenSat,
        cer_file: str,
        key_file: str,
        sat_pass_code: str,
        invoicing_type: str,
        invoice_type: str,
        supplier_unit_id: UUID,
    ) -> MxSatCertificateGQL:
        raise NotImplementedError

    @abstractmethod
    async def get_customer_certificate(
        self, supplier_business_id: UUID, rfc: str
    ) -> MxSatCertificateGQL:
        raise NotImplementedError

    @abstractmethod
    async def cancel_customer_invoice(
        self,
        orden_details_id: UUID,
        motive: str,
        uuid_replacement: Optional[str] = None,
    ) -> InvoiceStatus:
        raise NotImplementedError

    @abstractmethod
    async def cancel_customer_invoice_by_invoice(
        self,
        mx_invoice_id: UUID,
        motive: str,
        uuid_replacement: Optional[str] = None,
    ) -> InvoiceStatus:
        raise NotImplementedError

    @abstractmethod
    async def get_mx_sat_invocing_certificate(
        self, supplier_unit_id: UUID
    ) -> MxSatInvoicingCertificateInfo | NoneType:
        raise NotImplementedError


# Repositories
class MxInvoiceRepositoryInterface:
    @abstractmethod
    async def new(
        self, mx_invoice: MxInvoice, orden_details_id: UUID
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        mx_invoice_id: UUID,
        status: Optional[InvoiceStatusType] = None,
        cancel_result: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def associate(
        self, mx_invoice_id: UUID, orden_details_id: UUID, created_by: UUID
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self, mx_invoice: MxInvoice, orden_details_id: UUID
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def add_consolidated(
        self, mx_invoice: MxInvoice, orden_details_ids: List[UUID]
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def add_associate(
        self, mx_invoice_id: UUID, orden_details_id: UUID, created_by: UUID
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def add_paystatus(
        self, mx_invoice_id: UUID, orden_details_id: UUID, created_by: UUID
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get(self, orden_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_from_orden_details(self, orden_details_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def find_asocciated_ordenes(self, invoice_id: UUID) -> List[MxInvoiceOrden]:
        raise NotImplementedError

    @abstractmethod
    async def get_asocciated_orden(self, invoice_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def get_external(self, orden_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, mx_invoice_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_multiple_associated(
        self, orden_ids: List[UUID]
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_assocciated_by_orden(
        self, orden_details_id: UUID
    ) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_invoice_details_by_orden(
        self, orden_id: UUID
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_invoice_details_by_dates(
        self,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        receiver: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def find(self) -> List[MxInvoice]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_next_folio(self, supplier_business_id: UUID) -> int:
        raise NotImplementedError


class MxInvoiceComplementRepositoryInterface:
    @abstractmethod
    async def add(self, mx_invoice_complement: MxInvoiceComplement) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def find(self) -> List[MxInvoice]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_next_folio(self) -> int:
        raise NotImplementedError

    @abstractmethod
    async def find_by_invoice(self, mx_invoice_id: UUID) -> List[MxInvoiceComplement]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_many(self, mx_invoice_complement_ids=List[UUID]) -> List[Any]:
        raise NotImplementedError


class MxSatCertificateRepositoryInterface:
    @abstractmethod
    async def upsert(
        self,
        sat_certificate: MxSatInvoicingCertificateInfo,
    ) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_certificate(self, supplier_unit_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError


class MxInvoicingExecutionRepositoryInterface:
    @abstractmethod
    async def add(self, mx_inv_exec: MxInvoicingExecution) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, orden_details_id: UUID) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def edit(self, mx_inv_exec: MxInvoicingExecution) -> bool:
        raise NotImplementedError
