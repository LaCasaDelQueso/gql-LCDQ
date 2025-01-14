"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.authos.get_emails_to_ecommerce_users
"""

import argparse
import asyncio
import base64
from types import NoneType
from typing import Any, Dict, List
from uuid import UUID
from bson import Binary
from databases import Database
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.repository import CoreMongoRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore
logger = get_logger(get_app())


def parse_args() -> argparse.Namespace:
    # get file xlsx from directory
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--supplier-business-id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    _args = parser.parse_args()
    return _args


async def fetch_supplier_business_account(
    info: InjectedStrawberryInfo, supplier_business_id: UUID
) -> List[Dict[Any, Any]] | NoneType:
    """Get supplier business account

    Args:
        supplier_business_id (UUID): unique supplier business id

    Raises:
        GQLApiException

    Returns:
        Dict[Any, Any]: Supplier Business model dict
    """
    db = info.context["db"].sql
    sql_query = f"""
            SELECT restaurant_business_id, branch_name from restaurant_branch where id in
            (SELECT restaurant_branch_id from supplier_restaurant_relation where supplier_unit_id in
            (SELECT id from supplier_unit where supplier_business_id = '{supplier_business_id}'))
            AND restaurant_business_id not in
            (SELECT restaurant_business_id FROM ecommerce_user_restaurant_relation)"""
    rest_bus = await db.fetch_all(sql_query, {})  # type: ignore
    rest_bus_list = []
    for rb in rest_bus:
        rb_obj = dict(rb)
        rest_bus_list.append(Binary.from_uuid(rb_obj["restaurant_business_id"]))
    core_mongo_repo = CoreMongoRepository(info)  # type: ignore
    query = {"restaurant_business_id": {"$in": rest_bus_list}}
    restaurant_business_info = await core_mongo_repo.search(
        core_element_collection="restaurant_business_account",
        core_element_name="Restaurant Business Account",
        core_query=query,
    )

    if not restaurant_business_info:
        return None
    emails = []
    for result in restaurant_business_info:
        emails.append({"email": result["email"]})
    return emails


async def update_allowed_payment_methods_db(db: Database, vals: Dict[str, Any]) -> bool:
    try:
        await db.execute(
            """
            UPDATE supplier_unit
            SET account_number = :account_number, allowed_payment_methods = :allowed_payment_methods
            WHERE id = :id
            """,
            vals,
        )
        return True
    except Exception as e:
        logger.error(e)
        return False


def match_supplier_business_account(
    supplier_business_id: UUID, supplier_business_account: List[Dict[str, Any]]
) -> Dict[Any, Any] | NoneType:
    for sba in supplier_business_account:
        if sba["supplier_business_id"] == supplier_business_id:
            return sba
    return None


async def update_allowed_payment_methods_by_supplier_unit(
    db: Database,
    supplier_unit: List[Dict[Any, Any]],
    supplier_business_account: List[Dict[Any, Any]],
) -> bool:
    for su in supplier_unit:
        sba = match_supplier_business_account(
            su["supplier_business_id"], supplier_business_account
        )
        if sba:
            if "default_commertial_conditions" in sba:
                vals = {
                    "id": su["id"],
                    "account_number": sba[
                        "default_commertial_conditions"
                    ].account_number,
                    "allowed_payment_methods": [
                        apm.value
                        for apm in sba[
                            "default_commertial_conditions"
                        ].allowed_payment_methods
                    ],
                }
            else:
                vals = {
                    "id": su["id"],
                    "account_number": "",
                    "allowed_payment_methods": [],
                }
            flag = await update_allowed_payment_methods_db(
                db,
                vals,
            )
            if not flag:
                print("Issues updating supplier unit: ", su["id"])
        else:
            print("Issues updating supplier unit: ", su["id"])
    return True


async def get_emails_to_ecommerce_users(
    info: InjectedStrawberryInfo, supplier_business_id: UUID
) -> bool:
    logger.info("Starting get emails to ecommerce users...")
    supplier_business_account = await fetch_supplier_business_account(
        info, supplier_business_id
    )
    df = pd.DataFrame(supplier_business_account)
    df = df.sort_values(by="email")
    with pd.ExcelWriter(
        f"{str(supplier_business_id)}_restaurant_emails.xlsx", engine="xlsxwriter"
    ) as writer:
        df.to_excel(writer, index=False)
    with open(f"{str(supplier_business_id)}_restaurant_emails.xlsx", "rb") as file:
        base64.b64encode(file.read()).decode()
    return True


async def get_emails_to_ecommerce_users_wrapper(supplier_business_id: UUID) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await get_emails_to_ecommerce_users(info, supplier_business_id)


async def main():
    try:
        await db_startup()
        logger.info("Starting get emails to ecommerce users ...")
        pargs = parse_args()
        supplier_business_id = UUID(pargs.supplier_business_id)
        resp = await get_emails_to_ecommerce_users_wrapper(supplier_business_id)
        if resp:
            logger.info("Finished get emails to ecommerce users ...")
        else:
            logger.info("Error to get emails to ecommerce users ...")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
