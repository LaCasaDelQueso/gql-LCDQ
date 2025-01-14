""" Script to add SaaS configuration to Supplier Alima Account.

This script does the following:

1. Fetches `paid_account` record.
2. Depending on account_name, it will generate a new paid_account_config record.


Usage:
    cd projects/gqlapi/
    # python -m gqlapi.scripts.alima_account.create_supplier_alima_config_account --help
"""
import asyncio
import argparse
import json
import logging
from typing import Any, Dict
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
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.create_supplier_alima_config_account", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate SaaS config for a given Supplier Alima Account."
    )
    parser.add_argument(
        "--supplier_business_id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )

    _args = parser.parse_args()
    # return args
    return _args


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def verify_paid_account_config_exists(
    db: Database, paid_account_id: uuid.UUID
) -> bool:
    """Verify Paid account config exists or not."""
    pa_confg = await db.fetch_one(
        """
        SELECT paid_account_id FROM paid_account_config
        WHERE paid_account_id = :paid_account_id
        """,
        {"paid_account_id": paid_account_id},
    )
    if not pa_confg:
        return False
    return True


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def generate_config_data(
    paid_account_name: str,
) -> Dict[str, Any]:
    # account name validation
    if paid_account_name.lower() not in ["alima_comercial", "alima_pro"]:
        raise Exception(
            f"Invalid account name: {paid_account_name}. Only `alima_commercial` and `alima_pro` are supported."
        )
    template_sections = [
        # Home
        {
            "section_id": "0",
            "section_name": "",
            "subsections": [
                {
                    "subsection_id": "0.1",
                    "subsection_name": "Home",
                    "available": True,
                    "plugins": [],
                }
            ],
        },
        # Clientes
        {
            "section_id": "1",
            "section_name": "Clientes",
            "subsections": [
                {
                    "subsection_id": "1.1",
                    "subsection_name": "Clientes",
                    "available": True,
                    "plugins": [],
                }
            ],
        },
        # Pedidos
        {
            "section_id": "2",
            "section_name": "Pedidos",
            "subsections": [
                {
                    "subsection_id": "2.1",
                    "subsection_name": "Catálogo",
                    "available": True,
                    "plugins": [],
                },
                {
                    "subsection_id": "2.2",
                    "subsection_name": "Pedidos",
                    "available": True,
                    "plugins": [],
                },
                {
                    "subsection_id": "2.3",
                    "subsection_name": "Facturas",
                    "available": True
                    if paid_account_name.lower() == "alima_pro"
                    else False,
                    "plugins": [],
                },
            ],
        },
        # Pagos
        {
            "section_id": "3",
            "section_name": "Pagos",
            "subsections": [
                {
                    "subsection_id": "3.1",
                    "subsection_name": "Pagos",
                    "available": True
                    if paid_account_name.lower() == "alima_pro"
                    else False,
                    "plugins": [],
                }
            ],
        },
        # Reports
        {
            "section_id": "4",
            "section_name": "Reportes",
            "subsections": [
                {
                    "subsection_id": "4.1",
                    "subsection_name": "Reportes",
                    "available": True,
                    "plugins": [],
                }
            ],
        },
        # E-commerce B2B
        {
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
        },
    ]
    return {
        "sections": template_sections,
    }


async def create_paid_account_config(
    db: Database,
    paid_account_id: uuid.UUID,
    config: Dict[str, Any],
) -> bool:
    """Create a paid account config record.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    config : Dict[str, Any]

    Returns
    -------
    uuid.UUID
    """
    # create paid account config
    try:
        await db.execute(
            """
            INSERT INTO paid_account_config (paid_account_id, config)
            VALUES (:paid_account_id, :config)
            """,
            {
                "paid_account_id": paid_account_id,
                "config": json.dumps(config),
            },
        )
        logging.info("Created paid account config!")
        return True
    except Exception as e:
        logging.error("Error creating paid account config")
        logging.error(e)
        return False


async def get_alima_bot(info: InjectedStrawberryInfo) -> uuid.UUID:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.fetch_by_email("admin")
    if not tmp or not tmp.id:
        raise Exception("Error getting Alima admin bot user")
    admin_user = tmp.id
    return admin_user


# ---------------------------------------------------------------------
# Create config for alima account
# ---------------------------------------------------------------------


async def create_alima_account_config(supplier_business_id: uuid.UUID) -> bool:
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
        logging.warning(
            f"Paid account for Supplier Business with id ({supplier_business_id}) not found"
        )
        return False
    # verify if the config already exists
    pa_config_exists = await verify_paid_account_config_exists(_db, paid_acount.id)
    if pa_config_exists:
        logging.warning(
            f"Paid account config already Exists for Supplier Business with id ({supplier_business_id}) already exists"
        )
        return False
    # create config
    config_data = await generate_config_data(paid_acount.account_name)
    if not await create_paid_account_config(_db, paid_acount.id, config_data):
        logging.warning(
            f"Paid account config not created for Supplier Business with id ({supplier_business_id})"
        )
        return False
    # show results
    logging.info("Finished creating Alima Account SaaS Config")
    logging.info("\n".join(["-----", f"Supplier Business ID: {supplier_business_id}"]))
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(
        f"Started creating Saas Config for Alima Account: {args.supplier_business_id}"
    )
    try:
        fl = await create_alima_account_config(
            uuid.UUID(args.supplier_business_id),
        )
        if not fl:
            logging.info(
                f"Supplier Business with id ({args.supplier_business_id}) not able to be created"
            )
            return
        logging.info(
            f"Finished creating Saas config for Alima account successfully: {args.supplier_business_id}"
        )
    except Exception as e:
        logging.error(
            f"Error creating Saas config for Alima account: {args.supplier_business_id}"
        )
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
