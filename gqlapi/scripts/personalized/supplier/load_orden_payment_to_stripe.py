"""
Script that generates a Stripe Transfer Payment Intent based on a given Orden Id.

How to run (file path as example):
        poetry run python -m gqlapi.scripts..personalized.supplier.consolidated_orden_with_stripe --orden_id
"""

import argparse
import asyncio
import json
import logging
from types import NoneType
from typing import List
from uuid import UUID
from gqlapi.domain.models.v2.utils import OrdenStatusType, PayMethodType
import pandas as pd

from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi, StripeCurrency
from gqlapi.domain.models.v2.restaurant import RestaurantBranchTag
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.integrations.integrations import (
    IntegrationsWebhookandler,
)
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.mongo import mongo_db as MongoDatabase

# logger
logger = get_logger(get_app())


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="New Scorpion Orden")
    parser.add_argument(
        "--orden_id",
        help="orden id",
        default=False,
    )
    return parser.parse_args()


pd.options.mode.chained_assignment = None  # type: ignore


def get_stripe_tag(tags: List[RestaurantBranchTag]) -> str | NoneType:
    for tag in tags:
        if tag.tag_key == "StripeId":
            return tag.tag_value
    return None


async def new_orden_la_casa_del_queso(
    info: InjectedStrawberryInfo, orden_id: str
) -> bool:
    logging.info("Starting to consolidate orden to la casa del queso...")
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
        rest_business_repo=RestaurantBusinessRepository(info),  # type: ignore
    )
    rest_branch_handler = RestaurantBranchRepository(info)  # type: ignore

    integrations_weebhook_partner_handler = IntegrationsWebhookandler(
        repo=IntegrationWebhookRepository(info)  # type: ignore
    )
    try:
        # call handler
        _resp = await _handler.search_orden(orden_id=UUID(orden_id))
        if (
            not _resp[0].branch
            or not _resp[0].details
            or not _resp[0].supplier
            or not _resp[0].supplier.supplier_business_account
            or not _resp[0].supplier.supplier_business_account.email
            or not _resp[0].supplier.supplier_business
            or _resp[0].details.total is None
        ):
            raise GQLApiException(
                msg="Error to get branch info",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # verify order is delivered
        if (
            _resp[0].status is None
            or OrdenStatusType(_resp[0].status.status) != OrdenStatusType.DELIVERED
        ):
            raise GQLApiException(
                msg="Orden is not delivered",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        if _resp[0].details.payment_method != PayMethodType.TRANSFER:
            return True
        workflow_vars = await integrations_weebhook_partner_handler.get_vars(
            _resp[0].supplier.supplier_business.id
        )
        if not workflow_vars:
            raise GQLApiException(
                msg="Error to get workflow vars",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        branch_tags = await rest_branch_handler.fetch_tags(_resp[0].branch.id)
        stripe_value = get_stripe_tag(branch_tags)
        if not stripe_value:
            return True
        workflow_vars_json = json.loads(workflow_vars.vars)
        stripe_api_secret = workflow_vars_json.get("stripe_api_secret")
        if not stripe_api_secret:
            raise GQLApiException(
                msg="Error to get stripe api secret",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        stripe_api = StripeApi(app_name=get_app(), stripe_api_secret=stripe_api_secret)
        try:
            stripe_api.create_transfer_payment_intent(
                stripe_customer_id=stripe_value,
                charge_description=f"PEDIDO: {_resp[0].orden_number}",
                charge_amount=_resp[0].details.total,
                email_to_confirm=_resp[0].supplier.supplier_business_account.email,
                currency=StripeCurrency.MXN,
                charge_metadata={
                    "orden_id": str(_resp[0].id),
                    "supplier_unit_id": str(_resp[0].details.supplier_unit_id),
                    "restaurant_branch_id": str(_resp[0].details.restaurant_branch_id),
                },
            )
        except Exception as e:
            # send email
            await send_email(
                subject="Error al procesar el pago",
                email_to=_resp[0].supplier.supplier_business_account.email,
                content=f"Ocurrio un error al procesar el pago de la orden {_resp[0].orden_number}: {e}",
            )

    except GQLApiException as ge:
        logger.warning(ge)
        raise GQLApiException(
            msg=ge.msg,
            error_code=ge.error_code,
        )
    except Exception as e:
        logger.error(e)
        raise GQLApiException(
            msg=str(e),
            error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
        )
    return True


async def la_casa_del_queso_orden_wrapper(orden_id: str) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await new_orden_la_casa_del_queso(info, orden_id)


async def main():
    try:
        args = parse_args()
        # Permite conectar a la db
        await db_startup()
        logging.info("Starting routine to consolidate orden to la casa del queso ...")

        resp = await la_casa_del_queso_orden_wrapper(args.orden_id)
        if resp:
            logging.info("Finished routine to consolidate orden to la casa del queso")
        else:
            logging.info("Error to consolidate orden to la casa del queso")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
