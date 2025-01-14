"""How to run (file path as example):
    poetry run python -m gqlapi.scripts.product.update_all_supplier_price_list \
    --supplier_price_lists ../../../_cambios_DB/{file}.xlsx"""

import datetime
import argparse
import asyncio
import json
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.handlers.supplier.supplier_price_list import SupplierPriceListHandler
from gqlapi.handlers.supplier.supplier_product import SupplierProductHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
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
)
from gqlapi.domain.models.v2.supplier import (
    SupplierUnit,
)
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from gqlapi.errors import GQLApiException
from gqlapi.repository.core.category import (
    CategoryRepository,
    RestaurantBranchCategoryRepository,
)
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
)
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
        "--supplier-business-id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--valid-until",
        help="Format YYYY-MM-DD",
        type=str,
        default=None,
        required=True,
    )

    parser.add_argument(
        "--supplier_price_lists",
        type=str,
        help="supplier_price_lists Template (XLSX)",
        required=True,
    )
    _args = parser.parse_args()
    if _args.supplier_price_lists.split(".")[-1] != "xlsx":
        raise Exception(
            "supplier_price_lists Template file has invalid format: Must be XLSX"
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


def normalize_supplier_price_list_data(df: pd.DataFrame) -> List[pd.DataFrame]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset({"sku", "supplier_product_id"}):
        raise Exception("Sheet de lista de precios tiene columnas faltantes!")

    return split_dataframe_by_restaurant(df)


async def upload_all_price_list(
    price_list_data: List[pd.DataFrame],
    supplier_business_id: UUID,
    valid_until: datetime.date,
    info: InjectedStrawberryInfo,
):
    supplier_user_repo = SupplierUserRepository(info)  # type: ignore
    _handler = SupplierRestaurantsHandler(
        supplier_restaurants_repo=SupplierRestaurantsRepository(info),  # type: ignore
        supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
        supplier_user_repo=supplier_user_repo,
        supplier_user_permission_repo=SupplierUserPermissionRepository(info),  # type: ignore
        restaurant_branch_repo=RestaurantBranchRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        restaurant_business_repo=RestaurantBusinessRepository(info),  # type: ignore
        restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),  # type: ignore
        category_repo=CategoryRepository(info),  # type: ignore
        restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),  # type: ignore
        product_repo=ProductRepository(info),  # type: ignore
        supplier_product_repo=SupplierProductRepository(info),  # type: ignore
        supplier_product_price_repo=SupplierProductPriceRepository(info),  # type: ignore
    )
    # instantiate handlers
    sp_handler = SupplierProductHandler(
        supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        supplier_user_repo=SupplierUserRepository(info),  # type: ignore
        supplier_user_permission_repo=SupplierUserPermissionRepository(info),  # type: ignore
        product_repo=ProductRepository(info),  # type: ignore
        category_repo=CategoryRepository(info),  # type: ignore
        supplier_product_repo=SupplierProductRepository(info),  # type: ignore
        supplier_product_price_repo=SupplierProductPriceRepository(info),  # type: ignore
        # supplier_product_stock_repo=SupplierProductStockRepository(info),
    )
    _handler = SupplierPriceListHandler(
        supplier_price_list_repo=SupplierPriceListRepository(info),  # type: ignore
        supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
        restaurant_branch_repo=RestaurantBranchRepository(info),  # type: ignore
        supplier_product_repo=SupplierProductRepository(info),  # type: ignore
        supplier_product_price_repo=SupplierProductPriceRepository(info),  # type: ignore
        supplier_product_handler=sp_handler,
    )
    sp_handler.supplier_price_list_handler = _handler

    try:
        core_user = await get_admin(info, supplier_business_id=supplier_business_id)
        units = await get_units(info, supplier_business_id=supplier_business_id)
        unit_dict = {unit.unit_name: unit for unit in units}
        price_list_relations = {}
        for price_list in price_list_data:
            price_list_name = price_list.columns[3]
            codes_names = [part.strip() for part in price_list_name.split("-")]
            spp_unit_name = codes_names[0]
            spp_list_name = codes_names[1]
            validation = price_list_relations.get(spp_list_name, None)
            unit = unit_dict.get(spp_unit_name, None)
            if not unit:
                logger.warning(f"Unit {spp_unit_name} not found")
                import pdb

                pdb.set_trace()
                continue
            if not validation:
                price_list_relations[spp_list_name] = [unit.id]
            else:
                price_list_relations[spp_list_name].append(unit.id)

        for price_list in price_list_data:
            price_list_name = price_list.columns[3]
            codes_names = [part.strip() for part in price_list_name.split("-")]
            spp_unit_name = codes_names[0]
            spp_list_name = codes_names[1]
            supplier_prices_dict = [
                {
                    "supplier_product_id": UUID(row["supplier_product_id"]),
                    "price": float(row[price_list_name]),
                    "valid_until": valid_until,
                }
                for index, row in price_list.iterrows()
            ]
            pl_relation = price_list_relations.get(spp_list_name, None)
            branch_ids = await fetch_last_supplier_price_list(
                info, pl_relation, spp_list_name
            )
            if not branch_ids and spp_list_name != "Lista General de Precios":
                logger.warning(f"List {spp_list_name} not found")
                continue
            prices_feedback = await _handler.edit_supplier_price_list(
                core_user.firebase_id,
                name=spp_list_name,
                supplier_unit_ids=pl_relation,
                supplier_prices=supplier_prices_dict,
                restaurant_branch_ids=branch_ids,
                is_default=(
                    True if spp_list_name == "Lista General de Precios" else False
                ),
                valid_until=valid_until,
            )
            if prices_feedback[0].status != "ok":
                continue
            else:
                logger.info(f"Price list {spp_list_name} updated")

    except GQLApiException as ge:
        raise Exception(ge.msg)


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


async def upload_supplier_price_list(
    supplier_price_list_data: List[pd.DataFrame],
    supplier_business_id: UUID,
    valid_until: str,
) -> Dict[Any, Any]:
    logger.info("Starting upload price lists ...")
    # Permite conectar a la db
    await db_startup()
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    valid_until_date = datetime.datetime.strptime(valid_until, "%Y-%m-%d").date()
    await upload_all_price_list(
        supplier_price_list_data, supplier_business_id, valid_until_date, _info
    )
    await db_shutdown()
    logger.info("Listo ...")
    return {"status": "ok", "data": "data"}


if __name__ == "__main__":
    try:
        pargs = parse_args()
        logger.info("Starting to upload all supplier price list db ...")

        xls = pd.ExcelFile(pargs.supplier_price_lists)
        logger.info("Starting upload supplier price list data...")
        price_list_data = normalize_supplier_price_list_data(
            pd.read_excel(
                xls,
                sheet_name="Sheet1",
                dtype={
                    "sku": str,
                },
            )
        )
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    resp = asyncio.run(
        upload_supplier_price_list(
            price_list_data, UUID(pargs.supplier_business_id), pargs.valid_until
        )
    )
    logger.info("Finished sync alima db!")
