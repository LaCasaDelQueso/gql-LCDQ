"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.monitor.script_execution
"""

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

pd.options.mode.chained_assignment = None  # type: ignore
logger = get_logger(
    "scripts.monitor.invoice_execution", logging.INFO, Environment(get_env())
)


async def get_scripts_failed(db: Database) -> List:
    scripts_failed = await db.fetch_all(
        """SELECT * FROM script_execution
            WHERE created_at > (NOW() -  interval '24 hours')
            and status IN ('error', 'running')"""
    )
    scripts_failed_list = []
    for sf in scripts_failed:
        sf_obj = dict(sf)
        if sf_obj["script_name"] == "script_monitor" and sf_obj["status"] == "running":
            continue
        scripts_failed_list.append(sf_obj)
    return scripts_failed_list


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


async def send_scripts_alert_email(invoices_failed_list: List[Dict[Any, Any]]) -> bool:
    df = pd.DataFrame(invoices_failed_list)
    html_table = df.to_html(index=False)
    return True


async def scripts_monitor(info: InjectedStrawberryInfo, password: str) -> bool:
    if password != RETOOL_SECRET_BYPASS:
        logging.info("Access Denied")
        raise Exception("Access Denied")
    _db = info.context["db"].sql
    scripts_failed_list = await get_scripts_failed(_db)  # type: ignore
    if not scripts_failed_list:
        return True
    return await send_scripts_alert_email(scripts_failed_list)  # type: ignore


async def scripts_monitor_wrapper(password: str) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=None,
    )
    return await scripts_monitor(info, password)


async def main():
    try:
        await db_startup()
        logger.info("Starting monitor to scripts ...")
        password = RETOOL_SECRET_BYPASS
        resp = await scripts_monitor_wrapper(password)
        if resp:
            logger.info("Finished Starting monitor to scripts")
        else:
            logger.info("Error to monitor to scripts")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
