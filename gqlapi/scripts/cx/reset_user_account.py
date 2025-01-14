""" Script to initialize the category database.

This script is used to initialize the category database with the
restaurant, and supplier categories.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.cx.reset_user_account --help
    # python -m gqlapi.scripts.cx.reset_user_account --email {email}
"""
import asyncio
import argparse
import logging
from typing import Any, Dict
import uuid
from bson import Binary
from databases import Database
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.lib.logger.logger.basic_logger import get_logger

from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "gqlapi.scripts.reset_user_account", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Reset user account.")
    parser.add_argument(
        "--email",
        help="Email from user to reset account from.",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--force",
        help="Forced mode. Rests user even if it has ordenes.",
        action="store_true",
        default=False,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def fetch_resto_user_info(
    db: Database, core_user_id: uuid.UUID
) -> Dict[str, Any]:
    reply: Dict[str, Any] = {
        "restaurant_user": None,
        "restaurant_business": None,
        "restaurant_branches": [],
        "restaurant_suppliers": [],
        "restaurant_supplier_prods": [],
        "restaurant_ordenes": [],
    }
    # resto user
    restaurant_user = await db.fetch_one(
        "SELECT id FROM restaurant_user WHERE core_user_id = :core_user_id LIMIT 1",
        {"core_user_id": core_user_id},
    )
    if not restaurant_user:
        return reply
    restaurant_user = dict(restaurant_user)
    reply["restaurant_user"] = restaurant_user
    # resto business
    restaurant_business = await db.fetch_one(
        """SELECT restaurant_business_id as id FROM restaurant_user_permission
            WHERE restaurant_user_id = :restaurant_user_id LIMIT 1""",
        {"restaurant_user_id": restaurant_user["id"]},
    )
    if not restaurant_business:
        return reply
    restaurant_business = dict(restaurant_business)
    reply["restaurant_business"] = restaurant_business
    # resto branches
    restaurant_branches = await db.fetch_all(
        "SELECT id FROM restaurant_branch WHERE restaurant_business_id = :restaurant_business_id",
        {"restaurant_business_id": restaurant_business["id"]},
    )
    reply["restaurant_branches"] = [dict(r) for r in restaurant_branches]
    # resto suppliers
    restaurant_suppliers = []
    for branch in restaurant_branches:
        tmp = await db.fetch_all(
            """SELECT supplier_business_id, id FROM restaurant_supplier_relation
                WHERE restaurant_branch_id = :restaurant_branch_id""",
            {"restaurant_branch_id": branch["id"]},
        )
        restaurant_suppliers.extend(tmp)
    reply["restaurant_suppliers"] = [dict(r) for r in restaurant_suppliers]
    # resto supplier prods
    restaurant_supplier_prods = []
    for supplier in restaurant_suppliers:
        tmp = await db.fetch_all(
            "SELECT id FROM supplier_product WHERE supplier_business_id = :supplier_business_id",
            {"supplier_business_id": supplier["supplier_business_id"]},
        )
        restaurant_supplier_prods.extend(tmp)
    reply["restaurant_supplier_prods"] = [dict(r) for r in restaurant_supplier_prods]
    # resto ordenes
    restaurant_ordenes = []
    for branch in restaurant_branches:
        tmp = await db.fetch_all(
            "SELECT orden_id as id FROM orden_details WHERE restaurant_branch_id = :restaurant_branch_id",
            {"restaurant_branch_id": branch["id"]},
        )
        restaurant_ordenes.extend(tmp)
    reply["restaurant_ordenes"] = [dict(r) for r in restaurant_ordenes]
    return reply


async def fetch_supplier_user_info(
    db: Database, core_user_id: uuid.UUID
) -> Dict[str, Any]:
    reply: Dict[str, Any] = {
        "supplier_user": None,
        "supplier_business": None,
        "supplier_units": [],
        "supplier_prods": [],
        "supplier_customers": [],
        "supplier_ordenes": [],
    }
    # supplier user
    supplier_user = await db.fetch_one(
        "SELECT id FROM supplier_user WHERE core_user_id = :core_user_id LIMIT 1",
        {"core_user_id": core_user_id},
    )
    if not supplier_user:
        return reply
    supplier_user = dict(supplier_user)
    reply["supplier_user"] = supplier_user
    # supplier business
    supplier_business = await db.fetch_one(
        "SELECT supplier_business_id as id FROM supplier_user_permission WHERE supplier_user_id = :supplier_user_id LIMIT 1",
        {"supplier_user_id": supplier_user["id"]},
    )
    if not supplier_business:
        return reply
    supplier_business = dict(supplier_business)
    reply["supplier_business"] = supplier_business
    # supplier units
    supplier_units = await db.fetch_all(
        "SELECT id FROM supplier_unit WHERE supplier_business_id = :supplier_business_id",
        {"supplier_business_id": supplier_business["id"]},
    )
    reply["supplier_units"] = [dict(r) for r in supplier_units]
    # supplier prods
    supplier_prods = await db.fetch_all(
        "SELECT id FROM supplier_product WHERE supplier_business_id = :supplier_business_id",
        {"supplier_business_id": supplier_business["id"]},
    )
    reply["supplier_prods"] = [dict(r) for r in supplier_prods]
    # supplier customers
    supplier_customers = []
    for unit in supplier_units:
        tmp = await db.fetch_all(
            "SELECT id FROM supplier_restaurant_relation WHERE supplier_unit_id = :supplier_unit_id",
            {"supplier_unit_id": unit["id"]},
        )
        supplier_customers.extend(tmp)
    reply["supplier_customers"] = [dict(r) for r in supplier_customers]
    # supplier ordenes
    supplier_ordenes = []
    for unit in supplier_units:
        tmp = await db.fetch_all(
            "SELECT orden_id as id FROM orden_details WHERE supplier_unit_id = :supplier_unit_id",
            {"supplier_unit_id": unit["id"]},
        )
        supplier_ordenes.extend(tmp)
    reply["supplier_ordenes"] = [dict(r) for r in supplier_ordenes]
    return reply


async def fetch_all_user_info(db: Database, email: str) -> Dict[str, Any]:
    reply: Dict[str, Any] = {
        "core_user": None,
    }
    # core
    core_user = await db.fetch_one(
        "SELECT id FROM core_user WHERE email = :email LIMIT 1",
        {"email": email},
    )
    if not core_user:
        return reply
    core_user = dict(core_user)
    reply["core_user"] = core_user
    # restaurant
    resto = await fetch_resto_user_info(db, core_user["id"])
    reply.update(resto)
    # supplier
    supplier = await fetch_supplier_user_info(db, core_user["id"])
    reply.update(supplier)
    return reply


# ---------------------------------------------------------------------
# delete functions
# ---------------------------------------------------------------------


async def delete_core_user(db: Database, core_user_id: uuid.UUID):
    await db.execute(
        "DELETE FROM core_user WHERE id = :core_user_id",
        {"core_user_id": core_user_id},
    )


async def delete_restaurant_user(db: Database, restaurant_user_id: uuid.UUID):
    await db.execute(
        "DELETE FROM restaurant_user WHERE id = :restaurant_user_id",
        {"restaurant_user_id": restaurant_user_id},
    )


async def delete_restaurant_business(db: Database, restaurant_business_id: uuid.UUID):
    await db.execute(
        "DELETE FROM restaurant_user_permission WHERE restaurant_business_id = :restaurant_business_id",
        {"restaurant_business_id": restaurant_business_id},
    )
    await db.execute(
        "DELETE FROM restaurant_business WHERE id = :restaurant_business_id",
        {"restaurant_business_id": restaurant_business_id},
    )


async def delete_restaurant_branch(db: Database, restaurant_branch_id: uuid.UUID):
    await db.execute(
        "DELETE FROM restaurant_branch_category WHERE restaurant_branch_id = :restaurant_branch_id",
        {"restaurant_branch_id": restaurant_branch_id},
    )
    await db.execute(
        "DELETE FROM restaurant_branch_mx_invoice_info WHERE branch_id = :restaurant_branch_id",
        {"restaurant_branch_id": restaurant_branch_id},
    )
    await db.execute(
        "DELETE FROM restaurant_branch WHERE id = :restaurant_branch_id",
        {"restaurant_branch_id": restaurant_branch_id},
    )


async def delete_restaurant_supplier_relation(
    db: Database, restaurant_supplier_relation_id: uuid.UUID
):
    await db.execute(
        "DELETE FROM restaurant_supplier_relation WHERE id = :restaurant_supplier_relation_id",
        {"restaurant_supplier_relation_id": restaurant_supplier_relation_id},
    )


async def delete_orden(db: Database, orden_id: uuid.UUID):
    await db.execute(
        "DELETE FROM orden_status WHERE orden_id = :orden_id",
        {"orden_id": orden_id},
    )
    await db.execute(
        "DELETE FROM orden_paystatus WHERE orden_id = :orden_id",
        {"orden_id": orden_id},
    )
    await db.execute(
        "DELETE FROM orden_details WHERE orden_id = :orden_id",
        {"orden_id": orden_id},
    )
    await db.execute(
        "DELETE FROM orden WHERE id = :orden_id",
        {"orden_id": orden_id},
    )


async def delete_restaurant_account(mongo: AsyncIOMotorClient, user_info: Dict[str, Any]):  # type: ignore
    if user_info["restaurant_user"]:
        await mongo.restaurant_business_account.delete_one(
            {"restaurant_user_id": Binary.from_uuid(user_info["restaurant_user"]["id"])}
        )
        await mongo.restaurant_employee_directory.delete_one(
            {"restaurant_user_id": Binary.from_uuid(user_info["restaurant_user"]["id"])}
        )


async def delete_supplier_account(mongo: AsyncIOMotorClient, user_info: Dict[str, Any]):  # type: ignore
    if user_info["supplier_user"]:
        await mongo.supplier_business_account.delete_one(
            {"supplier_user_id": Binary.from_uuid(user_info["supplier_user"]["id"])}
        )
        await mongo.supplier_employee_directory.delete_one(
            {"supplier_user_id": Binary.from_uuid(user_info["supplier_user"]["id"])}
        )


async def delete_all_restaurant_info(db: Database, user_info: Dict[str, Any]):
    if user_info["restaurant_ordenes"]:
        for orden in user_info["restaurant_ordenes"]:
            await delete_orden(db, orden["id"])
    if user_info["restaurant_suppliers"]:
        for supplier in user_info["restaurant_suppliers"]:
            await delete_restaurant_supplier_relation(db, supplier["id"])
    if user_info["restaurant_branches"]:
        for branch in user_info["restaurant_branches"]:
            await delete_restaurant_branch(db, branch["id"])
    if user_info["restaurant_business"]:
        await delete_restaurant_business(db, user_info["restaurant_business"]["id"])
    if user_info["restaurant_user"]:
        await delete_restaurant_user(db, user_info["restaurant_user"]["id"])


async def delete_supplier_restaurant_relation(
    db: Database, supplier_customer_id: uuid.UUID
):
    await db.execute(
        "DELETE FROM supplier_restaurant_relation WHERE id = :id",
        {"id": supplier_customer_id},
    )


async def delete_supplier_unit(db: Database, supplier_unit_id: uuid.UUID):
    await db.execute(
        "DELETE FROM supplier_unit_category WHERE supplier_unit_id = :supplier_unit_id",
        {"supplier_unit_id": supplier_unit_id},
    )
    await db.execute(
        "DELETE FROM supplier_unit WHERE id = :supplier_unit_id",
        {"supplier_unit_id": supplier_unit_id},
    )


async def delete_supplier_business(db: Database, supplier_business_id: uuid.UUID):
    await db.execute(
        "DELETE FROM supplier_user_permission WHERE supplier_business_id = :supplier_business_id",
        {"supplier_business_id": supplier_business_id},
    )
    await db.execute(
        "DELETE FROM supplier_business WHERE id = :supplier_business_id",
        {"supplier_business_id": supplier_business_id},
    )


async def delete_supplier_user(db: Database, supplier_user_id: uuid.UUID):
    await db.execute(
        "DELETE FROM supplier_user WHERE id = :supplier_user_id",
        {"supplier_user_id": supplier_user_id},
    )


async def delete_all_supplier_info(db: Database, user_info: Dict[str, Any]):
    if user_info["supplier_ordenes"]:
        for orden in user_info["supplier_ordenes"]:
            await delete_orden(db, orden["id"])
    if user_info["supplier_customers"]:
        for supplier in user_info["supplier_customers"]:
            await delete_supplier_restaurant_relation(db, supplier["id"])
    if user_info["supplier_units"]:
        for unit in user_info["supplier_units"]:
            await delete_supplier_unit(db, unit["id"])
    if user_info["supplier_business"]:
        await delete_supplier_business(db, user_info["supplier_business"]["id"])
    if user_info["supplier_user"]:
        await delete_supplier_user(db, user_info["supplier_user"]["id"])


# ---------------------------------------------------------------------
# reset user account
# ---------------------------------------------------------------------


async def reset_user_account(email: str, forced: bool = False) -> bool:
    """Reset user account

        Verifies all populated tables for a user and deletes them.

    Parameters
    ----------
    email : str
        _description_
    forced : bool, optional
        _description_, by default False

    Raises
    ------
    Exception
        _description_
    """
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    # get all user information
    user_info = await fetch_all_user_info(_db, email)
    if not user_info["core_user"]:
        logging.info(f"User with email {email} not found")
        return False
    # verify if it has ordenes
    if not forced:
        if user_info["restaurant_ordenes"] or user_info["supplier_ordenes"]:
            logging.info(f"User with email {email} has ordenes, IT CANNOT BE DELETED")
            return False
    # delete restaurant user and related info
    await delete_all_restaurant_info(_db, user_info)
    await delete_restaurant_account(_mongo, user_info)
    # delete supplier user and related info
    await delete_all_supplier_info(_db, user_info)
    await delete_supplier_account(_mongo, user_info)
    # delete core user
    await delete_core_user(_db, user_info["core_user"]["id"])
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(f"Starting reseting account: {args.email}")
    try:
        fl = await reset_user_account(args.email, args.force)
        if not fl:
            logging.info(f"User with email {args.email} not able to be reseted")
            return
        logging.info(f"Finished reseting account: {args.email}")
        logging.info("DO NOT FORGET TO DELETE USER FROM FIREBASE")
    except Exception as e:
        logging.error(f"Error reseting account: {args.email}")
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
