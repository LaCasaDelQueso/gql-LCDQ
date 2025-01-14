"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.orden.convert_orden_confirm --date {date}"""


import argparse
import asyncio
from datetime import datetime
import logging
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.repository import CoreDataOrchestationRepository
from gqlapi.utils.automation import InjectedStrawberryInfo

import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore


query = """UPDATE orden_status
SET status='delivered'
WHERE orden_id in
(SELECT
    od.orden_id
    FROM orden_details od
    JOIN orden_status os
    ON od.orden_id = os.orden_id
    WHERE os.status = 'accepted'
    AND od.delivery_date = :delivery_date)"""


async def change_orden_to_confirm(date: datetime.date) -> bool:  # type: ignore
    orden_repo = CoreDataOrchestationRepository(sql_db=SQLDatabase)
    core_values = {"delivery_date": date}
    return await orden_repo.edit(
        core_element_name="Orden Satus", core_query=query, core_values=core_values
    )


async def confirm_orden_status(info: InjectedStrawberryInfo, date: str) -> bool:
    date_object = datetime.strptime(date, "%Y-%m-%d").date()
    logging.info("Starting change orden status...")
    change_status = await change_orden_to_confirm(date_object)
    return change_status


async def confirm_orden_status_wrapper(date: str) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=None,
    )
    return await confirm_orden_status(info, date)


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Reset user account.")
    parser.add_argument(
        "--date",
        help="Delivery_date (AAAA-MM_DD)",
        type=str,
        default=None,
        required=True,
    )
    return parser.parse_args()


async def main():
    try:
        pargs = parse_args()
        # Permite conectar a la db
        await db_startup()
        logging.info(
            "Starting routine to convert ordenes from confirmed to delivered ..."
        )

        resp = await confirm_orden_status_wrapper(pargs.date)
        if resp:
            logging.info(
                "Finished routine to convert ordenes from confirmed to delivered!"
            )
        else:
            logging.info("Error to update orders")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
