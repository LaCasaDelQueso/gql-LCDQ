""" Script to Create a Supplier Invoice given its defined charges.

This script does the following:

1. Computes the total amount due for the invoice based on the charges and arguments.
2. Creates a record in the `billing_invoice` table.
3. Creates a record in the `billing_invoice_charge` table for each charge.
4. Creates a record in the `billing_invoice_paystatus` table with status `unpaid`.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.billing.create_daily_alima_invoice_v3
"""

import asyncio
from datetime import datetime, timezone
import itertools
import uuid
from gqlapi.utils.notifications import format_email_table
import pandas as pd

from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.config import (
    RETOOL_SECRET_BYPASS,
)
from gqlapi.handlers.services.mails import (
    send_reports_alert,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.domain.models.v2.utils import (
    PayProviderType,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, authos_database as AuthosDatabase, db_shutdown, db_startup
from gqlapi.handlers.alima_account.billing import AlimaBillingRunner
from gqlapi.config import ENV as DEV_ENV

logger = get_logger("scripts.create_daily_alima_invoice_v3")

# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def get_alima_bot(info: InjectedStrawberryInfo) -> uuid.UUID:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.get_by_email("admin")
    admin_user = tmp.id
    if not admin_user:
        raise Exception("Error getting Alima admin bot user")
    return admin_user


# ---------------------------------------------------------------------
# Create supplier billing invoice
# ---------------------------------------------------------------------


async def send_create_supplier_billing_invoices_v3(
    info: InjectedStrawberryInfo, password: str
) -> bool:
    logger.info("Starting send daily alima invoice v3 ...")
    current_date = datetime.now(timezone.utc).replace(tzinfo=None)
    # Authorization validation
    if password != RETOOL_SECRET_BYPASS:
        logger.info("Access Denied")
        raise Exception("Access Denied")
    # initialization
    logger.info("Initializing Alima Billing Runner handler...")
    payproviders = [PayProviderType.CARD_STRIPE, PayProviderType.TRANSFER_STRIPE]
    # bill_periods = ["monthly", "annual"]
    bill_periods = ["monthly"]
    runner = AlimaBillingRunner(
        info=info,  # type: ignore
        plans={
            "alima_comercial",
            "alima_pro",
            "alima_comercial_anual",
            "alima_pro_anual",
        },
        pay_providers=set(payproviders),
    )
    # generate permutations of payproviders and ['annual', 'monthly] with functools
    billing_tasks_params = list(itertools.product(bill_periods, payproviders))
    # run billing invoicing routines in paralell
    billing_reports = await asyncio.gather(
        *[
            runner.run_billing_routine(
                pay_provider=pay_provider,
                billing_period="monthly" if billing_period == "monthly" else "annual",
                current_date=current_date,
            )
            for billing_period, pay_provider in billing_tasks_params
        ]
    )
    # send execution report
    rep_list_dicts = []
    for rlist, prms in zip(billing_reports, billing_tasks_params):
        for r in rlist:
            logger.info(f"Report for: {prms}")
            rdict = {"Periodo": prms[0], "PayProvider": str(prms[1])}
            rdict.update(r.__dict__)
            rep_list_dicts.append(rdict)
    if len(rep_list_dicts) > 0:
        df = pd.DataFrame(rep_list_dicts).sort_values(by=["Periodo", "PayProvider"])
        print()
        print(df, "\n\n")
        html_table = format_email_table(
            df.to_html(index=False, classes="table table-bordered table-striped ")
        )
    return True


async def send_create_alima_invoices_v3_wrapper(password: str) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase, AuthosDatabase)
    # Permite conectar a la db
    _resp = await send_create_supplier_billing_invoices_v3(_info, password)
    return _resp


async def main():
    try:
        logger.info("Started creating Daily Supplier Billing Invoice (V3)")
        await db_startup()
        password = RETOOL_SECRET_BYPASS
        fl = await send_create_alima_invoices_v3_wrapper(password)
        if fl:
            logger.info("Finished creating Daily Supplier Billing Invoice (V3)")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
