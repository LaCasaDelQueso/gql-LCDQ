""" Script to Update Paid Account Config To Unblock Ecommerce B2b

    How to run:
    poetry run python -m gqlapi.scripts.update_paid_config_to_add_ecommerce --help
    # poetry run python -m gqlapi.scripts.authos.update_paid_config_to_add_ecommerce
"""

import asyncio
import json
import logging
from typing import List
from databases import Database
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.db import (
    db_shutdown,
    db_startup,
    authos_database as AuthosSQLDatabase,
    database as SQLDatabase,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger


logger = get_logger(
    "scripts.create_new_ecommerce_seller ", logging.INFO, Environment(get_env())
)


async def get_paid_account_config(db: Database) -> List:
    paid_account_config = await db.fetch_all("SELECT * FROM paid_account_config")
    paid_account_config_list = []
    for pac in paid_account_config:
        pac_obj = dict(pac)
        paid_account_config_list.append(pac_obj)
    return paid_account_config_list


async def update_paid_account_to_add_ecommerce(info: InjectedStrawberryInfo) -> bool:
    _db = info.context["db"].sql
    if not _db:
        logger.error("No database connection")
        return False
    pac_list = await get_paid_account_config(_db)  # type: ignore
    for pac in pac_list:
        config_json = json.loads(pac["config"])
        ecommerce_section = {
            "section_id": "5",
            "section_name": "E-commerce B2B",
            "subsections": [
                {
                    "subsection_id": "5.1",
                    "subsection_name": "E-commerce B2B",
                    "available": True,
                    "plugins": [],
                }
            ],
        }
        config_json["sections"].append(ecommerce_section)
        config_string = json.dumps(config_json)
        try:
            await _db.execute(
                """
                UPDATE paid_account_config
                SET config = :config
                WHERE paid_account_id = :paid_account_id
                """,
                {"paid_account_id": pac["paid_account_id"], "config": config_string},
            )
        except Exception as e:
            logger.error(e)
    return True


async def update_paid_account_to_add_ecommerce_wrapper() -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
        authos=AuthosSQLDatabase,
    )
    return await update_paid_account_to_add_ecommerce(info)


async def main():
    try:
        # connect to DB
        await db_startup()
        logger.info("Starting script to update paid account to add ecommerce")
        resp = await update_paid_account_to_add_ecommerce_wrapper()
        if resp:
            logger.info("Finished script to to update paid account to add ecommerce")
        else:
            logger.info("Error to to update paid account to add ecommerce")
        await db_shutdown()
    except Exception as e:
        logger.error(e)
        logger.info("Error to to update paid account to add ecommerce")


if __name__ == "__main__":
    logger.info("Edit update paid account to add ecommerce")
    asyncio.run(main())
