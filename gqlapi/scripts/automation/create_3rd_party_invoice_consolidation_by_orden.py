""" Script to Create a Supplier Invoice Consolidation with orden.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.automation.create_3rd_party_invoice_consolidation_by_orden --help
"""
import asyncio
import argparse
import logging
from typing import List
import uuid
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.repository.core.cart import CartProductRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.repository.core.invoice import (
    MxInvoiceRepository,
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
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.models.v2.utils import (
    PayMethodType,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup

logger = get_logger(
    "scripts.create_3rd_party_invoice_consolidation_by_orden",
    logging.INFO,
    Environment(get_env()),
)

# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create 3rd Party INvoice Consolidation by ordenes."
    )
    parser.add_argument(
        "--orders",
        nargs="+",
        help="Orden to consolidate",
    )
    parser.add_argument(
        "--public_general_invoice",
        help="To invoice puplic general",
        type=bool,
        default=False,
        required=False,
    )
    parser.add_argument(
        "--payment_form",
        help="if io is PPD, PM is defauld TBD, so send any",
        choices=["cash", "transfer", "card", "to_be_determined"],
        type=str,
        default=False,
        required=True,
    )
    _args = parser.parse_args()
    # return args
    return _args


async def get_alima_bot(info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.get_by_email("admin")
    admin_user = tmp.id
    if not admin_user:
        raise Exception("Error getting Alima admin bot user")
    return tmp


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def send_create_alima_invoice_consolidation_by_orden_v2(
    info: InjectedStrawberryInfo,
    orden_list: List[uuid.UUID],
    public_general_invoice_flag: bool,
    payment_form: str,
) -> bool:
    logging.info("Starting send consolidated invoice ...")
    core_user_repo = CoreUserRepository(info)  # type: ignore
    supplier_business_repo = SupplierBusinessRepository(info)  # type: ignore
    supplier_business_account_repo = SupplierBusinessAccountRepository(info)  # type: ignore
    supplier_unit_repo = SupplierUnitRepository(info)  # type: ignore
    restaurant_branch_repo = RestaurantBranchRepository(info)  # type: ignore
    orden_repo = OrdenRepository(info)  # type: ignore
    orden_details_repo = OrdenDetailsRepository(info)  # type: ignore
    orden_status_repo = OrdenStatusRepository(info)  # type: ignore
    orden_payment_repo = OrdenPaymentStatusRepository(info)  # type: ignore
    cart_product_repo = CartProductRepository(info)  # type: ignore
    supp_prod_repo = SupplierProductRepository(info)  # type: ignore
    mx_sat_cer_repo = MxSatCertificateRepository(info)  # type: ignore
    mx_invoice_repository = MxInvoiceRepository(info)  # type: ignore
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
        supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
            info  # type: ignore
        ),
    )
    if not isinstance(public_general_invoice_flag, bool):
        public_general_invoice_flag = False
    alima_bot = await get_alima_bot(info=info)
    # fetch orden details
    ord_details = await ord_handler.search_ordens_with_many(orden_ids=orden_list)
    if await mxinv_handler.new_consolidated_customer_invoice(
        ordenes=ord_details,
        public_general_invoice_flag=public_general_invoice_flag,
        payment_method=PayMethodType(payment_form),
        core_user=alima_bot,
    ):
        return True
    return False


async def send_create_alima_invoice_consolidation_by_orden_v2_wrapper(
    orden_list: List[uuid.UUID], public_general_invoice_flag: bool, payment_form: str
) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    # Permite conectar a la db
    _resp = await send_create_alima_invoice_consolidation_by_orden_v2(
        _info, orden_list, public_general_invoice_flag, payment_form
    )
    return _resp


async def main():
    try:
        args = parse_args()
        logging.info("Started creating Consolidated Supplier Invoice ")
        await db_startup()
        orden_list = []
        for orden in args.orders:
            orden_list.append(uuid.UUID(orden))
        if len(orden_list) == 0:
            raise Exception("No orden to consolidate")
        fl = await send_create_alima_invoice_consolidation_by_orden_v2_wrapper(
            orden_list, args.public_general_invoice, args.payment_form
        )
        if fl:
            logging.info("Finished Started creating Consolidated Supplier Invoice")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
