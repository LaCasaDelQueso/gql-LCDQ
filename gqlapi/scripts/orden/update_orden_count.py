"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.orden.update_orden_count
"""

import asyncio
import logging
from typing import Any, Dict, List
from databases import Database
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger

import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore
logger = get_logger("scripts.update_orden_count", logging.INFO, Environment(get_env()))


async def get_supplier_business_ids(db: Database) -> List:
    supplier_business = await db.fetch_all("SELECT * FROM supplier_business")
    supplier_business_ids = []
    for sb in supplier_business:
        sb_obj = dict(sb)
        supplier_business_ids.append(sb_obj["id"])
    return supplier_business_ids


async def update_ordenes(db: Database, vals: List[Dict[str, Any]]) -> bool:
    try:
        await db.execute_many(
            """
            UPDATE orden
            SET orden_number = :orden_number
            WHERE id = :id
            """,
            vals,
        )
        return True
    except Exception as e:
        logger.error(e)
        return False


async def update_orden_count_by_supplier_business(
    db: Database, supplier_business_ids: List
) -> bool:
    for sbid in supplier_business_ids:
        orders = await db.fetch_all(
            """
            SELECT DISTINCT(ord.id) id, ord.created_at
            FROM orden ord
            JOIN orden_details od ON ord.id = od.orden_id
            JOIN supplier_unit su ON od.supplier_unit_id = su.id
            WHERE su.supplier_business_id = :supplier_business_id
            ORDER BY ord.created_at ASC
            """,
            {"supplier_business_id": sbid},
        )
        count = 1
        acc = []
        for ord in orders:
            ord_obj = dict(ord)
            acc.append({"id": ord_obj["id"], "orden_number": str(count)})
            count += 1
        flag = await update_ordenes(db, acc)
        if not flag:
            print("Issues updating supplier business: ", sbid)
            return False
    return True


async def update_orden_count(info: InjectedStrawberryInfo) -> bool:
    logger.info("Starting change orden count...")
    _db = info.context["db"].sql
    supplier_business_ids = await get_supplier_business_ids(_db)  # type: ignore
    return await update_orden_count_by_supplier_business(_db, supplier_business_ids)  # type: ignore


async def update_orden_count_wrapper() -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=None,
    )
    return await update_orden_count(info)


async def main():
    try:
        await db_startup()
        logger.info("Starting routine to update orden count ...")

        resp = await update_orden_count_wrapper()
        if resp:
            logger.info("Finished routine to update orden count")
        else:
            logger.info("Error to update orders")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
