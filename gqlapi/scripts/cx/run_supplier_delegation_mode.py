""" Script to activate/deactive delegated mode


Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.cx.run_supplier_delegation_mode --help
"""
import asyncio
import argparse
import logging
from typing import List
import uuid
from bson import Binary
from gqlapi.domain.models.v2.core import SupplierEmployeeInfo, SupplierEmployeeInfoPermission

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


async def get_supplier_user_perms(
    email: str,
    c_user_repo: CoreUserRepository,
    s_user_repo: SupplierUserRepository,
    su_perms_repo: SupplierUserPermissionRepository,
) -> SupplierUserPermission:
    """Get supplier user permissions"""
    core_user = await c_user_repo.fetch_by_email(email)
    if not core_user or not core_user.id:
        raise Exception(f"Core User not found: {email}")
    supplier_user = await s_user_repo.fetch(core_user.id)
    if not supplier_user:
        raise Exception(f"Supplier User not found: {email}")
    su_perms_dict = await su_perms_repo.fetch(supplier_user["id"])
    if not su_perms_dict:
        raise Exception(f"Supplier User permissions not found: {supplier_user['id']}")
    su_perms = SupplierUserPermission(**su_perms_dict)
    logging.info(
        f"Supplier User ({supplier_user['id']}), original Supplier business: {su_perms.supplier_business_id}"
    )
    return su_perms


async def get_employee_directory(
    supplier_user_id: uuid.UUID,
    employee_repo: EmployeeRepository,
) -> SupplierEmployeeInfo:
    """Get employee directory"""
    employee_dict = await employee_repo.fetch(
        core_element_collection="supplier_employee_directory",
        user_id_key="supplier_user_id",
        user_id=supplier_user_id,
    )
    if not employee_dict:
        raise Exception(f"Employee directory not found: {supplier_user_id}")
    if employee_dict["unit_permissions"]:
        perms_ = []
        for em in employee_dict["unit_permissions"]:
            em["unit_id"] = Binary.as_uuid(em["unit_id"])
            perms_.append(SupplierEmployeeInfoPermission(**em))
        employee_dict["unit_permissions"] = perms_
    employee = SupplierEmployeeInfo(**employee_dict)
    logging.info(f"Employee directory ({supplier_user_id}): {employee}")
    return employee


async def get_supplier_units(
    supplier_business_id: uuid.UUID,
    s_unit_repo: SupplierUnitRepository,
) -> List[SupplierUnit]:
    """Get supplier branches"""
    s_units_dict = await s_unit_repo.find(supplier_business_id=supplier_business_id)
    if not s_units_dict:
        raise Exception(f"Supplier Units not found: {supplier_business_id}")
    s_units = [SupplierUnit(**s) for s in s_units_dict]
    logging.info(
        f"Supplier Units ({supplier_business_id}): {[b.unit_name for b in s_units]}"
    )
    return s_units


async def update_supplier_user_perms(
    supplier_user_id: uuid.UUID,
    supplier_business_id: uuid.UUID,
    su_perms_repo: SupplierUserPermissionRepository,
) -> bool:
    return await su_perms_repo.edit(
        supplier_user_id=supplier_user_id,
        supplier_business_id=supplier_business_id,
        display_routes_section=True,
        display_sales_section=True,
    )


async def update_employee_directory(
    supplier_user_id: uuid.UUID,
    supplier_unit_ids: List[uuid.UUID],
    employee: SupplierEmployeeInfo,
    employee_repo: EmployeeRepository,
) -> bool:
    new_units = []
    for sui in supplier_unit_ids:
        _seip = SupplierEmployeeInfoPermission(
            unit_id=sui, permissions=default_unit_perms
        )
        new_units.append(_seip)
    employee.unit_permissions = new_units
    return await employee_repo.edit(
        core_element_collection="supplier_employee_directory",
        user_id_key="supplier_user_id",
        user_id=supplier_user_id,
        employee=employee,
    )


async def delegation_mode(
    email: str,
    supplier_business_id: uuid.UUID,
) -> bool:
    # init
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    c_user_repo = CoreUserRepository(_info)  # type: ignore
    s_user_repo = SupplierUserRepository(_info)  # type: ignore
    su_perms_repo = SupplierUserPermissionRepository(_info)  # type: ignore
    s_unit_repo = SupplierUnitRepository(_info)  # type: ignore
    employee_repo = EmployeeRepository(_info)  # type: ignore
    # get supplier user and perms -> print initial permissions
    su_perms = await get_supplier_user_perms(
        email=email,
        c_user_repo=c_user_repo,
        s_user_repo=s_user_repo,
        su_perms_repo=su_perms_repo,
    )
    # get employee directory
    employee = await get_employee_directory(
        supplier_user_id=su_perms.supplier_user_id,
        employee_repo=employee_repo,
    )
    # get sup business and units from supplier business
    logging.info(f"Supplier Units (from {supplier_business_id}) to be set: ")
    s_units = await get_supplier_units(
        supplier_business_id=supplier_business_id,
        s_unit_repo=s_unit_repo,
    )
    # update sup perms to business
    if not await update_supplier_user_perms(
        supplier_user_id=su_perms.supplier_user_id,
        supplier_business_id=supplier_business_id,
        su_perms_repo=su_perms_repo,
    ):
        logging.warning(f"Error updating Supplier User permissions: {email}")
        return False
    # update employee directory
    if not await update_employee_directory(
        supplier_user_id=su_perms.supplier_user_id,
        supplier_unit_ids=[s.id for s in s_units],
        employee=employee,
        employee_repo=employee_repo,
    ):
        logging.warning(f"Error updating Employee directory: {email}")
        return False
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(f"Starting sending {args.business_id} docs to: {args.email} ...")
    try:
        r_user_email = args.email
    except Exception as e:
        logging.error(f"Error parsing supplier_user_id: {args.email}")
        logging.error(e)
        return
    try:
        r_bus = uuid.UUID(args.business_id)
    except Exception as e:
        logging.error(f"Error parsing business_id: {args.business_id}")
        logging.error(e)
        return
    try:
        fl = await delegation_mode(r_user_email, r_bus)
        if not fl:
            logging.info(
                f"NOT able to set delegation from {args.business_id} to {args.email}"
            )
            return
        logging.info(f"Successfully set delegation  to: {args.email}")
    except Exception as e:
        logging.error(f"Error setting delegation  to: {args.email}")
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
