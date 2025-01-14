"""
Script that generates a Stripe Transfer Payment Intents in Batch based on:
    - Supplier Business Id
    - Start Date

    -->
    - Supplier Business Id: The Supplier Business Id to filter the Ordenes
    - CSV: The CSV file with the Restaurant Branch ID and respective start date
        - restaurant_branch_id
        - start_date

How to run (file path as example):
    poetry run python -m gqlapi.scripts.personalized.supplier.batch_load_orden_payments_to_stripe \
    --supplier_business_id {supplier_business_id}
"""

import datetime
import argparse
import asyncio
import json
from pprint import pprint
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi, StripeCurrency
from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.models.v2.utils import DataTypeTraslate, OrdenStatusType, PayStatusType
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.integrations.integrations import IntegrationsWebhookandler
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
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
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.scripts.personalized.supplier.load_orden_payment_to_stripe import (
    get_stripe_tag,
)
from typing import List
from uuid import UUID
import sys
from gqlapi.domain.models.v2.supplier import (
    SupplierUnit,
)
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd
from gqlapi.lib.logger.logger.basic_logger import get_logger
from tqdm import tqdm

logger = get_logger(get_app())

pd.options.mode.chained_assignment = None  # type: ignore


def parse_args() -> argparse.Namespace:
    # get file xlsx from directory
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--supplier_business_id",
        type=str,
        help="supplier business_id",
        required=True,
    )
    parser.add_argument(
        "--restaurant_file",
        type=str,
        help="restaurants xlsx file",
        required=True,
    )
    _args = parser.parse_args()
    return _args


def normalize_restaurants_date(df: pd.DataFrame) -> pd.DataFrame:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset({"restaurant_branch_id", "start_date"}):
        raise Exception("Sheet de restaurantes tiene columnas faltantes!")
    df = df[~df["restaurant_branch_id"].isnull()]

    return df


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


async def set_not_paid_orden_in_stripe(
    _info: InjectedStrawberryInfo, supplier_business_id: UUID, rest_pd: pd.DataFrame
) -> bool:
    # convert start_date to datetime
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
    rest_branch_repo = RestaurantBranchRepository(_info)  # type: ignore
    integrations_weebhook_partner_handler = IntegrationsWebhookandler(
        repo=IntegrationWebhookRepository(_info)  # type: ignore
    )
    supplier_unit_repo = SupplierUnitRepository(_info)  # type: ignore
    supplier_units = await supplier_unit_repo.find(
        supplier_business_id=supplier_business_id
    )
    supplier_units_list = []
    for supplier_unit in supplier_units:
        supplier_units_list.append(SupplierUnit(**supplier_unit))
    ordenes: List[OrdenGQL] = []
    branches = rest_pd["restaurant_branch_id"].unique()
    for su in tqdm(supplier_units_list, desc="Orders from SUs"):
        for br in tqdm(branches, desc="Orders from Branches"):
            ordenes_unit = await _handler.find_orden(
                supplier_unit_id=su.id,
                restaurant_branch_id=br,
                from_date=datetime.datetime.strptime("2024-07-10", "%Y-%m-%d"),
                paystatus=PayStatusType.UNPAID,
            )
            if not ordenes_unit:
                continue
            ordenes.extend(ordenes_unit)
    if not ordenes:
        logger.info("No ordenes found")
        return False
    if not ordenes[0].supplier or not ordenes[0].supplier.supplier_business:
        raise GQLApiException(
            msg="Error to get supplier business",
            error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
        )
    # instance stripe
    workflow_vars = await integrations_weebhook_partner_handler.get_vars(
        ordenes[0].supplier.supplier_business.id
    )
    if not workflow_vars:
        raise GQLApiException(
            msg="Error to get workflow vars",
            error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
        )
    workflow_vars_json = json.loads(workflow_vars.vars)
    stripe_api_secret = workflow_vars_json.get("stripe_api_secret", None)
    if not stripe_api_secret:
        raise GQLApiException(
            msg="Error to get stripe api secret",
            error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
        )
    stripe_api = StripeApi(app_name=get_app(), stripe_api_secret=stripe_api_secret)
    ordenes_group_by_rest = {}
    for orden in ordenes:
        if not orden.branch or not orden.branch.id:
            continue
        if orden.status and orden.status.status == OrdenStatusType.CANCELED.value:
            continue
        if orden.branch.id in ordenes_group_by_rest:
            ordenes_group_by_rest[orden.branch.id].append(orden)
        else:
            ordenes_group_by_rest[orden.branch.id] = [orden]
    # sort cronologically each order by branch
    sorted_ordenes_group_by_rest = {}
    for key, ords in ordenes_group_by_rest.items():
        # verify start date
        filtered_date_series = rest_pd[rest_pd["restaurant_branch_id"] == str(key)][
            "start_date"
        ]
        if filtered_date_series.empty:
            continue
        filtered_date = datetime.datetime.strptime(
            filtered_date_series.iloc[0], "%Y-%m-%d %H:%M:%S"
        )
        sorted_ordenes_group_by_rest[key] = sorted(
            [v for v in ords if v.details.delivery_date >= filtered_date],
            key=lambda x: x.details.delivery_date,
            reverse=False,
        )
    import pdb

    pdb.set_trace()
    # group by por cada restaurante y luego hacer un loop por cada restaurante
    for key, ords in sorted_ordenes_group_by_rest.items():
        print(f"Procesando ordenes para el restaurante {key}")
        print(f"Total de ordenes: {len(ords)}")
        pprint(
            [
                {
                    "# Number": o.orden_number,
                    "Delivery Date": o.details.delivery_date,
                }
                for o in ords
            ]
        )
        flg = input("Desea continuar? (y/n): ")
        if flg != "y":
            print("Skiping ...")
            continue
        # skip not found restaurant branch
        if str(key) not in rest_pd["restaurant_branch_id"].values:
            continue
        # verify branch
        branch_tags = await rest_branch_repo.fetch_tags(key)
        if not branch_tags:
            print(f"No stripe value for this Restaurant Branch: {key}")
            continue
        stripe_value = get_stripe_tag(branch_tags)
        if not stripe_value:
            print(f"No stripe value for this Restaurant Branch: {key}")
            continue
        # get the start date for the restaurant branch
        results = 0
        for orden in ords:
            try:
                if (
                    not orden.details
                    or not orden.details.total
                    or not orden.supplier
                    or not orden.supplier.supplier_business
                    or not orden.branch
                    # or not orden.branch.tags
                    or not orden.supplier.supplier_business_account
                    or not orden.supplier.supplier_business_account.email
                    or not orden.status
                ):
                    logger.error(f"Orden {orden.id} not found")
                    continue
                if (
                    DataTypeTraslate.get_orden_status_encode(orden.status.status)
                    == "Cancelado"
                ):
                    continue
                stripe_api.create_transfer_payment_intent(
                    stripe_customer_id=stripe_value,
                    charge_description=f"PEDIDO: {orden.orden_number}",
                    charge_amount=orden.details.total,
                    email_to_confirm=orden.supplier.supplier_business_account.email,
                    currency=StripeCurrency.MXN,
                    charge_metadata={
                        "orden_id": str(orden.id),
                        "supplier_unit_id": str(orden.details.supplier_unit_id),
                        "restaurant_branch_id": str(orden.details.restaurant_branch_id),
                    },
                )
                results += 1
            except Exception as e:
                logger.error(e)
                continue
        print(f"Ordenes procesadas del restaurante ({key}): ", results)

    await db_shutdown()
    logger.info("Listo ...")
    return True


async def set_not_paid_orden_in_stripe_wrapper(
    supplier_business_id: UUID,
    restaurant_pd: pd.DataFrame,
) -> bool:
    logger.info("Starting set orden in stripe ...")
    # Permite conectar a la d
    await db_startup()
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    return await set_not_paid_orden_in_stripe(
        _info, supplier_business_id, restaurant_pd
    )


if __name__ == "__main__":
    try:
        pargs = parse_args()
        logger.info("Starting to set not paid orden in stripe ...")
        xls = pd.ExcelFile(pargs.restaurant_file)
        logger.info("Starting to set orden paid and generate paid receipt...")
        restaurant_pd = normalize_restaurants_date(
            pd.read_excel(
                xls,
                dtype={"restaurant_branch_id": str, "start_date": str},
            )
        )

    except Exception as e:
        logger.error(e)
        sys.exit(1)

    resp = asyncio.run(
        set_not_paid_orden_in_stripe_wrapper(pargs.supplier_business_id, restaurant_pd)
    )
    logger.info("Finished sync alima db!")
