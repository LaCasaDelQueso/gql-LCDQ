import base64
from datetime import date, datetime, timedelta
from enum import Enum
import json
from types import NoneType
from typing import Any, Dict, Optional, List
from uuid import UUID, uuid4

from bs4 import BeautifulSoup
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import (
    construct_route_jpg_to_invoice,
)
from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
import pandas as pd

from gqlapi.lib.clients.clients.facturamaapi.facturama import (
    Customer,
    CustomerAddress,
    FacturamaClientApi,
    FacturamaComplement,
    FacturamaInvoice,
    FacturamaInvoiceComplement,
    FacturamaPayments,
    GlobalInformationFacturama,
    Issuer,
    Item,
    PaymentForm,
    PaymentFormFacturama,
    RelatedDocuments,
    SatTaxes,
)
from gqlapi.domain.interfaces.v2.orden.cart import (
    CartProductGQL,
    CartProductRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import (
    CustomerMxInvoiceGQL,
    FacturamaData,
    InvoiceStatus,
    IssuerGQL,
    MxInvoiceComplementRepositoryInterface,
    MxInvoiceGQL,
    MxInvoiceHandlerInterface,
    MxInvoiceRepositoryInterface,
    MxSatCertificateGQL,
    MxSatCertificateHandlerInterface,
    MxSatCertificateRepositoryInterface,
    MxUploadInvoice,
    MxUploadInvoiceMsg,
    ReceiverGQL,
)
from gqlapi.domain.interfaces.v2.orden.orden import (
    OrdenDetailsRepositoryInterface,
    OrdenGQL,
    OrdenPaymentStatusRepositoryInterface,
    OrdenRepositoryInterface,
    PaymentReceiptGQL,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchInvoicingOptionsRepositoryInterface,
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import INVOICE_PAYMENT_MAP
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.models.v2.core import (
    CartProduct,
    CoreUser,
    MxInvoice,
    MxInvoiceComplement,
    MxInvoiceOrden,
    MxSatInvoicingCertificateInfo,
    Orden,
    OrdenDetails,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBranch, RestaurantBranchMxInvoiceInfo
from gqlapi.domain.models.v2.supplier import (
    InvoicingOptions,
    SupplierBusiness,
    SupplierProduct,
    SupplierUnit,
)
from gqlapi.domain.models.v2.utils import (
    CFDIType,
    DataTypeDecoder,
    InvoiceStatusType,
    InvoiceTriggerTime,
    InvoiceType,
    PayMethodType,
    RegimenSat,
    SellingOption,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException, error_code_decode
from gqlapi.handlers.services.mails import (
    send_new_consolidated_invoice_notification,
    send_restaurant_new_invoice_complement_notification,
    send_restaurant_new_invoice_notification,
)
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.config import (
    APP_TZ,
    ENV as DEV_ENV,
    FACT_USR,
    FACT_PWD,
)
from gqlapi.utils.cart import calculate_subtotal_without_tax
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple

# logger
logger = get_logger(get_app())


class MxInvoiceHandler(MxInvoiceHandlerInterface):
    def __init__(
        self,
        mx_invoice_repository: MxInvoiceRepositoryInterface,
        orden_details_repo: OrdenDetailsRepositoryInterface,
        core_user_repo: CoreUserRepositoryInterface,
        supplier_unit_repo: SupplierUnitRepositoryInterface,
        restaurant_branch_repo: Optional[RestaurantBranchRepositoryInterface] = None,
        supplier_business_repo: Optional[SupplierBusinessRepositoryInterface] = None,
        orden_repo: Optional[OrdenRepositoryInterface] = None,
        cart_product_repo: Optional[CartProductRepositoryInterface] = None,
        supp_prod_repo: Optional[SupplierProductRepositoryInterface] = None,
        mx_sat_cer_repo: Optional[MxSatCertificateRepositoryInterface] = None,
        supplier_user_repo: Optional[SupplierUserRepositoryInterface] = None,
        supplier_user_perms_repo: Optional[
            SupplierUserPermissionRepositoryInterface
        ] = None,
        mx_invoice_complement_repository: Optional[
            MxInvoiceComplementRepositoryInterface
        ] = None,
        orden_payment_repo: Optional[OrdenPaymentStatusRepositoryInterface] = None,
        supplier_restaurant_relation_mx_invoice_options_repo: Optional[
            RestaurantBranchInvoicingOptionsRepositoryInterface
        ] = None,
    ):
        self.mx_invoice_repository = mx_invoice_repository
        self.orden_details_repo = orden_details_repo
        self.core_user_repo = core_user_repo
        self.supplier_unit_repo = supplier_unit_repo
        if orden_payment_repo:
            self.orden_payment_repo = orden_payment_repo
        if restaurant_branch_repo:
            self.restaurant_branch_repo = restaurant_branch_repo
        if supplier_business_repo:
            self.supplier_business_repo = supplier_business_repo
        if orden_repo:
            self.orden_repo = orden_repo
        if cart_product_repo:
            self.cart_prod_repo = cart_product_repo
        if supp_prod_repo:
            self.supp_prod_repo = supp_prod_repo
        if mx_sat_cer_repo:
            self.mx_sat_cer_repo = mx_sat_cer_repo
        if supplier_user_repo:
            self.supplier_user_repo = supplier_user_repo
        if supplier_user_perms_repo:
            self.supplier_user_perms_repo = supplier_user_perms_repo
        if mx_invoice_complement_repository:
            self.mx_invoice_comp_repo = mx_invoice_complement_repository
        if supplier_restaurant_relation_mx_invoice_options_repo:
            self.supplier_restaurant_relation_mx_invoice_options_repo = (
                supplier_restaurant_relation_mx_invoice_options_repo
            )

    async def upload_invoice(
        self, pdf_file: bytes, xml_file: bytes, orden_id: UUID
    ) -> MxUploadInvoiceMsg:
        """Uploads an invoice to the MX Invoice DB

        Parameters
        ----------
        pdf_file : bytes
        xml_file : bytes
        orden_id : UUID

        Returns
        -------
        MxUploadInvoiceMsg

        Raises
        ------
        GQLApiException
        """
        # parse xml file to extract info
        parsed_vals = {}
        try:
            xml = BeautifulSoup(xml_file, features="xml")
            comp = xml.find("cfdi:Comprobante").__dict__["attrs"]
            timb = xml.find("tfd:TimbreFiscalDigital").__dict__["attrs"]
            parsed_vals.update(
                {
                    "total": float(comp["Total"]),
                    "invoice_number": comp.get("Folio", "Sin Folio"),
                    "payment_method": (
                        InvoiceType.PUE
                        if comp.get("MetodoPago", "PUE") == "PUE"
                        else InvoiceType.PPD
                    ),
                    "sat_invoice_uuid": timb["UUID"],
                    "status": InvoiceStatusType.ACTIVE,
                }
            )
        except Exception as e:
            logger.error(e)
            return MxUploadInvoiceMsg(
                msg=error_code_decode(GQLApiErrorCodeType.WRONG_XML_FORMAT.value),
                success=False,
            )
        # get orden details
        ordn_dets = await self.orden_details_repo.get_last(orden_id)
        # get supplier business from supplier unit
        supplier_unit = await self.supplier_unit_repo.get(ordn_dets["supplier_unit_id"])
        # getting admin user - as this cannot be tracted
        admin_usr = await self.core_user_repo.get_by_email("admin")
        # create MxInvoice object
        parsed_vals.update(
            {
                "pdf_file": pdf_file,
                "xml_file": xml_file,
                "supplier_business_id": supplier_unit["supplier_business_id"],
                "restaurant_branch_id": ordn_dets["restaurant_branch_id"],
                "created_by": admin_usr.id,
            }
        )
        mx_invoice = MxInvoice(**parsed_vals)
        # call repository to upload
        resp = await self.mx_invoice_repository.add(mx_invoice, ordn_dets["id"])
        if not resp:
            raise GQLApiException(
                msg=error_code_decode(GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value),
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # return MxUploadInvoice
        return MxUploadInvoiceMsg(
            msg=(
                "La factura ha sido guardada correctamente"
                if resp["success"]
                else "No hemos podido guardar la factura correspondiente."
            ),
            success=resp["success"],
        )

    async def get_invoice(self, orden_id: UUID) -> MxInvoiceGQL:
        """Get invoice from MX Invoice DB

        Parameters
        ----------
        orden_id : UUID

        Returns
        -------
        MxInvoiceGQL
        """
        # get orden details
        ordn_dets = await self.orden_details_repo.fetch_last(orden_id)
        if not ordn_dets:
            raise GQLApiException(
                msg="Orden Details not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch from repo
        mx_inv = await self.mx_invoice_repository.fetch_from_orden_details(
            ordn_dets.get("id", None)
        )
        if not mx_inv:
            raise GQLApiException(
                msg="Invoice not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        mx_inv_assoc = await self.mx_invoice_repository.get_asocciated_orden(
            mx_inv["id"]
        )
        # get supplier info
        sup_unit = await self.supplier_unit_repo.fetch(ordn_dets["supplier_unit_id"])
        supplier = SupplierBusiness(
            **await self.supplier_business_repo.fetch(sup_unit["supplier_business_id"])
        )
        # get branch info
        branch = RestaurantBranch(
            **await self.restaurant_branch_repo.get(ordn_dets["restaurant_branch_id"])
        )
        # build response
        mx_inv_gql = MxInvoiceGQL(
            id=mx_inv["id"],
            sat_invoice_uuid=mx_inv["sat_invoice_uuid"],
            invoice_number=mx_inv["invoice_number"],
            total=mx_inv["total"],
            status=InvoiceStatusType(
                DataTypeDecoder.get_mxinvoice_status_value(mx_inv["status"])
            ),
            created_by=mx_inv["created_by"],
            created_at=mx_inv["created_at"],
            orden=MxInvoiceOrden(**mx_inv_assoc),
            supplier=supplier,
            restaurant_branch=branch,
            pdf_file=(
                base64.b64encode(mx_inv["pdf_file"]).decode("utf-8")
                if isinstance(mx_inv["pdf_file"], bytes)
                else None
            ),
            xml_file=(
                base64.b64encode(mx_inv["xml_file"]).decode("utf-8")
                if isinstance(mx_inv["xml_file"], bytes)
                else None
            ),
        )
        return mx_inv_gql

    async def get_customer_invoices_by_orden_supply(
        self, orden_id: UUID
    ) -> List[MxInvoiceGQL]:
        """Get historic invoice from MX Invoice DB

        Parameters
        ----------
        orden_id : UUID

        Returns
        -------
        MxInvoiceGQL
        """
        # get orden details (only to get unit and rest)
        ordn_dets = await self.orden_details_repo.fetch_last(orden_id)
        if not ordn_dets:
            raise GQLApiException(
                msg="Orden Details not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get supplier info
        sup_unit = await self.supplier_unit_repo.fetch(ordn_dets["supplier_unit_id"])
        supplier = SupplierBusiness(
            **await self.supplier_business_repo.fetch(sup_unit["supplier_business_id"])
        )
        # get branch info
        branch = RestaurantBranch(
            **await self.restaurant_branch_repo.get(ordn_dets["restaurant_branch_id"])
        )
        # fetch from repo
        _invs = await self.mx_invoice_repository.fetch_invoice_details_by_orden(
            orden_id=orden_id
        )
        if not _invs:
            raise GQLApiException(
                msg="There are no orders associated with that order",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        mx_inv_list = []
        for _inv in _invs:
            mx_cert_inf = await self.mx_sat_cer_repo.fetch_certificate(
                supplier_unit_id=_inv["supplier_unit_id"]
            )
            if not mx_cert_inf:
                raise GQLApiException(
                    msg="There are no orders associated with that order",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                )
            try:
                pdf = ""
                xml = ""
                if "pdf_file" in _inv:
                    pdf = base64.b64encode(_inv["pdf_file"]).decode("utf-8")
                if "xml_file" in _inv:
                    xml = base64.b64encode(_inv["xml_file"]).decode("utf-8")
                mx_inv = MxInvoiceGQL(
                    id=_inv["mx_invoice_id"],
                    orden_id=orden_id,
                    sat_invoice_uuid=_inv["sat_invoice_uuid"],
                    invoice_number=_inv["invoice_number"],
                    total=_inv["total"],
                    status=InvoiceStatusType(
                        DataTypeDecoder.get_mxinvoice_status_value(_inv["status"])
                    ),
                    created_by=_inv["created_by"],
                    created_at=_inv["created_at"],
                    orden=MxInvoiceOrden(
                        id=_inv["created_at"],
                        mx_invoice_id=_inv["mx_invoice_id"],
                        orden_details_id=_inv["id"],
                        created_at=_inv["created_at_mx_inv_ord"],
                        created_by=_inv["created_by_mx_inv_ord"],
                        last_updated=_inv["last_updated"],
                    ),
                    supplier=supplier,
                    restaurant_branch=branch,
                    pdf_file=pdf,
                    xml_file=xml,
                    cancel_result=_inv["cancel_result"],
                )
                mx_inv_list.append(mx_inv)
            except Exception as e:
                logger.error(e)
                raise GQLApiException(
                    msg="Error to build invoice details",
                    error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR,
                )
        return mx_inv_list

    async def fetch_invoices(self, orden_ids: List[UUID]) -> List[MxInvoiceGQL]:
        """Get invoices from MX Invoice DB

        Parameters
        ----------
        orden_ids : List[UUID]

        Returns
        -------
        MxInvoiceGQL
        """
        # get multiple invoices
        mult_invs = await self.mx_invoice_repository.fetch_multiple_associated(
            orden_ids
        )
        # fetch suppliers
        suppliers_idx = {}
        for inv in mult_invs:
            if inv["supplier_business_id"] in suppliers_idx:
                continue
            suppliers_idx[inv["supplier_business_id"]] = SupplierBusiness(
                **await self.supplier_business_repo.get(inv["supplier_business_id"])
            )
        # fetch branches
        branches_idx = {}
        for inv in mult_invs:
            if inv["restaurant_branch_id"] in branches_idx:
                continue
            branches_idx[inv["restaurant_branch_id"]] = RestaurantBranch(
                **await self.restaurant_branch_repo.get(inv["restaurant_branch_id"])
            )
        # build response - [TODO] - extend to return XML and PDF files
        list_mx_invs = []
        for mx_inv in mult_invs:
            mx_inv_gql = MxInvoiceGQL(
                id=mx_inv["id"],
                orden_id=mx_inv["orden_id"],
                sat_invoice_uuid=mx_inv["sat_invoice_uuid"],
                invoice_number=mx_inv["invoice_number"],
                total=mx_inv["total"],
                status=InvoiceStatusType(
                    DataTypeDecoder.get_mxinvoice_status_value(mx_inv["status"])
                ),
                created_by=mx_inv["created_by"],
                created_at=mx_inv["created_at"],
                orden=MxInvoiceOrden(
                    id=mx_inv["mx_invoice_orden_id"],
                    mx_invoice_id=mx_inv["id"],
                    orden_details_id=mx_inv["orden_details_id"],
                    created_at=mx_inv["mxio_created_at"],
                    created_by=mx_inv["mxio_created_by"],
                    last_updated=mx_inv["mxio_last_updated"],
                ),
                supplier=suppliers_idx[mx_inv["supplier_business_id"]],
                restaurant_branch=branches_idx[mx_inv["restaurant_branch_id"]],
                pdf_file=(
                    base64.b64encode(mx_inv["pdf_file"]).decode("utf-8")
                    if isinstance(mx_inv["pdf_file"], bytes)
                    else None
                ),
                xml_file=(
                    base64.b64encode(mx_inv["xml_file"]).decode("utf-8")
                    if isinstance(mx_inv["xml_file"], bytes)
                    else None
                ),
                invoice_type=mx_inv["payment_method"],
            )
            list_mx_invs.append(mx_inv_gql)
        return list_mx_invs

    async def get_invoice_external(self, orden_id: UUID) -> MxUploadInvoice:
        """Get invoice from MX Invoice DB with exposable Orden Details info

        Parameters
        ----------
        order_id : UUID

        Returns
        -------
        MxUploadInvoice
            MxUploadInvoiceMsg: success=True if found
            MxInvoiceError: success=False if not found
        """
        # get orden details
        ordn_dets = await self.orden_details_repo.fetch_last(orden_id)
        if not ordn_dets:
            raise GQLApiException(
                msg="Orden Details not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get mx invoice
        try:
            _inv = await self.mx_invoice_repository.fetch_from_orden_details(
                ordn_dets.get("id", None)
            )
            if not _inv:
                raise GQLApiException(
                    msg="Invoice not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            mx_inv_msg = {
                "msg": "Mx Invoice has been found",
                "success": True,
            }
        except Exception:
            logger.warning("No invoice found")
            mx_inv_msg = {
                "msg": "Mx Invoice was not found",
                "success": False,
            }
        # get branch info
        branch = RestaurantBranch(
            **await self.restaurant_branch_repo.get(ordn_dets["restaurant_branch_id"])
        )
        # build response
        return MxUploadInvoice(
            upload_msg=MxUploadInvoiceMsg(**mx_inv_msg),
            orden_id=orden_id,
            orden_delivery_date=ordn_dets["delivery_date"],
            restaurant_branch=branch,
            orden_total=ordn_dets["total"],
        )

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
        # verify if orden has already been invoiced
        if await self.mx_invoice_repository.fetch_assocciated_by_orden(
            orden_details_id=orden_details_id
        ):
            raise GQLApiException(
                msg="This order is already invoiced",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        # fetch user info including CSD files
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        # fetch core user
        if firebase_id:
            core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        elif core_user:
            pass
        else:
            logger.warning("No user info provided")
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        # fetch orden details
        orden_details_data = await self.orden_details_repo.fetch(
            orden_details_id=orden_details_id
        )
        if orden_details_data:
            orden_details = OrdenDetails(**orden_details_data)
        else:
            raise GQLApiException(
                msg="orden_Details not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        orden = await self.orden_repo.fetch(orden_details.orden_id)
        if orden:
            orden_obj = Orden(**orden)
        else:
            raise GQLApiException(
                msg="orden not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_product_list = await self.cart_prod_repo.find_many(
            cols=[
                "row_to_json(sp.*) AS sp_json",
                # "row_to_json(pp.*) AS pp_json",
                "cp.*",
            ],
            tablename="""cart_product cp
                    JOIN supplier_product sp ON cp.supplier_product_id = sp.id
                    """,
            filter_values=[
                {
                    "column": "cp.cart_id",
                    "operator": "=",
                    "value": (f"'{orden_details.cart_id}'"),
                }
            ],
        )
        # retrieve cart products
        if not supplier_product_list:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.EMPTY_DATA.value,
                msg="Cart Products not found",
            )
        cprod_list = []
        for supplier_product_data in supplier_product_list:
            cprod = CartProductGQL(**sql_to_domain(supplier_product_data, CartProduct))
            cprod.supp_prod = SupplierProduct(
                **json.loads(supplier_product_data["sp_json"])
            )
            if (
                not (
                    isinstance(cprod.supp_prod.tax, float)
                    or isinstance(cprod.supp_prod.tax, int)
                )
                or cprod.supp_prod.tax < 0
                or cprod.supp_prod.tax > 1
            ):
                raise GQLApiException(
                    msg=f"{cprod.supp_prod.description} has wrong tax",
                    error_code=GQLApiErrorCodeType.FACTURAMA_WRONG_INVOICE_TAX.value,
                )
            cprod_list.append(cprod)
        if not isinstance(orden_details.tax, float):
            raise GQLApiException(
                msg=f"Orden Details: {orden_details.id} has no tax",
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_TAX_INVOICE_DATA.value,
            )
        subtotal_dir = calculate_subtotal_without_tax(cprod_list)
        if subtotal_dir["tax"] != orden_details.tax:
            raise GQLApiException(
                msg="Error to validate tax",
                error_code=GQLApiErrorCodeType.FACTURAMA_TAX_NO_MATCH_WITH_ORDEN.value,
            )
        # fetch certificate info
        mx_prov_cert = MxSatInvoicingCertificateInfo(
            **await self.mx_sat_cer_repo.fetch_certificate(
                orden_details.supplier_unit_id
            )
        )
        _resp = await facturma_api.get_csd(rfc=mx_prov_cert.rfc)
        if "status" in _resp and _resp["status"] == "error":
            logger.warning("Issuer does not have CSD")
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                msg=_resp.get("msg", "error to get csd"),
            )
        # fetch branch info
        rest_branch_mx_inv_info_data = await self.restaurant_branch_repo.fetch_tax_info(
            orden_details.restaurant_branch_id
        )
        rest_branch = RestaurantBranch(
            **await self.restaurant_branch_repo.fetch(
                orden_details.restaurant_branch_id
            )
        )
        rest_branch_mx_inv_info = RestaurantBranchMxInvoiceInfo(
            **rest_branch_mx_inv_info_data
        )
        # fetch supplier unit info
        supp_unit = SupplierUnit(
            **await self.supplier_unit_repo.fetch(id=orden_details.supplier_unit_id)
        )
        supp_buss = await self.supplier_business_repo.fetch(
            supp_unit.supplier_business_id
        )
        if not supp_buss:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                msg="Issues fetch supplier business",
            )
        supplier_business = SupplierBusiness(**supp_buss)
        if supplier_business.logo_url:
            url = construct_route_jpg_to_invoice(route=supplier_business.logo_url)
        else:
            url = None
        # build Customer object
        client = Customer(
            Email=rest_branch_mx_inv_info.email,
            Address=CustomerAddress(
                ZipCode=rest_branch_mx_inv_info.zip_code,
            ),
            Rfc=rest_branch_mx_inv_info.mx_sat_id,
            Name=rest_branch_mx_inv_info.legal_name,
            CfdiUse=rest_branch_mx_inv_info.cfdi_use.name,
            FiscalRegime=str(rest_branch_mx_inv_info.sat_regime.value),
            TaxZipCode=rest_branch_mx_inv_info.zip_code,
        )
        global_information = None
        if client.Rfc != "XAXX010101000" and client.Rfc != "XEXX010101000":
            # if not in facturama, create customer in facturama
            if not rest_branch_mx_inv_info_data.get("invoicing_provider_id", None):
                new_client = await facturma_api.new_client(client=client)
                if new_client.get("status") != "ok":
                    raise GQLApiException(
                        msg=new_client.get("msg", "Error to create client"),
                        error_code=GQLApiErrorCodeType.FACTURAMA_NEW_CUSTOMER_ERROR.value,
                    )
                client.Id = new_client["data"]["Id"]
                if not await self.restaurant_branch_repo.edit_tax_info(
                    restaurant_branch_id=rest_branch.id,
                    invoicing_provider_id=new_client["data"]["Id"],
                ):
                    raise GQLApiException(
                        msg="Eroro to add invoicing provider id",
                        error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                    )
            # build invoice
            if client.Address:
                client.Address.Street = rest_branch_mx_inv_info.full_address
        else:
            cfdi_type = "I"
            payment_method = "PUE"
            global_information = GlobalInformationFacturama(
                Periodicity="01",
                Months=issue_date.strftime("%m"),
                Year=issue_date.strftime("%Y"),
            )
            if client.Rfc == "XAXX010101000":
                client = Customer(
                    Email=rest_branch_mx_inv_info.email,
                    Address=CustomerAddress(
                        ZipCode=expedition_place,
                    ),
                    Rfc=rest_branch_mx_inv_info.mx_sat_id,
                    Name="PUBLICO EN GENERAL",
                    CfdiUse="S01",
                    FiscalRegime="616",
                    TaxZipCode=expedition_place,
                )
            else:
                client = Customer(
                    Email=rest_branch_mx_inv_info.email,
                    Address=CustomerAddress(
                        ZipCode=expedition_place,
                    ),
                    Rfc=rest_branch_mx_inv_info.mx_sat_id,
                    Name=rest_branch_mx_inv_info.legal_name,
                    CfdiUse="S01",
                    FiscalRegime="616",
                    TaxZipCode=expedition_place,
                )
        Items = get_items(
            cprod_list,
            (
                float(orden_details.shipping_cost)
                if orden_details.shipping_cost
                else orden_details.shipping_cost
            ),
        )
        folio = await self.mx_invoice_repository.fetch_next_folio(
            supp_unit.supplier_business_id
        )
        display_date = issue_date.strftime("%Y-%m-%d")
        issuer = Issuer(
            Rfc=mx_prov_cert.rfc,
            FiscalRegime=str(mx_prov_cert.sat_regime.value),
            Name=mx_prov_cert.legal_name,
        )
        _invoice = FacturamaInvoice(
            LogoUrl=url,
            CfdiType=cfdi_type,
            PaymentForm=payment_form,
            ExpeditionPlace=expedition_place,
            PaymentMethod=payment_method,
            Date=issue_date,
            Folio=f"F-{folio}",
            Receiver=client,
            Issuer=issuer,
            Items=Items,
            OrdenNumber=str(orden_details.id),
            Observations=f"""Fecha de entrega: {display_date},
            # Pedido: {orden_obj.orden_number},
            Restaurante: {rest_branch.branch_name}""",
            GlobalInformation=global_information,
        )
        invoice_create = await facturma_api.new_3rd_party_invoice(invoice=_invoice)
        if invoice_create.get("status") != "ok":
            logger.error(invoice_create["msg"])
            raise GQLApiException(
                msg=invoice_create.get("msg", "Error to create invoice"),
                error_code=GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value,
            )
        # fetch invoice files
        _xml_file = await facturma_api.get_3rd_party_xml_invoice_by_id(
            id=invoice_create["data"].Id
        )
        _pdf_file = await facturma_api.get_3rd_party_pdf_invoice_by_id(
            id=invoice_create["data"].Id
        )
        pdf_file = None
        xml_file = None
        if "status" in _xml_file and _xml_file["status"] == "ok":
            xml_file = _xml_file["data"]
        else:
            logger.error(_xml_file["msg"])
        if "status" in _pdf_file and _pdf_file["status"] == "ok":
            pdf_file = _pdf_file["data"]
        else:
            logger.error(_pdf_file["msg"])

        # insert invoice in DB
        invoice_save = await self.mx_invoice_repository.add(
            MxInvoice(
                supplier_business_id=supp_unit.supplier_business_id,
                restaurant_branch_id=orden_details.restaurant_branch_id,
                sat_invoice_uuid=invoice_create["data"].Complement.TaxStamp.Uuid,
                invoice_number=invoice_create["data"].Folio,
                invoice_provider_id=invoice_create["data"].Id,
                invoice_provider="facturama",
                pdf_file=pdf_file,  # type: ignore (safe)
                xml_file=xml_file,  # type: ignore (safe)
                total=invoice_create["data"].Total,
                status=InvoiceStatusType.ACTIVE,
                payment_method=PaymentFormFacturama[
                    invoice_create["data"].PaymentMethod
                ],
                created_by=core_user.id,
                result=invoice_create["data"].Result,
            ),
            orden_details_id=orden_details.id,
        )

        if "success" in invoice_save and invoice_save["success"]:
            pdf, xml = "", ""
            if pdf_file:
                pdf = base64.b64encode(pdf_file).decode("utf-8")  # type: ignore (safe)
            if xml_file:
                xml = base64.b64encode(xml_file).decode("utf-8")  # type: ignore (safe)
            if _pdf_file and _xml_file:
                pdf_file_str = base64.b64encode(_pdf_file["data"]).decode("utf-8")
                xml_file_str = base64.b64encode(_xml_file["data"]).decode("utf-8")
                attcht = [
                    {
                        "content": pdf_file_str,
                        "filename": f"Factura_{rest_branch.branch_name}_Folio_{folio}.pdf",
                        "mimetype": "application/pdf",
                    },
                    {
                        "content": xml_file_str,
                        "filename": f"Factura_{rest_branch.branch_name}_Folio_{folio}.xml",
                        "mimetype": "application/xml",
                    },
                ]

                if not await send_restaurant_new_invoice_notification(
                    email_to=[rest_branch_mx_inv_info.email],  # type: ignore
                    restaurant_business_name=rest_branch.branch_name,
                    supplier_business_name=supplier_business.name,
                    folio=folio,
                    delivery_date=issue_date.strftime("%Y-%m-%d"),
                    attchs=attcht,
                ):
                    raise Exception("Error sending Invoice email")
            return CustomerMxInvoiceGQL(
                sat_id=invoice_create["data"].Id,
                total=invoice_create["data"].Total,
                issue_date=invoice_create["data"].Date,
                issuer=IssuerGQL(
                    rfc=invoice_create["data"].Issuer.Rfc,
                    business_name=(
                        invoice_create["data"].Issuer.TaxName
                        if invoice_create["data"].Issuer.TaxName
                        else "N/A"
                    ),
                ),
                receiver=ReceiverGQL(
                    rfc=invoice_create["data"].Receiver.Rfc,
                    business_name=invoice_create["data"].Receiver.Name,
                ),
                pdf=pdf,
                xml=xml,
            )
        else:
            raise GQLApiException(
                msg="Error to save invoice",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

    def validate_uniqueness(self, orden_delatis_list: List[OrdenDetails]) -> bool:
        unit_set = set()
        branch_set = set()
        for ord_det in orden_delatis_list:
            if ord_det.supplier_unit_id not in unit_set:
                unit_set.add(ord_det.supplier_unit_id)
            if ord_det.restaurant_branch_id not in branch_set:
                branch_set.add(ord_det.restaurant_branch_id)
        if len(branch_set) != 1 or len(unit_set) != 1:
            return False
        return True

    async def fetch_consolidated_by_orders(
        self, unit_repo: SupplierUnitRepositoryInterface, orden_ids: List[UUID]
    ) -> List[Dict[Any, Any]]:
        consolidated_record = await unit_repo.raw_query(
            query=f"""WITH orden_details_view as (
                -- get last status from orden
                WITH last_orden_status AS (
                    WITH rcos AS (
                        SELECT
                            orden_id,
                            status,
                            ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
                        FROM orden_status
                )
                    SELECT * FROM rcos WHERE row_num = 1
                ),
                -- get last pay status from orden
                last_pay_status AS (
                    WITH rcos AS (
                        SELECT
                            orden_id,
                            status as paystatus,
                            ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
                        FROM orden_paystatus
                )
                    SELECT * FROM rcos WHERE row_num = 1
                ),
                -- get last version of orden
                last_orden_version AS (
                    WITH last_upd AS (
                        SELECT
                            orden_id,
                            id as orden_details_id,
                            ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
                        FROM orden_details
                    )
                    SELECT * FROM last_upd WHERE row_num = 1
                )
                SELECT
                    orden_details.*,
                    los.status,
                    lps.paystatus
                FROM last_orden_version lov
                JOIN orden_details ON orden_details.id = lov.orden_details_id
                JOIN last_orden_status los ON los.orden_id = lov.orden_id
                LEFT JOIN last_pay_status lps ON lps.orden_id = lov.orden_id
        )
        , exploted_cart as (
            SELECT
                cp.cart_id,
                sp.sku,
                min(sp.description) "description",
                sum(round(cp.quantity * 1000)::double precision / 1000) "quantity",
                min(sp.sell_unit) "sell_unit",
                max(cp.unit_price) "unit_price",
                sum(cp.subtotal) "subtotal",
                min(sp.tax) "tax",
                min(sp.id::varchar)::uuid "supplier_product_id",
                min(sp.tax_id) "tax_id",
                min(sp.tax_unit) "tax_unit"
            FROM cart_product cp
            JOIN supplier_product sp on sp.id = cp.supplier_product_id
            WHERE cp.cart_id in (
                SELECT cart_id FROM orden_details_view od
                join supplier_unit su ON su.id = od.supplier_unit_id
                WHERE od.orden_id in {list_into_strtuple(orden_ids)}
            )
            AND cp.quantity > 0
            GROUP BY 1,2
            ORDER BY 3
            ),
            summary_prods as (
                SELECT
                    exploted_cart."description",
                    SUM(exploted_cart."quantity") as "quantity",
                    exploted_cart."sell_unit" as "sell_unit",
                    exploted_cart."unit_price",
                    SUM(exploted_cart."subtotal") as "subtotal",
                    min(exploted_cart."tax") as "tax",
                    min(exploted_cart.tax_id) "tax_id",
                    min(exploted_cart.tax_unit) "tax_unit",
                    min(exploted_cart."supplier_product_id"::varchar) as "supplier_product_id"
                FROM exploted_cart
                LEFT JOIN orden_details_view od on exploted_cart.cart_id = od.cart_id
                JOIN restaurant_branch rb on rb.id = od.restaurant_branch_id
                GROUP BY "description", "sell_unit", "unit_price"
            )
        SELECT
            "description",
            "sell_unit",
            "quantity"::varchar "quantity",
            "unit_price"::varchar "unit_price",
            (round("subtotal" * 1000)::double precision / 1000)::varchar "subtotal",
            "tax",
            "tax_id",
            "tax_unit",
            "supplier_product_id"
        FROM summary_prods
        order by "description" """,
            vals={},
        )
        if not consolidated_record:
            return []
        return [dict(c) for c in consolidated_record]

    def get_reference_orden(self, ordenes: List[OrdenGQL]):
        for orden in ordenes:
            if orden.details:
                if (
                    orden.details.supplier_unit_id
                    and orden.details.restaurant_branch_id
                ):
                    return {
                        "supplier_unit_id": UUID(orden.details.supplier_unit_id),  # type: ignore
                        "restaurant_branch_id": UUID(orden.details.restaurant_branch_id),  # type: ignore
                    }
        return None

    async def new_consolidated_customer_invoice(
        self,
        ordenes: List[OrdenGQL],
        payment_method: PayMethodType,
        public_general_invoice_flag: bool,
        firebase_id: Optional[str] = None,
        core_user: Optional[CoreUser] = None,
    ) -> List[CustomerMxInvoiceGQL]:
        if firebase_id:
            core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        elif core_user:
            pass
        else:
            logger.warning("No user info provided")
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        orden_detials_list: List[OrdenDetails] = []
        orden_id_list = []
        orden_details_ids_list = []
        ordens_ship_cost: float = 0
        for orden in ordenes:
            if orden.details:
                orden_id_list.append(orden.details.orden_id)
                orden_detials_list.append(orden.details)
                orden_details_ids_list.append(orden.details.id)
                if orden.details.shipping_cost:
                    ordens_ship_cost = ordens_ship_cost + float(
                        orden.details.shipping_cost
                    )
        if not self.validate_uniqueness(orden_detials_list):
            raise Exception("Any Orden have multiples units/branch")
        invoice_associated = await self.mx_invoice_repository.fetch_multiple_associated(
            orden_ids=orden_id_list
        )

        if invoice_associated:  # [TODO] Check if have any cancel
            raise GQLApiException(
                msg="Any order is already invoiced",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        # fetch user info including CSD files
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        # fetch core user
        consolidate = await self.fetch_consolidated_by_orders(
            self.supplier_unit_repo, orden_id_list
        )
        print(sum([float(con["subtotal"]) for con in consolidate]))
        df = pd.DataFrame(consolidate)
        print(df[["description", "quantity", "subtotal", "unit_price"]])
        # retrieve cart products
        if not consolidate:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.EMPTY_DATA.value,
                msg="Products not found",
            )
        reference_orden = self.get_reference_orden(ordenes)
        if not reference_orden:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.EMPTY_DATA.value,
                msg="Details not found",
            )

        mx_prov_cert = MxSatInvoicingCertificateInfo(
            **await self.mx_sat_cer_repo.fetch_certificate(
                reference_orden["supplier_unit_id"]
            )
        )
        sr_rel = await self.supplier_unit_repo.raw_query(
            """SELECT * FROM supplier_restaurant_relation
                    WHERE supplier_unit_id = :supplier_unit_id
                    AND restaurant_branch_id = :restaurant_branch_id
                """,
            {
                "supplier_unit_id": reference_orden["supplier_unit_id"],
                "restaurant_branch_id": reference_orden["restaurant_branch_id"],
            },
        )
        if not sr_rel:
            raise GQLApiException(
                msg="Supplier Restaurant Relation not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        _resp = await facturma_api.get_csd(rfc=mx_prov_cert.rfc)
        if "status" in _resp and _resp["status"] == "error":
            logger.warning("Issuer does not have CSD")
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                msg=_resp.get("msg", "error to get csd"),
            )
        # fetch branch info
        rest_branch_mx_inv_info_data = await self.restaurant_branch_repo.fetch_tax_info(
            reference_orden["restaurant_branch_id"]
        )
        rest_branch = RestaurantBranch(
            **await self.restaurant_branch_repo.fetch(
                reference_orden["restaurant_branch_id"]
            )
        )
        rest_branch_mx_inv_info = RestaurantBranchMxInvoiceInfo(
            **rest_branch_mx_inv_info_data
        )
        # fetch supplier unit info
        supp_unit = SupplierUnit(
            **await self.supplier_unit_repo.fetch(
                id=reference_orden["supplier_unit_id"]
            )
        )

        io_info = await self.supplier_restaurant_relation_mx_invoice_options_repo.fetch(
            sr_rel[0]["id"]
        )
        supplier = await self.supplier_business_repo.fetch(
            supp_unit.supplier_business_id
        )
        if not supplier:
            raise GQLApiException(
                msg="Supplier not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_business = SupplierBusiness(**supplier)
        if supplier_business.logo_url:
            url = construct_route_jpg_to_invoice(route=supplier_business.logo_url)
        else:
            url = None
        invoice_method = None
        if public_general_invoice_flag:
            invoice_method = "PUE"
        else:
            if io_info and io_info.invoice_type:
                invoice_method = io_info.invoice_type.value
            else:
                if mx_prov_cert.invoicing_options.invoice_type:
                    invoice_method = mx_prov_cert.invoicing_options.invoice_type.value
        if not invoice_method:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                msg="Error, no invoce info",
            )
        if public_general_invoice_flag:
            # build Customer object
            client = Customer(
                Address=CustomerAddress(
                    ZipCode=mx_prov_cert.zip_code,
                ),
                Rfc="XAXX010101000",
                Name="PÚBLICO EN GENERAL",
                CfdiUse="S01",
                FiscalRegime="616",
                TaxZipCode=mx_prov_cert.zip_code,
            )
        else:
            client = Customer(
                Email=rest_branch_mx_inv_info.email,
                Address=CustomerAddress(
                    ZipCode=rest_branch_mx_inv_info.zip_code,
                ),
                Rfc=rest_branch_mx_inv_info.mx_sat_id,
                Name=rest_branch_mx_inv_info.legal_name,
                CfdiUse=rest_branch_mx_inv_info.cfdi_use.name,
                FiscalRegime=str(rest_branch_mx_inv_info.sat_regime.value),
                TaxZipCode=rest_branch_mx_inv_info.zip_code,
            )

            # if not in facturama, create customer in facturama
            if not rest_branch_mx_inv_info_data.get("invoicing_provider_id", None):
                new_client = await facturma_api.new_client(client=client)
                if new_client.get("status") != "ok":
                    raise GQLApiException(
                        msg=new_client.get("msg", "Error to create client"),
                        error_code=GQLApiErrorCodeType.FACTURAMA_NEW_CUSTOMER_ERROR.value,
                    )
                client.Id = new_client["data"]["Id"]
                if not await self.restaurant_branch_repo.edit_tax_info(
                    restaurant_branch_id=rest_branch.id,
                    invoicing_provider_id=new_client["data"]["Id"],
                ):
                    raise GQLApiException(
                        msg="Eroro to add invoicing provider id",
                        error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                    )
            # build invoice
            if client.Address:
                client.Address.Street = rest_branch_mx_inv_info.full_address
        Items = get_consolidated_items(consolidate, float(ordens_ship_cost))
        folio = await self.mx_invoice_repository.fetch_next_folio(
            supp_unit.supplier_business_id
        )
        p_form = (
            INVOICE_PAYMENT_MAP[payment_method].value
            if invoice_method == InvoiceType.PUE.value
            else PaymentForm.TBD.value  # PPD
        )
        pedidos = ", ".join([str(pedidos.orden_number) for pedidos in ordenes])
        _invoice = FacturamaInvoice(
            LogoUrl=url,
            CfdiType=CFDIType.INGRESO.value,
            PaymentForm=p_form,
            ExpeditionPlace=mx_prov_cert.zip_code,
            PaymentMethod=invoice_method,
            Date=datetime.utcnow() - timedelta(hours=6),
            Folio=f"F-{folio}",
            Receiver=client,
            Issuer=Issuer(
                Rfc=mx_prov_cert.rfc,
                FiscalRegime=str(mx_prov_cert.sat_regime.value),
                Name=mx_prov_cert.legal_name,
            ),
            Items=Items,
            OrdenNumber=", ".join([str(uuid) for uuid in orden_details_ids_list]),
            Observations=f"""# Pedidos: {pedidos},
            Restaurante: {rest_branch.branch_name}""",
        )
        invoice_create = await facturma_api.new_3rd_party_invoice(invoice=_invoice)
        if invoice_create.get("status") != "ok":
            logger.error(invoice_create["msg"])
            raise GQLApiException(
                msg=invoice_create.get("msg", "Error to create invoice"),
                error_code=GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value,
            )
        # fetch invoice files
        _xml_file = await facturma_api.get_3rd_party_xml_invoice_by_id(
            id=invoice_create["data"].Id
        )
        _pdf_file = await facturma_api.get_3rd_party_pdf_invoice_by_id(
            id=invoice_create["data"].Id
        )
        pdf_file = None
        xml_file = None
        if "status" in _xml_file and _xml_file["status"] == "ok":
            xml_file = _xml_file["data"]
        else:
            logger.error(_xml_file["msg"])
        if "status" in _pdf_file and _pdf_file["status"] == "ok":
            pdf_file = _pdf_file["data"]
        else:
            logger.error(_pdf_file["msg"])
        customer_mx_invoice_customer_list = []
        inv_orden_details_ids_list = []
        for orden_details in orden_detials_list:
            inv_orden_details_ids_list.append(orden_details.id)
            # insert invoice in DB
        invoice_save = await self.mx_invoice_repository.add_consolidated(
            MxInvoice(
                supplier_business_id=supp_unit.supplier_business_id,
                restaurant_branch_id=reference_orden["restaurant_branch_id"],
                sat_invoice_uuid=invoice_create["data"].Complement.TaxStamp.Uuid,
                invoice_number=invoice_create["data"].Folio,
                invoice_provider_id=invoice_create["data"].Id,
                invoice_provider="facturama",
                pdf_file=pdf_file,  # type: ignore (safe)
                xml_file=xml_file,  # type: ignore (safe)
                total=invoice_create["data"].Total,
                status=InvoiceStatusType.ACTIVE,
                payment_method=PaymentFormFacturama[
                    invoice_create["data"].PaymentMethod
                ],
                created_by=core_user.id,  # type: ignore (safe)
                result=invoice_create["data"].Result,
            ),
            orden_details_ids=inv_orden_details_ids_list,
        )

        if "success" in invoice_save and invoice_save["success"]:
            pdf, xml = "", ""
            if pdf_file:
                pdf = base64.b64encode(pdf_file).decode("utf-8")  # type: ignore (safe)
            if xml_file:
                xml = base64.b64encode(xml_file).decode("utf-8")  # type: ignore (safe)
            customer_mx_invoice_customer_list.append(
                CustomerMxInvoiceGQL(
                    sat_id=invoice_create["data"].Id,
                    total=invoice_create["data"].Total,
                    issue_date=invoice_create["data"].Date,
                    issuer=IssuerGQL(
                        rfc=invoice_create["data"].Issuer.Rfc,
                        business_name=(
                            invoice_create["data"].Issuer.TaxName
                            if invoice_create["data"].Issuer.TaxName
                            else "N/A"
                        ),
                    ),
                    receiver=ReceiverGQL(
                        rfc=invoice_create["data"].Receiver.Rfc,
                        business_name=invoice_create["data"].Receiver.Name,
                    ),
                    pdf=pdf,
                    xml=xml,
                )
            )
        else:
            logger.error(f"Error to save invoice for invoice {invoice_save}")

        df = pd.DataFrame(
            [
                domain_to_dict(
                    odl,
                    skip=[
                        "orden_id",
                        "restaurant_branch_id",
                        "supplier_unit_id",
                        "cart_id",
                        "delivery_type",
                        "subtotal_without_tax",
                        "tax",
                        "discount",
                        "discount_code",
                        "cashback",
                        "cashback_transation_id",
                        "shipping_cost",
                        "packaging_cost",
                        "service_fee",
                        "payment_method",
                        "created_by",
                        "approved_by",
                        "created_at",
                        "subtotal",
                    ],
                )
                for odl in orden_detials_list
            ]
        )
        column_name_mapping = {
            "delivery_date": "fecha de entrega",
            "delivery_time": "hora de entrega",
            "comments": "comentarios",
        }
        df = df.rename(columns=column_name_mapping)
        html_table = df.to_html(index=False)
        if _pdf_file and _xml_file:
            pdf_file_str = base64.b64encode(_pdf_file["data"]).decode("utf-8")
            xml_file_str = base64.b64encode(_xml_file["data"]).decode("utf-8")
            today = datetime.utcnow().strftime("%Y-%m-%d")
            attcht = [
                {
                    "content": pdf_file_str,
                    "filename": f"ConsolidadoPDF_{supplier_business.name}_{today}.pdf",
                    "mimetype": "application/pdf",
                },
                {
                    "content": xml_file_str,
                    "filename": f"Consolidado_xml_{supplier_business.name}_{today}.xml",
                    "mimetype": "application/xml",
                },
            ]

            if not await send_new_consolidated_invoice_notification(
                email_to=[rest_branch_mx_inv_info.email],  # type: ignore
                restaurant_business_name=rest_branch.branch_name,
                supplier_business_name=supplier_business.name,
                folio=folio,
                html_table=html_table,
                attchs=attcht,
            ):
                raise GQLApiException(
                    msg="Error to send mail",
                    error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
        return customer_mx_invoice_customer_list

    async def new_customer_invoice_complement(
        self,
        payment_info: PaymentReceiptGQL,
        ord_details: OrdenDetails,
        amount: float,
        firebase_id: Optional[str] = None,
        core_user: Optional[CoreUser] = None,
    ) -> CustomerMxInvoiceGQL:
        amount = round(amount, 2)
        orden_ids: List[UUID] = []
        if payment_info.ordenes:
            for ordenes in payment_info.ordenes:
                orden_ids.append(ordenes.orden_id)
        invoices_info = await self.mx_invoice_repository.fetch_multiple_associated(
            orden_ids
        )
        # fetch user info including CSD files
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        # fetch core user
        if firebase_id:
            core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        elif core_user:
            pass
        else:
            logger.warning("No user info provided")
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch orden details
        orden_details_data = await self.orden_details_repo.fetch(
            orden_details_id=ord_details.id
        )
        if orden_details_data:
            orden_details = OrdenDetails(**orden_details_data)
        else:
            raise GQLApiException(
                msg="orden_Details not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if not orden_details.payment_method:
            orden_details.payment_method = PayMethodType.CASH

        # fetch certificate info
        mx_prov_cert = MxSatInvoicingCertificateInfo(
            **await self.mx_sat_cer_repo.fetch_certificate(
                orden_details.supplier_unit_id
            )
        )
        _resp = await facturma_api.get_csd(rfc=mx_prov_cert.rfc)
        if "status" in _resp and _resp["status"] == "error":
            logger.warning("Issuer does not have CSD")
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                msg=_resp.get("msg", "error to get csd"),
            )
        rest_branch = RestaurantBranch(
            **await self.restaurant_branch_repo.fetch(
                orden_details.restaurant_branch_id
            )
        )
        # fetch branch info
        rest_branch_mx_inv_info_data = await self.restaurant_branch_repo.fetch_tax_info(
            orden_details.restaurant_branch_id
        )
        rest_branch_mx_inv_info = RestaurantBranchMxInvoiceInfo(
            **rest_branch_mx_inv_info_data
        )
        # fetch supplier unit info
        supp_unit = SupplierUnit(
            **await self.supplier_unit_repo.fetch(id=orden_details.supplier_unit_id)
        )
        supplier = await self.supplier_business_repo.fetch(
            supp_unit.supplier_business_id
        )
        if not supplier:
            raise GQLApiException(
                msg="Supplier not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_business = SupplierBusiness(**supplier)
        if supplier_business.logo_url:
            url = construct_route_jpg_to_invoice(route=supplier_business.logo_url)
        else:
            url = None
        # build Customer object
        client = Customer(
            Rfc=rest_branch_mx_inv_info.mx_sat_id,
            Name=rest_branch_mx_inv_info.legal_name,
            CfdiUse="CP01",
            FiscalRegime=str(rest_branch_mx_inv_info.sat_regime.value),
            TaxZipCode=rest_branch_mx_inv_info.zip_code,
        )
        folio = await self.mx_invoice_comp_repo.fetch_next_folio()
        folio = "F-" + str(folio)
        # Map payment method
        payment_method = INVOICE_PAYMENT_MAP[
            PayMethodType(orden_details.payment_method)
        ].value
        related_documents: List[RelatedDocuments] = []
        unique_folios_set = set()
        unique_orden_numbers_set = set()
        for inv in invoices_info:
            if inv["invoice_number"] not in unique_folios_set and inv["invoice_number"]:
                unique_folios_set.add(inv["invoice_number"])
                related_documents.append(
                    RelatedDocuments(
                        TaxObject="01",
                        Folio=inv["invoice_number"],
                        Uuid=str(inv["sat_invoice_uuid"]),
                        PaymentMethod="PPD",
                        PartialityNumber=1,
                        PreviousBalanceAmount=amount,
                        AmountPaid=amount,
                        ImpSaldoInsoluto=0,
                    )
                )
            if (
                inv["orden_number"] not in unique_orden_numbers_set
                and inv["orden_number"]
            ):
                unique_orden_numbers_set.add(inv["orden_number"])
        date = (datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d")
        complement = FacturamaPayments(
            Payments=[
                FacturamaComplement(
                    Date=date,
                    PaymentForm=payment_method,
                    Amount=amount,
                    RelatedDocuments=related_documents,
                )
            ]
        )
        _invoice_complement = FacturamaInvoiceComplement(
            LogoUrl=url,
            CfdiType="P",
            NameId="1",
            ExpeditionPlace=mx_prov_cert.zip_code,
            Folio=folio,
            Receiver=client,
            Observations=f"""
            # Pedidos: {",".join(map(str, unique_orden_numbers_set))},
            # Facturas: {",".join(map(str, unique_folios_set))},
            Restaurante: {rest_branch.branch_name},""",
            Issuer=Issuer(
                Rfc=mx_prov_cert.rfc,
                FiscalRegime=str(mx_prov_cert.sat_regime.value),
                Name=mx_prov_cert.legal_name,
            ),
            Complemento=complement,
        )
        invoice_complement_create = await facturma_api.new_3rd_party_invoice_complement(
            invoice_complement=_invoice_complement
        )

        if invoice_complement_create.get("status") != "ok":
            logger.error(invoice_complement_create["msg"])
            raise GQLApiException(
                msg=invoice_complement_create.get("msg", "Error to create invoice"),
                error_code=GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value,
            )
        # fetch invoice files
        _xml_file = await facturma_api.get_3rd_party_xml_invoice_by_id(
            id=invoice_complement_create["data"].Id
        )
        _pdf_file = await facturma_api.get_3rd_party_pdf_invoice_by_id(
            id=invoice_complement_create["data"].Id
        )
        pdf_file = None
        xml_file = None
        if "status" in _xml_file and _xml_file["status"] == "ok":
            xml_file = _xml_file["data"]
        else:
            logger.error(_xml_file["msg"])
        if "status" in _pdf_file and _pdf_file["status"] == "ok":
            pdf_file = _pdf_file["data"]
        else:
            logger.error(_pdf_file["msg"])
        # insert invoice in DB

        if payment_info.ordenes:
            invoice_complement_save = []
            for inv in invoices_info:
                ics = await self.mx_invoice_comp_repo.add(
                    MxInvoiceComplement(
                        mx_invoice_id=inv["id"],
                        sat_invoice_uuid=invoice_complement_create[
                            "data"
                        ].Complement.TaxStamp.Uuid,
                        invoice_number=invoice_complement_create["data"].Folio,
                        invoice_provider_id=invoice_complement_create["data"].Id,
                        invoice_provider="facturama",
                        pdf_file=pdf_file,  # type: ignore (safe)
                        xml_file=xml_file,  # type: ignore (safe)
                        total=amount,
                        status=InvoiceStatusType.ACTIVE,
                        created_by=core_user.id,
                        result=invoice_complement_create["data"].Result,
                    )
                )
                await self.orden_payment_repo.add_payment_complement_receipt_association(
                    payment_info.ordenes[0].id, ics["id"]
                )
                invoice_complement_save.append(ics)

        if (
            "success" in invoice_complement_save[0]
            and invoice_complement_save[0]["success"]
        ):
            pdf, xml = "", ""
            if pdf_file:
                pdf = base64.b64encode(pdf_file).decode("utf-8")  # type: ignore (safe)
            if xml_file:
                xml = base64.b64encode(xml_file).decode("utf-8")  # type: ignore (safe)
            if _pdf_file and _xml_file:
                pdf_file_str = base64.b64encode(_pdf_file["data"]).decode("utf-8")
                xml_file_str = base64.b64encode(_xml_file["data"]).decode("utf-8")
                attcht = [
                    {
                        "content": pdf_file_str,
                        "filename": f"Factura_{rest_branch.branch_name}_Folio_{folio}.pdf",
                        "mimetype": "application/pdf",
                    },
                    {
                        "content": xml_file_str,
                        "filename": f"Factura_{rest_branch.branch_name}_Folio_{folio}.xml",
                        "mimetype": "application/xml",
                    },
                ]
                if not await send_restaurant_new_invoice_complement_notification(
                    email_to=[rest_branch_mx_inv_info.email],  # type: ignore
                    restaurant_business_name=rest_branch.branch_name,
                    supplier_business_name=supplier_business.name,
                    folio=folio,
                    delivery_date=date,
                    attchs=attcht,
                ):
                    raise Exception("Error sending Invoice email")
            return CustomerMxInvoiceGQL(
                sat_id=invoice_complement_create["data"].Id,
                total=invoice_complement_create["data"].Total,
                issue_date=invoice_complement_create["data"].Date,
                issuer=IssuerGQL(
                    rfc=invoice_complement_create["data"].Issuer.Rfc,
                    business_name=(
                        invoice_complement_create["data"].Issuer.TaxName
                        if invoice_complement_create["data"].Issuer.TaxName
                        else "N/A"
                    ),
                ),
                receiver=ReceiverGQL(
                    rfc=invoice_complement_create["data"].Receiver.Rfc,
                    business_name=invoice_complement_create["data"].Receiver.Name,
                ),
                pdf=pdf,
                xml=xml,
            )
        else:
            raise GQLApiException(
                msg="Error to save invoice",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

    async def new_consolidated_customer_invoice_complement(
        self,
        payment_info: PaymentReceiptGQL,
        ord_details: OrdenDetails,
        amounts: Dict[Any, Any],  # format {"orden_id: amount"}
        firebase_id: Optional[str] = None,
        core_user: Optional[CoreUser] = None,
    ) -> CustomerMxInvoiceGQL:
        orden_ids: List[UUID] = []
        if payment_info.ordenes:
            for ordenes in payment_info.ordenes:
                orden_ids.append(ordenes.orden_id)
        invoices_info = await self.mx_invoice_repository.fetch_multiple_associated(
            orden_ids
        )
        # fetch user info including CSD files
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        # fetch core user
        if firebase_id:
            core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        elif core_user:
            pass
        else:
            logger.warning("No user info provided")
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch orden details
        orden_details_data = await self.orden_details_repo.fetch(
            orden_details_id=ord_details.id
        )
        if orden_details_data:
            orden_details = OrdenDetails(**orden_details_data)
        else:
            raise GQLApiException(
                msg="orden_Details not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if not orden_details.payment_method:
            orden_details.payment_method = PayMethodType.CASH

        # fetch certificate info
        mx_prov_cert = MxSatInvoicingCertificateInfo(
            **await self.mx_sat_cer_repo.fetch_certificate(
                orden_details.supplier_unit_id
            )
        )
        _resp = await facturma_api.get_csd(rfc=mx_prov_cert.rfc)
        if "status" in _resp and _resp["status"] == "error":
            logger.warning("Issuer does not have CSD")
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                msg=_resp.get("msg", "error to get csd"),
            )
        rest_branch = RestaurantBranch(
            **await self.restaurant_branch_repo.fetch(
                orden_details.restaurant_branch_id
            )
        )
        # fetch branch info
        rest_branch_mx_inv_info_data = await self.restaurant_branch_repo.fetch_tax_info(
            orden_details.restaurant_branch_id
        )
        rest_branch_mx_inv_info = RestaurantBranchMxInvoiceInfo(
            **rest_branch_mx_inv_info_data
        )
        # fetch supplier unit info
        supp_unit = SupplierUnit(
            **await self.supplier_unit_repo.fetch(id=orden_details.supplier_unit_id)
        )
        supplier = await self.supplier_business_repo.fetch(
            supp_unit.supplier_business_id
        )
        if not supplier:
            raise GQLApiException(
                msg="Supplier not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_business = SupplierBusiness(**supplier)
        if supplier_business.logo_url:
            url = construct_route_jpg_to_invoice(route=supplier_business.logo_url)
        else:
            url = None
        # build Customer object
        client = Customer(
            Rfc=rest_branch_mx_inv_info.mx_sat_id,
            Name=rest_branch_mx_inv_info.legal_name,
            CfdiUse="CP01",
            FiscalRegime=str(rest_branch_mx_inv_info.sat_regime.value),
            TaxZipCode=rest_branch_mx_inv_info.zip_code,
        )
        folio = await self.mx_invoice_comp_repo.fetch_next_folio()
        folio = "F-" + str(folio)
        # Map payment method
        payment_method = INVOICE_PAYMENT_MAP[
            PayMethodType(orden_details.payment_method)
        ].value
        related_documents: List[RelatedDocuments] = []
        unique_folios_set = set()
        invoices_dict: List[Dict[Any, Any]] = []
        unique_orden_numbers_set = set()
        for inv in invoices_info:
            existing_index = next(
                (
                    index
                    for index, item in enumerate(invoices_dict)
                    if inv["orden_number"] in item
                ),
                -1,
            )
            if inv["invoice_number"] not in unique_folios_set:
                unique_folios_set.add(inv["invoice_number"])
                invoices_dict.append(
                    {
                        inv["invoice_number"]: {
                            "amount": amounts[inv["orden_id"]],
                            "sat_invoice_uuid": inv["sat_invoice_uuid"],
                        }
                    }
                )
            else:
                # If the item already exists, update its amount
                existing_item = invoices_dict[existing_index]
                existing_item[inv["invoice_number"]]["amount"] = (
                    existing_item[inv["invoice_number"]]["amount"]
                    + amounts[inv["orden_id"]]
                )
            if (
                inv["orden_number"] not in unique_orden_numbers_set
                and inv["orden_number"]
            ):
                unique_orden_numbers_set.add(inv["orden_number"])
        for invoices in invoices_dict:
            folio_key = next(iter(invoices.keys()))
            related_documents.append(
                RelatedDocuments(
                    TaxObject="01",
                    Folio=folio_key,
                    Uuid=str(invoices[folio_key]["sat_invoice_uuid"]),
                    PaymentMethod="PPD",
                    PartialityNumber=1,
                    PreviousBalanceAmount=round(
                        float(invoices[folio_key]["amount"]), 2
                    ),
                    AmountPaid=round(float(invoices[folio_key]["amount"]), 2),
                    ImpSaldoInsoluto=0,
                )
            )

        complement = FacturamaPayments(
            Payments=[
                FacturamaComplement(
                    Date=(datetime.utcnow() - timedelta(hours=6)).strftime("%Y-%m-%d"),
                    PaymentForm=payment_method,
                    Amount=round(float(payment_info.payment_value), 2),
                    RelatedDocuments=related_documents,
                )
            ]
        )
        _invoice_complement = FacturamaInvoiceComplement(
            LogoUrl=url,
            CfdiType="P",
            NameId="1",
            ExpeditionPlace=mx_prov_cert.zip_code,
            Folio=folio,
            Receiver=client,
            Observations=f"""
            # Pedidos: {",".join(map(str, unique_orden_numbers_set))},
            # Facturas: {",".join(map(str, unique_folios_set))},
            Restaurante: {rest_branch.branch_name},""",
            Issuer=Issuer(
                Rfc=mx_prov_cert.rfc,
                FiscalRegime=str(mx_prov_cert.sat_regime.value),
                Name=mx_prov_cert.legal_name,
            ),
            Complemento=complement,
        )
        invoice_complement_create = await facturma_api.new_3rd_party_invoice_complement(
            invoice_complement=_invoice_complement
        )

        if invoice_complement_create.get("status") != "ok":
            logger.error(invoice_complement_create["msg"])
            raise GQLApiException(
                msg=invoice_complement_create.get("msg", "Error to create invoice"),
                error_code=GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value,
            )
        # fetch invoice files
        _xml_file = await facturma_api.get_3rd_party_xml_invoice_by_id(
            id=invoice_complement_create["data"].Id
        )
        _pdf_file = await facturma_api.get_3rd_party_pdf_invoice_by_id(
            id=invoice_complement_create["data"].Id
        )
        pdf_file = None
        xml_file = None
        if "status" in _xml_file and _xml_file["status"] == "ok":
            xml_file = _xml_file["data"]
        else:
            logger.error(_xml_file["msg"])
        if "status" in _pdf_file and _pdf_file["status"] == "ok":
            pdf_file = _pdf_file["data"]
        else:
            logger.error(_pdf_file["msg"])
        # insert invoice in DB

        if payment_info.ordenes:
            invoice_complement_save = []
            for inv in invoices_info:
                ics = await self.mx_invoice_comp_repo.add(
                    MxInvoiceComplement(
                        mx_invoice_id=inv["id"],
                        sat_invoice_uuid=invoice_complement_create[
                            "data"
                        ].Complement.TaxStamp.Uuid,
                        invoice_number=invoice_complement_create["data"].Folio,
                        invoice_provider_id=invoice_complement_create["data"].Id,
                        invoice_provider="facturama",
                        pdf_file=pdf_file,  # type: ignore (safe)
                        xml_file=xml_file,  # type: ignore (safe)
                        total=payment_info.payment_value,
                        status=InvoiceStatusType.ACTIVE,
                        created_by=core_user.id,
                        result=invoice_complement_create["data"].Result,
                    )
                )
                for orden_payment in payment_info.ordenes:
                    await self.orden_payment_repo.add_payment_complement_receipt_association(
                        orden_payment.id, ics["id"]
                    )
                invoice_complement_save.append(ics)

        if (
            "success" in invoice_complement_save[0]
            and invoice_complement_save[0]["success"]
        ):
            pdf, xml = "", ""
            if pdf_file:
                pdf = base64.b64encode(pdf_file).decode("utf-8")  # type: ignore (safe)
            if xml_file:
                xml = base64.b64encode(xml_file).decode("utf-8")  # type: ignore (safe)
            return CustomerMxInvoiceGQL(
                sat_id=invoice_complement_create["data"].Id,
                total=invoice_complement_create["data"].Total,
                issue_date=invoice_complement_create["data"].Date,
                issuer=IssuerGQL(
                    rfc=invoice_complement_create["data"].Issuer.Rfc,
                    business_name=(
                        invoice_complement_create["data"].Issuer.TaxName
                        if invoice_complement_create["data"].Issuer.TaxName
                        else "N/A"
                    ),
                ),
                receiver=ReceiverGQL(
                    rfc=invoice_complement_create["data"].Receiver.Rfc,
                    business_name=invoice_complement_create["data"].Receiver.Name,
                ),
                pdf=pdf,
                xml=xml,
            )
        else:
            raise GQLApiException(
                msg="Error to save invoice",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

    async def get_customer_invoices_by_orden(
        self, orden_id: UUID
    ) -> List[CustomerMxInvoiceGQL]:
        if not await self.orden_repo.validation(orden_id=orden_id):
            raise GQLApiException(
                msg="orden not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        _invs = await self.mx_invoice_repository.fetch_invoice_details_by_orden(
            orden_id=orden_id
        )
        if not _invs:
            raise GQLApiException(
                msg="There are no orders associated with that order",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        cust_mx_inv_list = []
        for _inv in _invs:
            mx_cert_inf = await self.mx_sat_cer_repo.fetch_certificate(
                supplier_unit_id=_inv["supplier_unit_id"]
            )
            if not mx_cert_inf:
                raise GQLApiException(
                    msg="There are no orders associated with that order",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                )
            try:
                pdf = ""
                xml = ""
                if "pdf_file" in _inv:
                    pdf = base64.b64encode(_inv["pdf_file"]).decode("utf-8")
                if "xml_file" in _inv:
                    xml = base64.b64encode(_inv["xml_file"]).decode("utf-8")
                mx_cert = MxSatInvoicingCertificateInfo(**mx_cert_inf)
                cust_mx_inv = CustomerMxInvoiceGQL(
                    sat_id=_inv["invoice_provider_id"],  # type: ignore
                    total=_inv["total"],  # type: ignore
                    issue_date=_inv["created_at"],
                    issuer=IssuerGQL(
                        rfc=_inv["mx_sat_id"],  # type: ignore
                        business_name=_inv["legal_name"],  # type: ignore
                    ),
                    receiver=ReceiverGQL(
                        rfc=mx_cert.rfc,  # type: ignore
                        business_name=mx_cert.legal_name,  # type: ignore
                    ),
                    pdf=pdf,  # type: ignore
                    xml=xml,  # type: ignore
                )
                cust_mx_inv_list.append(cust_mx_inv)
            except Exception as e:
                logger.error(e)
                raise GQLApiException(
                    msg="Error to build invoice details",
                    error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR,
                )
        return cust_mx_inv_list

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
        # fetch supplier user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_user = await self.supplier_user_repo.fetch(core_user.id)
        if not supplier_user:
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch supplier unit and supplier_business permissions
        supplier_unit = await self.supplier_unit_repo.fetch(supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Supplier Unit not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        su_perms = await self.supplier_user_perms_repo.fetch_by_supplier_business(
            supplier_unit["supplier_business_id"]
        )
        # verify core user has access to supplier unit
        _user_w_access = False
        if su_perms:
            if supplier_user["id"] in [sup["supplier_user_id"] for sup in su_perms]:
                _user_w_access = True
        if not _user_w_access:
            raise GQLApiException(
                msg="User has no access to this supplier unit",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch invoices, suppliers and branches
        _invs = await self.mx_invoice_repository.fetch_invoice_details_by_dates(
            supplier_unit_id=supplier_unit_id,
            from_date=from_date,
            until_date=until_date,
            receiver=receiver,
            page=page,
            page_size=page_size,
        )
        if not _invs:
            logger.warning("No invoices found")
            return []
        # fetch suppliers
        suppliers_idx = {}
        for inv in _invs:
            if inv["supplier_business_id"] in suppliers_idx:
                continue
            suppliers_idx[inv["supplier_business_id"]] = SupplierBusiness(
                **await self.supplier_business_repo.get(inv["supplier_business_id"])
            )
        # fetch branches
        branches_idx = {}
        for inv in _invs:
            if inv["restaurant_branch_id"] in branches_idx:
                continue
            branches_idx[inv["restaurant_branch_id"]] = RestaurantBranch(
                **await self.restaurant_branch_repo.get(inv["restaurant_branch_id"])
            )
        # build response
        list_mx_invs = []
        for mx_inv in _invs:
            mx_inv_gql = MxInvoiceGQL(
                id=mx_inv["id"],
                orden_id=mx_inv["orden_id"],
                sat_invoice_uuid=mx_inv["sat_invoice_uuid"],
                invoice_number=mx_inv["invoice_number"],
                total=mx_inv["total"],
                status=InvoiceStatusType(
                    DataTypeDecoder.get_mxinvoice_status_value(mx_inv["status"])
                ),
                created_by=mx_inv["created_by"],
                created_at=mx_inv["created_at"],
                orden=MxInvoiceOrden(
                    id=mx_inv["mx_invoice_orden_id"],
                    mx_invoice_id=mx_inv["id"],
                    orden_details_id=mx_inv["orden_details_id"],
                    created_at=mx_inv["mxio_created_at"],
                    created_by=mx_inv["mxio_created_by"],
                    last_updated=mx_inv["mxio_last_updated"],
                ),
                supplier=suppliers_idx[mx_inv["supplier_business_id"]],
                restaurant_branch=branches_idx[mx_inv["restaurant_branch_id"]],
                pdf_file=(
                    base64.b64encode(mx_inv["pdf_file"]).decode("utf-8")
                    if isinstance(mx_inv["pdf_file"], bytes)
                    else None
                ),
                xml_file=(
                    base64.b64encode(mx_inv["xml_file"]).decode("utf-8")
                    if isinstance(mx_inv["xml_file"], bytes)
                    else None
                ),
            )
            list_mx_invs.append(mx_inv_gql)
        return list_mx_invs

    async def cancel_customer_invoice(
        self,
        orden_id: UUID,
        motive: str,
        uuid_replacement: Optional[str] = None,
    ) -> InvoiceStatus:
        ordn_dets = await self.orden_details_repo.fetch_last(orden_id)
        if not ordn_dets:
            raise GQLApiException(
                msg="Issues to get orden details",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        ord_det_obj = OrdenDetails(**ordn_dets)
        invoice_associated = (
            await self.mx_invoice_repository.fetch_assocciated_by_orden(
                orden_details_id=ord_det_obj.id
            )
        )
        if not invoice_associated:
            raise GQLApiException(
                msg="This order doesn't invoiced orden",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        invoice_associated = MxInvoiceOrden(**invoice_associated)

        invoices_associated = await self.mx_invoice_repository.find_asocciated_ordenes(
            invoice_associated.mx_invoice_id
        )
        if not invoices_associated:
            raise GQLApiException(
                msg="Error to find invoices associated",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        for ia in invoices_associated:
            inv_comp = await self.mx_invoice_comp_repo.find_by_invoice(ia.mx_invoice_id)
            if len(inv_comp) > 0:
                raise GQLApiException(
                    msg="This order has a complement",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        mx_invoice = await self.mx_invoice_repository.fetch(
            mx_invoice_id=invoice_associated.mx_invoice_id
        )
        if not mx_invoice:
            raise GQLApiException(
                msg="Error to find mx_invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        mx_invoice = MxInvoice(**mx_invoice)
        if not mx_invoice.invoice_provider_id:
            raise GQLApiException(
                msg="Not able to cancel invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        _resp = await facturma_api.cancel_3rd_party_pdf_invoice_by_id(
            id=mx_invoice.invoice_provider_id,
            motive=motive,
            uuid_replacement=uuid_replacement,
        )
        if "status" not in _resp:
            raise GQLApiException(
                msg="Error data structure",
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
        if _resp["status"] == "error":
            raise GQLApiException(
                msg="Error to cancel invoice from facturama",
                error_code=GQLApiErrorCodeType.FACTURAMA_DELETE_ERROR.value,
            )
        if _resp["status"] == "ok":
            if await self.mx_invoice_repository.edit(
                mx_invoice_id=mx_invoice.id,  # type: ignore
                status=InvoiceStatusType.CANCELED,
                cancel_result=json.dumps(_resp["data"]),
            ):
                for ia in invoices_associated:
                    od = await self.orden_details_repo.fetch(ia.orden_details_id)
                    if not od:
                        raise GQLApiException(
                            msg="Issues to get orden details",
                            error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                        )
                    od_obj = OrdenDetails(**od)
                    if not await self.orden_details_repo.add(
                        OrdenDetails(
                            id=uuid4(),
                            orden_id=od_obj.orden_id,
                            version=od_obj.version + 1,
                            restaurant_branch_id=od_obj.restaurant_branch_id,
                            supplier_unit_id=od_obj.supplier_unit_id,
                            cart_id=od_obj.cart_id,
                            delivery_date=od_obj.delivery_date,
                            delivery_time=od_obj.delivery_time,
                            delivery_type=SellingOption(od_obj.delivery_type),
                            subtotal_without_tax=od_obj.subtotal_without_tax,
                            tax=od_obj.tax,
                            subtotal=od_obj.subtotal,
                            discount=od_obj.discount,
                            discount_code=od_obj.discount_code,
                            cashback=od_obj.cashback,
                            cashback_transation_id=od_obj.cashback_transation_id,
                            shipping_cost=od_obj.shipping_cost,
                            packaging_cost=od_obj.packaging_cost,
                            service_fee=od_obj.service_fee,
                            total=od_obj.total,
                            comments=od_obj.comments,
                            payment_method=PayMethodType(od_obj.payment_method),
                            created_by=od_obj.created_by,
                            approved_by=od_obj.approved_by,
                        )
                    ):
                        raise GQLApiException(
                            msg="Error to cancel invoice from facturama",
                            error_code=GQLApiErrorCodeType.FACTURAMA_DELETE_ERROR.value,
                        )
            return InvoiceStatus(id=mx_invoice.invoice_provider_id, canceled=True)
        return InvoiceStatus(id=mx_invoice.invoice_provider_id, canceled=False)

    async def cancel_customer_invoice_by_invoice(
        self,
        mx_invoice_id: UUID,
        motive: str,
        uuid_replacement: Optional[str] = None,
    ) -> InvoiceStatus:
        inv_comp = await self.mx_invoice_comp_repo.find_by_invoice(mx_invoice_id)
        if len(inv_comp) > 0:
            raise GQLApiException(
                msg="This order has a complement",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        mx_invoice = await self.mx_invoice_repository.fetch(mx_invoice_id=mx_invoice_id)
        if not mx_invoice:
            raise GQLApiException(
                msg="Error to find mx_invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        mx_invoice = MxInvoice(**mx_invoice)
        if not mx_invoice.invoice_provider_id:
            raise GQLApiException(
                msg="Not able to cancel invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        _resp = await facturma_api.cancel_3rd_party_pdf_invoice_by_id(
            id=mx_invoice.invoice_provider_id,
            motive=motive,
            uuid_replacement=uuid_replacement,
        )
        if "status" not in _resp:
            raise GQLApiException(
                msg="Error data structure",
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
        if _resp["status"] == "error":
            raise GQLApiException(
                msg="Error to cancel invoice from facturama",
                error_code=GQLApiErrorCodeType.FACTURAMA_DELETE_ERROR.value,
            )
        if _resp["status"] == "ok":
            if await self.mx_invoice_repository.edit(
                mx_invoice_id=mx_invoice.id,  # type: ignore
                status=InvoiceStatusType.CANCELED,
                cancel_result=json.dumps(_resp["data"]),
            ):
                return InvoiceStatus(id=mx_invoice.invoice_provider_id, canceled=True)
            return InvoiceStatus(id=mx_invoice.invoice_provider_id, canceled=False)
        return InvoiceStatus(id=mx_invoice.invoice_provider_id, canceled=False)

    async def format_invoices_to_export(
        self, invoices: List[MxInvoiceGQL]
    ) -> List[Dict[Any, Any]]:
        # sort invoices by id
        sorted_invoices = sorted(invoices, key=lambda inv: inv.id)
        # create an index referncing the multiple orden_ids of a given invoice
        inv_idx = {}
        for inv in sorted_invoices:
            if inv.id in inv_idx:
                inv_idx[inv.id].append(str(inv.orden_id))
            else:
                inv_idx[inv.id] = [str(inv.orden_id)]
        # accumulated invoices
        acc_, frmt_invs = set(), []
        # serialize each invoice
        for s_inv in sorted_invoices:
            # skip invoices already added
            if s_inv.id in acc_:
                continue
            _inv_dict = {}
            for k, v in s_inv.__dict__.items():
                if "_by" in k or k == "orden" or "_file" in k:
                    pass
                elif isinstance(v, Enum):
                    if k == "status":
                        _inv_dict[k] = (
                            "Activa"
                            if v.value == InvoiceStatusType.ACTIVE.value
                            else "Cancelada"
                        )
                    else:
                        _inv_dict[k] = v.value
                elif isinstance(v, datetime):
                    if k == "created_at":
                        # split date and time
                        _inv_dict[k] = v.astimezone(APP_TZ).strftime("%Y-%m-%d")
                        _inv_dict[k + "_time"] = v.astimezone(APP_TZ).strftime(
                            "%H:%M CST"
                        )
                    else:
                        _inv_dict[k] = v.astimezone(APP_TZ).strftime(
                            "%Y-%m-%d %H:%M CST"
                        )
                elif isinstance(v, UUID):
                    _inv_dict[k] = str(v)
                elif isinstance(v, RestaurantBranch):
                    _inv_dict["Cliente"] = v.branch_name
                elif isinstance(v, SupplierBusiness):
                    _inv_dict["Proveedor"] = v.name
                else:
                    _inv_dict[k] = str(v)
            _inv_dict["orden_ids"] = ",".join(inv_idx[s_inv.id])
            acc_.add(s_inv.id)
            frmt_invs.append(_inv_dict)
        # return
        return frmt_invs

    async def get_invoice_type(self, orden_details_id) -> InvoiceType | None:
        mx_invoice = await self.mx_invoice_repository.fetch_from_orden_details(
            orden_details_id=orden_details_id
        )
        if not mx_invoice:
            return None
        mx_invoice_obj = MxInvoice(**mx_invoice)
        return mx_invoice_obj.payment_method

    async def validate_complements_by_orders(self, orden_ids: List[UUID]) -> bool:
        for orden_id in orden_ids:
            ordn_dets = await self.orden_details_repo.fetch_last(orden_id)
            if not ordn_dets:
                raise GQLApiException(
                    msg="Issues to get orden details",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            ord_det_obj = OrdenDetails(**ordn_dets)
            invoice_associated = (
                await self.mx_invoice_repository.fetch_assocciated_by_orden(
                    orden_details_id=ord_det_obj.id
                )
            )
            if not invoice_associated:
                continue
            invoice_associated = MxInvoiceOrden(**invoice_associated)

            invoices_associated = (
                await self.mx_invoice_repository.find_asocciated_ordenes(
                    invoice_associated.mx_invoice_id
                )
            )
            if not invoices_associated:
                raise GQLApiException(
                    msg="Error to find invoices associated",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            for ia in invoices_associated:
                inv_comp = await self.mx_invoice_comp_repo.find_by_invoice(
                    ia.mx_invoice_id
                )
                if len(inv_comp) > 0:
                    raise GQLApiException(
                        msg="This order has a complement",
                        error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                    )
        return True

    async def re_invoice(
        self,
        old_ordn_det: OrdenDetails,
        motive: str,
        orden_id: UUID,
    ) -> InvoiceStatus:
        new_ord_det = await self.orden_details_repo.fetch_last(orden_id)

        if not new_ord_det:
            raise GQLApiException(
                msg="Issues to get orden details",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        new_ord_det_obj = OrdenDetails(**new_ord_det)
        invoice_associated = (
            await self.mx_invoice_repository.fetch_assocciated_by_orden(
                orden_details_id=old_ordn_det.id
            )
        )
        new_invoice_associated = (
            await self.mx_invoice_repository.fetch_assocciated_by_orden(
                orden_details_id=new_ord_det_obj.id
            )
        )
        if not new_invoice_associated:
            raise GQLApiException(
                msg="This order doesn't invoiced orden",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        new_invoice_associated = MxInvoiceOrden(**new_invoice_associated)

        new_invoice = await self.mx_invoice_repository.fetch(
            new_invoice_associated.mx_invoice_id
        )
        if not new_invoice:
            raise GQLApiException(
                msg="Error to get new invoice invoiced",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        new_invoice_obj = MxInvoice(**new_invoice)
        if not invoice_associated:
            return InvoiceStatus(id=new_invoice_obj.id, canceled=True)  # type: ignore (safe)

        invoice_associated = MxInvoiceOrden(**invoice_associated)

        invoices_associated = await self.mx_invoice_repository.find_asocciated_ordenes(
            invoice_associated.mx_invoice_id
        )
        if not invoices_associated:
            raise GQLApiException(
                msg="Error to find invoices associated",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        for ia in invoices_associated:
            inv_comp = await self.mx_invoice_comp_repo.find_by_invoice(ia.mx_invoice_id)
            if len(inv_comp) > 0:
                raise GQLApiException(
                    msg="This order has a complement",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )

        mx_invoice = await self.mx_invoice_repository.fetch(
            mx_invoice_id=invoice_associated.mx_invoice_id
        )
        if not mx_invoice:
            raise GQLApiException(
                msg="Error to find mx_invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        mx_invoice = MxInvoice(**mx_invoice)
        if mx_invoice.status == "canceled":
            return InvoiceStatus(id=mx_invoice.id, canceled=True)  # type: ignore (safe)
        if not mx_invoice.invoice_provider_id:
            raise GQLApiException(
                msg="Not able to cancel invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        _resp = await facturma_api.cancel_3rd_party_pdf_invoice_by_id(
            id=mx_invoice.invoice_provider_id,
            motive=motive,
            uuid_replacement=str(new_invoice_obj.sat_invoice_uuid),
        )
        if "status" not in _resp:
            raise GQLApiException(
                msg="Error data structure",
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
        if _resp["status"] == "error":
            raise GQLApiException(
                msg="Error to cancel invoice from facturama",
                error_code=GQLApiErrorCodeType.FACTURAMA_DELETE_ERROR.value,
            )
        if _resp["status"] == "ok":
            if await self.mx_invoice_repository.edit(
                mx_invoice_id=mx_invoice.id,  # type: ignore
                status=InvoiceStatusType.CANCELED,
                cancel_result=json.dumps(_resp["data"]),
            ):
                return InvoiceStatus(id=mx_invoice.id, canceled=True)  # type: ignore (safe)
        return InvoiceStatus(id=mx_invoice.id, canceled=False)  # type: ignore (safe)


class MxSatCertificateHandler(MxSatCertificateHandlerInterface):
    def __init__(
        self,
        mx_sat_certificate_repository: MxSatCertificateRepositoryInterface,
    ):
        self.mx_sat_certificate_repository = mx_sat_certificate_repository

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
        # build MX Sat Certificate Info
        mx_info = MxSatInvoicingCertificateInfo(
            rfc=rfc,
            zip_code=zip_code,
            legal_name=legal_name,
            sat_regime=sat_regime,
            sat_pass_code=sat_pass_code,
            cer_file=cer_file,
            key_file=key_file,
            supplier_unit_id=supplier_unit_id,
            invoicing_options=InvoicingOptions(
                automated_invoicing=(
                    True if invoicing_type.lower() != "deactivated" else False
                ),
                triggered_at=(
                    InvoiceTriggerTime.AT_PURCHASE
                    if invoicing_type.lower() == "at_purchase"
                    else (
                        InvoiceTriggerTime.AT_DELIVERY
                        if invoicing_type.lower() == "at_delivery"
                        else None
                    )
                ),
                invoice_type=InvoiceType(invoice_type),
            ),
        )
        if not await self.mx_sat_certificate_repository.upsert(
            sat_certificate=mx_info,
        ):
            raise GQLApiException(
                msg="Error while saving certificate in Mongo",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        # verify if certificate exists in facturama
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        fact_data = await facturma_api.get_csd(rfc=rfc)
        if fact_data["status"] == "error":
            if fact_data["status_code"] == 404:
                _resp = await facturma_api.new_csd(mx_sat_invoice_certificate=mx_info)
                if "status" in _resp and _resp["status"] == "error":
                    raise GQLApiException(
                        msg=_resp.get("msg", "error upload csd"),
                        error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                    )
            else:
                raise GQLApiException(
                    msg=fact_data.get("msg", "error to upload csd"),
                    error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                )
        if fact_data["status"] == "ok":
            _resp = await facturma_api.edit_csd(mx_sat_invoice_certificate=mx_info)
            if "status" in _resp and _resp["status"] == "error":
                raise GQLApiException(
                    msg=_resp.get("msg", "error edit csd"),
                    error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                )

        facturama_certificate = await facturma_api.get_csd(rfc=rfc)
        if facturama_certificate["status"] == "error":
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                msg=facturama_certificate.get("msg", "error to get csd"),
            )
        # build response
        sat_certificate_gql = MxSatCertificateGQL(
            mx_sat_certificate=mx_info,
            facturama_response=FacturamaData(**facturama_certificate["data"]),
        )
        return sat_certificate_gql

    async def get_customer_certificate(
        self, supplier_business_id: UUID, rfc: str
    ) -> MxSatCertificateGQL:
        _mongo_data = MxSatInvoicingCertificateInfo(
            **await self.mx_sat_certificate_repository.fetch_certificate(
                supplier_business_id
            )
        )
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        facturama_certificate = await facturma_api.get_csd(rfc=rfc)
        if (
            "status" in facturama_certificate
            and facturama_certificate["status"] == "error"
        ):
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
                msg=facturama_certificate.get("msg", "error to get csd"),
            )
        # build response
        sat_certificate_gql = MxSatCertificateGQL(
            mx_sat_certificate=_mongo_data,
            facturama_response=FacturamaData(**facturama_certificate),
        )
        return sat_certificate_gql

    async def get_mx_sat_invocing_certificate(
        self, supplier_unit_id: UUID
    ) -> MxSatInvoicingCertificateInfo | NoneType:
        sat_cert = await self.mx_sat_certificate_repository.fetch_certificate(
            supplier_unit_id
        )
        if not sat_cert:
            return None
        _mongo_data = MxSatInvoicingCertificateInfo(**sat_cert)
        return _mongo_data


def get_items(
    cart_product_list: List[CartProductGQL], shipping_cost: Optional[float]
) -> List[Item]:
    try:
        item_list = []
        for cart_product in cart_product_list:
            if cart_product.subtotal is None:
                raise GQLApiException(
                    msg="Error to find subtotal orden",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if cart_product.quantity is None:
                raise GQLApiException(
                    msg="Error to find quantity cart to invoice",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if cart_product.supp_prod is None:
                raise GQLApiException(
                    msg="Error to find product cart to invoice",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            _div: float = 1
            total_tax_sum = 0
            if cart_product.supp_prod.tax:
                _div += cart_product.supp_prod.tax
            if cart_product.supp_prod.mx_ieps:
                _div += cart_product.supp_prod.mx_ieps
            _subtotal = round(cart_product.subtotal / _div, 4)
            _quantity = round(cart_product.quantity, 4)
            _unitprice = round(_subtotal / _quantity, 4)
            _taxes = []
            _totaltax = round(_subtotal * cart_product.supp_prod.tax, 4)
            _iva_tax = SatTaxes(
                Total=_totaltax,
                Name="IVA",
                Base=_subtotal,
                Rate=cart_product.supp_prod.tax,
                IsRetention=False,
            )
            _taxes.append(_iva_tax)
            total_tax_sum += _totaltax
            if cart_product.supp_prod.mx_ieps:
                _total_ieps = round(_subtotal * cart_product.supp_prod.mx_ieps, 4)
                _taxes.append(
                    SatTaxes(
                        Total=_total_ieps,
                        Name="IEPS",
                        Base=_subtotal,
                        Rate=cart_product.supp_prod.mx_ieps,  # type: ignore
                        IsRetention=False,
                    )
                )
                total_tax_sum += _total_ieps
            if len(_taxes) == 0:
                raise GQLApiException(
                    msg="Error to find taxes to invoice",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )

            item = Item(
                ProductCode=cart_product.supp_prod.tax_id,  # type: ignore
                Description=cart_product.supp_prod.description,  # type: ignore
                UnitCode=cart_product.supp_prod.tax_unit,  # type: ignore
                Subtotal=_subtotal,
                Quantity=_quantity,
                TaxObject="02",
                Total=round(_subtotal + total_tax_sum, 4),  # type: ignore
                Taxes=_taxes,
                UnitPrice=_unitprice,
            )
            item_list.append(item)
        sorted_item_list = sorted(item_list, key=lambda item: item.Description)
        if isinstance(shipping_cost, float) and shipping_cost > 0:
            _subtotal = round(shipping_cost / (1.16), 4)
            _unitprice = _subtotal
            _totaltax = round(_subtotal * 0.16, 4)
            sorted_item_list.append(
                Item(
                    ProductCode="78102205",
                    Description="Cargo por envío",
                    UnitCode="E48",
                    Subtotal=_subtotal,
                    Quantity=1,
                    TaxObject="02",
                    Total=round(_subtotal * (1.16), 4),
                    Taxes=[
                        SatTaxes(
                            Total=_totaltax,
                            Name="IVA",
                            Base=_subtotal,
                            Rate=0.16,
                            IsRetention=False,
                        )
                    ],
                    UnitPrice=_unitprice,
                )
            )
        return sorted_item_list
    except Exception as e:
        logger.error(e)
        raise GQLApiException(
            msg="Error to build sat items",
            error_code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
        )


def get_consolidated_items(
    product_list: List[Dict[Any, Any]], ordens_ship_cost: Optional[float] = None
) -> List[Item]:
    try:
        item_list = []
        for cart_product in product_list:
            cart_product["subtotal"] = float(cart_product["subtotal"])
            cart_product["tax"] = float(cart_product["tax"])
            cart_product["quantity"] = float(cart_product["quantity"])
            _subtotal = round(cart_product["subtotal"] / (1 + cart_product["tax"]), 4)

            _quantity = round(cart_product["quantity"], 4)
            _unitprice = round(_subtotal / _quantity, 4)
            _totaltax = round(_subtotal * cart_product["tax"], 4)

            item = Item(
                ProductCode=cart_product["tax_id"],  # type: ignore
                Description=cart_product["description"],  # type: ignore
                UnitCode=cart_product["tax_unit"],  # type: ignore
                Subtotal=_subtotal,
                Quantity=_quantity,
                TaxObject="02",
                Total=round(_subtotal * (1 + cart_product["tax"]), 4),  # type: ignore
                Taxes=[
                    SatTaxes(
                        Total=_totaltax,
                        Name="IVA",
                        Base=_subtotal,
                        Rate=cart_product["tax"],  # type: ignore
                        IsRetention=False,
                    )
                ],
                UnitPrice=_unitprice,
            )
            item_list.append(item)
        sorted_item_list = sorted(item_list, key=lambda item: item.Description)
        if isinstance(ordens_ship_cost, float) and ordens_ship_cost > 0:
            _subtotal = round(ordens_ship_cost / (1.16), 4)
            _unitprice = _subtotal
            _totaltax = round(_subtotal * 0.16, 4)
            sorted_item_list.append(
                Item(
                    ProductCode="78102205",
                    Description="Cargo por envío(s)",
                    UnitCode="E48",
                    Subtotal=_subtotal,
                    Quantity=1,
                    TaxObject="02",
                    Total=round(_subtotal * (1.16), 4),
                    Taxes=[
                        SatTaxes(
                            Total=_totaltax,
                            Name="IVA",
                            Base=_subtotal,
                            Rate=0.16,
                            IsRetention=False,
                        )
                    ],
                    UnitPrice=_unitprice,
                )
            )

        return sorted_item_list
    except Exception as e:
        logger.error(e)
        raise GQLApiException(
            msg="Error to build sat items",
            error_code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
        )
