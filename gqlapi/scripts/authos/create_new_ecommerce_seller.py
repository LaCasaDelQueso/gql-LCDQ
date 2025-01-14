""" Script to Create new Ecommerce Seller in the Authos service

    How to run:
    poetry run python -m gqlapi.scripts.authos.create_new_ecommerce_seller --help
    # poetry run python -m gqlapi.scripts.authos.create_new_ecommerce_seller --seller-name {name} --supplier-business-id {id}
"""

import argparse
import asyncio
from datetime import datetime
import logging
from uuid import UUID, uuid4
import secrets
from bson import Binary
from databases import Database
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.db import (
    db_shutdown,
    db_startup,
    authos_database as AuthosSQLDatabase,
    database as SQLDatabase,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from motor.motor_asyncio import AsyncIOMotorClient
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(
    "scripts.create_new_ecommerce_seller ", logging.INFO, Environment(get_env())
)

creation_queries = [
    """
    CREATE TABLE IF NOT EXISTS ecommerce_user_{esecret_key} (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        first_name varchar NOT NULL,
        last_name varchar NOT NULL,
        email varchar(255) NOT NULL,
        phone_number varchar(255),
        password varchar(255) NOT NULL,
        disabled boolean DEFAULT 'f' NOT NULL,
        created_at timestamp NOT NULL DEFAULT NOW(),
        last_updated timestamp NOT NULL DEFAULT NOW()
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS user_session_{esecret_key} (
        session_token text PRIMARY KEY NOT NULL,
        ecommerce_user_id uuid references ecommerce_user_{esecret_key} (id),
        session_data json,
        expiration timestamp NOT NULL,
        created_at timestamp DEFAULT NOW() NOT NULL,
        last_updated timestamp DEFAULT NOW() NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS pwd_restore_{esecret_key} (
        restore_token text PRIMARY KEY NOT NULL,
        ecommerce_user_id uuid REFERENCES ecommerce_user_{esecret_key} (id),
        expiration timestamp NOT NULL
    );
    """,
]


async def _ecomm_seller_exists(adb: Database, supplier_business_id: UUID) -> bool:
    # check if seller already exists
    qry = """
        SELECT id FROM ecommerce_seller WHERE supplier_business_id = :id
        """
    try:
        resp = await adb.fetch_one(qry, {"id": supplier_business_id})
        if resp:
            return True
    except Exception as e:
        logger.error(e)
        logger.info("Error to query ecommerce_seller table")
        raise e
    return False


def _generate_secret_key() -> str:
    # create a truly random string of 8 characters
    return secrets.token_urlsafe(8).replace("-", "").lower()


async def _add_ecomm_seller(
    adb: Database, seller_name: str, supplier_business_id: UUID
) -> str:
    qry = """
        INSERT INTO ecommerce_seller (id, seller_name, secret_key, supplier_business_id, created_at, last_updated)
        VALUES (:id, :seller_name, :secret_key, :supplier_business_id, :created_at, :last_updated)
        """
    _id = uuid4()
    _secret = _generate_secret_key()
    try:
        await adb.execute(
            qry,
            {
                "id": _id,
                "seller_name": seller_name,
                "supplier_business_id": supplier_business_id,
                "secret_key": _secret,
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
            },
        )
    except Exception as e:
        logger.error(e)
        logger.info("Error to insert ecommerce_seller table")
        raise e
    return _secret


async def set_display_marketplace(
    mongo_db: AsyncIOMotorClient,  # type: ignore
    supplier_business_id: UUID,
    display_marketplace: bool,
) -> bool:
    """Set display in marketplace flag for the supplier business"""
    try:
        # update mongo collection
        collection = mongo_db.supplier_business_account
        await collection.update_one(
            {"supplier_business_id": Binary.from_uuid(supplier_business_id)},
            {
                "$set": {
                    "displays_in_marketplace": display_marketplace,
                    "last_updated": datetime.utcnow(),
                }
            },
        )
        return True
    except Exception as e:
        logger.error(e)
        logger.error("Error to set display in marketplace flag")
        return False


async def create_new_ecomm_seller(
    info: InjectedStrawberryInfo,
    seller_name: str,
    supplier_business_id: UUID,
    display_marketplace: bool = False,
) -> bool:
    if not info.context["db"].authos:
        logger.warning("Authos DB not connected!")
        return False

    # check if seller already exists
    if await _ecomm_seller_exists(info.context["db"].authos, supplier_business_id):
        logger.warning(
            "Ecommerce Seller with given Supplier Business ID already exists!"
        )
        return False
    # create one if not
    _secrt = await _add_ecomm_seller(
        info.context["db"].authos, seller_name, supplier_business_id
    )
    # create respective tables
    for _q in creation_queries:
        await info.context["db"].authos.execute(_q.format(esecret_key=_secrt))
    # log
    logger.info("Ecommerce Seller created successfully!")
    logger.info(f"Seller Name: {seller_name}")
    logger.info(f"Supplier Business ID: {supplier_business_id}")
    logger.info(f"Secret Key: {_secrt}")
    # display in marketplace
    if display_marketplace:
        return await set_display_marketplace(
            info.context["db"].mongo, supplier_business_id, display_marketplace  # type: ignore (safe)
        )
    return True


async def create_new_ecomm_seller_wrapper(
    seller_name: str, supplier_business_id: UUID, display_marketplace: bool = False
) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
        authos=AuthosSQLDatabase,
    )
    return await create_new_ecomm_seller(
        info, seller_name, supplier_business_id, display_marketplace
    )


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create new Ecommerce Seller in the Authos service"
    )
    parser.add_argument(
        "--seller-name",
        help="Seller Name",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--supplier-business-id",
        help="Supplier Business ID",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--display-marketplace",
        help="Display in Marketplace",
        action="store_true",
        default=False,
        required=False,
    )
    return parser.parse_args()


async def main():
    try:
        pargs = parse_args()
        # connect to DB
        await db_startup()
        logger.info(
            "Starting script to insert new Ecommerce Seller in the Authos service"
        )

        resp = await create_new_ecomm_seller_wrapper(
            pargs.seller_name,
            UUID(pargs.supplier_business_id),
            pargs.display_marketplace,
        )
        if resp:
            logger.info(
                "Finished script to insert new Ecommerce Seller in the Authos service"
            )
        else:
            logger.info("Error to inserting new Ecommerce Seller in the Authos service")
        await db_shutdown()
    except Exception as e:
        logger.error(e)
        logger.info("Error to inserting new Ecommerce Seller in the Authos service")


if __name__ == "__main__":
    logger.info("Create new Ecommerce Seller in the Authos service")
    asyncio.run(main())
