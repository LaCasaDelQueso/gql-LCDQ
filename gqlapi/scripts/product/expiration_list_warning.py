"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.product.expiration_list_warning --date {date}"""


import argparse
import asyncio
import datetime
import logging
from typing import Any, Dict, List, Optional
from bson import Binary
from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.handlers.services.mails import send_notification_price_list_expiration
from gqlapi.repository import CoreMongoBypassRepository
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository

from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.utils.automation import InjectedStrawberryInfo

from databases import Database
import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore


async def get_price_list_expiration(
    expiration_date: datetime.date, db: Database  # type: ignore
) -> List[Dict[Any, Any]]:
    expiration_price_list = await db.fetch_all(
        """
        with concat_table as (
        SELECT
            spl.name as name,
            spl.valid_upto as valid_upto,
            spl.supplier_unit_id as supplier_unit_id,
            spl.created_at as created_at,
            su.supplier_business_id as supplier_business_id,
            su.unit_name as unit_name,
            CONCAT (spl.supplier_unit_id, spl.name) as concat_name
            FROM supplier_price_list spl JOIN supplier_unit su ON spl.supplier_unit_id = su.id
            JOIN supplier_business sb ON su.supplier_business_id = sb.id
            WHERE sb.active = TRUE
        ),
        distinct_name as (
        SELECT
            DISTINCT ON (concat_name) concat_name,
            valid_upto,
            supplier_unit_id,
            supplier_business_id,
            unit_name,
            name,
            created_at
        FROM concat_table
        ORDER BY concat_name, created_at DESC)

        SELECT * FROM distinct_name
        WHERE valid_upto = :expiration_date
        """,
        {"expiration_date": expiration_date},
    )

    if not expiration_price_list:
        return []
    return [dict(r) for r in expiration_price_list]  # type: ignore


async def send_notification(
    expiration_price_list: List[Dict[Any, Any]],
    info: InjectedStrawberryInfo,
):
    supplier_business_repo = SupplierBusinessRepository(info=info)  # type: ignore
    mongo_bypass = CoreMongoBypassRepository(mongo_db=MongoDatabase)  # type: ignore

    for epl in expiration_price_list:
        supplier_business = SupplierBusiness(
            **await supplier_business_repo.fetch(epl["supplier_business_id"])
        )
        supplier_business_account = await mongo_bypass.fetch(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            query={"supplier_business_id": Binary.from_uuid(supplier_business.id)},
        )
        content = ""
        for name, unit_name in zip(epl["name"], epl["unit_name"]):
            content = content + name + " - (" + unit_name + ")\n"
        await send_notification_price_list_expiration(
            email_to=supplier_business_account["email"],
            name=supplier_business.name,
            price_list=content,
        )


async def send_warning(info: InjectedStrawberryInfo, date: str, tolerance: Optional[int] = 1) -> bool:  # type: ignore
    logging.info("Starting send warning ...")
    # Permite conectar a la db

    _db = info.context["db"].sql
    _mongo = info.context["db"].mongo

    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    if not tolerance:
        tolerance = 1
    date_object = datetime.datetime.strptime(
        date, "%Y-%m-%d"
    ).date() + datetime.timedelta(days=tolerance)
    logging.info("Get_expiration price list...")
    expiration_price_list = await get_price_list_expiration(date_object, _db)
    if not expiration_price_list:
        logging.info("There are no price lists that expire on that date")
        return True
    expiration_price_list_df = pd.DataFrame(expiration_price_list)

    grouped_df = (
        expiration_price_list_df.groupby("supplier_business_id")
        .agg({"name": list, "unit_name": list})
        .reset_index()
    )
    grouped_expiration_price_list = grouped_df.to_dict(orient="records")

    await send_notification(grouped_expiration_price_list, info=info)

    return True


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Reset user account.")
    parser.add_argument(
        "--date",
        help="1 Day before Expiration_date (AAAA-MM_DD)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--tolerance",
        help="Days before Expiration_date (AAAA-MM_DD)",
        type=int,
        default=1,
        required=False,
    )
    return parser.parse_args()


async def send_warning_warapper(date: str, tolerance: Optional[int] = 1) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    # Permite conectar a la db
    _resp = await send_warning(_info, date, tolerance)
    return _resp


async def main():
    try:
        pargs = parse_args()
        await db_startup()
        logging.info("Starting routine to suppliers Pricen List expiration warning ...")

        resp = await send_warning_warapper(pargs.date, pargs.tolerance)
        if resp:
            logging.info("Finished routine suppliers Pricen List expiration warning")
        else:
            logging.info("Error to update orders")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
