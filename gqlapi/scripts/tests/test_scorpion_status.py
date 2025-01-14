"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.tests.test_scorpion_status"""

import asyncio
import logging
from typing import List
from uuid import UUID

from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.supplier import SupplierUnit
from gqlapi.domain.models.v2.utils import OrdenStatusType
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.integrations.integrations.scorpion import ScorpionClientApi, ScorpionToken
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.config import (
    ENV as DEV_ENV,
    RETOOL_SECRET_BYPASS,
    SCORPION_USER,
    SCORPION_PASSWORD,
)

# from lib.integrations.integrations.scorpion import ScorpionClientApi

from gqlapi.mongo import mongo_db as MongoDatabase

import pandas as pd

# logger
logger = get_logger(get_app())

pd.options.mode.chained_assignment = None  # type: ignore


async def get_units(
    _info: InjectedStrawberryInfo,
    supplier_business_id: UUID,
) -> List[SupplierUnit]:
    unit_repo = SupplierUnitRepository(info=_info)  # type: ignore
    try:
        tmp = await unit_repo.find(supplier_business_id=supplier_business_id)
        if not tmp:
            raise Exception("Error find unit")
        units = []
        for unit in tmp:
            units.append(SupplierUnit(**unit))
        return units
    except Exception:
        raise Exception("Error getting unit")


async def get_alima_bot(info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    cusr = await core_repo.fetch_by_email("admin")
    if not cusr or not cusr.id:
        raise Exception("Error getting Alima admin bot user")
    return cusr


async def tets_update_orden_scorpion(
    info: InjectedStrawberryInfo, password: str
) -> bool:
    logging.info("Starting update orden status to scorpion...")
    if password != RETOOL_SECRET_BYPASS:
        logging.info("Access Denied")
        raise Exception("Access Denied")
    _handler = OrdenHandler(
        orden_repo=OrdenRepository(info),  # type: ignore
        orden_det_repo=OrdenDetailsRepository(info),  # type: ignore
        orden_status_repo=OrdenStatusRepository(info),  # type: ignore
        orden_payment_repo=OrdenPaymentStatusRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        rest_branc_repo=RestaurantBranchRepository(info),  # type: ignore
        supp_unit_repo=SupplierUnitRepository(info),  # type: ignore
        cart_repo=CartRepository(info),  # type: ignore
        cart_prod_repo=CartProductRepository(info),  # type: ignore
        rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),  # type: ignore
        supp_bus_acc_repo=SupplierBusinessAccountRepository(info),  # type: ignore
        supp_bus_repo=SupplierBusinessRepository(info),  # type: ignore
        rest_business_repo=RestaurantBusinessRepository(info),  # type: ignore
    )
    try:
        scorpion_api = ScorpionClientApi(env=DEV_ENV)
        token = await scorpion_api.get_token(
            token=ScorpionToken(user=SCORPION_USER, password=SCORPION_PASSWORD)
        )
        if token.status == "error" or not token.value:
            raise GQLApiException(
                msg="Error to add integrations partner orden",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # get alima bot
        alima_bot = await get_alima_bot(info)
        scorpion_orden = await scorpion_api.get_ordenes(
            token=token.value, orden_number="C00000023"
        )
        if scorpion_orden and scorpion_orden.value:
            if scorpion_orden.value == "80":
                await _handler.edit_orden(
                    firebase_id=alima_bot.firebase_id,
                    orden_id=ord.id,
                    status=OrdenStatusType.DELIVERED,
                )
            # [TODO] if Unauthorized request IP.

    except GQLApiException as ge:
        logger.warning(ge)
        return False
    except Exception as e:
        logger.error(e)
        return False
    return True


async def test_scorpion_orden_status_wrapper(password: str) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await tets_update_orden_scorpion(info, password)


async def main():
    try:
        # Permite conectar a la db
        await db_startup()
        logging.info("Starting routine to update orden status to scorpion ...")

        resp = await test_scorpion_orden_status_wrapper(password=RETOOL_SECRET_BYPASS)
        if resp:
            logging.info("Finished routine to update orden status to scorpion")
        else:
            logging.info("Error to update orders")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
