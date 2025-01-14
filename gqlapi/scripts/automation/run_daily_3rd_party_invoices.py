""" Script to create all Customer invoices needed on behalf of Supplier Businesses.

This script does the following:

1. Fetches all Supplier Units with active invoicing rules
2. For each Supplier Unit:
    1. Fetch all ordenes from the past 24hrs that have not been invoiced / failed invoicing
    2. For each Orden:
        1. Fetches the Restaurant Branch information from Orden UUID
        1.1. Retrieves RFC
        1.2. Retrieves Invoice Type
        2. Fetches the Supplier Business information from Orden UUID
            2.1. Retrieves Expedition Place
        3. Creates a new Customer Invoice
        4. Save into the Invoicing Execution table the result of the Invoice creation

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.automation.run_daily_3rd_party_invoices --help
"""
import asyncio
import argparse
from datetime import datetime, timedelta
import json
import logging
from typing import List
import uuid
from bson import Binary

from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import RestaurantBranchGQL
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import INVOICE_PAYMENT_MAP
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitGQL
from gqlapi.domain.models.v2.core import (
    CoreUser,
    MxInvoicingExecution,
    MxSatInvoicingCertificateInfo,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBranchMxInvoiceInfo
from gqlapi.domain.models.v2.supplier import (
    InvoicingOptions,
    SupplierUnitDeliveryOptions,
)
from gqlapi.domain.models.v2.utils import (
    CFDIType,
    ExecutionStatusType,
    InvoiceConsolidation,
    InvoiceTriggerTime,
    InvoiceType,
    OrdenStatusType,
    RegimenSat,
    SellingOption,
    ServiceDay,
)
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.repository.core.cart import CartProductRepository
from gqlapi.repository.core.invoice import (
    MxInvoiceRepository,
    MxInvoicingExecutionRepository,
    MxSatCertificateRepository,
)
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository

# from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.run_daily_3rd_party_invoice", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Daily Supplier 3rd party Invoices"
    )
    parser.add_argument(
        "--date",
        help="Date (YYYY-MM-DD)",
        type=str,
        default=None,
        required=True,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def fetch_orden_details(
    orden_id: uuid.UUID,
    orden_handler: OrdenHandler,
    restaurant_branch_repo: RestaurantBranchRepository,
    supplier_unit_repo: SupplierUnitRepository,
    supplier_unit_delivery_repo: SupplierUnitDeliveryRepository,
    mxcert_repo: MxSatCertificateRepository,
) -> OrdenGQL:
    _ords = await orden_handler.search_orden(orden_id=orden_id)
    if not _ords or not isinstance(_ords[0], OrdenGQL):
        raise Exception("Error getting Orden details")
    ord_detail = _ords[0]
    if not ord_detail or not ord_detail.details or not ord_detail.supplier:
        raise Exception("Error getting Orden details")
    if not ord_detail.branch:
        # get branch
        branch = await restaurant_branch_repo.fetch(
            ord_detail.details.restaurant_branch_id
        )
        branch_tax = await restaurant_branch_repo.fetch_tax_info(
            ord_detail.details.restaurant_branch_id
        )
        if not branch:
            raise Exception("Error getting Restaurant Branch details")
        if not branch_tax or not branch_tax.get("mx_sat_id"):
            raise Exception(
                "Cannot generate invoice: No Restaurant Branch tax available"
            )
        ord_detail.branch = RestaurantBranchGQL(
            **branch,
            tax_info=RestaurantBranchMxInvoiceInfo(**branch_tax),
        )
    if not ord_detail.supplier or not ord_detail.supplier.supplier_unit:
        # get unit
        sunit = await supplier_unit_repo.fetch(ord_detail.details.supplier_unit_id)
        sunit_deliv_dict = await supplier_unit_delivery_repo.fetch(
            uuid.UUID(str(ord_detail.details.supplier_unit_id))
        )
        sunit_tax = await mxcert_repo.fetch_certificate(
            uuid.UUID(str(ord_detail.details.supplier_unit_id))
        )
        if not sunit or not sunit_deliv_dict:
            raise Exception("Error getting Supplier Unit details")
        if not sunit_tax:
            raise Exception("Cannot generate invoice: No Supplier Unit Tax details")
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


async def get_active_invoicing_suppliers(
    mx_cert_repo: MxSatCertificateRepository,
) -> List[MxSatInvoicingCertificateInfo]:
    # get all suppliers with active invoicing rules
    _su_delivs = await mx_cert_repo.find(
        core_element_collection="supplier_unit_mx_invoice_info",
        core_element_name="Supplier Unit MX Invoice Info",
        core_query={},
    )
    su_delivs = []
    for _data in _su_delivs:
        _data["supplier_unit_id"] = Binary.as_uuid(_data["supplier_unit_id"])
        if _data["cer_file"]:
            _data["cer_file"] = _data["cer_file"].decode("utf-8")
        if _data["key_file"]:
            _data["key_file"] = _data["key_file"].decode("utf-8")
        _data["sat_regime"] = RegimenSat(_data["sat_regime"])
        if _data["invoicing_options"]:
            _data["invoicing_options"] = InvoicingOptions(
                automated_invoicing=_data["invoicing_options"]["automated_invoicing"],
                invoice_type=InvoiceType(_data["invoicing_options"]["invoice_type"])
                if _data["invoicing_options"]["invoice_type"]
                else None,
                triggered_at=InvoiceTriggerTime(
                    _data["invoicing_options"]["triggered_at"]
                )
                if _data["invoicing_options"]["triggered_at"]
                else None,
                consolidation=InvoiceConsolidation(
                    _data["invoicing_options"]["consolidation"]
                )
                if _data["invoicing_options"]["consolidation"]
                else None,
            )
        _mx_certs = MxSatInvoicingCertificateInfo(**_data)
        # if not automated invoicing - skip
        if not _mx_certs.invoicing_options.automated_invoicing:
            continue
        su_delivs.append(_mx_certs)
    return su_delivs


async def get_alima_bot(info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    cusr = await core_repo.fetch_by_email("admin")
    if not cusr or not cusr.id:
        raise Exception("Error getting Alima admin bot user")
    return cusr


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def run_daily_3rd_party_invoices(
    info: InjectedStrawberryInfo,
    date: str,
) -> bool:
    date_object = datetime.strptime(date, "%Y-%m-%d").date()
    # initialize repos
    core_user_repo = CoreUserRepository(info)  # type: ignore
    supplier_business_repo = SupplierBusinessRepository(info)  # type: ignore
    supplier_business_account_repo = SupplierBusinessAccountRepository(info)  # type: ignore
    supplier_unit_repo = SupplierUnitRepository(info)  # type: ignore
    supplier_unit_delivery_repo = SupplierUnitDeliveryRepository(info)  # type: ignore
    restaurant_branch_repo = RestaurantBranchRepository(info)  # type: ignore
    orden_repo = OrdenRepository(info)  # type: ignore
    orden_details_repo = OrdenDetailsRepository(info)  # type: ignore
    orden_status_repo = OrdenStatusRepository(info)  # type: ignore
    orden_payment_repo = OrdenPaymentStatusRepository(info)  # type: ignore
    cart_product_repo = CartProductRepository(info)  # type: ignore
    supp_prod_repo = SupplierProductRepository(info)  # type: ignore
    mx_sat_cer_repo = MxSatCertificateRepository(info)  # type: ignore
    mx_invoice_repository = MxInvoiceRepository(info)  # type: ignore
    mx_invoicing_exec_repo = MxInvoicingExecutionRepository(info)  # type: ignore
    # initial handler
    ord_handler = OrdenHandler(
        orden_repo=orden_repo,
        orden_det_repo=orden_details_repo,
        orden_status_repo=orden_status_repo,
        orden_payment_repo=orden_payment_repo,
        cart_prod_repo=cart_product_repo,
        supp_bus_repo=supplier_business_repo,
        supp_unit_repo=supplier_unit_repo,
        supp_bus_acc_repo=supplier_business_account_repo,
        rest_branc_repo=restaurant_branch_repo,
    )
    mxinv_handler = MxInvoiceHandler(
        mx_invoice_repository=mx_invoice_repository,
        orden_details_repo=orden_details_repo,
        core_user_repo=core_user_repo,
        supplier_unit_repo=supplier_unit_repo,
        restaurant_branch_repo=restaurant_branch_repo,
        supplier_business_repo=supplier_business_repo,
        orden_repo=orden_repo,
        cart_product_repo=cart_product_repo,
        supp_prod_repo=supp_prod_repo,
        mx_sat_cer_repo=mx_sat_cer_repo,
    )
    # get alima bot
    alima_bot = await get_alima_bot(info)
    # get all suppliers with active invoicing rules
    su_delivs = await get_active_invoicing_suppliers(mx_sat_cer_repo)
    # iterate over all suppliers
    for su in su_delivs:
        logger.info("------------------------------------------------")
        logger.info(f"Supplier Unit: {su.supplier_unit_id}")
        # fetch all ordenes from ast 24hrs and this supplier
        _ords = await ord_handler.search_orden(
            supplier_unit_id=su.supplier_unit_id,
            from_date=date_object - timedelta(days=1),
            to_date=date_object,
        )
        for j, ord in enumerate(_ords):
            logger.info(f"Orden: {j} - {ord.id}")
            # verify orden status
            if ord.status and ord.status.status:
                if (
                    ord.status.status == OrdenStatusType.ACCEPTED
                    and su.invoicing_options.triggered_at
                    == InvoiceTriggerTime.AT_PURCHASE
                ):
                    # if accepted and triggered at purchase - create invoice
                    pass
                elif (
                    ord.status.status == OrdenStatusType.DELIVERED
                    and su.invoicing_options.triggered_at
                    == InvoiceTriggerTime.AT_DELIVERY
                ):
                    # if delivered and triggered at delivery - create invoice
                    pass
                else:
                    logger.info(
                        f"Orden status is ready to create invoice: {ord.status.status}"
                    )
                    continue
            else:
                logger.info("No available Orden status! Cannot invoice!")
                continue
            # fetch execution info, if already executed pass
            _exec = await mx_invoicing_exec_repo.fetch(orden_details_id=ord.details.id)  # type: ignore (safe)
            if _exec:
                logger.info(
                    f"Orden has already been executed in invoicing: {_exec['status']}"
                )
                continue
            # get orden details info
            ord_details = await fetch_orden_details(
                orden_id=ord.id,
                orden_handler=ord_handler,
                restaurant_branch_repo=restaurant_branch_repo,
                supplier_unit_repo=supplier_unit_repo,
                supplier_unit_delivery_repo=supplier_unit_delivery_repo,
                mxcert_repo=mx_sat_cer_repo,
            )
            # data validation
            if (
                ord_details.details is None
                or not ord_details.details.id
                or not ord_details.details.payment_method
                or ord_details.branch is None
                or ord_details.branch.tax_info is None
                or not ord_details.branch.tax_info.mx_sat_id
                or ord_details.supplier is None
                or ord_details.supplier.supplier_unit is None
                or ord_details.supplier.supplier_unit.tax_info is None
                or not ord_details.supplier.supplier_unit.tax_info.zip_code
                or not ord_details.supplier.supplier_unit.tax_info.invoicing_options.invoice_type
            ):
                raise Exception("Cannot generate Invoice: Missing Orden details data")
            # create execution
            mxinv_exec = MxInvoicingExecution(
                id=uuid.uuid4(),
                orden_details_id=ord_details.details.id,
                execution_start=datetime.utcnow(),
                status=ExecutionStatusType.RUNNING,
                result="{}",
            )
            i_exec_id = await mx_invoicing_exec_repo.add(mxinv_exec)
            if not i_exec_id:
                raise Exception("Error creating Invoicing Execution")
            # create invoice
            try:
                invoice_params = dict(
                    orden_details_id=ord_details.details.id,
                    cfdi_type=CFDIType.INGRESO.value,
                    payment_form=INVOICE_PAYMENT_MAP[
                        ord_details.details.payment_method
                    ].value,
                    expedition_place=ord_details.supplier.supplier_unit.tax_info.zip_code,
                    issue_date=datetime.utcnow() - timedelta(hours=6),
                    payment_method=ord_details.supplier.supplier_unit.tax_info.invoicing_options.invoice_type.value,
                    core_user=alima_bot,
                )
                logger.info("Invoice Params:")
                logger.info(invoice_params)
                res_inv = await mxinv_handler.new_customer_invoice(
                    orden_details_id=ord_details.details.id,
                    cfdi_type=CFDIType.INGRESO.value,
                    payment_form=INVOICE_PAYMENT_MAP[
                        ord_details.details.payment_method
                    ].value,
                    expedition_place=ord_details.supplier.supplier_unit.tax_info.zip_code,
                    issue_date=datetime.utcnow() - timedelta(hours=6),
                    payment_method=ord_details.supplier.supplier_unit.tax_info.invoicing_options.invoice_type.value,
                    core_user=alima_bot,
                )
                print(res_inv)
                if not res_inv or not res_inv.sat_id:
                    raise Exception("Error creating Invoice")
                mxinv_exec.status = ExecutionStatusType.SUCCESS
                mxinv_exec.result = json.dumps(
                    {
                        "status": "ok",
                        "msg": "Invoice created successfully",
                        "sat_id": res_inv.sat_id,
                    }
                )
                mxinv_exec.execution_end = datetime.utcnow()
                await mx_invoicing_exec_repo.edit(mxinv_exec)
            except Exception as e:
                logger.error(e)
                mxinv_exec.status = ExecutionStatusType.FAILED
                mxinv_exec.result = json.dumps({"status": "error", "error": str(e)})
                mxinv_exec.execution_end = datetime.utcnow()
                await mx_invoicing_exec_repo.edit(mxinv_exec)

    return True


async def run_daily_3rd_party_invoices_warapper(date: str) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    # Permite conectar a la db

    _resp = await run_daily_3rd_party_invoices(_info, date)
    return _resp


async def main():
    args = parse_args()
    logger.info(f"Started running daily Supplier 3rd party Invoices: {args.date}")
    try:
        await db_startup()

        fl = await run_daily_3rd_party_invoices_warapper(
            args.date,
        )
        if not fl:
            logger.info(
                f"Daily Supplier 3rd party Invoices for ({args.date}) not able to be created"
            )
            return
        logger.info(
            f"Finished creating Daily Supplier 3rd party Invoices successfully: {args.date}"
        )
        await db_shutdown()
    except Exception as e:
        logger.error(f"Error creating Daily Supplier 3rd party Invoices: {args.date}")
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
