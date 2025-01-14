""" Script to Cancel a Alima Invoice on behalf of a Supplier Business.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.alima_account.cancel_supplier_invoice --help
"""

import asyncio
import argparse
import logging
from typing import Optional
import uuid

from gqlapi.domain.models.v2.core import (
    CoreUser,
)
from gqlapi.errors import GQLApiException
from gqlapi.handlers.alima_account.account import AlimaAccountHandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.alima_account.billing import (
    AlimaBillingInvoiceRepository,
    AlimaBillingInvoiceComplementRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository

# from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.cancel_alima_invoice", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Cancel Alima Invoice for Supplier")
    parser.add_argument(
        "--supplier-business-id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--motive",
        help="motive to cancel invoice (typical is 02)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--date",
        help="month of invoice MM-YYYY",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--uuid_replacement",
        help="(Optional) SAT UUID that will replace the canceled one",
        type=str,
        default=None,
        required=False,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def get_alima_bot(info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    cusr = await core_repo.fetch_by_email("admin")
    if not cusr or not cusr.id:
        raise Exception("Error getting Alima admin bot user")
    return cusr


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def cancel_internal_invoice(
    supplier_business_id: uuid.UUID,
    date: str,
    motive: str,
    uuid_replacement: Optional[str] = None,
) -> bool:
    info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = info.context["db"].sql
    _mongo = info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")

    # initialize repos
    supplier_business_repo = SupplierBusinessRepository(info)  # type: ignore
    supplier_business_account_repo = SupplierBusinessAccountRepository(info)  # type: ignore
    paid_account_repo = AlimaAccountRepository(info)  # type: ignore
    alima_billing_repo = AlimaBillingInvoiceRepository(info)  # type: ignore
    alima_billing_comp_repo = AlimaBillingInvoiceComplementRepository(info)  # type: ignore
    billing_invoice_repo = AlimaAccountHandler(
        alima_account_repository=paid_account_repo,
        supplier_business_repository=supplier_business_repo,
        supplier_business_account_repository=supplier_business_account_repo,
        core_user_repository=CoreUserRepository(info),  # type: ignore
        supplier_user_repository=SupplierUserRepository(info),  # type: ignore
        supplier_user_permission_repository=SupplierUserPermissionRepository(info),  # type: ignore
        alima_billing_invoice_repository=alima_billing_repo,
        alima_billing_complement_repository=alima_billing_comp_repo,
    )
    cancel_validation = await billing_invoice_repo.cancel_alima_invoice(
        supplier_business_id=supplier_business_id,
        date=date,
        motive=motive,
        uuid_replacement=uuid_replacement,
    )
    await db_shutdown()
    return cancel_validation.canceled


async def main():
    args = parse_args()
    print(args)
    logger.info(f"Started cancel Supplier Invoice: {args.supplier_business_id}")
    try:
        uuidrep = (
            args.uuid_replacement
            if (args.uuid_replacement and uuid.UUID(args.uuid_replacement))
            else None
        )
        fl = await cancel_internal_invoice(
            uuid.UUID(args.supplier_business_id),
            date=args.date,
            motive=args.motive,
            uuid_replacement=uuidrep,
        )
        if not fl:
            logger.info(
                f"Error cancel supplier Invoice for ({args.supplier_business_id})"
            )
            return
        logger.info(
            f"Finished cancel Supplier Invoice successfully: {args.supplier_business_id}"
        )
    except GQLApiException as e:
        logger.error(f"Error cancel Supplier Invoice: {args.supplier_business_id}")
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
