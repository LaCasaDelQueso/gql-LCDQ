"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.billing.send_reminder_alima_billing"""
import argparse
import asyncio
import datetime
from datetime import timedelta
import logging
from typing import Any, Dict, List
from gqlapi.handlers.services.mails import (
    send_account_inactive,
    send_account_inactive_notification,
    send_alima_invoice_pending_notification,
)
from gqlapi.utils.automation import InjectedStrawberryInfo

import pandas as pd
from databases import Database
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase

from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.mongo import mongo_db as MongoDatabase


pd.options.mode.chained_assignment = None  # type: ignore


async def get_alima_billing(
    _db: Database,
) -> List[Dict[Any, Any]]:
    try:
        alima_billing_invoices = await _db.fetch_all(
            """
        SELECT
            bi.id as id,
            sb.name as name,
            bi.invoice_month as fecha,
            bi.invoice_number as folio,
            CONCAT(bi.total::text, ' ',bi.currency) as total,
            bi.status,

            bip.status as status_pago,
            sb.id supplier_business_id,
            bi.created_at created_at
        FROM billing_invoice bi
        JOIN billing_invoice_paystatus bip
            ON bi.id = bip.billing_invoice_id
        JOIN paid_account pa
            ON pa.id = bi.paid_account_id
        JOIN supplier_business sb
            ON sb.id = pa.customer_business_id
        WHERE bip.status = 'unpaid' AND bi.status = 'active'
        """
        )

        if not alima_billing_invoices:
            return []
        return [dict(r) for r in alima_billing_invoices]  # type: ignore
    except Exception as e:
        logging.error(e)
        raise Exception("Error to get alima invoices")


async def send_email_to_reminders(
    al_hist_invs: List[Dict[Any, Any]],
    info: InjectedStrawberryInfo,
):
    supplier_business_repo = SupplierBusinessRepository(info=info)  # type: ignore
    _supp_handler = SupplierBusinessHandler(
        supplier_business_repo=supplier_business_repo,  # type: ignore
        supplier_business_account_repo=SupplierBusinessAccountRepository(info=info),  # type: ignore
    )
    today: datetime.date = datetime.datetime.utcnow().date()
    for inv in al_hist_invs:
        created_at = inv.get("created_at").date()  # type: ignore
        # Map Dict
        if created_at == today - timedelta(days=5):
            pay_date: int = 5
        else:
            if created_at == today - timedelta(days=7):
                pay_date: int = 7
            else:
                if created_at == today - timedelta(days=10):
                    pay_date: int = 10
                else:
                    if created_at == today - timedelta(days=15):
                        pay_date: int = 15
                    else:
                        if created_at == today - timedelta(days=20):
                            pay_date: int = 20
                        else:
                            continue

        supplier_business_account = await _supp_handler.account_repository.fetch(
            supplier_business_id=inv.get("supplier_business_id")  # type: ignore
        )
        if not supplier_business_account:
            continue
        name = inv.get("name", None)
        date = inv.get("fecha", None)
        if pay_date == 10 or pay_date == 7 or pay_date == 5:
            if not await send_alima_invoice_pending_notification(
                email_to=supplier_business_account["email"],
                name=inv.get("name", None),
                tolerance=10 - pay_date,
                month=date,
            ):
                logging.error(f"error send email to {name}")
            continue
        if pay_date == 15:
            if not await send_account_inactive_notification(
                email_to=supplier_business_account["email"],
                name=inv.get("name", None),
                tolerance=20 - pay_date,
                month=date,
            ):
                logging.error(f"error send email to {name}")
            continue
        if pay_date == 20:
            if not await send_account_inactive(
                email_to=supplier_business_account["email"], name=name, month=date
            ):
                logging.error(f"error send email to {name}")
            if not await supplier_business_repo.edit(
                id=inv.get("supplier_business_id", None), active=True
            ):
                raise Exception("Error al desactivar la cuenta")
            continue


async def send_reminders(info: InjectedStrawberryInfo) -> bool:
    logging.info("Starting send reminders ...")
    logging.info("Get_billing info...")
    _db = info.context["db"].sql
    billings = await get_alima_billing(_db)  # type: ignore
    if not billings:
        logging.info("There are no billing to pay")
        return True
    await send_email_to_reminders(al_hist_invs=billings, info=info)
    return True


async def send_reminders_wrapper() -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    # Permite conectar a la db
    _resp = await send_reminders(_info)
    return _resp


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Send reminders to pay Alima Invoice.")
    return parser.parse_args()


async def main():
    try:
        logging.info("Starting routine to send reminders to pay Alima Invoice. ...")
        await db_startup()
        resp = await send_reminders_wrapper()
        if resp:
            logging.info("Finished routine send reminders to pay Alima Invoice.")
        else:
            logging.info("Error to send reminders to pay Alima Invoice.")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
