"""How to run (file path as example):
    poetry run python -m gqlapi.scripts.authos.create_ecommerce_users_from_mails \
    --new_clients ../../../_cambios_DB/{file}.xlsx"""

from abc import ABC
import argparse
import asyncio
import base64
import secrets
import string
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    SupplierRestaurantCreationGQL,
)
from gqlapi.domain.models.v2.authos import IEcommerceUser
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.b2bcommerce.ecommerce_seller import EcommerceSellerHandler
from gqlapi.handlers.services.authos import EcommerceJWTHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.repository.b2bcommerce.ecommerce_seller import (
    EcommerceSellerRepository,
    EcommerceUserRestaurantRelationRepository,
)
from gqlapi.repository.core.category import (
    SupplierUnitCategoryRepository,
)
from gqlapi.repository.core.invoice import MxSatCertificateRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
)
from gqlapi.repository.services.authos import EcommerceUserRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
import numpy as np
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
import sys
from gqlapi.db import (
    database as SQLDatabase,
    db_startup,
    db_shutdown,
    authos_database as AuthosSQLDatabase,
)
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd

from strawberry import asdict, type as strawberry_type

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
        "--new_clients",
        type=str,
        help="Supplier Clients to eCommerce Template (XLSX)",
        required=True,
    )
    _args = parser.parse_args()
    if _args.new_clients.split(".")[-1] != "xlsx":
        raise Exception(
            "Supplier Clients to eCommerce Template file has invalid format: Must be XLSX"
        )
    return _args


@strawberry_type
class GmailsFeedback(ABC):
    email: str
    password: Optional[str] = None
    status: str
    msg: str
    restaurant_name: Optional[str] = None


def has_duplicates(input_list):
    # Use a set to check for duplicates
    seen = set()
    for value in input_list:
        if value in seen:
            return True  # Found a duplicate
        seen.add(value)
    return False  # No duplicates found


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    random_string = "".join(secrets.choice(characters) for _ in range(length))
    return random_string


async def upload_ecomerce_verify_client(
    ecommerse_seller_handler: EcommerceUserRestaurantRelationRepository,
    ecommerse_user_repo: EcommerceUserRepository,
    new_user: SupplierRestaurantCreationGQL,
    ref_secret_key: str,
):
    if await ecommerse_user_repo.fetch_by_email(
        email=new_user.restaurant_business_account.email, ref_secret_key=ref_secret_key  # type: ignore
    ):
        return GmailsFeedback(
            msg="Ese correo ya existe para este proveedor",
            email=new_user.restaurant_business_account.email,  # type: ignore
            password=None,
            status="Error",
        )
    else:
        password = generate_random_string(12)
        logger.info(new_user.restaurant_business_account.email + "/" + password)  # type: ignore
        ecommerce_user_id = uuid4()
        # encode password
        hpswd = EcommerceJWTHandler.hash_password(password)
        if not await ecommerse_user_repo.add(
            ref_secret_key=ref_secret_key,
            ecommerce_user=IEcommerceUser(
                id=ecommerce_user_id,
                first_name=new_user.restaurant_business.name,  # type: ignore
                last_name=new_user.restaurant_business.name,  # type: ignore
                email=new_user.restaurant_business_account.email,  # type: ignore
                phone_number=new_user.restaurant_business_account.phone_number,  # type: ignore
                password=hpswd,
            ),
        ):
            return GmailsFeedback(
                msg="Error al crear el usuario",
                email=new_user.restaurant_business_account.email,  # type: ignore
                password=None,
                status="Error",
            )
        try:
            if not await ecommerse_seller_handler.add(
                ecommerce_user_id=ecommerce_user_id,
                restaurant_business_id=new_user.restaurant_business.id,  # type: ignore
            ):
                if not await ecommerse_user_repo.delete(
                    ecommerce_user_id, ref_secret_key
                ):
                    raise Exception(f"Error al borrar el usuario {new_user.restaurant_business_account.email}")  # type: ignore
                return GmailsFeedback(
                    msg="Error al crear relacion",
                    email=new_user.restaurant_business_account.email,  # type: ignore
                    password=None,
                    status="Error",
                )
        except Exception:
            if not await ecommerse_user_repo.delete(ecommerce_user_id, ref_secret_key):
                raise Exception(f"Error al borrar el usuario{new_user.restaurant_business_account.email}")  # type: ignore
            return GmailsFeedback(
                msg="Error al crear relacion",
                email=new_user.restaurant_business_account.email,  # type: ignore
                password=None,
                status="Error",
            )
        return GmailsFeedback(
            msg="Ok",
            email=new_user.restaurant_business_account.email,  # type: ignore
            password=password,
            status="Ok",
            restaurant_name=new_user.restaurant_business.name,  # type: ignore
        )


async def verify_emails_to_upload(
    supp_rest: List[SupplierRestaurantCreationGQL],
    gmails: List[str],
    ecommerse_seller_handler: EcommerceUserRestaurantRelationRepository,
    ecommerse_user_repo: EcommerceUserRepository,
    secret_key: str,
) -> pd.DataFrame:
    gmails_feedback = []
    for gmail in gmails:
        res_bus_found: List[SupplierRestaurantCreationGQL] = []
        for rbao in supp_rest:
            if rbao.restaurant_business_account:
                if gmail == rbao.restaurant_business_account.email:
                    res_bus_found.append(rbao)
        if len(res_bus_found) == 0:
            gmails_feedback.append(
                GmailsFeedback(
                    msg="No se encontro Cliente de este mail",
                    email=gmail,
                    password=None,
                    status="Error",
                )
            )
            continue
        if len(res_bus_found) > 1:
            msg = "El correo pertenece a "
            for rbf in res_bus_found:
                if rbf.restaurant_business:
                    msg = msg + rbf.restaurant_business.name + ", "
            gmails_feedback.append(
                GmailsFeedback(msg=msg, email=gmail, password=None, status="Error")
            )
            continue

        gmails_feedback.append(
            await upload_ecomerce_verify_client(
                ecommerse_seller_handler,
                ecommerse_user_repo,
                res_bus_found[0],
                secret_key,
            )
        )
        continue
    gm_to_pd = []
    for gm in gmails_feedback:
        gm_to_pd.append(asdict(gm))
    return pd.DataFrame(gm_to_pd)


async def upload_ecommerce_clients(
    clients_data: List[Dict[Any, Any]],
    supplier_business_id: UUID,
    info: InjectedStrawberryInfo,
):
    gmails = []
    for client in clients_data:
        gmails.append(client["email"])
    if has_duplicates(gmails):
        raise GQLApiException(
            "Template has duplicated emails",
            GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
        )
    # instance handlers
    sup_rest_rel_handler = SupplierRestaurantsHandler(
        supplier_restaurants_repo=SupplierRestaurantsRepository(info),  # type: ignore
        supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
        supplier_user_repo=SupplierUserRepository(info),  # type: ignore
        supplier_user_permission_repo=SupplierUserPermissionRepository(info),  # type: ignore
        restaurant_branch_repo=RestaurantBranchRepository(info),  # type: ignore
        restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),  # type: ignore
    )
    sup_biz_handler = SupplierBusinessHandler(
        supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
        supplier_business_account_repo=SupplierBusinessAccountRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
    )
    sup_unit_handler = SupplierUnitHandler(
        supplier_unit_repo=SupplierUnitRepository(info),  # type: ignore
        unit_category_repo=SupplierUnitCategoryRepository(info),  # type: ignore
        supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),  # type: ignore
        core_user_repo=CoreUserRepository(info),  # type: ignore
        tax_info_repo=MxSatCertificateRepository(info),  # type: ignore
        supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
    )
    _ecommerce_user_rest_rel_repo = EcommerceUserRestaurantRelationRepository(info)  # type: ignore
    _ecommerce_user_repo = EcommerceUserRepository(info)  # type: ignore
    _handler = EcommerceSellerHandler(
        ecommerce_seller_repo=EcommerceSellerRepository(info),  # type: ignore
        supplier_business_handler=sup_biz_handler,
        supplier_unit_handler=sup_unit_handler,
    )
    ecomm_seller = await _handler.ecommerce_seller_repo.fetch(
        id_key="supplier_business_id", id_value=supplier_business_id
    )
    if not ecomm_seller:
        raise GQLApiException(
            "Ecommerce seller not found",
            GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
        )
    supplier_units = await sup_unit_handler.fetch_supplier_units(
        supplier_business_id=supplier_business_id
    )
    if len(supplier_units) == 0:
        raise GQLApiException(
            "Units not found",
            GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
        )
    supplier_unit_ids = []
    for unit in supplier_units:
        supplier_unit_ids.append(unit.id)
    supp_rest = await sup_rest_rel_handler.find_supplier_restaurants(
        supplier_unit_ids=supplier_unit_ids, supplier_business_id=supplier_business_id
    )
    if len(supp_rest) == 0:
        raise GQLApiException(
            "Restaurants not found",
            GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
        )

    # rest_buss_acc = await rest_bus_acc.find({"gmail": {"$in": gmails}})
    # if not rest_buss_acc:
    #     raise GQLApiException(
    #         "Restaurants Business Account not found",
    #         GQLApiErrorCodeType.FETCH_MONGO_DB_EMPTY_RECORD.value,
    #     )
    # rest_buss_acc_obj=[]
    # for rba in rest_buss_acc:
    #     rest_buss_acc_obj.append(RestaurantBusinessAccount(**rba))

    df = await verify_emails_to_upload(
        supp_rest,
        gmails,
        _ecommerce_user_rest_rel_repo,
        _ecommerce_user_repo,
        ecomm_seller.secret_key,
    )
    with pd.ExcelWriter(
        f"{str(supplier_business_id)}_ecommerce_clients.xlsx", engine="xlsxwriter"
    ) as writer:
        df.to_excel(writer, index=False)
    with open(f"{str(supplier_business_id)}_ecommerce_clients.xlsx", "rb") as file:
        base64.b64encode(file.read()).decode()


def normalize_clients_data(df: pd.DataFrame) -> List[Dict[Any, Any]]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset(
        {
            "email",
        }
    ):
        raise Exception("Sheet de ecommerce clients tiene columnas faltantes!")
    # clean data
    data = df[~df["email"].isnull()]
    # If no data on the sheet
    if data.empty:
        raise Exception("No se puede cargar archivo, la hoja está vacía.")
    data_dir = data.replace({np.nan: None}).to_dict("records")
    return data_dir


async def upload_supplier_ecommerce_clients(
    clients_data: List[Dict[Any, Any]], supplier_business_id: UUID
) -> Dict[Any, Any]:
    logger.info("Starting upload ecommerce catalog ...")
    # Permite conectar a la db
    await db_startup()
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase, AuthosSQLDatabase)
    logger.info("Starting upload ecommerce categories...")
    await upload_ecommerce_clients(clients_data, supplier_business_id, _info)
    await db_shutdown()
    logger.info("Listo ...")
    return {"status": "ok", "data": "data"}


if __name__ == "__main__":
    try:
        pargs = parse_args()
        logger.info("Starting to upload ecommerce supplier clients db ...")

        xls = pd.ExcelFile(pargs.new_clients)
        logger.info("Starting upload supplier data...")
        clients_data = normalize_clients_data(
            pd.read_excel(
                xls,
                sheet_name="Sheet1",
                dtype={"email": str},
            )
        )

    except Exception as e:
        logger.error(e)
        sys.exit(1)

    resp = asyncio.run(
        upload_supplier_ecommerce_clients(
            clients_data, UUID(pargs.supplier_business_id)
        )
    )
    logger.info("Finish to upload ecommerce supplier clients db ...")
