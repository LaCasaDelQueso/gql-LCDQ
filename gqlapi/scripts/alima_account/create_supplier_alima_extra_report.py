""" Script to add extra report costs to Supplier Alima Account.

Usage:
    cd projects/gqlapi/
    # python -m gqlapi.scripts.alima_account.create_supplier_alima_extra_report --help
"""
import asyncio
import argparse
import logging
from typing import Any, Dict, List
import uuid

from databases import Database
from gqlapi.handlers.alima_account.account import AlimaAccountHandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
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
from gqlapi.domain.models.v2.utils import (
    ChargeType,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.create_supplier_alima_extra_report", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Add Report cost to Supplier Alima Account.")
    parser.add_argument(
        "--supplier_business_id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--report-name",
        help="Report Name.",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--report-price",
        help="Report price in $",
        type=float,
        default=None,
        required=False,
    )

    _args = parser.parse_args()
    # return args
    return _args


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def fetch_supplier_business_info(
    db: Database, supplier_business_id: uuid.UUID
) -> Dict[str, Any]:
    """Fetch supplier business information."""
    supplier = await db.fetch_one(
        """
        SELECT id, name, active FROM supplier_business
        WHERE id = :supplier_business_id
        """,
        {"supplier_business_id": supplier_business_id},
    )
    if not supplier:
        logging.warning("Not able to retrieve supplier information")
        return {}
    if supplier["active"]:
        logging.warning("Supplier Business is alreadfy ACTIVE!")
        return {}
    logging.info("Got Supplier Business info")
    return dict(supplier)


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def create_new_charge(
    db: Database,
    paid_account_id: uuid.UUID,
    charge_type: str,
    charge_amount: float,
    charge_amount_type: str,  # "$" or "%"
    charge_description: str
) -> uuid.UUID:
    """Create a new charge.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    charge_type : ChargeType
    charge_amount : float
    charge_amount_type : str

    Returns
    -------
    uuid.UUID
    """
    # create charge
    charge_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO charge (id, paid_account_id, charge_type, charge_amount, charge_amount_type, currency, charge_description)
        VALUES (:id, :paid_account_id, :charge_type, :charge_amount, :charge_amount_type, :currency, :charge_description)
        """,
        {
            "id": charge_id,
            "paid_account_id": paid_account_id,
            "charge_type": charge_type,
            "charge_amount": charge_amount
            if charge_amount_type == "$"
            else charge_amount / 100,
            "charge_amount_type": charge_amount_type,
            "currency": "MXN",
            "charge_description": charge_description
        },
    )
    logging.info(f"Created Charge: {charge_type}")
    return charge_id


async def get_alima_bot(info: InjectedStrawberryInfo) -> uuid.UUID:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.fetch_by_email("admin")
    if not tmp or not tmp.id:
        raise Exception("Error getting Alima admin bot user")
    admin_user = tmp.id
    return admin_user


async def desactive_charges(
    db: Database, paid_account_id: uuid.UUID, charge_type: List[str]
) -> bool:
    try:
        await db.execute(
            """
            UPDATE charge SET active = f
            WHERE charge_type in (:charge_type)
            AND paid_account_id = :paid_account_id
            AND active = t
            """,
            {"paid_account_id": paid_account_id, "charge_type": charge_type},
        )
        logging.info(f"Desactivate charges of: {paid_account_id}")
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------
# Create alima account
# ---------------------------------------------------------------------


async def create_alima_extra_report(
    supplier_business_id: uuid.UUID, report_name: str, report_price: float
) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")

    _handler = AlimaAccountHandler(
        AlimaAccountRepository(_info),  # type: ignore
        CoreUserRepository(_info),  # type: ignore
        SupplierBusinessRepository(_info),  # type: ignore
        SupplierBusinessAccountRepository(_info),  # type: ignore
        SupplierUserRepository(_info),  # type: ignore
        SupplierUserPermissionRepository(_info),  # type: ignore
    )
    paid_acount = await _handler.repository.fetch_alima_account(supplier_business_id)
    if not paid_acount:
        return False

    await create_new_charge(
        _db,
        paid_acount.id,
        ChargeType.REPORTS.value,
        report_price,
        "$",
        report_name
    )

    # show results
    logging.info("Finished creating Supplier Alima Extra Report")
    logging.info("\n".join(["-----", f"Supplier Business ID: {supplier_business_id}"]))
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(
        f"Started creating Supplier Alima Extra Report: {args.supplier_business_id}"
    )
    try:
        fl = await create_alima_extra_report(
            uuid.UUID(args.supplier_business_id),
            args.report_name,
            args.report_price,
        )
        if not fl:
            logging.info(
                f"Supplier Business with id ({args.supplier_business_id}) not able to be created"
            )
            return
        logging.info(
            f"Finished creating Alima account successfully: {args.supplier_business_id}"
        )
    except Exception as e:
        logging.error(
            f"Error creating Supplier Alima Extra Report: {args.supplier_business_id}"
        )
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
