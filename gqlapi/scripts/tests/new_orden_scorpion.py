"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.tests.new_orden_scorpion"""

import argparse
import asyncio
import json
import logging
from types import NoneType
from typing import Any, Dict
from uuid import UUID
from databases import Database
from fuzzywuzzy import fuzz
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchContactInfo,
)
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.integrations.integrations import IntegrationsPartnerHandler
from gqlapi.handlers.integrations.scorpion import ScorpionHandler
from gqlapi.handlers.restaurant.restaurant_business import RestaurantBusinessHandler
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
from gqlapi.config import ENV as DEV_ENV, SCORPION_USER, SCORPION_PASSWORD

# from lib.integrations.integrations.scorpion import ScorpionClientApi

from gqlapi.mongo import mongo_db as MongoDatabase

import pandas as pd

# logger
logger = get_logger(get_app())


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="New Scorpion Orden")
    parser.add_argument(
        "--orden_id",
        help="orden id",
        default=False,
    )
    return parser.parse_args()


pd.options.mode.chained_assignment = None  # type: ignore


async def get_scorpion_zone_info(
    db: Database, zip_code: str, source: str, neighbool: str
) -> NoneType | Dict[Any, Any]:
    zone_info = await db.fetch_all(
        """
        SELECT * from third_parties_data_zones
        WHERE zip_code = :zip_code AND source = :source
        """,
        {"source": source, "zip_code": zip_code},
    )
    if not zone_info:
        return None
    indez_colonias = []
    for zone in zone_info:
        zone_dict = dict(zone)
        fuz = fuzz.ratio(neighbool, zone_dict["neighborhood"])
        indez_colonias.append({"col": zone_dict["neighborhood"], "rank": fuz})

    sorted_indez = sorted(indez_colonias, key=lambda x: x["rank"], reverse=True)
    colonia_select = sorted_indez[0]
    for zone in zone_info:
        zone_dict = dict(zone)
        zone_dict["neighborhood"] = colonia_select["col"]
        return zone_dict
    return None


async def new_orden_scorpion(info: InjectedStrawberryInfo, orden_id: str) -> bool:
    logging.info("Starting create new orden to scorpion...")
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
    res_biz_handler = RestaurantBusinessHandler(
        restaurant_business_repo=RestaurantBusinessRepository(info),  # type: ignore
        restaurant_business_account_repo=RestaurantBusinessAccountRepository(
            info  # type: ignore
        ),
    )
    scorpion_handler = ScorpionHandler(
        integrations_orden_repo=IntegrationsOrdenRepository(info)  # type: ignore
    )
    integrations_partner_handler = IntegrationsPartnerHandler(
        repo=IntegrationsPartnerRepository(info)  # type: ignore
    )
    try:
        # call handler
        _resp = await _handler.search_orden(orden_id=UUID(orden_id))
        if (
            not _resp[0].supplier
            or not _resp[0].supplier.supplier_business
            or not _resp[0].cart
        ):
            raise GQLApiException(
                msg="Error to get suppplier info",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        ordenes = await _handler.count_daily_ordenes(
            supplier_business_id=_resp[0].supplier.supplier_business.id
        )
        zone_info = await get_scorpion_zone_info(
            db=info.context["db"].sql,  # type: ignore
            zip_code=_resp[0].branch.zip_code if _resp[0].branch else "00000",
            neighbool=_resp[0].branch.neighborhood if _resp[0].branch else "",
            source="scorpion",
        )
        # GET NUMBER
        if not _resp[0].branch:
            raise GQLApiException(
                msg="Error to get branch info",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # get restaurant business for contact info
        _biz = await res_biz_handler.fetch_restaurant_business(
            _resp[0].branch.restaurant_business_id
        )

        _resp[0].branch.contact_info = RestaurantBranchContactInfo(
            business_name=_biz.name,
            display_name=_biz.account.legal_rep_name if _biz.account else "",
            email=_biz.account.email if _biz.account else "",
            phone_number=_biz.account.phone_number if _biz.account else "",
        )

        integrations_partner = await integrations_partner_handler.get_by_name(
            name="scorpion"
        )
        if not integrations_partner:
            raise GQLApiException(
                msg="Error to find partner info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        validate_orden = await scorpion_handler.get_by_multiple_ordenes(
            orden_ids=[_resp[0].id]
        )
        if validate_orden:
            raise GQLApiException(
                msg="Orden already exist",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        scorpion_api = ScorpionClientApi(env=DEV_ENV)
        token = await scorpion_api.get_token(
            token=ScorpionToken(user=SCORPION_USER, password=SCORPION_PASSWORD)
        )
        if token.status == "error" or not token.value:
            raise GQLApiException(
                msg="Error to get token",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        val_ord_num = "C" + str(_resp[0].orden_number).zfill(8)
        scorpion_orden_val = await scorpion_api.get_orden(
            token=token.value, number_orden=val_ord_num
        )
        if scorpion_orden_val.msg != "empty":
            raise GQLApiException(
                msg="Orden already exist in scorpion",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # Create table, with orden_details, and scorpion orden_number
        int_part_ord_id = await scorpion_handler.new_orden(
            integrations_partner_id=integrations_partner.id,
            orden_id=_resp[0].id,
            status="running",
        )
        if not int_part_ord_id:
            raise GQLApiException(
                msg="Error to add integrations partner orden",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

        if token.status == "error" or not token.value:
            await scorpion_handler.edit_orden(
                id=int_part_ord_id,
                integrations_partner_id=integrations_partner.id,
                orden_id=_resp[0].id,
                integrations_orden_id="",
                status="failed",
                reason=token.msg,
            )
            raise GQLApiException(
                msg="Error to add integrations partner orden",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        orden_save = await scorpion_api.save_orden(
            token=token.value,
            orden=_resp[0],
            consecutive=int(ordenes),
            zone_info=zone_info,
        )
        if orden_save.status == "ok" and orden_save.value and orden_save.result:
            await scorpion_handler.edit_orden(
                id=int_part_ord_id,
                integrations_partner_id=integrations_partner.id,
                orden_id=_resp[0].id,
                integrations_orden_id=orden_save.value,
                status="success",
                reason="Send orden to scorpion",
                result=json.dumps({"save_orden": orden_save.result}),
            )
        else:
            await scorpion_handler.edit_orden(
                id=int_part_ord_id,
                integrations_partner_id=integrations_partner.id,
                orden_id=_resp[0].id,
                integrations_orden_id="",
                status="failed",
                reason=orden_save.msg,
            )
            raise GQLApiException(
                msg="Error to send order scorpion",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        scorpion_orden = await scorpion_api.get_orden(
            token=token.value, number_orden=orden_save.value
        )
        if (
            scorpion_orden.status == "ok"
            and scorpion_orden.value
            and scorpion_orden.result
            and orden_save.result
        ):
            prod_val = None
            if int(scorpion_orden.value) > len(_resp[0].cart):
                prod_val = "Scorpion orden has more products than orden"
            elif int(scorpion_orden.value) < len(_resp[0].cart):
                prod_val = "Scorpion orden has less products than orden"
            if prod_val:
                await scorpion_handler.edit_orden(
                    id=int_part_ord_id,
                    integrations_partner_id=integrations_partner.id,
                    orden_id=_resp[0].id,
                    status="failed",
                    reason=prod_val,
                    result=json.dumps(
                        {
                            "save_orden": orden_save.result,
                            "get_orden": scorpion_orden.result,
                        }
                    ),
                )
                raise GQLApiException(
                    msg="Error save and get scorpion orden",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            else:
                await scorpion_handler.edit_orden(
                    id=int_part_ord_id,
                    integrations_partner_id=integrations_partner.id,
                    orden_id=_resp[0].id,
                    status="success",
                    reason="Correct orden save",
                    result=json.dumps(
                        {
                            "save_orden": orden_save.result,
                            "get_orden": scorpion_orden.result,
                        }
                    ),
                )
        else:
            await scorpion_handler.edit_orden(
                id=int_part_ord_id,
                integrations_partner_id=integrations_partner.id,
                orden_id=_resp[0].id,
                status="failed",
                reason=scorpion_orden.msg,
            )
            raise GQLApiException(
                msg="Error save and get scorpion orden",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

    except GQLApiException as ge:
        logger.warning(ge)
        raise GQLApiException(
            msg=ge.msg,
            error_code=ge.error_code,
        )
    except Exception as e:
        logger.error(e)
        raise GQLApiException(
            msg=str(e),
            error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
        )
    return True


async def scorpion_orden_wrapper(orden_id: str) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await new_orden_scorpion(info, orden_id)


async def main():
    try:
        args = parse_args()
        # Permite conectar a la db
        await db_startup()
        logging.info("Starting routine to new orden to scorpion ...")

        resp = await scorpion_orden_wrapper(args.orden_id)
        if resp:
            logging.info("Finished routine to new_orden_to scorpion")
        else:
            logging.info("Error to update orders")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
