""" Migrate Alima Billing Payment Methods.

    This script is used to migrate billing payment methods for Alima accounts.

Usage:
    cd projects/gqlapi/
    # python -m gqlapi.scripts.alima_account.migrate_alima_billing_paymethods --help
"""

import asyncio
import argparse
import logging
import uuid
from databases import Database
import pandas as pd

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.models.v2.utils import (
    PayMethodType,
    PayProviderType,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.migrate_alima_billing_paymethods", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Migrate Alima Billing Accounts")
    parser.add_argument(
        "--migration-file",
        help="CSV File containing Paid Account ID, payment type and payment provider",
        type=str,
        default=None,
        required=True,
    )

    _args = parser.parse_args()
    # return args
    return _args


async def update_billing_payment_method(
    db: Database,
    paid_account_id: uuid.UUID,
    payment_type: PayMethodType,
    payment_provider: PayProviderType,
    payment_provider_id: str = "",
    account_number: str = "",
    account_name: str = "",
    bank_name: str = "",
) -> bool:
    """Update billing payment method.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    payment_type : PayMethodType
    payment_provider : PayProviderType
    payment_provider_id : str
    created_by : uuid.UUID

    Returns
    -------
    uuid.UUID
    """
    # update billing payment method
    try:
        await db.execute(
            """
            UPDATE billing_payment_method
                SET payment_provider_id = :payment_provider_id,
                    payment_type = :payment_type,
                    payment_provider = :payment_provider,
                    account_number = :account_number,
                    account_name = :account_name,
                    bank_name = :bank_name
                WHERE paid_account_id = :paid_account_id
            """,
            {
                "paid_account_id": paid_account_id,
                "payment_type": payment_type.value,
                "payment_provider": payment_provider.value,
                "payment_provider_id": payment_provider_id,
                "account_number": account_number,
                "account_name": account_name,
                "bank_name": bank_name,
            },
        )
        logging.info(f"Updated Billing Payment Method: {payment_type.value}")
        return True
    except Exception as e:
        logging.error(e)
        logging.error("Error to update billing payment method")
        return False


# ---------------------------------------------------------------------
# Update billing methods
# ---------------------------------------------------------------------


async def migrate_billing_accounts(
    migration_file: str,
) -> bool:
    """Migrate billing accounts.

    Parameters
    ----------
    migration_file : str

    Returns
    -------
    bool

    Raises
    ------
    Exception
    """
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    # read file and parse data
    df = pd.read_csv(migration_file, dtype=str)
    # valdiate columns
    needed_cols = [
        "business",
        "paid_account_id",
        "pay_method",
        "stripe_customer_id",
        "clabe",
    ]
    if not all([_c in df.columns for _c in needed_cols]):
        raise Exception(
            "Invalid columns in migration file, missing: business, paid_account_id, pay_method, stripe_customer_id, clabe"
        )
    # verify data, first pay_method needs to be one of the PayProviderType values
    payprov_members = [pp.value for pp in PayProviderType.__members__.values()]
    if not all([_p in payprov_members for _p in df["pay_method"].tolist()]):
        raise Exception("Invalid pay_method values in migration file")
    df["clabe"] = df["clabe"].apply(lambda x: str(x) if not pd.isnull(x) else "")
    df["stripe_customer_id"] = df["stripe_customer_id"].fillna("")
    # iterate over all records
    for _idx, row in df.iterrows():
        logging.info(f"Processing row: {_idx}, Business: {row['business']}")
        # get data
        paid_account_id = uuid.UUID(row["paid_account_id"])
        pay_provider = PayProviderType(row["pay_method"])
        pay_method = (
            PayMethodType.CARD
            if pay_provider == PayProviderType.CARD_STRIPE
            else PayMethodType.TRANSFER
        )
        stripe_customer_id = (
            row["stripe_customer_id"] if row["stripe_customer_id"] else ""
        )
        account_number = row["clabe"]
        if pay_provider == PayProviderType.TRANSFER_BBVA:
            account_number = "012180001182328575"
        bank_name = {
            PayProviderType.CARD_STRIPE: "",
            PayProviderType.TRANSFER_BBVA: "BBVA",
            PayProviderType.TRANSFER_STRIPE: "BANAMEX",
        }[pay_provider]
        account_name = {
            PayProviderType.CARD_STRIPE: "",
            PayProviderType.TRANSFER_BBVA: "SERVICIOS DE DISTRIBUCION DE PERECEDEROS NEUTRO",
            PayProviderType.TRANSFER_STRIPE: "",
        }[pay_provider]
        # update payment methods
        paym_flag = await update_billing_payment_method(
            _db,
            paid_account_id,
            pay_method,
            pay_provider,
            stripe_customer_id,
            account_number,
            account_name,
            bank_name,
        )
        if not paym_flag:
            logging.error(
                f"Error updating billing payment method for: {row['business']}"
            )
            return False
        logging.info(
            f"Updated billing payment method for: {row['business']}: {pay_provider}"
        )
    # show results
    logging.info("Finished migration of billing accounts")
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(f"Started migrariont Alima billing Accounts: {args.migration_file}")
    try:
        fl = await migrate_billing_accounts(
            args.migration_file,
        )
        if not fl:
            logging.info(
                f"Migration for Alima billing accounts failed: {args.migration_file}"
            )
            return
        logging.info(
            f"Finished migration for Alima billing accounts: {args.migration_file}"
        )
    except Exception as e:
        logging.error(f"Error creating Alima billing accounts: {args.migration_file}")
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
