"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.monitor.invoice_execution
"""

import argparse
import asyncio
import logging
from typing import Any, Dict, List
from databases import Database
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.config import RETOOL_SECRET_BYPASS
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.handlers.services.mails import send_monitor_alert
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger

import pandas as pd


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tolerance", help="how many hour to tolerance", required=True)
    _args = parser.parse_args()
    return _args


pd.options.mode.chained_assignment = None  # type: ignore
logger = get_logger(
    "scripts.monitor.invoice_execution", logging.INFO, Environment(get_env())
)


async def get_invoices_failed(db: Database, tolerance: int) -> List:
    invoices_failed = await db.fetch_all(
        f"""SELECT
            mxie.id,
            sb.name "Proveedor",
            su.unit_name "CEDIS",
            rbr.branch_name "Sucursal",
            od.delivery_date,
            mxie.orden_details_id,
            (mxie.execution_start - interval '6 hours') execution_start,
            mxie.status,
            mxie.result,
            (mxie.execution_end - interval '6 hours') execution_end
        FROM mx_invoicing_execution mxie
        JOIN orden_details od ON od.id = mxie.orden_details_id
        JOIN restaurant_branch rbr ON rbr.id = od.restaurant_branch_id
        JOIN supplier_unit su ON su.id = od.supplier_unit_id
        JOIN supplier_business sb ON sb.id = su.supplier_business_id
        WHERE mxie.execution_start > (NOW() -  interval '{str(tolerance)} hours')
        and mxie.status IN ('failed', 'running')
        order by mxie.execution_start desc"""
    )
    invoices_failed_list = []
    for i_f in invoices_failed:
        if_obj = dict(i_f)
        invoices_failed_list.append(if_obj)
    return invoices_failed_list


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


async def send_monitor_alert_email(invoices_failed_list: List[Dict[Any, Any]]) -> bool:
    df = pd.DataFrame(invoices_failed_list)
    html_table = df.to_html(index=False)
    return True


async def invoice_monitor(
    info: InjectedStrawberryInfo, password: str, tolerance: int
) -> bool:
    if password != RETOOL_SECRET_BYPASS:
        logging.info("Access Denied")
        raise Exception("Access Denied")
    _db = info.context["db"].sql
    invoices_failed_list = await get_invoices_failed(_db, tolerance)  # type: ignore
    if not invoices_failed_list:
        return True
    return await send_monitor_alert_email(invoices_failed_list)  # type: ignore


async def invoice_monitor_wrapper(password: str, tolerance: int) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=None,
    )
    return await invoice_monitor(info, password, tolerance)


async def main():
    try:
        await db_startup()
        logger.info("Starting monitor to invoices ...")
        password = RETOOL_SECRET_BYPASS
        pargs = parse_args()
        tolerance = pargs.tolerance
        resp = await invoice_monitor_wrapper(password, tolerance)
        if resp:
            logger.info("Finished Starting monitor to invoices")
        else:
            logger.info("Error to monitor to invoices")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
