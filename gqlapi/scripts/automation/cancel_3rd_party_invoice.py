""" Script to Cancel a Customer Invoice on behalf of a Supplier Business.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.automation.cancel_3rd_party_invoice --help
"""

import asyncio
import argparse
from typing import Optional
import uuid
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.models.v2.core import (
    CoreUser,
)
from gqlapi.errors import GQLApiException
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.repository.core.invoice import (
    MxInvoiceComplementRepository,
    MxInvoiceRepository,
    MxSatCertificateRepository,
)
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository

# from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(get_app())


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Cancel new Supplier 3rd party Invoice"
    )
    parser.add_argument(
        "--by",
        help="invoice or orden",
        type=str,
        default=None,
        required=True,
        choices=["invoice", "orden"],
    )
    parser.add_argument(
        "--orden_id",
        help="Orden ID (UUID)",
        type=str,
        default=None,
        required=False,
    )
    parser.add_argument(
        "--mx_invoice_id",
        help="MX INVOICE ID (UUID)",
        type=str,
        default=None,
        required=False,
    )
    parser.add_argument(
        "--motive",
        help="motive to cancel invoice (typical is 02)",
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


async def cancel_3rd_party_invoice(
    motive: str,
    cancel_type: str,
    orden_id: Optional[uuid.UUID] = None,
    mx_invoice_id: Optional[uuid.UUID] = None,
    uuid_replacement: Optional[str] = None,
) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")

    mxinv_handler = MxInvoiceHandler(
        mx_invoice_repository=MxInvoiceRepository(_info),  # type: ignore
        orden_details_repo=OrdenDetailsRepository(_info),  # type: ignore
        core_user_repo=CoreUserRepository(_info),  # type: ignore
        mx_sat_cer_repo=MxSatCertificateRepository(_info),  # type: ignore
        mx_invoice_complement_repository=MxInvoiceComplementRepository(_info),  # type: ignore
        supplier_unit_repo=SupplierUnitRepository(_info),  # type: ignore
    )
    if cancel_type == "orden" and orden_id:
        cancel_validation = await mxinv_handler.cancel_customer_invoice(
            orden_id=orden_id,
            motive=motive,
            uuid_replacement=uuid_replacement,
        )
    if cancel_type == "invoice" and mx_invoice_id:
        cancel_validation = await mxinv_handler.cancel_customer_invoice_by_invoice(
            mx_invoice_id=mx_invoice_id,
            motive=motive,
            uuid_replacement=uuid_replacement,
        )
    await db_shutdown()
    return cancel_validation.canceled


async def main():
    args = parse_args()
    print(args)
    logger.info(f"Started cancel Supplier 3rd party Invoice: {args.orden_id}")
    try:
        uuidrep = (
            args.uuid_replacement
            if (args.uuid_replacement and uuid.UUID(args.uuid_replacement))
            else None
        )
        if args.by == "invoice" and not args.mx_invoice_id:
            logger.info("invoice param not found")
            return
        if args.by == "orden" and not args.orden_id:
            logger.info("invoice param not found")
            return
        fl = await cancel_3rd_party_invoice(
            motive=args.motive,
            cancel_type=args.by,
            orden_id=uuid.UUID(args.orden_id) if args.orden_id else None,
            mx_invoice_id=uuid.UUID(args.mx_invoice_id) if args.mx_invoice_id else None,
            uuid_replacement=uuidrep,
        )
        if not fl:
            logger.info("Error cancel 3rd party Invoice")
            return
        logger.info("Finished cancel Supplier 3rd party Invoice successfully")
    except GQLApiException as e:
        logger.error("Error cancel Supplier 3rd party Invoice Invoice")
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
