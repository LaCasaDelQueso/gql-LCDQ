"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.tests.get_scorpion_orden_status"""

import asyncio
import logging
from typing import List
from uuid import UUID

from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.integrations import IntegrationOrden
from gqlapi.domain.models.v2.supplier import SupplierUnit
from gqlapi.domain.models.v2.utils import OrdenStatusType
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.integrations.integrations import IntegrationsPartnerHandler
from gqlapi.handlers.integrations.scorpion import ScorpionHandler
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.integrarions.integrations import (
    IntegrationsOrdenRepository,
    IntegrationsPartnerRepository,
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


async def update_orden_scorpion(info: InjectedStrawberryInfo, password: str) -> bool:
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
    scorpion_handler = ScorpionHandler(
        integrations_orden_repo=IntegrationsOrdenRepository(info)  # type: ignore
    )
    integrations_partner_handler = IntegrationsPartnerHandler(
        repo=IntegrationsPartnerRepository(info)  # type: ignore
    )
    try:
        integrations_partner = await integrations_partner_handler.get_by_name(
            name="scorpion"
        )
        if not integrations_partner:
            raise GQLApiException(
                msg="Error to find partner info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        units = await get_units(info, integrations_partner.business_id)
        # fetET UNITS AND LOOP
        if not units:
            raise GQLApiException(
                msg="Error to find units",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        orders: List[OrdenGQL] = []
        # call handler

        for unit in units:
            _resp_sub = await _handler.find_orden(
                # supplier_business_id=,
                status=OrdenStatusType.SUBMITTED,
                supplier_unit_id=unit.id,
            )
            _resp_acc = await _handler.find_orden(
                # supplier_business_id=,
                status=OrdenStatusType.ACCEPTED,
                supplier_unit_id=unit.id,
            )
            for ord in _resp_sub:
                orders.append(ord)
            for ord in _resp_acc:
                orders.append(ord)

        if not orders:
            return True

        ord_ind = {}
        ord_idx = []
        for ordenes in orders:
            ord_idx.append(ordenes.id)
            ord_ind[ordenes.id] = ordenes
        scorpion_ordenes = await scorpion_handler.get_by_multiple_ordenes(ord_idx)
        sord_index = {}
        for sord in scorpion_ordenes:
            sord_index[sord.orden_id] = sord
        if not scorpion_ordenes:
            return True

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
        for ord in orders:
            on: IntegrationOrden = sord_index.get(ord.id, None)
            if on and on.integrations_orden_id:
                scorpion_orden = await scorpion_api.get_ordenes(
                    token=token.value, orden_number=on.integrations_orden_id
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


async def scorpion_orden_status_wrapper(password: str) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await update_orden_scorpion(info, password)


async def main():
    try:
        # Permite conectar a la db
        await db_startup()
        logging.info("Starting routine to update orden status to scorpion ...")

        resp = await scorpion_orden_status_wrapper(password=RETOOL_SECRET_BYPASS)
        if resp:
            logging.info("Finished routine to update orden status to scorpion")
        else:
            logging.info("Error to update orders")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
