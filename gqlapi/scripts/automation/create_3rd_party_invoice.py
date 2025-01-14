""" Script to Create a Customer Invoice on behalf of a Supplier Business.

This script does the following:

1. Fetches the Restaurant Branch information from Orden UUID
  1.1. Retrieves RFC
  1.2. Retrieves Invoice Type
2. Fetches the Supplier Business information from Orden UUID
    2.1. Retrieves Expedition Place
3. Creates a new Customer Invoice

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.automation.create_3rd_party_invoice --help
"""
import asyncio
import argparse
from datetime import datetime, timedelta
import logging
import uuid

from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import RestaurantBranchGQL
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import INVOICE_PAYMENT_MAP
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitGQL
from gqlapi.domain.models.v2.core import CoreUser, MxSatInvoicingCertificateInfo
from gqlapi.domain.models.v2.restaurant import RestaurantBranchMxInvoiceInfo
from gqlapi.domain.models.v2.supplier import SupplierUnitDeliveryOptions
from gqlapi.domain.models.v2.utils import (
    CFDIType,
    SellingOption,
    ServiceDay,
)
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.supplier.supplier_invoice import SupplierInvoiceHandler
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
from gqlapi.repository.restaurant.restaurant_branch import (
    RestaurantBranchInvoicingOptionsRepository,
    RestaurantBranchRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
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
    "scripts.create_3rd_party_invoice", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create new Supplier 3rd party Invoice"
    )
    parser.add_argument(
        "--orden-id",
        help="Orden ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


@deprecated("Use SuppliierInvoiceHandler.fetch_orden_details instead")
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
    if not ord_detail.branch or not ord_detail.branch.tax_info:
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
    if (
        not ord_detail.supplier
        or not ord_detail.supplier.supplier_unit
        or not ord_detail.supplier.supplier_unit.tax_info
    ):
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


async def get_alima_bot(info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    cusr = await core_repo.fetch_by_email("admin")
    if not cusr or not cusr.id:
        raise Exception("Error getting Alima admin bot user")
    return cusr


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def create_3rd_party_invoice(
    orden_id: uuid.UUID,
) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    # initialize repos
    core_user_repo = CoreUserRepository(_info)  # type: ignore
    supplier_business_repo = SupplierBusinessRepository(_info)  # type: ignore
    supplier_business_account_repo = SupplierBusinessAccountRepository(_info)  # type: ignore
    supplier_unit_repo = SupplierUnitRepository(_info)  # type: ignore
    supplier_unit_delivery_repo = SupplierUnitDeliveryRepository(_info)  # type: ignore
    restaurant_branch_repo = RestaurantBranchRepository(_info)  # type: ignore
    orden_repo = OrdenRepository(_info)  # type: ignore
    orden_details_repo = OrdenDetailsRepository(_info)  # type: ignore
    orden_status_repo = OrdenStatusRepository(_info)  # type: ignore
    orden_payment_repo = OrdenPaymentStatusRepository(_info)  # type: ignore
    cart_product_repo = CartProductRepository(_info)  # type: ignore
    supp_prod_repo = SupplierProductRepository(_info)  # type: ignore
    mx_sat_cer_repo = MxSatCertificateRepository(_info)  # type: ignore
    mx_invoice_repository = MxInvoiceRepository(_info)  # type: ignore
    mx_invoicing_exec_repo = MxInvoicingExecutionRepository(_info)  # type: ignore
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
    # supplier invoice handler
    sup_invo_handler = SupplierInvoiceHandler(
        orden_handler=ord_handler,
        mx_invoice_handler=mxinv_handler,
        restaurant_branch_repo=restaurant_branch_repo,
        supplier_unit_repo=supplier_unit_repo,
        supplier_unit_delivery_repo=supplier_unit_delivery_repo,
        mx_sat_cer_repo=mx_sat_cer_repo,
        mx_invoicing_exec_repo=mx_invoicing_exec_repo,
        supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(_info),  # type: ignore
        supplier_restaurants_repo=SupplierRestaurantsRepository(_info),  # type: ignore
    )
    # get alima bot
    alima_bot = await get_alima_bot(_info)
    # get orden details info
    ord_details = await sup_invo_handler.fetch_orden_details(
        orden_id=orden_id,
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
    # create invoice
    try:
        # [TODO] @Fer Update paymenth_method if branch have invoicing options
        invoice_params = dict(
            orden_details_id=ord_details.details.id,
            cfdi_type=CFDIType.INGRESO.value,
            payment_form=INVOICE_PAYMENT_MAP[ord_details.details.payment_method].value,
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
            payment_form=INVOICE_PAYMENT_MAP[ord_details.details.payment_method].value,
            expedition_place=ord_details.supplier.supplier_unit.tax_info.zip_code,
            issue_date=datetime.utcnow() - timedelta(hours=6),
            payment_method=ord_details.supplier.supplier_unit.tax_info.invoicing_options.invoice_type.value,
            core_user=alima_bot,
        )
        print(res_inv)
    except Exception as e:
        logger.error(e)
        return False
    # show results
    # logger.info("Finished creating Supplier Billing Invoice")
    # logger.info(
    #     "\n".join(
    #         [
    #             "-----",
    #             f"Supplier Business ID: {supplier_business_id}",
    #             f"Paid Account ID: {paid_account_id}",
    #             f"Billing Invoice ID: {b_invoice_id}",
    #             f"Billing Invoice Charges IDs: {b_invoice_charges}",
    #             f"Billing Invoice Total: {total_charges['total']}",
    #             "-----",
    #         ]
    #     )
    # )
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    print(args)
    logger.info(f"Started creating Supplier 3rd party Invoice: {args.orden_id}")
    try:
        fl = await create_3rd_party_invoice(
            uuid.UUID(args.orden_id),
        )
        if not fl:
            logger.info(
                f"Supplier 3rd party Invoice for ({args.orden_id}) not able to be created"
            )
            return
        logger.info(
            f"Finished creating Supplier 3rd party Invoice successfully: {args.orden_id}"
        )
    except Exception as e:
        logger.error(
            f"Error creating Supplier 3rd party Invoice Invoice: {args.orden_id}"
        )
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
