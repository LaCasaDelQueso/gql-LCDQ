""" Script to Disable and Re-enable Supplier Alima Account.

Usage:
    cd projects/gqlapi/
    # python -m gqlapi.scripts.alima_account.enable_disable_alima_account --help
"""

import asyncio
import argparse
import logging
from typing import Literal
import uuid

from gqlapi.handlers.alima_account.account import AlimaAccountHandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.b2bcommerce.ecommerce_seller import EcommerceSellerRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import (
    database as SQLDatabase,
    authos_database as AuthosDatabase,
    db_shutdown,
    db_startup,
)


logger = get_logger(
    "scripts.enable_disable_alima_account", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Enable/Disable Supplier Alima Account."
    )
    parser.add_argument(
        "--supplier_business_id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--action_type",
        help="Action. Options: (reenable, disable)",
        type=str,
        choices=["disable", "reenable"],
        default=None,
        required=True,
    )

    _args = parser.parse_args()
    # return args
    return _args


async def reenable_disable_alima_account(
    info: InjectedStrawberryInfo,
    supplier_business_id: uuid.UUID,
    action: Literal["reenable", "disable"],
) -> bool:
    """Disable / Enable Alima Account.

    Parameters
    ----------
    info: StrawberryInfo
    supplier_business_id : uuid.UUID
    action: Literal['reenable', 'disable']

    Returns
    -------
    bool
    """
    _handler = AlimaAccountHandler(
        AlimaAccountRepository(info),  # type: ignore
        CoreUserRepository(info),  # type: ignore
        SupplierBusinessRepository(info),  # type: ignore
        SupplierBusinessAccountRepository(info),  # type: ignore
        SupplierUserRepository(info),  # type: ignore
        SupplierUserPermissionRepository(info),  # type: ignore
        ecommerce_seller_repository=EcommerceSellerRepository(info),  # type: ignore
    )
    if action == "disable":
        return await _handler.disable_alima_account(supplier_business_id)
    elif action == "reenable":
        return await _handler.reactivate_alima_account(supplier_business_id)


async def reenable_disable_alima_account_wrapper(
    supplier_business_id: uuid.UUID, action: Literal["reenable", "disable"]
) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase, AuthosDatabase)
    # Permite conectar a la db
    _resp = await reenable_disable_alima_account(_info, supplier_business_id, action)
    return _resp


async def main():
    args = parse_args()
    logging.info(
        f"Started enabling/disabling Supplier Alima Account: {args.supplier_business_id}"
    )
    try:
        await db_startup()
        fl = await reenable_disable_alima_account_wrapper(
            uuid.UUID(args.supplier_business_id), args.action_type
        )
        if not fl:
            logging.info(
                f"Supplier Business with id ({args.supplier_business_id}) not able to be disabled/reenabled "
            )
            return
        logging.info(
            f"Finished creating Alima account successfully: {args.supplier_business_id}"
        )
        await db_shutdown()
    except Exception as e:
        logging.error(
            f"Error creating Supplier Alima account: {args.supplier_business_id}"
        )
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
