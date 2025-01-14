from datetime import datetime, timedelta
import json
import logging
from typing import List, Optional
from uuid import UUID, uuid4
from gqlapi.lib.clients.clients.facturamaapi.facturama import PaymentForm
from gqlapi.domain.interfaces.v2.orden.invoice import (
    CustomerMxInvoiceGQL,
    MxInvoiceHandlerInterface,
    MxInvoicingExecutionRepositoryInterface,
    MxSatCertificateRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL, OrdenHandlerInterface
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchGQL,
    RestaurantBranchInvoicingOptionsRepositoryInterface,
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import (
    INVOICE_PAYMENT_MAP,
    SupplierInvoiceHandlerInterface,
    SupplierInvoiceHookListenerInterface,
    SupplierInvoiceTriggerInfo,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    SupplierRestaurantsRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import (
    SupplierUnitDeliveryRepositoryInterface,
    SupplierUnitGQL,
    SupplierUnitRepositoryInterface,
)
from gqlapi.domain.models.v2.core import MxInvoicingExecution, MxSatInvoicingCertificateInfo
from gqlapi.domain.models.v2.restaurant import RestaurantBranchMxInvoiceInfo
from gqlapi.domain.models.v2.supplier import SupplierUnitDeliveryOptions
from gqlapi.domain.models.v2.utils import (
    CFDIType,
    ExecutionStatusType,
    InvoiceTriggerTime,
    InvoiceType,
    OrdenStatusType,
    PayMethodType,
    SellingOption,
    ServiceDay,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


class SupplierInvoiceHandler(SupplierInvoiceHandlerInterface):
    def __init__(
        self,
        orden_handler: OrdenHandlerInterface,
        mx_invoice_handler: MxInvoiceHandlerInterface,
        restaurant_branch_repo: RestaurantBranchRepositoryInterface,
        supplier_unit_repo: SupplierUnitRepositoryInterface,
        supplier_unit_delivery_repo: SupplierUnitDeliveryRepositoryInterface,
        mx_sat_cer_repo: MxSatCertificateRepositoryInterface,
        mx_invoicing_exec_repo: MxInvoicingExecutionRepositoryInterface,
        supplier_restaurant_relation_mx_invoice_options_repo: Optional[
            RestaurantBranchInvoicingOptionsRepositoryInterface
        ] = None,
        supplier_restaurants_repo: Optional[
            SupplierRestaurantsRepositoryInterface
        ] = None,
    ):
        self.orden_handler = orden_handler
        self.mx_invoice_handler = mx_invoice_handler
        self.restaurant_branch_repo = restaurant_branch_repo
        self.supplier_unit_repo = supplier_unit_repo
        self.supplier_unit_delivery_repo = supplier_unit_delivery_repo
        self.mx_sat_cer_repo = mx_sat_cer_repo
        self.mx_invoicing_exec_repo = mx_invoicing_exec_repo
        if supplier_restaurant_relation_mx_invoice_options_repo:
            self.supplier_restaurant_relation_mx_invoice_options_repo = (
                supplier_restaurant_relation_mx_invoice_options_repo
            )
        if supplier_restaurants_repo:
            self.supplier_restaurants_repo = supplier_restaurants_repo

    async def fetch_orden_details(self, orden_id: UUID) -> OrdenGQL:
        # search orden info
        _ords = await self.orden_handler.search_orden(orden_id=orden_id)
        if not _ords or not isinstance(_ords[0], OrdenGQL):
            raise GQLApiException(
                msg="Error getting Orden details",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_MATCH.value,
            )
        # fetch most recent orden details
        ord_detail = sorted(
            _ords, key=lambda k: k.details.version if k.details else 1, reverse=True
        )[0]
        if not ord_detail or not ord_detail.details or not ord_detail.supplier:
            raise GQLApiException(
                msg="Error getting Orden details",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_MATCH.value,
            )
        if not ord_detail.branch or not ord_detail.branch.tax_info:
            # get branch
            branch = await self.restaurant_branch_repo.fetch(
                ord_detail.details.restaurant_branch_id
            )
            branch_tax = await self.restaurant_branch_repo.fetch_tax_info(
                ord_detail.details.restaurant_branch_id
            )

            # fetch supplier restaurant relation
            sr_rel = await self.supplier_restaurants_repo.raw_query(
                """SELECT * FROM supplier_restaurant_relation
                    WHERE supplier_unit_id = :supplier_unit_id
                    AND restaurant_branch_id = :restaurant_branch_id
                """,
                {
                    "supplier_unit_id": ord_detail.supplier.supplier_unit.id,  # type: ignore
                    "restaurant_branch_id": ord_detail.details.restaurant_branch_id,
                },
            )
            if not sr_rel:
                raise GQLApiException(
                    msg="Supplier Restaurant Relation not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            io_info = (
                await self.supplier_restaurant_relation_mx_invoice_options_repo.fetch(
                    sr_rel[0]["id"]
                )
            )
            if not branch:
                raise GQLApiException(
                    msg="Error getting Restaurant Branch details",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if not branch_tax or not branch_tax.get("mx_sat_id"):
                raise GQLApiException(
                    msg="Cannot generate invoice: No Restaurant Branch tax available",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            ord_detail.branch = RestaurantBranchGQL(
                **branch,
                tax_info=RestaurantBranchMxInvoiceInfo(**branch_tax),
                invoice_options=io_info,
            )
        if (
            not ord_detail.supplier
            or not ord_detail.supplier.supplier_unit
            or not ord_detail.supplier.supplier_unit.tax_info
        ):
            # get unit
            sunit = await self.supplier_unit_repo.fetch(
                ord_detail.details.supplier_unit_id
            )
            sunit_deliv_dict = await self.supplier_unit_delivery_repo.fetch(
                UUID(str(ord_detail.details.supplier_unit_id))
            )
            sunit_tax = await self.mx_sat_cer_repo.fetch_certificate(
                UUID(str(ord_detail.details.supplier_unit_id))
            )
            if not sunit or not sunit_deliv_dict:
                raise GQLApiException(
                    msg="Error getting Supplier Unit details",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if not sunit_tax:
                raise GQLApiException(
                    msg="Cannot generate invoice: No Supplier Unit Tax details",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            sunit_deliv = SupplierUnitDeliveryOptions(
                supplier_unit_id=sunit_deliv_dict["supplier_unit_id"],
                selling_option=[
                    SellingOption(so) for so in sunit_deliv_dict["selling_option"]
                ],
                service_hours=[
                    ServiceDay(**_servd) for _servd in sunit_deliv_dict["service_hours"]
                ],
                regions=[str(r).upper() for r in sunit_deliv_dict["regions"]],
                delivery_time_window=sunit_deliv_dict["delivery_time_window"],
                warning_time=sunit_deliv_dict["warning_time"],
                cutoff_time=sunit_deliv_dict["cutoff_time"],
            )
            ord_detail.supplier.supplier_unit = SupplierUnitGQL(
                **sunit,
                delivery_info=sunit_deliv,
                tax_info=MxSatInvoicingCertificateInfo(**sunit_tax),
            )
        return ord_detail

    async def trigger_supplier_invoice(
        self, firebase_id: str, orden: OrdenGQL
    ) -> SupplierInvoiceTriggerInfo:
        # data validation
        if (
            orden.details is None
            or not orden.details.id
            or not orden.details.payment_method
            or orden.branch is None
            or orden.branch.tax_info is None
            or not orden.branch.tax_info.mx_sat_id
            or orden.supplier is None
            or orden.supplier.supplier_unit is None
            or orden.supplier.supplier_unit.tax_info is None
            or not orden.supplier.supplier_unit.tax_info.zip_code
            or not orden.supplier.supplier_unit.tax_info.invoicing_options.invoice_type
        ):
            raise GQLApiException(
                msg="Cannot generate Invoice: Missing Orden details data",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create execution record
        mxinv_exec = MxInvoicingExecution(
            id=uuid4(),
            orden_details_id=orden.details.id,
            execution_start=datetime.utcnow(),
            status=ExecutionStatusType.RUNNING,
            result="{}",
        )
        exec_res = await self.mx_invoicing_exec_repo.fetch(mxinv_exec.orden_details_id)
        if not exec_res:
            # if it doesnt exist - create one
            i_exec_id = await self.mx_invoicing_exec_repo.add(mxinv_exec)
        else:
            # if it does - update it
            mxinv_exec.id = exec_res["id"]
            i_exec_id = await self.mx_invoicing_exec_repo.edit(mxinv_exec)
        if not i_exec_id:
            raise GQLApiException(
                msg="Error creating Invoice Execution record",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # set default failed unless success
        mxinv_exec.status = ExecutionStatusType.FAILED
        # create mx invoice
        logging.debug(f"Creating Mx Invoice for {orden.id}...")
        res_inv = None
        try:
            if orden.branch and orden.branch.invoice_options:
                payment_method = orden.branch.invoice_options.invoice_type
            else:
                payment_method = (
                    orden.supplier.supplier_unit.tax_info.invoicing_options.invoice_type
                )
            p_form = (
                INVOICE_PAYMENT_MAP[orden.details.payment_method].value
                if payment_method == InvoiceType.PUE
                else PaymentForm.TBD.value  # PPD
            )
            res_inv = await self.mx_invoice_handler.new_customer_invoice(
                orden_details_id=orden.details.id,
                cfdi_type=CFDIType.INGRESO.value,
                payment_form=p_form,
                expedition_place=orden.supplier.supplier_unit.tax_info.zip_code,
                issue_date=datetime.utcnow() - timedelta(hours=6),
                payment_method=payment_method.value,  # type: ignore (safe)
                firebase_id=firebase_id,
            )
            mxinv_exec.status = ExecutionStatusType.SUCCESS
        except GQLApiException as ge:
            # update execution record
            if ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value:
                mxinv_exec.result = json.dumps({"status": "warning", "warning": ge.msg})
            elif ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
                mxinv_exec.result = json.dumps({"status": "warning", "warning": ge.msg})
            elif ge.error_code == GQLApiErrorCodeType.EMPTY_DATA.value:
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": "No hay productos en la orden de venta a facturar.",
                    }
                )
            elif ge.error_code == GQLApiErrorCodeType.FACTURAMA_WRONG_INVOICE_TAX.value:
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": f"Hay un producto con el porcentaje de IVA incorrecto ({ge.msg}).",
                    }
                )
            elif (
                ge.error_code == GQLApiErrorCodeType.FACTURAMA_NO_TAX_INVOICE_DATA.value
            ):
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": "No hay IVA calculado en la orden de venta que se desea facturar.",
                    }
                )
            elif (
                ge.error_code
                == GQLApiErrorCodeType.FACTURAMA_TAX_NO_MATCH_WITH_ORDEN.value
            ):
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": "El IVA de la orden de venta no coincide con la factura a generar, favor de verificarlo.",
                    }
                )
            elif ge.error_code == GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value:
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": """El proveedor no tiene dado de alta el CSD,
                                    o los datos de facturación del proveedor son incorrectos.""",
                    }
                )
            elif (
                ge.error_code == GQLApiErrorCodeType.FACTURAMA_NEW_CUSTOMER_ERROR.value
            ):
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": f"La información de facturación del cliente no es correcta: {ge.msg}.",
                    }
                )
            elif ge.error_code == GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value:
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": f"Error al generar la factura en SAT: {ge.msg}.",
                    }
                )
            else:
                mxinv_exec.result = json.dumps(
                    {
                        "status": "error",
                        "error": f"Hubo un error creando la factura: {ge.msg}. Favor de contactar a soporte.",
                    }
                )
            # update execution record
            mxinv_exec.status = ExecutionStatusType.FAILED
            mxinv_exec.execution_end = datetime.utcnow()
        except Exception as e:
            mxinv_exec.result = json.dumps(
                {
                    "status": "error",
                    "error": f"Hubo un error creando la factura: {e}. Favor de contactar a soporte.",
                }
            )
            # update execution record
            mxinv_exec.status = ExecutionStatusType.FAILED
            mxinv_exec.execution_end = datetime.utcnow()
        if mxinv_exec.status == ExecutionStatusType.SUCCESS and res_inv is not None:
            # update for success
            mxinv_exec.result = json.dumps(
                {"status": "success", "sat_id": str(res_inv.sat_id)}
            )
            mxinv_exec.execution_end = datetime.utcnow()
        # run execution
        if not await self.mx_invoicing_exec_repo.edit(mxinv_exec):
            logging.error(f"Issues creating Mx Invoice: {mxinv_exec.result}")
            raise GQLApiException(
                msg="Error to update mx_invoice execution",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        # return result
        return SupplierInvoiceTriggerInfo(
            **mxinv_exec.__dict__,
            customer_invoice=res_inv,
        )

    async def trigger_supplier_consolidated_invoice(
        self,
        firebase_id: str,
        ordenes: List[OrdenGQL],
        payment_method: PayMethodType,
        public_general_invoice_flag: bool,
    ) -> List[CustomerMxInvoiceGQL]:
        # data validation
        if ordenes is None or len(ordenes) == 0 or not payment_method:
            raise GQLApiException(
                msg="Cannot generate Invoice: Missing Orden details data",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        orden_reference = self.get_reference_orden(ordenes)
        logging.debug(f"Creating Consolidated Mx Invoice {orden_reference.details.supplier_unit_id}...")  # type: ignore (safe)
        try:
            return await self.mx_invoice_handler.new_consolidated_customer_invoice(
                ordenes=ordenes,
                payment_method=payment_method,  # type: ignore (safe)
                firebase_id=firebase_id,
                public_general_invoice_flag=public_general_invoice_flag,
            )
            # mxinv_exec.status = ExecutionStatusType.SUCCESS
        except GQLApiException as ge:
            raise GQLApiException(
                msg=ge.msg,
                error_code=ge.error_code,
            )

    async def fetch_supplier_invoice_exec_status(
        self, orden_id: UUID
    ) -> SupplierInvoiceTriggerInfo:
        # fetch orden details
        ord_details = await self.fetch_orden_details(orden_id=orden_id)
        if not ord_details or not ord_details.details:
            raise GQLApiException(
                msg="Error fetching Orden details",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # first fetch execution status
        i_exec_id = await self.mx_invoicing_exec_repo.fetch(
            orden_details_id=ord_details.details.id
        )
        if not i_exec_id:
            raise GQLApiException(
                msg="Error fetching Invoice Execution record",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        return SupplierInvoiceTriggerInfo(
            **i_exec_id,
        )

    def get_reference_orden(self, orden: list[OrdenGQL]) -> OrdenGQL:
        return orden[0]


class SupplierInvoiceHookListener(SupplierInvoiceHookListenerInterface):
    @staticmethod
    async def on_orden_status_changed(
        supplier_handler: SupplierInvoiceHandlerInterface,
        firebase_id: str,
        orden_id: UUID,
        status: OrdenStatusType,
    ) -> bool:
        logging.info(f"On_orden_status_changed: {orden_id} - {status}")
        try:
            # fetch orden details
            ord_details = await supplier_handler.fetch_orden_details(orden_id=orden_id)
            _sup = ord_details.supplier
            _rest_inv_opt = None
            if ord_details.branch:
                _rest_inv_opt = ord_details.branch.invoice_options
            if (
                not (_sup)
                or not (_sup.supplier_unit)
                or not (_sup.supplier_unit.tax_info)
            ):
                logging.warning(
                    "Cannot generate Invoice: Missing Supplier Invoicing data"
                )
                return False
            # verify invoicing rules for the supplier unit
            result = None
            if not _rest_inv_opt:
                if not (_sup.supplier_unit.tax_info.invoicing_options):
                    logging.warning(
                        "Cannot generate Invoice: Missing Supplier Invoicing options data"
                    )
                    return False
                _inv_opt = _sup.supplier_unit.tax_info.invoicing_options
                if _inv_opt.automated_invoicing:
                    # - on accepted status
                    if (
                        status == OrdenStatusType.ACCEPTED
                        and _inv_opt.triggered_at == InvoiceTriggerTime.AT_PURCHASE
                    ):
                        # call invoice execution
                        result = await supplier_handler.trigger_supplier_invoice(
                            firebase_id=firebase_id,
                            orden=ord_details,
                        )
                        logging.info(f"Result: {result.status}")
                        return (
                            result.status == ExecutionStatusType.SUCCESS
                            if result
                            else False
                        )
                    # - on delivered status
                    elif (
                        status == OrdenStatusType.DELIVERED
                        and _inv_opt.triggered_at == InvoiceTriggerTime.AT_DELIVERY
                    ):
                        # call invoice execution
                        result = await supplier_handler.trigger_supplier_invoice(
                            firebase_id=firebase_id,
                            orden=ord_details,
                        )
                        logging.info(f"Result: {result.status}")
                        return (
                            result.status == ExecutionStatusType.SUCCESS
                            if result
                            else False
                        )
                    else:
                        logging.info("Nothing to execute for this status change.")
                        return False
                else:
                    logging.info("Nothing to execute for this status change.")
                    return False
            else:
                if _rest_inv_opt.automated_invoicing:
                    # - on accepted status
                    if (
                        status == OrdenStatusType.ACCEPTED
                        and _rest_inv_opt.triggered_at == InvoiceTriggerTime.AT_PURCHASE
                    ):
                        # call invoice execution
                        result = await supplier_handler.trigger_supplier_invoice(
                            firebase_id=firebase_id,
                            orden=ord_details,
                        )
                        logging.info(f"Result: {result.status}")
                        return (
                            result.status == ExecutionStatusType.SUCCESS
                            if result
                            else False
                        )
                    # - on delivered status
                    elif (
                        status == OrdenStatusType.DELIVERED
                        and _rest_inv_opt.triggered_at == InvoiceTriggerTime.AT_DELIVERY
                    ):
                        # call invoice execution
                        result = await supplier_handler.trigger_supplier_invoice(
                            firebase_id=firebase_id,
                            orden=ord_details,
                        )
                        logging.info(f"Result: {result.status}")
                        return (
                            result.status == ExecutionStatusType.SUCCESS
                            if result
                            else False
                        )
                    else:
                        logging.info("Nothing to execute for this status change.")
                        return False

                else:
                    logging.info("Nothing to execute for this status change.")
                    return False
        except Exception as e:
            logging.error(f"Error on_orden_status_changed: {e}")
            return False
