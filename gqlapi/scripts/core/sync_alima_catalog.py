"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.core.sync_alima_catalog \
        --alima_catalog_db ../../../_cambios_DB/{file}.xlsx"""


import argparse
import asyncio
import logging
from types import NoneType
from typing import Any, Dict, List
import uuid
from uuid import UUID
import sys
from gqlapi.domain.models.v2.core import (
    Category,
    CoreUser,
    Product,
    ProductFamily,
    ProductFamilyCategory,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
    SupplierProduct,
)
from gqlapi.domain.models.v2.utils import (
    CategoryType,
    DataTypeDecoder,
    DataTypeTraslate,
    NotificationChannelType,
    UOMType,
)
from gqlapi.config import ALIMA_ADMIN_BUSINESS
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.category import CategoryHandler
from gqlapi.handlers.core.product import ProductFamilyHandler, ProductHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.repository.core.category import (
    CategoryRepository,
    ProductFamilyCategoryRepository,
)
from gqlapi.repository.core.product import ProductFamilyRepository, ProductRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.utils.helpers import serialize_product_description
import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore


def normalize_category_data(df: pd.DataFrame) -> List[Dict[Any, Any]]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset(
        {"id", "name", "category_type", "keywords", "parent_product_category_id"}
    ):
        raise Exception("Sheet de category tiene columnas faltantes!")

    # clean data
    data = df[~df["name"].isnull()]

    # If no data on the sheet
    if data.empty:
        raise Exception(f"No se puede cargar archivo, la hoja {df.Name} está vacía.")

    # Uso apply junto a una función auxiliar.
    df["category_type"] = df["category_type"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["name"] = df["name"].apply(lambda value: " ".join(str(value).strip().split()))
    df["keywords"] = df["keywords"].apply(
        lambda value: " ".join(str(value).strip().split())
    )

    # converts the data to its respective data type
    try:
        data["id"] = data["id"].astype(int)
        data["name"] = data["name"].astype(str)
        data["category_type"] = data["category_type"].astype(str)
    except Exception:
        raise Exception("Algun valor tiene datos inválidos!")

    data["keywords"] = data["keywords"].fillna("")
    data["parent_product_category_id"] = data["parent_product_category_id"].fillna(0)
    if data.isnull().values.any():
        sys.exit()

    # Convert
    data = data.sort_values("parent_product_category_id", ascending=True)
    if data.isnull().values.any():
        raise Exception("Sheet de category tiene datos vacios")

    data_dir = data.to_dict("records")

    parent_validation_list = []
    for category in data_dir:
        try:
            category["category_type"] = CategoryType(category["category_type"].lower())
        except Exception:
            raise Exception(f"Error CategoryType in {category['name']}")
        if category["keywords"]:
            try:
                category["keywords"] = category["keywords"].split(",")
            except Exception:
                raise Exception(f"Error in keywords in {category['name']}")
        else:
            category["keywords"] = [""]
        if category["parent_product_category_id"] != 0:
            if category["parent_product_category_id"] in parent_validation_list:
                parent_validation_list.append(category["id"])
            else:
                raise Exception(f"No existe parent_category de {category['name']}")
        else:
            parent_validation_list.append(category["id"])

    return data_dir


def normalize_item_data(df: pd.DataFrame) -> List[Dict[Any, Any]]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset({"id", "name", "buy_unit"}):
        raise Exception("Sheet de category tiene columnas faltantes!")

    # clean data
    data = df[~df["name"].isnull()]

    # If no data on the sheet
    if data.empty:
        raise Exception(f"No se puede cargar archivo, la hoja {df.Name} está vacía.")

    # Uso apply junto a una función auxiliar.
    df["buy_unit"] = df["buy_unit"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["name"] = df["name"].apply(lambda value: " ".join(str(value).strip().split()))
    # df['keywords'] = df['keywords'].apply(lambda value:" ".join(str(value).strip().split()))

    # converts the data to its respective data type
    try:
        data["id"] = data["id"].astype(int)
        data["name"] = data["name"].astype(str)
        data["buy_unit"] = data["buy_unit"].astype(str).str.lower()
    except Exception:
        raise Exception("Algun item tiene datos inválidos!")

    if data.isnull().values.any():
        raise Exception("Sheet de items tiene datos vacios")

    data_dir = data.to_dict("records")
    for items in data_dir:
        # Dict={item_id, item_name, buy_unit, category_id}
        try:
            items["buy_unit"] = UOMType(
                DataTypeTraslate.get_uomtype_decode(items["buy_unit"])
            )
        except Exception:
            raise Exception(f"Error UOMType in {items['name']}")
    return data_dir


def normalize_cat_item_data(df: pd.DataFrame) -> List[Dict[Any, Any]]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset(
        {
            "id",
            "item_id",
            "product_category_id",
            "category_name",
            "item_name",
            "item_buyunit",
        }
    ):
        raise Exception("Sheet de category tiene columnas faltantes!")

    # clean data
    data = df[~df["item_name"].isnull()]

    # If no data on the sheet
    if data.empty:
        raise Exception(f"No se puede cargar archivo, la hoja {df.Name} está vacía.")

    # Uso apply junto a una función auxiliar.
    df["category_name"] = df["category_name"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["item_name"] = df["item_name"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["item_buyunit"] = df["item_buyunit"].apply(
        lambda value: " ".join(str(value).strip().split())
    )

    # converts the data to its respective data type
    try:
        data["item_id"] = data["item_id"].astype(int)
        data["id"] = data["id"].astype(str)
        data["product_category_id"] = data["product_category_id"].astype(int)
        data["category_name"] = data["category_name"].astype(str)
        data["item_name"] = data["item_name"].astype(str)
        data["item_buyunit"] = data["item_buyunit"].astype(str).str.lower()
    except Exception:
        raise Exception("Algun valor tiene datos inválidos!")
    if data.isnull().values.any():
        raise Exception("Sheet de category-item tiene datos vacios")
    data_dir = data.to_dict("records")
    return data_dir


def normalize_product_data(df: pd.DataFrame) -> List[Dict[Any, Any]]:
    # validate that it contains the most important columns
    if not set(df.columns).issuperset(
        {
            "id",
            "item_id",
            "item_name",
            "sku",
            "upc",
            "description",
            "keywords",
            "sell_unit",
            "conversion_factor",
            "buy_unit",
            "estimated_weight",
            "sat_code",
            "tax_amount",
        }
    ):
        raise Exception("Sheet de category tiene columnas faltantes!")

    # clean data
    data = df[~df["item_name"].isnull()]

    data["estimated_weight"] = data["estimated_weight"].fillna(0)

    data["upc"] = data["upc"].fillna("")

    # If no data on the sheet
    if data.empty:
        raise Exception(f"No se puede cargar archivo, la hoja {df.Name} está vacía.")

    # Uso apply junto a una función auxiliar.
    df["item_name"] = df["item_name"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["description"] = df["description"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["buy_unit"] = df["buy_unit"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["sell_unit"] = df["sell_unit"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    df["keywords"] = df["keywords"].apply(
        lambda value: " ".join(str(value).strip().split())
    )
    data["keywords"] = data["keywords"].fillna("")

    # converts the data to its respective data type
    try:
        data["keywords"] = data["keywords"].astype(str)
        data["conversion_factor"] = data["conversion_factor"].astype(float)
        data["estimated_weight"] = data["estimated_weight"].astype(float)
        data["sell_unit"] = data["sell_unit"].astype(str).str.lower()
        data["buy_unit"] = data["buy_unit"].astype(str).str.lower()
        data["sku"] = data["sku"].astype(int).astype(str)
        data["sat_code"] = data["sat_code"].astype(int).astype(str)
        # data["sku"] = data["sku"].astype(str)
    except Exception:
        raise Exception("Algun valor tiene datos inválidos!")
    if data.isnull().values.any():
        raise Exception("Sheet de products tiene datos vacios")
    data_dir = data.to_dict("records")

    for product in data_dir:
        validator_dict = get_validator(product=product)
        validator = validator_dict["validator"]
        if not validator:
            raise Exception("Un dato no contiene dato para validación")
        try:
            product["sell_unit"] = UOMType(
                DataTypeTraslate.get_uomtype_decode(product["sell_unit"])
            )
        except Exception:
            product["sell_unit"] = UOMType.KG
            # raise Exception(f"Error sell_unit in validator {validator_key} {validator}")
        try:
            product["buy_unit"] = UOMType(
                DataTypeTraslate.get_uomtype_decode(product["buy_unit"])
            )
        except Exception:
            product["buy_unit"] = UOMType.KG
            # raise Exception(f"Error buy_unit in validator {validator}")
        try:
            product["sku"] = str(product["sku"])
        except Exception:
            raise Exception(f"Error in sku in {validator}")
        try:
            product["keywords"] = get_keywords_format(product, validator)
        except Exception:
            raise Exception("Error de formato en keywords")

    return data_dir


def parse_args() -> argparse.Namespace:
    # get file xlsx from directory
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--alima_catalog_db", type=str, help="Alima catalog DB (XLSX)", required=True
    )
    _args = parser.parse_args()
    if _args.alima_catalog_db.split(".")[-1] != "xlsx":
        raise Exception("Alima catalog DB file has invalid format: Must be XLSX")
    return _args


def get_category(
    categories_dict_dir: List[Category] | NoneType, category: Dict[Any, Any]
) -> Category | NoneType:
    if categories_dict_dir:
        for category_dir in categories_dict_dir:
            if category["name"] == category_dir.name:
                return category_dir
    return None


def get_product_family(
    prod_fam_dict_dir: List[ProductFamily] | NoneType, item: Dict[Any, Any]
) -> ProductFamily | NoneType:
    if prod_fam_dict_dir:
        for prod_fam_dir in prod_fam_dict_dir:
            if (
                item["name"] == prod_fam_dir.name
                and item["buy_unit"].value == prod_fam_dir.buy_unit
            ):
                return prod_fam_dir
    return None


def set_product_values(
    prod: Product, product: Dict[Any, Any], sku: str | NoneType, upc: str | NoneType
) -> Dict[Any, Any]:
    update_product_values = {}
    if product["item_name"] == prod.name:
        update_product_values["item_name"] = None
    else:
        update_product_values["item_name"] = product["item_name"]
    if product["description"] == prod.description:
        update_product_values["description"] = None
    else:
        update_product_values["description"] = product["description"]
    if product["keywords"] == prod.keywords:
        update_product_values["keywords"] = None
    else:
        update_product_values["keywords"] = product["keywords"]
    if product["conversion_factor"] == prod.conversion_factor:
        update_product_values["conversion_factor"] = None
    else:
        update_product_values["conversion_factor"] = product["conversion_factor"]
    if product["buy_unit"].value == prod.buy_unit:
        update_product_values["buy_unit"] = None
    else:
        update_product_values["buy_unit"] = product["buy_unit"]

    if product["estimated_weight"] == prod.estimated_weight:
        update_product_values["estimated_weight"] = None
    else:
        update_product_values["estimated_weight"] = product["estimated_weight"]
    if product["sell_unit"].value == prod.sell_unit:
        update_product_values["sell_unit"] = None
    else:
        update_product_values["sell_unit"] = product["sell_unit"]
    if sku == prod.sku:
        update_product_values["sku"] = None
    else:
        update_product_values["sku"] = sku
    if upc == prod.upc:
        update_product_values["upc"] = None
    else:
        update_product_values["upc"] = upc
    return update_product_values


def set_supplier_product_values(
    supp_prod: SupplierProduct,
    product: Dict[Any, Any],
    alima_id: UUID,
    prod: Product,
    min_quantity: float,
    tax_unit: str,
) -> Dict[Any, Any]:
    update_product_values = {}

    if prod.id == supp_prod.product_id:
        update_product_values["product_id"] = None
    else:
        update_product_values["product_id"] = prod.id

    if product["description"] == supp_prod.description:
        update_product_values["description"] = None
    else:
        update_product_values["description"] = product["description"]
    if product["conversion_factor"] == supp_prod.conversion_factor:
        update_product_values["conversion_factor"] = None
    else:
        update_product_values["conversion_factor"] = product["conversion_factor"]
    if product["buy_unit"].value == supp_prod.buy_unit:
        update_product_values["buy_unit"] = None
    else:
        update_product_values["buy_unit"] = product["buy_unit"]
    if product["estimated_weight"] == supp_prod.estimated_weight:
        update_product_values["estimated_weight"] = None
    else:
        update_product_values["estimated_weight"] = product["estimated_weight"]
    if product["sell_unit"].value == supp_prod.sell_unit:
        update_product_values["sell_unit"] = None
    else:
        update_product_values["sell_unit"] = product["sell_unit"]
    if supp_prod.supplier_business_id == alima_id:
        update_product_values["supplier_business_id"] = None
    else:
        update_product_values["supplier_business_id"] = alima_id
    if supp_prod.tax_id == product["sat_code"]:
        update_product_values["sat_code"] = None
    else:
        update_product_values["sat_code"] = product["sat_code"]
    if supp_prod.min_quantity == min_quantity:
        update_product_values["min_quantity"] = None
    else:
        update_product_values["min_quantity"] = min_quantity
    if supp_prod.tax == product["tax_amount"]:
        update_product_values["tax_amount"] = None
    else:
        update_product_values["tax_amount"] = product["tax_amount"]
    if supp_prod.tax_unit == tax_unit:
        update_product_values["tax_unit"] = None
    else:
        update_product_values["tax_unit"] = tax_unit

    return update_product_values


def get_product_family_category(
    prod_fam_cat_dict_dir: List[ProductFamilyCategory] | NoneType,
    item: UUID,
    category: UUID,
) -> ProductFamilyCategory | NoneType:
    if prod_fam_cat_dict_dir:
        for prod_fam_cat_dir in prod_fam_cat_dict_dir:
            if (
                item == prod_fam_cat_dir.product_family_id
                and category == prod_fam_cat_dir.category_id
            ):
                return prod_fam_cat_dir
    return None


def get_product(
    prod_dict_dir: List[Product] | List[SupplierProduct] | NoneType,
    validator_key: str,
    validator: str,
) -> Product | SupplierProduct | NoneType:
    if prod_dict_dir:
        for prod_dir in prod_dict_dir:
            if validator_key == "upc":
                if prod_dir.upc == validator:
                    return prod_dir
            else:
                if prod_dir.sku == validator:
                    return prod_dir
    return None


async def upload_prod_families(
    item_data: List[Dict[Any, Any]],
    info: InjectedStrawberryInfo,
) -> Dict[Any, Any]:
    _prod_fam_handler = ProductFamilyHandler(
        prod_fam_repo=ProductFamilyRepository(info=info),  # type: ignore
        core_user_repo=CoreUserRepository(info=info),  # type: ignore
    )
    core_user = await get_admin(info)
    prod_fam_index = {}
    try:
        prod_fam_dict_dir = await _prod_fam_handler.search_product_families()
    except GQLApiException as ge:
        if ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
            prod_fam_dict_dir = None
        else:
            raise Exception("Error al buscar product families")
    try:
        for items in item_data:
            prod_fam = get_product_family(
                prod_fam_dict_dir=prod_fam_dict_dir, item=items
            )

            if prod_fam:
                try:
                    prod_fam_index[items["id"]] = prod_fam.id
                except Exception as e:
                    logging.error(e)
                    logging.warning(
                        f"No se puedo actualizar product family {prod_fam.name}"
                    )
            else:
                try:
                    new_prod_fam = await _prod_fam_handler.repository.new(
                        ProductFamily(
                            name=items["name"],
                            buy_unit=items["buy_unit"],
                            id=uuid.uuid4(),
                            created_by=core_user.id,  # type: ignore
                        )
                    )
                    prod_fam_index[items["id"]] = new_prod_fam
                except Exception as e:
                    logging.error(e)
                    raise Exception(f"No se puedo crear {items['name']}")
    except Exception:
        raise Exception
    return prod_fam_index


async def upload_prod_fam_categories(
    item_category_data: List[Dict[Any, Any]],
    category_index: Dict[Any, Any],
    prod_fam_index: Dict[Any, Any],
    info: InjectedStrawberryInfo,
):
    core_user = await get_admin(info)
    prod_fam_cat_repo = ProductFamilyCategoryRepository(info=info)  # type: ignore
    try:
        prod_fam_cat_dict_dir = await prod_fam_cat_repo.search()
    except GQLApiException as ge:
        if ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
            prod_fam_cat_dict_dir = None
        else:
            raise Exception("Error al buscar product families category")
    try:
        for pro_cat in item_category_data:
            prod_fam_cat = get_product_family_category(
                prod_fam_cat_dict_dir=prod_fam_cat_dict_dir,
                item=prod_fam_index[pro_cat["item_id"]],
                category=category_index[pro_cat["product_category_id"]],
            )

            if not prod_fam_cat:
                try:
                    await prod_fam_cat_repo.new(
                        prod_fam_category=ProductFamilyCategory(
                            product_family_id=prod_fam_index[pro_cat["item_id"]],
                            category_id=category_index[pro_cat["product_category_id"]],
                            created_by=core_user.id,  # type: ignore
                        )
                    )
                except GQLApiException as ge:
                    logging.error(ge.msg)
                    logging.warning(f"Error en {pro_cat['item_id']}")
                    raise Exception("Error al crear product families category")
    except Exception:
        raise Exception


async def upload_categories(
    category_data: List[Dict[Any, Any]], info: InjectedStrawberryInfo
) -> Dict[Any, Any]:
    _category_handler = CategoryHandler(
        category_repo=CategoryRepository(info=info),  # type: ignore
        core_user_repo=CoreUserRepository(info=info),  # type: ignore
    )
    core_user = await get_admin(info)
    category_index = {}

    try:
        categories_dict_dir = await _category_handler.search_categories(
            category_type=CategoryType.PRODUCT
        )

    except GQLApiException as ge:
        if ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
            categories_dict_dir = None
        else:
            raise Exception("Error al buscar product families")
    try:
        for category in category_data:
            if category["parent_product_category_id"] != 0:
                category["parent_product_category_id"] = category_index[
                    category["parent_product_category_id"]
                ]
            else:
                category["parent_product_category_id"] = None

            cat = get_category(
                category=category, categories_dict_dir=categories_dict_dir
            )

            if cat:
                category_index[category["id"]] = cat.id  # type: ignore
                if CategoryType(cat.category_type) == category["category_type"]:
                    cat_type = None
                else:
                    cat_type = category["category_type"]
                if cat.name == category["name"]:
                    cat_name = None
                else:
                    cat_name = category["name"]
                if cat.keywords == category["keywords"]:
                    cat_keywords = None
                else:
                    cat_keywords = category["keywords"]
                if cat.parent_category_id == category["parent_product_category_id"]:
                    cat_parent_product_category_id = None
                else:
                    cat_parent_product_category_id = category[
                        "parent_product_category_id"
                    ]
                try:
                    await _category_handler.repository.update(
                        category_id=cat.id,
                        name=cat_name,
                        keywords=cat_keywords,
                        category_type=cat_type,
                        parent_category_id=cat_parent_product_category_id,
                    )

                except GQLApiException as ge:
                    if (
                        ge.error_code
                        == GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value
                    ):
                        continue
                    else:
                        logging.error(ge.msg)
                        raise Exception(
                            f"Error al actualizar categoria {category['name']}"
                        )
            else:
                try:
                    cat = await _category_handler.repository.new(
                        Category(
                            id=uuid.uuid4(),
                            created_by=core_user.id,  # type: ignore
                            name=category["name"],
                            keywords=category["keywords"],
                            category_type=category["category_type"],
                            parent_category_id=category["parent_product_category_id"],
                        )
                    )
                    category_index[category["id"]] = cat
                except Exception as e:
                    logging.error(e)
                    logging.warning(f"No se puedo crear {category['name']}")
                    raise Exception("Error al crear categoria")
    except Exception:
        raise Exception
    return category_index


async def upload_products_loop(
    products_data: List[Dict[Any, Any]],
    prod_fam_index: Dict[Any, Any],
    _product_handler: ProductHandler,
    supp_prod_repo: SupplierProductRepository,
    core_user: CoreUser,
    alima_suppier: SupplierBusiness,
    prod_dict_dir: List[Product] | NoneType,
    supp_prod_dict_dir: List[SupplierProduct] | NoneType,
):
    for product in products_data:
        validator_dict = get_validator(product=product)
        validator_key = validator_dict["validator_key"]
        validator = validator_dict["validator"]
        min_quantity = get_min_quantity(product["sell_unit"])
        product["estimated_weight"] = get_estimated_weight(product["estimated_weight"])
        tax_unit = get_tax_unit(product["sell_unit"])
        try:
            prod = get_product(prod_dict_dir, validator_key, validator)

            if prod:
                new_key_values = get_new_validators(
                    validator_key=validator_key, product=product, prod=prod
                )
                sku = new_key_values["sku"]
                upc = new_key_values["upc"]

                try:
                    update_product = set_product_values(prod=prod, product=product, sku=sku, upc=upc)  # type: ignore
                    logging.debug("Editar producto")
                    await _product_handler.repository.update(
                        product_id=prod.id,
                        name=update_product["item_name"],
                        description=update_product["description"],
                        sku=update_product["sku"],
                        keywords=update_product["keywords"],
                        conversion_factor=update_product["conversion_factor"],
                        buy_unit=update_product["buy_unit"],
                        estimated_weight=update_product["estimated_weight"],
                        sell_unit=update_product["sell_unit"],
                        upc=update_product["upc"],
                    )
                except GQLApiException as ge:
                    if (
                        ge.error_code
                        == GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value
                    ):
                        pass
                    else:
                        logging.error(ge.msg)
                        raise Exception(
                            f"No se puedo actualizar {product['item_name']}"
                        )

            else:
                logging.debug("Crear Producto")
                try:
                    prod = Product(
                        id=uuid.uuid4(),
                        product_family_id=prod_fam_index[product["item_id"]],
                        name=product["item_name"],
                        description=product["description"],
                        sku=product["sku"],
                        keywords=product["keywords"],
                        conversion_factor=product["conversion_factor"],
                        buy_unit=product["buy_unit"],
                        estimated_weight=product["estimated_weight"],
                        created_by=core_user.id,  # type: ignore
                        sell_unit=product["sell_unit"],
                        upc=product["upc"],
                    )

                    await _product_handler.repository.new(
                        product=prod,
                        validate_by=validator_key,
                        validate_against=validator,
                    )
                except GQLApiException as ge:
                    logging.error(ge.msg)
                    raise Exception("Error al crear un nuevo product")
            product["sku"] = serialize_product_description(
                product["description"], product["sell_unit"]
            )
            validator_dict = get_validator(product=product)
            validator_key = validator_dict["validator_key"]
            validator = validator_dict["validator"]
            supp_prod = get_product(supp_prod_dict_dir, validator_key, validator)
            product["sku"] = serialize_product_description(
                    product["description"],
                    product["sell_unit"])
            if supp_prod:
                new_key_values = get_new_validators(
                    validator_key=validator_key, product=product, prod=supp_prod
                )
                sku = new_key_values["sku"]
                upc = new_key_values["upc"]
                try:
                    update_supp_prod_vals = set_supplier_product_values(
                        supp_prod=supp_prod,  # type: ignore
                        product=product,
                        prod=prod,  # type: ignore
                        alima_id=alima_suppier.id,
                        min_quantity=min_quantity,
                        tax_unit=tax_unit,
                    )
                    if not (
                        await supp_prod_repo.update(
                            id=supp_prod.id,
                            product_id=update_supp_prod_vals["product_id"],
                            sku=sku,
                            upc=upc,
                            description=update_supp_prod_vals["description"],
                            supplier_business_id=update_supp_prod_vals[
                                "supplier_business_id"
                            ],
                            tax_id=update_supp_prod_vals["sat_code"],
                            conversion_factor=update_supp_prod_vals[
                                "conversion_factor"
                            ],
                            buy_unit=update_supp_prod_vals["buy_unit"],
                            min_quantity=update_supp_prod_vals["min_quantity"],
                            estimated_weight=update_supp_prod_vals["estimated_weight"],
                            sell_unit=update_supp_prod_vals["sell_unit"],
                            tax=update_supp_prod_vals["tax_amount"],
                            tax_unit=update_supp_prod_vals["tax_unit"],
                        )
                    ):
                        continue
                except Exception:
                    raise Exception
            else:
                try:
                    logging.debug("Crear supplier prod")
                    await supp_prod_repo.new(
                        supplier_product=SupplierProduct(
                            id=uuid.uuid4(),
                            product_id=prod.id,  # type: ignore
                            sku=product["sku"],
                            upc=product["upc"],
                            description=product["description"],
                            supplier_business_id=alima_suppier.id,
                            tax_id=product["sat_code"],
                            tax_unit=tax_unit,
                            tax=product["tax_amount"],
                            conversion_factor=product["conversion_factor"],
                            buy_unit=product["buy_unit"],
                            unit_multiple=min_quantity,
                            min_quantity=min_quantity,
                            estimated_weight=product["estimated_weight"],
                            is_active=True,
                            created_by=core_user.id,  # type: ignore
                            sell_unit=product["sell_unit"],
                        )
                    )
                except Exception as e:
                    logging.error(e)
                    raise Exception("Error al crear supplier product")
        except Exception as e:
            logging.error(e)
            raise Exception("Error al crear supplier product")


async def upload_products(
    products_data: List[Dict[Any, Any]],
    prod_fam_index: Dict[Any, Any],
    info: InjectedStrawberryInfo,
):
    _product_handler = ProductHandler(
        prod_repo=ProductRepository(info=info),  # type: ignore
        prod_fam_repo=ProductFamilyRepository(info=info),  # type: ignore
        core_user_repo=CoreUserRepository(info=info),  # type: ignore
    )
    supp_prod_repo = SupplierProductRepository(info=info)  # type: ignore
    core_user = await get_admin(_info=info)
    alima_suppier = await get_alima_supplier(_info=info)

    try:
        prods_dict_dir = await _product_handler.search_products()
    except GQLApiException as ge:
        if ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
            prods_dict_dir = None
        else:
            raise Exception("Error al buscar products")
    try:
        supp_prods_dict_dir = await supp_prod_repo.search()
    except GQLApiException as ge:
        if ge.error_code == GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
            supp_prods_dict_dir = None
        else:
            raise Exception("Error al buscar products")

    await upload_products_loop(
        products_data=products_data,
        prod_fam_index=prod_fam_index,
        _product_handler=_product_handler,
        supp_prod_repo=supp_prod_repo,
        core_user=core_user,
        alima_suppier=alima_suppier,
        prod_dict_dir=prods_dict_dir,
        supp_prod_dict_dir=supp_prods_dict_dir,
    )


def get_keywords_format(product: Dict[Any, Any], validator):
    if product["keywords"]:
        try:
            return product["keywords"].split(",")
        except Exception:
            logging.error(f"Error in keywords in {validator}")
            raise Exception

    else:
        product["keywords"] = [""]


async def new_supplier_product(
    supp_prod_repo: SupplierProductRepository,
    product: Dict[Any, Any],
    new_product: Product,
    alima_suppier: SupplierBusiness,
    min_quantity: float,
    core_user: CoreUser,
):
    logging.debug("Crear supplier prod")
    await supp_prod_repo.new(
        supplier_product=SupplierProduct(
            id=uuid.uuid4(),
            product_id=new_product.id,  # type: ignore
            sku=product["sku"],
            upc=product["upc"],
            description=product["description"],
            supplier_business_id=alima_suppier.id,
            tax_id="",
            tax_unit="",
            tax=0,
            conversion_factor=product["conversion_factor"],
            buy_unit=product["buy_unit"],
            unit_multiple=1,
            min_quantity=min_quantity,
            estimated_weight=product["estimated_weight"],
            is_active=True,
            created_by=core_user.id,  # type: ignore
            sell_unit=product["sell_unit"],
        )
    )


def get_new_validators(
    validator_key: str, product: Dict[Any, Any], prod: Product | SupplierProduct
) -> Dict[Any, Any]:
    new_vals = {}
    if validator_key == "upc":
        new_vals["sku"] = product["sku"]
        new_vals["upc"] = get_upc_validator(product, prod)
        return new_vals
    else:
        new_vals["upc"] = None
        new_vals["sku"] = get_sku_validator(product, prod)
        return new_vals


def get_validator(product: Dict[Any, Any]) -> Dict[Any, Any]:
    validator_dict = {}
    if product["upc"]:
        validator_dict["validator_key"] = "upc"
        validator_dict["validator"] = product["upc"]
        return validator_dict
    else:
        validator_dict["validator_key"] = "sku"
        validator_dict["validator"] = product["sku"]
        return validator_dict


def get_sku_validator(product: Dict[Any, Any], prod: Product | SupplierProduct):
    if product["sku"] == prod.sku:
        return None
    else:
        return product["sku"]


def get_upc_validator(product: Dict[Any, Any], prod: Product | SupplierProduct):
    if product["upc"] == prod.upc:
        return None
    else:
        return product["upc"]


def get_tax_unit(uom_type: UOMType) -> str:
    return DataTypeDecoder.get_sat_unit_code(uom_type=uom_type.value)


def get_min_quantity(sell_unit: UOMType) -> float:
    if sell_unit == UOMType.KG:
        return 0.1
    else:
        return 1


def get_estimated_weight(estimated_weight: float) -> float | NoneType:
    if estimated_weight:
        return estimated_weight
    else:
        return None


async def get_alima_supplier(_info: InjectedStrawberryInfo) -> SupplierBusiness:
    _handler = SupplierBusinessHandler(supplier_business_repo=SupplierBusinessRepository(info=_info))  # type: ignore
    supplier_business_repo = SupplierBusinessRepository(info=_info)  # type: ignore
    try:
        tmp = await _handler.repository.fetch(UUID(ALIMA_ADMIN_BUSINESS))
        if not tmp:
            raise Exception("Error getting admin user")
        return SupplierBusiness(**tmp)
    except Exception:
        supplier_business_id = await supplier_business_repo.new(
            "Alima", "México", NotificationChannelType.EMAIL
        )
        return SupplierBusiness(
            **await supplier_business_repo.get(supplier_business_id)
        )


async def get_admin(_info: InjectedStrawberryInfo) -> CoreUser:
    core_repo = CoreUserRepository(info=_info)  # type: ignore
    try:
        tmp = await core_repo.get_by_email("admin")
        if not tmp:
            raise Exception("Error getting admin user")
        return tmp
    except Exception:
        admin_user_id = await core_repo.new(
            CoreUser(
                id=uuid.uuid4(),
                email="admin",
                first_name="Alima",
                last_name="Bot",
                firebase_id="admin",
            )
        )
        return await core_repo.get(admin_user_id)


async def search_pruduct_by_validator(
    validator_key: str, validator: str, _product_handler: ProductHandler
) -> Product:
    if validator_key == "upc":
        products_dir = await _product_handler.search_products(upc=validator)
    else:
        products_dir = await _product_handler.search_products(sku=validator)
    return products_dir[0]


async def search_supplier_pruduct_by_validator(
    validator_key: str, validator: str, supp_prod_repo: SupplierProductRepository
) -> SupplierProduct:
    if validator_key == "upc":
        sup_products_dir = await supp_prod_repo.search(upc=validator)
    else:
        sup_products_dir = await supp_prod_repo.search(sku=validator)
    return sup_products_dir[0]


async def upload_alima_catalog(
    category_data: List[Dict[Any, Any]],
    item_data: List[Dict[Any, Any]],
    cat_item_data: List[Dict[Any, Any]],
    product_data: List[Dict[Any, Any]],
) -> Dict[Any, Any]:
    logging.info("Starting upload catalog ...")
    # Permite conectar a la db
    await db_startup()
    _info = InjectedStrawberryInfo(db=SQLDatabase, mongo=None)
    logging.info("Starting upload categories...")
    category_index = await upload_categories(category_data, _info)
    logging.info("Starting upload products family...")
    prod_fam_index = await upload_prod_families(item_data, _info)
    logging.info("Starting upload product family category...")
    await upload_prod_fam_categories(
        cat_item_data, category_index, prod_fam_index, _info
    )
    logging.info("Starting upload products...")
    await upload_products(product_data, prod_fam_index, _info)
    await db_shutdown()
    logging.info("Listo ...")
    return {"status": "ok", "data": "data"}


if __name__ == "__main__":
    try:
        pargs = parse_args()

        logging.info("Starting to sync alima db ...")

        xls = pd.ExcelFile(pargs.alima_catalog_db)
        logging.info("Starting normalize category data...")
        category_data = normalize_category_data(
            pd.read_excel(xls, sheet_name="Category")
        )
        logging.info("Starting normalize item category data...")
        item_data = normalize_item_data(pd.read_excel(xls, sheet_name="Item"))
        logging.info("Starting normalize category  item data...")
        cat_item_data = normalize_cat_item_data(
            pd.read_excel(xls, sheet_name="Category-Item")
        )
        logging.info("Starting normalize product data ...")
        product_data = normalize_product_data(pd.read_excel(xls, sheet_name="Product"))
    except Exception as e:
        logging.error(e)
        sys.exit(1)

    resp = asyncio.run(
        upload_alima_catalog(category_data, item_data, cat_item_data, product_data)
    )
    logging.info("Finished sync alima db!")
