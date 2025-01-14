""" Script to activate/deactive delegated mode


Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.cx.insert_mongo_employee --help
"""
import asyncio
import argparse
import logging
from typing import List
import uuid
from bson import Binary
from gqlapi.domain.models.v2.core import SupplierEmployeeInfo, SupplierEmployeeInfoPermission
from uuid import UUID
from gqlapi.domain.models.v2.supplier import SupplierUnit, SupplierUserPermission
from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.repository.user.employee import EmployeeRepository, default_unit_perms
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup
from gqlapi.domain.models.v2.core import (
    SupplierEmployeeInfo,
)

logger = get_logger(
    "gqlapi.scripts.run_supplier_delegation_mode",
    logging.INFO,
    Environment(get_env()),
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Run Supplier delegation mode.")
    parser.add_argument(
        "--email",
        help="Supplier user email",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--business_id",
        help="Supplier Business ID set",
        type=str,
        default=False,
        required=True,
    )
    return parser.parse_args()

async def insert_employee(

) -> bool:
    # init
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    employee_repo = EmployeeRepository(_info)  # type: ignore
    # get employee directory
    import pdb; pdb.set_trace()
    employee = await employee_repo.new_supplier_employee(
        core_element_collection="supplier_employee_directory",
        employee=SupplierEmployeeInfo(
                supplier_user_id=UUID('9ae63cb6-74d9-4450-8796-68a8a333a8dc')
                
            )
    )
    return True


async def main():    
    fl = await insert_employee()


if __name__ == "__main__":
    asyncio.run(main())
