"""How to run (file path as example):
    poetry run python -m gqlapi.scripts.supplier.upload_batch_supplier_clients \
    --supplier_clients ../../../_cambios_DB/{file}.xlsx"""


import argparse
import asyncio
import logging
from gqlapi.handlers.restaurant.restaurant_branch import RestaurantBranchHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.mongo import mongo_db as MongoDatabase
import numpy as np
from typing import Any, Dict, List, Optional
from uuid import UUID
import sys
from gqlapi.domain.models.v2.core import (
    Category,
    CoreUser,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierUnit,
)
from gqlapi.domain.models.v2.utils import (
    CFDIUse,
    CategoryType,
    DataTypeDecoder,
    RegimenSat,
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
        "--supplier_clients",
        type=str,
        help="Supplier Clients Template (XLSX)",
        required=True,
    )
    _args = parser.parse_args()
    if _args.supplier_clients.split(".")[-1] != "xlsx":
        raise Exception(
            "Supplier Clients Template file has invalid format: Must be XLSX"
        )
    return _args


def convert_to_str(value):
    return str(value) if pd.notna(value) else value


def update_zip(zip_code):
    # Check if the zip code has 4 digits
    if len(str(zip_code)) == 0:
        # Add a leading zero to make it 5 digits
        return "0" + str(zip_code)
    if len(str(zip_code)) == 4:
        # Add a leading zero to make it 5 digits
        return "0" + str(zip_code)
    else:
        # Leave 5-digit zip codes unchanged
        return zip_code


def normalize_clients_data(df: pd.DataFrame) -> List[Dict[Any, Any]]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset(
        {
            "Nombre del Negocio",
            "Cedis Asignado",
            "Nombre de Contacto",
            "Correo electrónico",
            "Teléfono",
            "Calle",
            "Numero Ext",
            "Número Int",
            "Código Postal",
            "Colonia",
            "Municipio o Alcaldía",
            "Estado",
            "Pais",
            "Régimen Fiscal",
            "RFC",
            "Nombre o Razón Social",
            "Dirección Fiscal",
            "Uso CFDI",
            "CP Facturación",
            "Email Facturación",
            "Tipo de Factura",
            "Facturación Automática",
        }
    ):
        raise Exception("Sheet de category tiene columnas faltantes!")
    # clean data
    data = df[~df["Nombre del Negocio"].isnull()]
    # If no data on the sheet
    if data.empty:
        raise Exception(f"No se puede cargar archivo, la hoja {df.Name} está vacía.")
    # Use str.extract to apply the pattern and create a new column with the extracted numbers
    # data["Régimen Fiscal"] = data["Régimen Fiscal"].apply(
    #     lambda x: x.split("(")[1].split(")")[0]
    # )
    data["Nombre o Razón Social"] = data["Nombre o Razón Social"].str.strip()
    # data["Uso CFDI"] = data["Uso CFDI"].apply(lambda x: x.split("(")[1].split(")")[0])
    # converts the data to its respective data type
    try:
        data["Nombre del Negocio"] = data["Nombre del Negocio"].astype(str)
        data["Nombre de Contacto"] = data["Nombre de Contacto"].astype(str)
        data["Correo electrónico"] = data["Correo electrónico"].astype(str)
        data["Teléfono"] = data["Teléfono"].astype(str)
        data["Calle"] = data["Calle"].astype(str)
        data["Numero Ext"] = data["Numero Ext"].apply(convert_to_str)
        data["Numero Ext"] = data["Numero Ext"].fillna("")
        data["Número Int"] = data["Número Int"].apply(convert_to_str)
        data["Número Int"] = data["Número Int"].fillna("")
        data["Dirección Fiscal"] = data["Dirección Fiscal"].apply(convert_to_str)
        data["Dirección Fiscal"] = data["Dirección Fiscal"].fillna("")
        data["Código Postal"] = data["Código Postal"].astype(str)
        data["Código Postal"] = data["Código Postal"].apply(update_zip)
        data["Colonia"] = data["Colonia"].astype(str)
        data["Municipio o Alcaldía"] = data["Municipio o Alcaldía"].astype(str)
        data["Estado"] = data["Estado"].astype(str)
        data["Pais"] = data["Pais"].astype(str)
        data["Régimen Fiscal"] = data["Régimen Fiscal"].apply(convert_to_str)
        # data["Régimen Fiscal"] = data["Régimen Fiscal"].fillna("")
        data["RFC"] = data["RFC"].apply(convert_to_str)
        # data["RFC"] = data["RFC"].fillna("")
        data["Nombre o Razón Social"] = data["Nombre o Razón Social"].apply(
            convert_to_str
        )
        # data["Nombre o Razón Social"] = data["Nombre o Razón Social"].fillna("")
        data["Uso CFDI"] = data["Uso CFDI"].apply(convert_to_str)
        # data["Uso CFDI"] = data["Uso CFDI"].fillna("")
        data["CP Facturación"] = data["CP Facturación"].apply(convert_to_str)
        data["CP Facturación"] = data["CP Facturación"].apply(update_zip)
        data["Email Facturación"] = data["Email Facturación"].apply(convert_to_str)
    except Exception:
        raise Exception("Algun valor tiene datos inválidos!")
    data_dir = data.replace({np.nan: None}).to_dict("records")
    return data_dir


def get_full_address(client: Dict[Any, Any]) -> str:
    full_address = client["Calle"]
    if client["Numero Ext"]:
        full_address = full_address + " " + client["Numero Ext"]
    if client["Número Int"]:
        full_address = full_address + " " + client["Número Int"]
    return (
        full_address
        + ", "
        + client["Colonia"]
        + ", "
        + client["Municipio o Alcaldía"]
        + ", "
        + client["Estado"]
        + ", "
        + client["Pais"]
        + ", C.P. "
        + client["Código Postal"]
    )


async def upload_clients(
    clients_data: List[Dict[Any, Any]],
    supplier_business_id: UUID,
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
    _branch_handler = RestaurantBranchHandler(
        RestaurantBranchRepository(info),  # type: ignore
        RestaurantBranchCategoryRepository(info),  # type: ignore
    )
    core_user = await get_admin(info, supplier_business_id=supplier_business_id)
    # category = await get_category_other(info)
    units = await get_units(info, supplier_business_id=supplier_business_id)
    try:
        for client in clients_data:
            unit = await get_unit(unit_name=client["Cedis Asignado"], units=units)
            if not unit:
                raise Exception("Error to find units")
            if client["Uso CFDI"]:
                try:
                    client["Uso CFDI"] = CFDIUse(
                        DataTypeDecoder.get_cfdi_use_status_value(client["Uso CFDI"])
                    )
                except Exception:
                    print(f"Error CDFI USE {client['Nombre del Negocio']}")
                    logging.error(
                        f"Error to CFDI USE to {client['Nombre del Negocio']}"
                    )
                    continue
            if client["Régimen Fiscal"]:
                try:
                    client["Régimen Fiscal"] = RegimenSat(
                        DataTypeDecoder.get_sat_regimen_status_value(
                            client["Régimen Fiscal"]
                        )
                    )
                except Exception:
                    print(f"Error SAT REGIMEN {client['Nombre del Negocio']}")
                    logging.error(
                        f"Error to Sat Regimen to {client['Nombre del Negocio']}"
                    )
                    continue
            # if client["Tipo Factura"]:
            #     try:
            #         client["Tipo Factura"] = InvoiceType(client["Tipo Factura"])
            #     except Exception:
            #         print(f"Error Tipo Factura {client['Nombre del Negocio']}")
            #         logging.error(
            #             f"Error to Tipo Factura to {client['Nombre del Negocio']}"
            #         )
            #         continue

            # if client["Facturación Automática"]:
            #     try:
            #         client["Facturación Automática"] = InvoiceTriggerTime(client["Facturación Automática"])
            #     except Exception:
            #         print(f"Error Facturación Automática {client['Nombre del Negocio']}")
            #         logging.error(
            #             f"Error to Facturación Automática to {client['Nombre del Negocio']}"
            #         )
            #         continue

            sup_rest_creation = await _handler.new_supplier_restaurant_creation(
                firebase_id=core_user.firebase_id,
                supplier_unit_id=unit.id,
                name=client["Nombre del Negocio"],
                country=client["Pais"],
                # category_id=category.id,
                email=client["Correo electrónico"],
                phone_number=client["Teléfono"],
                contact_name=client["Nombre de Contacto"],
                branch_name=client["Nombre del Negocio"],
                full_address=get_full_address(client),
                street=client["Calle"],
                external_num=client["Numero Ext"],
                internal_num=client["Número Int"],
                neighborhood=client["Colonia"],
                city=client["Municipio o Alcaldía"],
                state=client["Estado"],
                zip_code=client["Código Postal"],
                rating=None,
                review=None,
            )
            if (
                client["RFC"]
                and client["Email Facturación"]
                and client["Nombre o Razón Social"]
                and client["CP Facturación"]
                and client["Régimen Fiscal"]
                and client["Uso CFDI"]
            ):
                await _branch_handler.edit_restaurant_branch_tax_info(
                    restaurant_branch_id=sup_rest_creation.relation.restaurant_branch_id,
                    mx_sat_id=client["RFC"],
                    email=client["Email Facturación"],
                    legal_name=client["Nombre o Razón Social"],
                    full_address=client["Dirección Fiscal"],
                    zip_code=client["CP Facturación"],
                    sat_regime=client["Régimen Fiscal"],
                    cfdi_use=client["Uso CFDI"],
                )
            else:
                logging.info("No complete tax info")

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


async def get_category_other(_info: InjectedStrawberryInfo) -> Category:
    category_repo = CategoryRepository(info=_info)  # type: ignore
    try:
        tmp = await category_repo.get_categories(
            name="Otro", category_type=CategoryType.RESTAURANT
        )
        if not tmp:
            raise Exception("Error getting category")
        return tmp[0]
    except Exception:
        raise Exception("Error getting category")


async def get_unit(
    units: List[SupplierUnit],
    unit_name: Optional[str] = None,
) -> SupplierUnit:
    for unit in units:
        if unit.unit_name == unit_name:
            return unit
    return units[0]


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


async def upload_supplier_clients(
    clients_data: List[Dict[Any, Any]], supplier_business_id: UUID
) -> Dict[Any, Any]:
    logging.info("Starting upload catalog ...")
    # Permite conectar a la db
    await db_startup()
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    logging.info("Starting upload categories...")
    await upload_clients(clients_data, supplier_business_id, _info)
    await db_shutdown()
    logging.info("Listo ...")
    return {"status": "ok", "data": "data"}


if __name__ == "__main__":
    try:
        pargs = parse_args()
        logging.info("Starting to upload supplier clients db ...")

        xls = pd.ExcelFile(pargs.supplier_clients)
        logging.info("Starting upload supplier data...")
        clients_data = normalize_clients_data(
            pd.read_excel(
                xls,
                sheet_name="Sheet1",
                dtype={
                    "Código Postal": str,
                    "Código Postal Facturación": str,
                    "Nombre o Razón Social": str,
                    "Tipo de Factura": str,
                    "Facturación Automática": str,
                },
            )
        )
    except Exception as e:
        logging.error(e)
        sys.exit(1)

    resp = asyncio.run(
        upload_supplier_clients(clients_data, UUID(pargs.supplier_business_id))
    )
    logging.info("Finished sync alima db!")
