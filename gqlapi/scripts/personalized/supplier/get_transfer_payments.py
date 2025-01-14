"""
Script that get a Stripe Transfer Payment by Supplier.

How to run (file path as example):
        poetry run python -m gqlapi.scripts..personalized.supplier.get_transfer_payments --supplier_business_id
"""

import argparse
import asyncio
from datetime import datetime
import json
import logging
from uuid import UUID
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.integrations.integrations import (
    IntegrationsWebhookandler,
)
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.mongo import mongo_db as MongoDatabase

# logger
logger = get_logger(get_app())


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="get_transfer_payments")
    parser.add_argument(
        "--supplier_business_id",
        help="supplier_business id",
        default=False,
    )
    parser.add_argument(
        "--start_date",
        help="start_date format YYYY-MM-DD",
        default=False,
    )
    parser.add_argument(
        "--end_date",
        help="start_date FORMAT YYYY-MM-DD",
        default=False,
    )
    return parser.parse_args()


async def get_trasnfer_payment(
    info: InjectedStrawberryInfo,
    supplier_business_id: str,
    start_date: str,
    end_date: str,
) -> bool:
    logging.info("Starting to get number of transfer payments...")
    integrations_weebhook_partner_handler = IntegrationsWebhookandler(
        repo=IntegrationWebhookRepository(info)  # type: ignore
    )
    try:
        workflow_vars = await integrations_weebhook_partner_handler.get_vars(
            UUID(supplier_business_id)
        )
        if not workflow_vars:
            raise GQLApiException(
                msg="Error to get workflow vars",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        workflow_vars_json = json.loads(workflow_vars.vars)
        stripe_api_secret = workflow_vars_json.get("stripe_api_secret", None)
        stripe_api = StripeApi(app_name=get_app(), stripe_api_secret=stripe_api_secret)
        try:
            transfer_payments = stripe_api.get_transfer_payments(
                datetime.strptime(start_date, "%Y-%m-%d"),
                datetime.strptime(end_date, "%Y-%m-%d-%H-%M-%S"),
            )
            logger.info(f"Number of transfer payments: {transfer_payments}")
        except Exception as e:
            logger.error(e)

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


async def get_trasnfer_payments_wrapper(
    supplier_business_id: str, start_date: str, end_date: str
) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await get_trasnfer_payment(info, supplier_business_id, start_date, end_date)


async def main():
    try:
        args = parse_args()
        # Permite conectar a la db
        await db_startup()
        logging.info("Starting routine to get transfer payments ...")

        resp = await get_trasnfer_payments_wrapper(
            args.supplier_business_id, args.start_date, args.end_date
        )
        if resp:
            logging.info("Finished routine to get transfer payments")
        else:
            logging.info("Error to get transfer payments")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
