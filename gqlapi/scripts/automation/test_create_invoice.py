""" Script to test create invoice.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.automation.test_create_invoice --supplier_unit_id {supplier_business_id}
"""
import asyncio
import argparse
from datetime import datetime, timedelta
import json
import logging
from typing import List
import uuid
from gqlapi.lib.clients.clients.facturamaapi.facturama import PaymentForm
from gqlapi.domain.models.v2.core import (
    CartProduct,
    CoreUser,
    Orden,
    OrdenDetails,
    OrdenPayStatus,
    OrdenStatus,
)

from gqlapi.domain.models.v2.utils import (
    CFDIType,
    DeliveryTimeWindow,
    InvoiceType,
    OrdenSourceType,
    OrdenStatusType,
    OrdenType,
    PayMethodType,
    PayStatusType,
    SellingOption,
    UOMType,
)
from gqlapi.config import (
    ALIMA_ADMIN_BRANCH,
)
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
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
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductRepository,
)
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository

# from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup

logger = get_logger("scripts.test_create_invoice", logging.INFO, Environment(get_env()))


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Run Test Supplier 3rd party Invoice")
    parser.add_argument(
        "--supplier_unit_id",
        help="unique id to supplier unit",
        type=str,
        default=None,
        required=True,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def create_fake_orden(
    alima_bot: CoreUser,
    info: InjectedStrawberryInfo,
    supplier_unit_id: uuid.UUID,
    cart_products: List[CartProduct],
    alima_uuid: uuid.UUID,
) -> uuid.UUID:
    _handler = OrdenHandler(
        orden_repo=OrdenRepository(info),  # type: ignore
        orden_det_repo=OrdenDetailsRepository(info),  # type: ignore
        orden_status_repo=OrdenStatusRepository(info),  # type: ignore
        orden_payment_repo=OrdenPaymentStatusRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        rest_branc_repo=RestaurantBranchRepository(info),  # type: ignore
        supp_unit_repo=SupplierUnitRepository(info),  # type: ignore
        cart_repo=CartRepository(info),  # type: ignore
        cart_prod_repo=CartProductRepository(info),  # type: ignore
        rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),  # type: ignore
        supp_bus_acc_repo=SupplierBusinessAccountRepository(info),  # type: ignore
        supp_bus_repo=SupplierBusinessRepository(info),  # type: ignore
    )
    try:
        # call handler
        await _handler.supp_unit_repo.exist(supplier_unit_id)
        cart_res = await _handler._build_cart(
            core_user=alima_bot,
            cart_products=cart_products,
        )

        # create orden
        orden_id = await _handler.orden_repo.add(
            Orden(
                id=uuid.uuid4(),
                orden_type=OrdenType.NORMAL,
                source_type=OrdenSourceType.AUTOMATION,
                created_by=alima_bot.id,  # type: ignore
            )
        )
        if not orden_id:
            raise Exception("Errot to creating orden")

        ord_details_uuid = uuid.uuid4()

        orden_details = await _handler.orden_det_repo.add(
            OrdenDetails(
                id=ord_details_uuid,
                orden_id=orden_id,
                version=1,
                restaurant_branch_id=alima_uuid,
                supplier_unit_id=supplier_unit_id,
                cart_id=cart_res["cart_id"],
                delivery_date=(datetime.today() + timedelta(days=1)).date(),  # tomorrow
                delivery_time=DeliveryTimeWindow(9, 18),
                delivery_type=SellingOption.SCHEDULED_DELIVERY,
                subtotal_without_tax=cart_res["subtotal_without_tax"]
                if cart_res["subtotal_without_tax"]
                else None,
                tax=cart_res.get("tax", 0),
                discount=None,
                discount_code=None,
                cashback=None,
                cashback_transation_id=None,
                shipping_cost=None,
                packaging_cost=None,
                service_fee=None,
                total=cart_res["total"] if cart_res["total"] else None,
                subtotal=cart_res["subtotal"] if cart_res["subtotal"] else None,
                comments="Test to supplier invoice",
                payment_method=PayMethodType.CASH,
                approved_by=alima_bot.id,
                created_by=alima_bot.id,  # type: ignore
            )
        )

        # create delivery status
        orden_status = await _handler.orden_status_repo.add(
            OrdenStatus(
                id=uuid.uuid4(),
                orden_id=orden_id,
                status=OrdenStatusType.DELIVERED,
                created_by=alima_bot.id,  # type: ignore
            )
        )

        # create payment status
        orden_paystatus = await _handler.orden_payment_repo.add(
            OrdenPayStatus(
                id=uuid.uuid4(),
                orden_id=orden_id,
                status=PayStatusType.UNPAID,
                created_by=alima_bot.id,  # type: ignore
            )
        )

        if not orden_paystatus or not orden_details or not orden_status:
            try:
                await _handler.orden_status_repo.new(
                    OrdenStatus(
                        id=uuid.uuid4(),
                        orden_id=orden_id,
                        status=OrdenStatusType.CANCELED,
                        created_by=alima_bot.id,  # type: ignore
                    )
                )
            except Exception as e:
                logging.error(e)
                raise Exception("Errot to delete orden orden complement")

        return ord_details_uuid
    except Exception as e:
        logging.error(e)
        raise Exception("Error to create fake orden")


async def get_alima_bot(info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    cusr = await core_repo.fetch_by_email("admin")
    if not cusr or not cusr.id:
        raise Exception("Error getting Alima admin bot user")
    return cusr


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def create_fake_invoice(
    alima_bot: CoreUser,
    ord_details_uuid: uuid.UUID,
    info: InjectedStrawberryInfo,
    supplier_unit_id: uuid.UUID,
):
    _handler = MxInvoiceHandler(
        mx_invoice_repository=MxInvoiceRepository(info),  # type: ignore
        orden_details_repo=OrdenDetailsRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
        restaurant_branch_repo=RestaurantBranchRepository(info),  # type: ignore
        supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
        orden_repo=OrdenRepository(info),  # type: ignore
        cart_product_repo=CartProductRepository(info),  # type: ignore
        supp_prod_repo=SupplierProductRepository(info),  # type: ignore
        mx_sat_cer_repo=MxSatCertificateRepository(info),  # type: ignore
    )
    mx_ser_repo = MxSatCertificateRepository(info=info)  # type: ignore
    mx_sert = await mx_ser_repo.fetch_certificate(supplier_unit_id=supplier_unit_id)

    # call handler to upload invoice
    return await _handler.new_customer_invoice(
        orden_details_id=ord_details_uuid,
        cfdi_type=CFDIType.INGRESO.value,
        payment_form=PaymentForm.CASH.value,
        expedition_place=mx_sert["zip_code"],
        issue_date=datetime.today(),
        payment_method=InvoiceType.PUE.value,
        core_user=alima_bot,
    )


async def get_fake_cart_products(
    supplier_unit_id: uuid.UUID, info: InjectedStrawberryInfo
) -> List[CartProduct]:
    # fetch supplier unit
    sup_unit_repo = SupplierUnitRepository(info=info)  # type: ignore
    supplier_unit = await sup_unit_repo.fetch(supplier_unit_id)
    if not supplier_unit:
        raise Exception("Error to get supplier unit")
    # fetch product from supplier unit
    sup_resto_handler = SupplierRestaurantsHandler(
        supplier_restaurants_repo=SupplierRestaurantsRepository(info=info),  # type: ignore
        supplier_unit_repo=SupplierUnitRepository(info=info),  # type: ignore
        supplier_user_repo=SupplierUserRepository(info=info),  # type: ignore
        supplier_user_permission_repo=SupplierUserPermissionRepository(info=info),  # type: ignore
        restaurant_branch_repo=RestaurantBranchRepository(info=info),  # type: ignore
    )
    spec_pl_ids = await sup_resto_handler.find_business_specific_price_ids(
        supplier_unit_id=supplier_unit_id,
        restaurant_branch_id=uuid.uuid4(),  # random uuid to get default list
    )
    if not spec_pl_ids:
        raise Exception("Error to get supplier product price ids")
    pr_qry = f"""
            SELECT
                spr.*,
                row_to_json(last_price.*) AS last_price_json
            FROM supplier_product_price as last_price
            JOIN supplier_product spr on spr.id = last_price.supplier_product_id
            WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
            """
    sp_prices = await sup_resto_handler.supplier_restaurants_repo.raw_query(pr_qry, {})
    if not sp_prices:
        raise Exception("Error to get supplier product prices")
    # create fake cart prod
    sp_prod = dict(sp_prices[0])
    sp_price = json.loads(sp_prod["last_price_json"])
    return [
        CartProduct(
            supplier_product_id=sp_prod["id"],
            supplier_product_price_id=uuid.UUID(sp_price["id"]),
            quantity=1,
            sell_unit=UOMType(sp_prod["sell_unit"]),
            unit_price=1,
            subtotal=1,
        )
    ]


async def main():
    args = parse_args()
    logger.info("Started running test to create supplier invoice")
    try:
        await db_startup()
        supplier_unit_id = uuid.UUID(args.supplier_unit_id)
        _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
        alima_bot = await get_alima_bot(info=_info)
        cart_product = await get_fake_cart_products(supplier_unit_id, info=_info)
        od = await create_fake_orden(
            alima_bot,
            info=_info,
            supplier_unit_id=supplier_unit_id,
            cart_products=cart_product,
            alima_uuid=uuid.UUID(ALIMA_ADMIN_BRANCH),
        )
        invoice = await create_fake_invoice(
            alima_bot=alima_bot,
            ord_details_uuid=od,
            info=_info,
            supplier_unit_id=supplier_unit_id,
        )
        logging.info("Create invoice with id: " + invoice.sat_id)  # type: ignore

        await db_shutdown()
    except Exception as e:
        logger.error("Error creating fake invoice")
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
