import base64
from datetime import date, datetime
from io import BytesIO, StringIO
import json
from typing import List, Optional
from uuid import UUID
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

import pandas as pd
import strawberry
from strawberry.types import Info as StrawberryInfo
from strawberry.file_uploads import Upload

from gqlapi.lib.clients.clients.facturamaapi.facturama import PaymentForm
from gqlapi.domain.models.v2.utils import CFDIType, InvoiceType, RegimenSat
from gqlapi.domain.interfaces.v2.orden.invoice import (
    CustomerMxInvoiceResult,
    ExportMxInvoiceGQL,
    ExportMxInvoiceResult,
    MxInvoiceError,
    MxInvoiceResult,
    MxInvoiceStatusResult,
    MxSatCertificateError,
    MxUploadInvoiceCheckResult,
    MxUploadInvoiceResult,
    MxUpsertCustomerSatCertificateResult,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.invoice import MxInvoiceHandler, MxSatCertificateHandler
from gqlapi.handlers.supplier.supplier_user import SupplierUserPermissionHandler
from gqlapi.repository.core.cart import CartProductRepository
from gqlapi.repository.core.invoice import (
    MxInvoiceComplementRepository,
    MxInvoiceRepository,
    MxSatCertificateRepository,
)
from gqlapi.repository.core.orden import OrdenDetailsRepository, OrdenRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import (
    CoreUserRepository,
)
from gqlapi.utils.helpers import serialize_encoded_file
from gqlapi.app.permissions import (
    IsAlimaRestaurantAuthorized,
    IsAuthenticated,
    IsAlimaSupplyAuthorized,
)

# logger
logger = get_logger(get_app())


@strawberry.type
class MxInvoiceMutation:
    @strawberry.mutation(name="uploadInvoice", permission_classes=[])
    async def upload_invoice(
        self, info: StrawberryInfo, pdf_file: Upload, xml_file: Upload, orden_id: UUID
    ) -> MxUploadInvoiceResult:  # type: ignore
        """Uploads an invoice to the MX Invoice DB

        Parameters
        ----------
        info : StrawberryInfo
        pdf_file : Upload
        xml_file : Upload
        orden_id : UUID

        Returns
        -------
        MxUploadInvoiceResult
            MxUploadInvoice: success=True
            MxInvoiceError: success=False
        """
        # validate pdf_file and xml_file
        if xml_file.filename.split(".")[-1] != "xml" or pdf_file.filename.split(".")[-1] != "pdf":  # type: ignore
            return MxInvoiceError(
                msg="Invalid XML and/or PDF file",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        try:
            # read files
            xml_data = await xml_file.read()  # type: ignore
            pdf_data = await pdf_file.read()  # type: ignore
        except Exception as e:
            logger.error(f"Error reading files: {e}")
            return MxInvoiceError(
                msg="Error reading files",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
        )
        try:
            # call handler to upload invoice
            res_inv = await _handler.upload_invoice(
                pdf_file=pdf_data,
                xml_file=xml_data,
                orden_id=orden_id,
            )
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return MxInvoiceError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxInvoiceError(
                msg="Error uploading invoice",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="upsertSupplierCsd",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def upsert_customers_sat_certificate(
        self,
        info: StrawberryInfo,
        rfc: str,
        legal_name: str,
        zip_code: str,
        cer_file: Upload,
        key_file: Upload,
        sat_regime: RegimenSat,
        sat_pass_code: str,
        invoicing_type: str,
        invoice_type: str,
        supplier_unit_id: UUID,
    ) -> MxUpsertCustomerSatCertificateResult:  # type: ignore
        logger.info("Create new customer sat certificate")
        # validate pdf_file and xml_file
        if cer_file.filename.split(".")[-1] != "cer" or key_file.filename.split(".")[-1] != "key":  # type: ignore
            return MxSatCertificateError(
                msg="Invalid cer and/or key file",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        try:
            # read files
            cer_data = await serialize_encoded_file(cer_file)  # type: ignore
            key_data = await serialize_encoded_file(key_file)  # type: ignore
        except Exception as e:
            logger.error(f"Error reading files: {e}")
            return MxSatCertificateError(
                msg="Error reading files",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler MxInvoice
        _handler = MxSatCertificateHandler(
            mx_sat_certificate_repository=MxSatCertificateRepository(info),
        )
        try:
            # call handler to upload invoice
            res_cert = await _handler.upsert_customer_certificate(
                legal_name=legal_name,
                zip_code=zip_code,
                sat_regime=sat_regime,
                cer_file=cer_data,
                key_file=key_data,
                rfc=rfc,
                sat_pass_code=sat_pass_code,
                invoicing_type=invoicing_type,
                invoice_type=invoice_type,
                supplier_unit_id=supplier_unit_id,
            )
            return res_cert
        except GQLApiException as ge:
            logger.warning(ge)
            return MxSatCertificateError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxSatCertificateError(
                msg="Error creating/updating customer sat certificate",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="newCustomerInvoice",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_customer_invoice(
        self,
        info: StrawberryInfo,
        orden_details_id: UUID,
        payment_form: PaymentForm,
        expedition_place: str,
        issue_date: datetime,
        payment_method: InvoiceType,
    ) -> CustomerMxInvoiceResult:  # type: ignore
        fb_id = info.context["request"].user.firebase_user.firebase_id

        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        try:
            # call handler to upload invoice
            res_inv = await _handler.new_customer_invoice(
                orden_details_id=orden_details_id,
                cfdi_type=CFDIType.INGRESO.value,
                payment_form=payment_form.value,
                expedition_place=expedition_place,
                issue_date=issue_date,
                payment_method=payment_method.value,
                firebase_id=fb_id,
            )
            # return res_cert
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return MxInvoiceError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxInvoiceError(
                msg="Error creating new customer invoice",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="cancelCustomerInvoice",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def cancel_customer_invoice(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
        motive: Optional[str] = None,
        uuid_replacement: Optional[UUID] = None,
    ) -> MxInvoiceStatusResult:  # type: ignore
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
        )
        try:
            if not motive:
                motive = "02"
            # call handler to upload invoice
            res_inv = await _handler.cancel_customer_invoice(
                orden_id=orden_id,
                motive=motive,
                uuid_replacement=str(uuid_replacement),
            )
            # return res_cert
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return MxInvoiceError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxInvoiceError(
                msg="Error creating new customer invoice",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    # @strawberry.mutation(
    #     name="newCustomerInvoiceComplement",
    #     permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    # )
    # async def post_new_customer_invoice_complement(
    #     self,
    #     info: StrawberryInfo,
    #     orden_details_id: UUID,
    #     amount: float,
    #     payment_form: str,
    #     payment_method: str,
    # ) -> CustomerMxInvoiceResult:  # type: ignore
    #     fb_id = info.context["request"].user.firebase_user.firebase_id

    #     # instantiate handler MxInvoice
    #     _handler = MxInvoiceHandler(
    #         mx_invoice_repository=MxInvoiceRepository(info),
    #         orden_details_repo=OrdenDetailsRepository(info),
    #         core_user_repo=CoreUserRepository(info),
    #         supplier_unit_repo=SupplierUnitRepository(info),
    #         restaurant_branch_repo=RestaurantBranchRepository(info),
    #         supplier_business_repo=SupplierBusinessRepository(info),
    #         orden_repo=OrdenRepository(info),
    #         cart_product_repo=CartProductRepository(info),
    #         supp_prod_repo=SupplierProductRepository(info),
    #         mx_sat_cer_repo=MxSatCertificateRepository(info),
    #         mx_invoice_complement_repository=MxInvoiceComplementRepository(info)
    #     )
    #     try:
    #         # [TODO] @Ferreyes - verify and change to make it work
    #         # call handler to upload invoice
    #         res_inv = await _handler.new_customer_invoice_complement(
    #             orden_details_id,
    #             amount,
    #             payment_form,
    #             payment_method,
    #             fb_id
    #         )
    #         # return res_cert
    #         return res_inv
    #     except GQLApiException as ge:
    #         logger.warning(ge)
    #         return MxInvoiceError(
    #             msg=ge.msg,
    #             code=int(ge.error_code),
    #         )
    #     except Exception as e:
    #         logger.error(e)
    #         return MxInvoiceError(
    #             msg="Error creating new customer invoice",
    #             code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
    #         )


@strawberry.type
class MxInvoiceQuery:
    @strawberry.field(
        name="getInvoiceDetails",
        permission_classes=[IsAuthenticated],
    )
    async def get_invoice(self, info: StrawberryInfo, orden_id: UUID) -> MxInvoiceResult:  # type: ignore
        """Endpoint to retrieve invoice details from MX Invoice
            associated to a given orden_id

        Parameters
        ----------
        info : StrawberryInfo
        orden_id: UUID
            Orden Id

        Returns
        -------
        MxInvoiceResult
        """
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
        )
        try:
            # [TODO] - validate user has access to this orden
            # fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to upload invoice
            res_inv = await _handler.get_invoice(orden_id)
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return MxInvoiceError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxInvoiceError(
                msg="Error retrieving invoice",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(name="getInvoiceExternalDetails", permission_classes=[])
    async def get_invoice_external(self, info: StrawberryInfo, orden_id: UUID) -> MxUploadInvoiceCheckResult:  # type: ignore
        """Endpoint to retrive invoice details from MX Invoice
            from a external (not authenticated location) it
             returns both orden details and invoice details if Found

        Parameters
        ----------
        info : StrawberryInfo
        orden_id : UUID
            Orden Id

        Returns
        -------
        MxUploadInvoiceResult
        """
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
        )
        try:
            # call handler to upload invoice
            res_inv = await _handler.get_invoice_external(orden_id)
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return MxInvoiceError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxInvoiceError(
                msg="Error retrieving invoice",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="getInvoices",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_invoices(self, info: StrawberryInfo, orden_ids: List[UUID]) -> List[MxInvoiceResult]:  # type: ignore
        """Endpoint to retrieve invoice details from MX Invoice
            associated to a given orden_id

        Parameters
        ----------
        info : StrawberryInfo
        orden_ids: List[UUID]
            Orden Ids

        Returns
        -------
        MxInvoiceResult
        """
        logger.info("Get invoices by ids")
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
        )
        try:
            # [TODO] - validate user has access to this orden
            # fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get invoices
            res_inv = await _handler.fetch_invoices(orden_ids)
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return [
                MxInvoiceError(
                    msg=ge.msg,
                    code=int(ge.error_code),
                )
            ]
        except Exception as e:
            logger.error(e)
            return [
                MxInvoiceError(
                    msg="Error retrieving invoices",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getCsd",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_customer_sat_certificate(
        self, info: StrawberryInfo, rfc: str
    ) -> MxUpsertCustomerSatCertificateResult:  # type: ignore
        # fb_id = info.context["request"].user.firebase_user.firebase_id
        _supp_user_permi_handler = SupplierUserPermissionHandler(
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_perm_repo=SupplierUserPermissionRepository(info),
        )
        fb_id = info.context["request"].user.firebase_user.firebase_id
        # fb_id = os.getenv("MYFB_ID")

        _handler = MxSatCertificateHandler(
            mx_sat_certificate_repository=MxSatCertificateRepository(info),
        )
        try:
            supp_user_perm = (
                await _supp_user_permi_handler.fetch_supplier_user_permission(
                    firebase_id=fb_id
                )
            )
            # call handler to upload invoice
            res_cert = await _handler.get_customer_certificate(
                supplier_business_id=supp_user_perm.supplier_business_id, rfc=rfc  # type: ignore
            )
            return res_cert
        except GQLApiException as ge:
            logger.warning(ge)
            return MxSatCertificateError(
                msg=ge.msg,
                code=int(ge.error_code),
            )

    @strawberry.field(
        name="getInvoiceDetailsByOrden",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_orden_customer_invoice(
        self, info: StrawberryInfo, orden_id: UUID
    ) -> List[CustomerMxInvoiceResult]:  # type: ignore
        """Endpoint to retrieve invoice details from MX Invoice
            associated to a given orden_id

        Parameters
        ----------
        info : StrawberryInfo
        orden_id: UUID
            Orden Id

        Returns
        -------
        MxInvoiceResult
        """
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            orden_repo=OrdenRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        try:
            # [TODO] - validate user has access to this orden
            # fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to upload invoice
            res_inv = await _handler.get_customer_invoices_by_orden(orden_id)
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return [
                MxInvoiceError(
                    msg=ge.msg,
                    code=int(ge.error_code),
                )
            ]

    @strawberry.field(
        name="getInvoiceDetailsByOrdenSupply",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_orden_customer_invoice_supply(
        self, info: StrawberryInfo, orden_id: UUID
    ) -> List[MxInvoiceResult]:  # type: ignore
        """Endpoint to retrieve invoice details from MX Invoice
            associated to a given orden_id

        Parameters
        ----------
        info : StrawberryInfo
        orden_id: UUID
            Orden Id

        Returns
        -------
        MxInvoiceResult
        """
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            orden_repo=OrdenRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        try:
            # [TODO] - validate user has access to this orden
            # fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to upload invoice
            res_inv = await _handler.get_customer_invoices_by_orden_supply(orden_id)
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return [
                MxInvoiceError(
                    msg=ge.msg,
                    code=int(ge.error_code),
                )
            ]

    @strawberry.field(
        name="getInvoiceDetailsByDates",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_customer_invoices_by_dates(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        receiver: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[MxInvoiceResult]:  # type: ignore
        """Endpoint to retrieve list of invoices from MX Invoice
            based on filtered dates and client (invoice receiver)

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_id: UUID
            Supplier Unit Id
        from_date: Optional[date]
            From Date
        until_date: Optional[date]
            Until Date
        receiver: Optional[str]
            Client name (restaurant busines name or branch name)
        page: Optional[int]
            Page number
        page_size: Optional[int]
            Page size

        Returns
        -------
        List[MxInvoiceResult]
        """
        logger.info("Get invoices list by filters")
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_perms_repo=SupplierUserPermissionRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get invoices
            res_inv = await _handler.get_customer_invoices_by_dates(
                firebase_id=fb_id,
                supplier_unit_id=supplier_unit_id,
                from_date=from_date,
                until_date=until_date,
                receiver=receiver,
                page=page,
                page_size=page_size,
            )
            return res_inv
        except GQLApiException as ge:
            logger.warning(ge)
            return [
                MxInvoiceError(
                    msg=ge.msg,
                    code=int(ge.error_code),
                )
            ]
        except Exception as e:
            logger.error(e)
            return [
                MxInvoiceError(
                    msg="Error retrieving invoices",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="exportInvoiceDetailsByDates",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def export_customer_invoices_by_dates(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        export_format: str,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        receiver: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> ExportMxInvoiceResult:  # type: ignore
        """Endpoint to retrieve list of invoices from MX Invoice
            based on filtered dates and client (invoice receiver)

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_id: UUID
            Supplier Unit Id
        export_format: str
            Export format (csv or xlsx)
        from_date: Optional[date]
            From Date
        until_date: Optional[date]
            Until Date
        receiver: Optional[str]
            Client name (restaurant busines name or branch name)
        page: Optional[int]
            Page number
        page_size: Optional[int]
            Page size

        Returns
        -------
        List[MxInvoiceResult]
        """
        logger.info("Export invoices list by filters")
        # validate format
        if export_format.lower() not in ["csv", "xlsx"]:
            return MxInvoiceError(
                msg="Invalid format",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler MxInvoice
        _handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_perms_repo=SupplierUserPermissionRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get invoices
            res_inv = await _handler.get_customer_invoices_by_dates(
                firebase_id=fb_id,
                supplier_unit_id=supplier_unit_id,
                from_date=from_date,
                until_date=until_date,
                receiver=receiver,
                page=page,
                page_size=page_size,
            )
            res_table = await _handler.format_invoices_to_export(res_inv)
            _df = pd.DataFrame(res_table)[
                [
                    "sat_invoice_uuid",
                    "invoice_number",
                    "status",
                    "Proveedor",
                    "Cliente",
                    "total",
                    "created_at",
                    "created_at_time",
                    "orden_ids",
                ]
            ].rename(
                columns={
                    "sat_invoice_uuid": "UUID Factura",
                    "invoice_number": "Folio Factura",
                    "status": "Estátus Factura",
                    "created_at": "Fecha de Emisión",
                    "created_at_time": "Hora de Emisión",
                    "total": "Valor Factura",
                    "orden_ids": "Pedidos Asociados",
                }
            )
            _df.sort_values(by="Fecha de Emisión", ascending=True, inplace=True)
            _df.reset_index(inplace=True, drop=True)

            # export
            if export_format == "csv":
                in_memory_csv = StringIO()
                _df.to_csv(in_memory_csv, index=False)
                in_memory_csv.seek(0)
                return ExportMxInvoiceGQL(
                    file=json.dumps(
                        {
                            "filename": f"reporte_facturas_{datetime.utcnow().date().isoformat()}.csv",
                            "mimetype": "text/csv",
                            "content": base64.b64encode(
                                in_memory_csv.read().encode("utf-8")
                            ).decode(),
                        }
                    ),
                    extension="csv",
                )
            elif export_format == "xlsx":
                in_memory_xlsx = BytesIO()
                _df.to_excel(in_memory_xlsx, index=False)
                in_memory_xlsx.seek(0)
                return ExportMxInvoiceGQL(
                    file=json.dumps(
                        {
                            "filename": f"reporte_facturas_{datetime.utcnow().date().isoformat()}.xlsx",
                            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "content": base64.b64encode(in_memory_xlsx.read()).decode(),
                        }
                    ),
                    extension="xlsx",
                )
        except GQLApiException as ge:
            logger.warning(ge)
            return MxInvoiceError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return MxInvoiceError(
                msg="Error retrieving invoices",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
