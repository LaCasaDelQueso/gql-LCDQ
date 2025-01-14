""" Script to activate/deactive delegated mode


Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.cx.run_restaurant_delegation_mode --help
"""
import asyncio
import argparse
import logging
from typing import List
import uuid
from bson import Binary
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import RestaurantBranchGQL
from gqlapi.domain.models.v2.core import (
    RestaurantEmployeeInfo,
    RestaurantEmployeeInfoPermission,
)
from gqlapi.domain.models.v2.restaurant import RestaurantUserPermission

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_user import (
    RestaurantUserPermissionRepository,
    RestaurantUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.repository.user.employee import EmployeeRepository, default_branch_perms
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup

logger = get_logger(
    "gqlapi.scripts.run_restaurant_delegation_mode",
    logging.INFO,
    Environment(get_env()),
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Run Restaurant delegation mode.")
    parser.add_argument(
        "--email",
        help="Restaurant user Email",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--business_id",
        help="Restaurant Business ID set",
        type=str,
        default=False,
        required=True,
    )
    return parser.parse_args()


async def get_restaurant_user_perms(
    email: str,
    c_user_repo: CoreUserRepository,
    r_user_repo: RestaurantUserRepository,
    ru_perms_repo: RestaurantUserPermissionRepository,
) -> RestaurantUserPermission:
    """Get restaurant user permissions"""
    core_user = await c_user_repo.fetch_by_email(email)
    if not core_user or not core_user.id:
        raise Exception(f"Core User not found: {email}")
    restaurant_user = await r_user_repo.fetch(core_user.id)
    if not restaurant_user or not restaurant_user.id:
        raise Exception(f"Restaurant User not found: {email}")
    ru_perms = await ru_perms_repo.fetch(restaurant_user.id)
    if not ru_perms:
        raise Exception(f"Restaurant User permissions not found: {email}")
    logging.info(
        f"Restaurant User ({restaurant_user.id}), original Resturant business: {ru_perms.restaurant_business_id}"
    )
    return ru_perms


async def get_restaurant_branches(
    restaurant_business_id: uuid.UUID,
    r_branch_repo: RestaurantBranchRepository,
) -> List[RestaurantBranchGQL]:
    """Get restaurant branches"""
    r_branches = await r_branch_repo.get_restaurant_branches(
        restaurant_business_id=restaurant_business_id
    )
    if not r_branches:
        raise Exception(f"Restaurant branches not found: {restaurant_business_id}")
    logging.info(
        f"Restaurant branches ({restaurant_business_id}): {[b.id for b in r_branches]}"
    )
    return r_branches


async def update_restaurant_user_perms(
    restaurant_user_id: uuid.UUID,
    restaurant_business_id: uuid.UUID,
    ru_perms_repo: RestaurantUserPermissionRepository,
) -> bool:
    return await ru_perms_repo.edit(
        restaurant_user_id=restaurant_user_id,
        restaurant_business_id=restaurant_business_id,
        display_orders_section=True,
        display_products_section=True,
        display_suppliers_section=True,
    )


async def get_employee_directory(
    restaurant_user_id: uuid.UUID,
    employee_repo: EmployeeRepository,
    email: str,
) -> RestaurantEmployeeInfo:
    """Get employee directory"""
    employee_dict = await employee_repo.fetch(
        core_element_collection="restaurant_employee_directory",
        user_id_key="restaurant_user_id",
        user_id=restaurant_user_id,
    )
    if not employee_dict:
        employee = RestaurantEmployeeInfo(
            restaurant_user_id=restaurant_user_id,
            email=email,
            branch_permissions=[],
        )
        if not await employee_repo.new_restaurant_employee(
            core_element_collection="restaurant_employee_directory",
            employee=employee,
        ):
            raise Exception(f"Employee directory not found: {restaurant_user_id}")
        else:
            return employee
    if employee_dict["branch_permissions"]:
        perms_ = []
        for em in employee_dict["branch_permissions"]:
            em["branch_id"] = Binary.as_uuid(em["branch_id"])
            perms_.append(RestaurantEmployeeInfoPermission(**em))
        employee_dict["branch_permissions"] = perms_
    employee = RestaurantEmployeeInfo(**employee_dict)
    logging.info(f"Employee directory ({restaurant_user_id}): {employee}")
    return employee


async def update_employee_directory(
    restaurant_user_id: uuid.UUID,
    restaurant_branch_ids: List[uuid.UUID],
    employee: RestaurantEmployeeInfo,
    employee_repo: EmployeeRepository,
) -> bool:
    new_branches = []
    for rui in restaurant_branch_ids:
        _seip = RestaurantEmployeeInfoPermission(
            branch_id=rui, permissions=default_branch_perms
        )
        new_branches.append(_seip)
    employee.branch_permissions = new_branches
    return await employee_repo.edit(
        core_element_collection="restaurant_employee_directory",
        user_id_key="restaurant_user_id",
        user_id=restaurant_user_id,
        employee=employee,
    )


async def delegation_mode(
    email: str,
    restaurant_business_id: uuid.UUID,
) -> bool:
    # init
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    ru_perms_repo = RestaurantUserPermissionRepository(_info)  # type: ignore
    r_branch_repo = RestaurantBranchRepository(_info)  # type: ignore
    c_user_repo = CoreUserRepository(_info)  # type: ignore
    r_user_repo = RestaurantUserRepository(_info)  # type: ignore
    r_branch_repo = RestaurantBranchRepository(_info)  # type: ignore
    employee_repo = EmployeeRepository(_info)  # type: ignore
    # get restaurant user and perms -> print initial permissions
    ru_perms = await get_restaurant_user_perms(
        email=email,
        c_user_repo=c_user_repo,
        r_user_repo=r_user_repo,
        ru_perms_repo=ru_perms_repo,
    )
    # get employee directory
    employee = await get_employee_directory(
        restaurant_user_id=ru_perms.restaurant_user_id,
        employee_repo=employee_repo,
        email=email,
    )
    # get sup business and branches from restauarnt business
    r_branches = await get_restaurant_branches(  # noqa
        restaurant_business_id=restaurant_business_id,
        r_branch_repo=r_branch_repo,
    )
    # update sup perms to business
    if not await update_restaurant_user_perms(
        restaurant_user_id=ru_perms.restaurant_user_id,
        restaurant_business_id=restaurant_business_id,
        ru_perms_repo=ru_perms_repo,
    ):
        logging.warning(f"Error updating Restaurant User permissions: {email}")
        return False
    # update employee directory
    if not await update_employee_directory(
        restaurant_user_id=ru_perms.restaurant_user_id,
        restaurant_branch_ids=[s.id for s in r_branches],
        employee=employee,
        employee_repo=employee_repo,
    ):
        logging.warning(f"Error updating Employee directory: {email}")
        return False
    # update employee directory
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(f"Starting sending {args.business_id} docs to: {args.email} ...")
    try:
        r_user = args.email
    except Exception as e:
        logging.error(f"Error parsing email: {args.email}")
        logging.error(e)
        return
    try:
        r_bus = uuid.UUID(args.business_id)
    except Exception as e:
        logging.error(f"Error parsing business_id: {args.business_id}")
        logging.error(e)
        return
    try:
        fl = await delegation_mode(r_user, r_bus)
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
