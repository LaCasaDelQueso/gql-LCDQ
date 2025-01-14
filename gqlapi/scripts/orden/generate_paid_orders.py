"""How to run (file path as example):
    poetry run python -m gqlapi.scripts.orden.generate_paid_orders \
    --supplier_orden_status ../../../_cambios_DB/{file}.xlsx"""

import datetime
import argparse
import asyncio
import json
import uuid
from gqlapi.domain.models.v2.utils import PayStatusType
from gqlapi.lib.environ.environ.environ import get_app
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
from gqlapi.repository.supplier.supplier_price_list import SupplierPriceListRepository
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.utils.helpers import list_into_strtuple
from typing import Any, Dict, List
from uuid import UUID
import sys
from gqlapi.domain.models.v2.core import (
    CoreUser,
    Orden,
    OrdenPayStatus,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierUnit,
)
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())

pd.options.mode.chained_assignment = None  # type: ignore


def parse_args() -> argparse.Namespace:
    # get file xlsx from directory
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--supplier_orden_status",
        type=str,
        help="supplier_orden_status Template (XLSX)",
        required=True,
    )
    _args = parser.parse_args()
    if _args.supplier_orden_status.split(".")[-1] != "xlsx":
        raise Exception(
            "supplier_orden_status Template file has invalid format: Must be XLSX"
        )
    return _args


async def fetch_last_supplier_price_list(
    info: InjectedStrawberryInfo, supplier_unit_ids: List[UUID], name: str
) -> List[UUID]:
    supplier_price_list_repo = SupplierPriceListRepository(info)  # type: ignore
    _spl = await supplier_price_list_repo.raw_query(
        query=f"""
                WITH last_price_list AS (
                    WITH rcos AS (
                        SELECT id, supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                            name, is_default, valid_from, valid_upto, created_by, created_at, last_updated,
                            ROW_NUMBER() OVER (PARTITION BY name, supplier_unit_id ORDER BY last_updated DESC) row_num
                        FROM supplier_price_list
                    )
                    SELECT * FROM rcos WHERE row_num = 1
                )
                SELECT lpl.id, lpl.supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                    lpl.name, lpl.is_default, valid_from, valid_upto, lpl.created_by, lpl.created_at,
                    lpl.last_updated
                FROM last_price_list lpl
                WHERE lpl.name = :name AND lpl.supplier_unit_id IN {list_into_strtuple(supplier_unit_ids)}
                """,
        vals={"name": name},
    )
    if not _spl or not _spl[0]:
        return []
    spl = dict(_spl[0])
    # parse supplier price list
    spl["supplier_product_price_ids"] = json.loads(spl["supplier_product_price_ids"])
    spl["supplier_restaurant_relation_ids"] = json.loads(
        spl["supplier_restaurant_relation_ids"]
    )
    return spl["supplier_restaurant_relation_ids"]


# Split the DataFrame
def split_dataframe_by_restaurant(df):
    sku_column = df.columns[1]
    sbi_column = df.columns[0]
    descriptions_column = df.columns[2]
    restaurant_columns = df.columns[3:]

    dfs = []
    for restaurant in restaurant_columns:
        restaurant_df = df[
            [sbi_column, sku_column, descriptions_column, restaurant]
        ].copy()
        restaurant_df = restaurant_df.dropna(subset=[restaurant])
        dfs.append(restaurant_df)

    return dfs


def normalize_supplier_orden_status(df: pd.DataFrame) -> pd.DataFrame:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset(
        {"orden_id", "estatus_de_pago"}
    ):
        raise Exception("Sheet de ordenes tiene columnas faltantes!")
    df = df[~df["orden_id"].isnull()]
    df = df.where(pd.notna(df), None)

    return df


async def get_admin(
    _info: InjectedStrawberryInfo, supplier_business_id: UUID
) -> CoreUser:
    core_user_repo = CoreUserRepository(info=_info)  # type: ignore
    supplier_user_repo = SupplierUserRepository(info=_info)  # type: ignore
    supplier_user_perm_repo = SupplierUserPermissionRepository(info=_info)  # type: ignore
    supp_usr_prm = await supplier_user_perm_repo.fetch_by_supplier_business(
        supplier_business_id=supplier_business_id
    )
    if not supp_usr_prm:
        raise Exception("Error getting supplier user permission")
    supp_usr = await supplier_user_repo.get_by_id(
        supplier_user_id=supp_usr_prm[0]["supplier_user_id"]
    )
    if not supp_usr:
        raise Exception("Error getting supplier user")
    core_user = await core_user_repo.fetch(core_user_id=supp_usr["core_user_id"])
    if not core_user:
        raise Exception("Error getting core user")
    return core_user


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


async def get_branch(
    _info: InjectedStrawberryInfo, supplier_restaurant_relation_id: UUID
) -> UUID | None:
    supplier_restaurants_repo = SupplierRestaurantsRepository(info=_info)  # type: ignore
    try:
        tmp = await supplier_restaurants_repo.fetch(supplier_restaurant_relation_id)
        if not tmp:
            import pdb

            pdb.set_trace()
            return None
        return tmp["restaurant_branch_id"]
    except Exception:
        raise Exception("Error getting branch")


async def upload_supplier_orden_status(
    supplier_orden_status_list_data: pd.DataFrame,
) -> Dict[Any, Any]:
    logger.info("Starting set supplier_orden_status ...")
    # Permite conectar a la db
    await db_startup()
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    orden_repo = OrdenRepository(info=_info)  # type: ignore
    orden_paystatus_repo = OrdenPaymentStatusRepository(info=_info)  # type: ignore
    core_repo = CoreUserRepository(info=_info)  # type: ignore
    _handler = OrdenHandler(
        orden_repo=OrdenRepository(_info),  # type: ignore
        orden_det_repo=OrdenDetailsRepository(_info),  # type: ignore
        orden_status_repo=OrdenStatusRepository(_info),  # type: ignore
        orden_payment_repo=OrdenPaymentStatusRepository(_info),  # type: ignore
        core_user_repo=CoreUserRepository(_info),  # type: ignore
        rest_branc_repo=RestaurantBranchRepository(_info),  # type: ignore
        supp_unit_repo=SupplierUnitRepository(_info),  # type: ignore
        cart_repo=CartRepository(_info),  # type: ignore
        cart_prod_repo=CartProductRepository(_info),  # type: ignore
        rest_buss_acc_repo=RestaurantBusinessAccountRepository(_info),  # type: ignore
        supp_bus_acc_repo=SupplierBusinessAccountRepository(_info),  # type: ignore
        supp_bus_repo=SupplierBusinessRepository(_info),  # type: ignore
        rest_business_repo=RestaurantBusinessRepository(_info),  # type: ignore
    )

    orden_ref_id = supplier_orden_status_list_data.iloc[0, 0]
    orden_ref = await orden_repo.fetch(UUID(str(orden_ref_id)))
    orden_ref_obj = Orden(**orden_ref)
    core_user = await core_repo.fetch(orden_ref_obj.created_by)
    if not core_user:
        logger.error(f"Core user {orden_ref} not found")
        await db_shutdown()
        return {"status": "error", "data": "Core user not found"}

    for index, row in supplier_orden_status_list_data.iterrows():
        orden_id = UUID(row["orden_id"])
        estatus_de_pago = row["estatus_de_pago"]
        last_payday = datetime.datetime.utcnow()

        comments = row.get("comments", None)
        if pd.isna(comments):
            comments = None
        try:
            orden_ref = None
            if estatus_de_pago.lower() == "pagado":
                orden = await _handler.find_orden(orden_id)
                if not orden or not orden[0].details or not orden[0].details.total:
                    logger.error(f"Orden {orden_id} not found")
                    continue
                current_paystatus = await orden_paystatus_repo.get_last(orden_id)
                current_paystatus_obj = (
                    OrdenPayStatus(**current_paystatus) if current_paystatus else None
                )
                if not current_paystatus_obj or current_paystatus_obj.status != "paid":
                    if await orden_paystatus_repo.add(
                        OrdenPayStatus(
                            id=uuid.uuid4(),
                            orden_id=orden_id,
                            status=PayStatusType.PAID,
                            created_by=orden[0].created_by,
                        )
                    ):
                        await _handler.add_payment_receipt(
                            orden_ids=[orden_id],
                            payment_value=orden[0].details.total,
                            payment_day=last_payday,
                            firebase_id=core_user.firebase_id,
                            comments=comments,
                        )
                    else:
                        logger.error(f"Error adding orden paystatus {orden_id}")
                        continue

        except Exception as e:
            logger.error(e)
            continue

    await db_shutdown()
    logger.info("Listo ...")
    return {"status": "ok", "data": "data"}


if __name__ == "__main__":
    try:
        pargs = parse_args()
        logger.info("Starting to set orden paid and generate paid receipt db ...")

        xls = pd.ExcelFile(pargs.supplier_orden_status)
        logger.info("Starting to set orden paid and generate paid receipt...")
        price_list_data = normalize_supplier_orden_status(
            pd.read_excel(
                xls,
                dtype={
                    "orden_id": str,
                    "estatus_de_pago": str,
                    # "monto_de_pago": float,
                    # "last_payday": str,
                },
            )
        )
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    resp = asyncio.run(upload_supplier_orden_status(price_list_data))
    logger.info("Finished sync alima db!")
