"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.supplier.update_allowed_payment_methods
"""

import asyncio
import logging
from types import NoneType
from typing import Any, Dict, List
from uuid import UUID
from bson import Binary
from databases import Database
from gqlapi.domain.models.v2.supplier import (
    MinimumOrderValue,
    SupplierBusinessCommertialConditions,
)
from gqlapi.domain.models.v2.utils import OrderSize, PayMethodType
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.repository import CoreMongoRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger

import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore
logger = get_logger("scripts.update_orden_count", logging.INFO, Environment(get_env()))


async def get_supplier_unit_ids(db: Database) -> List:
    supplier_unit = await db.fetch_all("SELECT * FROM supplier_unit")
    supplier_unit_ids = []
    for sb in supplier_unit:
        sb_obj = dict(sb)
        supplier_unit_ids.append(sb_obj)
    return supplier_unit_ids


async def fetch_supplier_business_account(
    info: InjectedStrawberryInfo,
) -> Dict[Any, Any] | NoneType:
    """Get supplier business account

    Args:
        supplier_business_id (UUID): unique supplier business id

    Raises:
        GQLApiException

    Returns:
        Dict[Any, Any]: Supplier Business model dict
    """
    core_mongo_repo = CoreMongoRepository(info)  # type: ignore
    query = {}
    supplier_business_account = await core_mongo_repo.search(
        core_element_collection="supplier_business_account",
        core_element_name="Supplier Business Account",
        core_query=query,
    )

    if not supplier_business_account:
        return None
    for result in supplier_business_account:
        # decoding bytes to string of stored files
        result["supplier_business_id"] = Binary.as_uuid(result["supplier_business_id"])
        if "legal_rep_id" in result and result["legal_rep_id"]:
            result["legal_rep_id"] = result["legal_rep_id"].decode("utf-8")
        if "incorporation_file" in result and result["incorporation_file"]:
            result["incorporation_file"] = result["incorporation_file"].decode("utf-8")
        if "mx_sat_csf" in result and result["mx_sat_csf"]:
            result["mx_sat_csf"] = result["mx_sat_csf"].decode("utf-8")
        if (
            "default_commertial_conditions" in result
            and result["default_commertial_conditions"]
        ):
            dconds = result["default_commertial_conditions"]
            try:
                result[
                    "default_commertial_conditions"
                ] = SupplierBusinessCommertialConditions(
                    minimum_order_value=MinimumOrderValue(
                        measure=OrderSize(dconds["minimum_order"]["measure"]),
                        amount=dconds["minimum_order"]["amount"],
                    ),
                    allowed_payment_methods=[
                        PayMethodType(apm) for apm in dconds["allowed_payment_methods"]
                    ],
                    policy_terms=dconds["policy_terms"],
                    account_number=dconds["account_number"],
                )
            except Exception as e:
                logging.warning(e)
                result["default_commertial_conditions"] = None
    return supplier_business_account


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


async def update_allowed_payment_methods(info: InjectedStrawberryInfo) -> bool:
    logger.info("Starting change allowed payment methods...")
    _db = info.context["db"].sql
    supplier_unit = await get_supplier_unit_ids(_db)  # type: ignore
    supplier_business_account = await fetch_supplier_business_account(info)
    return await update_allowed_payment_methods_by_supplier_unit(_db, supplier_unit, supplier_business_account)  # type: ignore


async def update_allowed_payment_methods_wrapper() -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await update_allowed_payment_methods(info)


async def main():
    try:
        await db_startup()
        logger.info("Starting routine to update allowed_payment_methods ...")

        resp = await update_allowed_payment_methods_wrapper()
        if resp:
            logger.info("Finished routine to update allowed_payment_methods")
        else:
            logger.info("Error to update allowed_payment_methods")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
