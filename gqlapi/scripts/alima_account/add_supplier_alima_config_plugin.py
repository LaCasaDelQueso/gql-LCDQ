""" Script to add a Plugin to SaaS configuration of Supplier Alima Account.

This script does the following:

1. Fetches `paid_account` record.
2. Depending on the plugin passed, it will prompt data inputs to update a new paid_account_config record.


Usage:
    cd projects/gqlapi/
    # python -m gqlapi.scripts.alima_account.add_supplier_alima_config_plugin --help
"""
import asyncio
import argparse
import json
import logging
from typing import Any, Dict, List
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
        description="Add Plugin to SaaS config for a given Supplier Alima Account."
    )
    parser.add_argument(
        "--supplier_business_id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--subsection_id",
        help="Subsection ID",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--plugin_id",
        help="Plugin ID",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--plugin_name",
        help="Plugin Name",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--plugin_provider",
        help="Plugin Provider",
        type=str,
        choices=["alima_metabase", "alima_module"],
        default=None,
        required=True,
    )
    parser.add_argument(
        "--plugin_provider_ref",
        help="Plugin Provider Reference",
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


async def fetch_paid_account_config(
    db: Database, paid_account_id: uuid.UUID
) -> Dict[str, Any]:
    """Get Paid account config exists or not."""
    pa_confg = await db.fetch_one(
        """
        SELECT * FROM paid_account_config
        WHERE paid_account_id = :paid_account_id
        """,
        {"paid_account_id": paid_account_id},
    )
    if not pa_confg:
        return {}
    return dict(pa_confg)


async def get_params_from_user_input(
    plugin_data: Dict[str, Any],
) -> Dict[str, Any]:
    from pprint import pprint

    end_flag = False
    plugin_data["plugin_params"] = []
    # show params and ask if requires params
    while not end_flag:
        print("-----")
        print("Plugin Params:")
        print("-----")
        pprint(plugin_data)
        print("-----")
        print("Do you want to ADD params to plugin?")
        print("1. Yes")
        print("2. No")
        print("-----")
        user_input = input("Enter value: ")
        if user_input == "1":
            print("-----")
            print("Enter params for plugin:")
            print("-----")
            tmp_dict = {}
            for key in [
                "param_name",
                "param_key",
                "param_type",
                "default_value",
                "options",
            ]:
                # skip options if param_type is not array
                if key == "options":
                    if "[]" not in tmp_dict["param_type"]:
                        continue
                    else:
                        tmpv: List[Dict[str, str]] = []
                        print("Enter options")
                        while True:
                            j = input("Enter key (press Enter to stop): ")
                            if j == "":
                                break
                            k = input("Enter label: ")
                            tmpv.append({"key": j, "label": k})
                        v = tmpv.copy()
                else:
                    v = input(f"Enter {key}: ")
                if key == "param_type" and isinstance(v, str):
                    v = v.lower()
                    if v not in ["string", "number", "date", "string[]", "number[]"]:
                        print("Invalid param type --------")
                        continue
                tmp_dict[key] = v
            plugin_data["plugin_params"].append(tmp_dict)
        else:
            end_flag = True
    print("-----")
    print("Plugin Params:")
    print("-----")
    pprint(plugin_data)
    print("-----")
    print("Do you want to CONTINUE creating plugin?")
    print("1. Yes")
    print("2. No")
    vrf = input("Enter value: ")
    if vrf == "1":
        return plugin_data
    else:
        return await get_params_from_user_input(plugin_data)


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def generate_config_data(
    pa_config: Dict[str, Any],
    plugin_data: Dict[str, Any],
    subsection_id: str,
) -> Dict[str, Any]:
    # update config dict
    template_sections = pa_config["sections"].copy()
    for section in template_sections:
        for subsection in section["subsections"]:
            if subsection["subsection_id"] == subsection_id:
                subsection["plugins"].append(plugin_data)
    return {
        "sections": template_sections,
    }


async def update_paid_account_config(
    db: Database,
    paid_account_id: uuid.UUID,
    config: Dict[str, Any],
) -> bool:
    """update a paid account config record.

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
            UPDATE paid_account_config
             SET config = :config,
                last_updated = NOW()
            WHERE paid_account_id = :paid_account_id
            """,
            {
                "paid_account_id": paid_account_id,
                "config": json.dumps(config),
            },
        )
        logging.info("Updated paid account config!")
        return True
    except Exception as e:
        logging.error("Error updating paid account config")
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
# Add plugin to config for alima account
# ---------------------------------------------------------------------


async def add_plugin_to_alima_account_config(
    supplier_business_id: uuid.UUID,
    subsection_id: str,
    plugin_id: str,
    plugin_name: str,
    plugin_provider: str,
    plugin_provider_ref: str,
) -> bool:
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
    pa_config = await fetch_paid_account_config(_db, paid_acount.id)
    if not pa_config:
        logging.warning(
            f"Paid account config does not Exist for Supplier Business with id ({supplier_business_id}) already exists"
        )
        return False
    # verify if the plugin already exists
    pa_config_json = json.loads(pa_config["config"])
    plugin_exists = False
    for section in pa_config_json["sections"]:
        for subsection in section["subsections"]:
            if subsection["subsection_id"] == subsection_id:
                for plugin in subsection["plugins"]:
                    if plugin["plugin_id"] == plugin_id:
                        plugin_exists = True
                        break
    if plugin_exists:
        logging.warning(
            f"Plugin already exists for Supplier Business with id ({supplier_business_id}) already exists"
        )
        return False
    # verify if plugin requires params
    plg_params = {
        "plugin_id": plugin_id,
        "plugin_name": plugin_name,
        "plugin_provider": plugin_provider,
        "plugin_provider_ref": plugin_provider_ref,
    }
    retrieve_plugin_params = await get_params_from_user_input(plg_params)
    # update config
    config_data = await generate_config_data(
        subsection_id=subsection_id,
        pa_config=pa_config_json,
        plugin_data=retrieve_plugin_params,
    )
    if not await update_paid_account_config(_db, paid_acount.id, config_data):
        logging.warning(
            f"Paid account config not updated for Supplier Business with id ({supplier_business_id})"
        )
        return False
    # show results
    logging.info("Finished updating Alima Account SaaS Config")
    logging.info("\n".join(["-----", f"Supplier Business ID: {supplier_business_id}"]))
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(
        f"Started updating Saas Config for Alima Account: {args.supplier_business_id}"
    )
    try:
        fl = await add_plugin_to_alima_account_config(
            uuid.UUID(args.supplier_business_id),
            args.subsection_id,
            args.plugin_id,
            args.plugin_name,
            args.plugin_provider,
            args.plugin_provider_ref,
        )
        if not fl:
            logging.info(
                f"Supplier Business with id ({args.supplier_business_id}) not able to be updated"
            )
            return
        logging.info(
            f"Finished updating Saas config for Alima account successfully: {args.supplier_business_id}"
        )
    except Exception as e:
        logging.error(
            f"Error updating Saas config for Alima account: {args.supplier_business_id}"
        )
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
