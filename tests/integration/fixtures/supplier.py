import asyncio
from uuid import UUID

# import tempfile
# import os
# import pandas as pd
import uuid
import pymongo
from bson import Binary
from gqlapi.domain.models.v2.utils import (
    UOMType,
)
import pytest
from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.config import MONGO_DB_NAME, MONGO_URI
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from .gqlapi import (  # noqa
    test_ficture_firebase_signin_ok,  # noqa
    test_ficture_firebase_signup_ok_delete_ok,  # noqa
    fixture_gql_api,
)
from .restaurant_user import (  # noqa
    test_ficture_new_restaurant_user_ok,  # noqa
    test_ficture_get_restaurant_user_by_token_ok,  # noqa
    test_fixture_new_restaurant_user_error,  # noqa
)
from .restaurant_business import (  # noqa
    test_ficture_get_restaurant_business_ok,  # noqa
    test_ficture_new_restaurant_business_error,  # noqa
    test_ficture_new_restaurant_business_ok,  # noqa
    test_ficture_edit_restaurant_business_error,  # noqa
    test_ficture_edit_restaurant_business_ok,  # noqa
)
from .category import (  # noqa
    test_ficture_get_categoty_restaurant,  # noqa
    test_ficture_get_category_supplier,  # noqa
)
from ..mocks.supplier import mock_rest_supplier
from ..queries.supplier import (
    query_test_edit_rest_supp,
    query_test_get_active_supp,
    query_test_get_supp_cat,
    query_test_get_supp_profile,
    query_test_new_rest_supplier,
    # query_test_upload_supplier_file,
)


async def create_muck_product(user: Dict[Any, Any]) -> Dict[Any, Any]:
    await db_startup()
    # core_user = await get_core_user_by_firebase_id(user)

    prod_family_values = {
        "id": uuid.uuid4(),
        "name": "TestProdFamily",
        "buy_unit": UOMType.KG.value,
        "created_by": user["resp_js_new_rest_user"]["data"]["newRestaurantUser"][
            "coreUserId"
        ],
    }
    prod_fam_query = """INSERT INTO product_family
                (
                id,
                name,
                buy_unit,
                created_by
                )
                    VALUES
                    (:id,
                    :name,
                    :buy_unit,
                    :created_by)
                """
    await SQLDatabase.execute(
        query=prod_fam_query,
        values=prod_family_values,
    )
    prod_values = {
        "id": uuid.uuid4(),
        "product_family_id": prod_family_values["id"],
        "sku": "55432",
        "upc": "",
        "name": "productTest",
        "keywords": ["Product"],
        "description": "productTest",
        "sell_unit": UOMType.KG.value,
        "conversion_factor": 1,
        "buy_unit": UOMType.KG.value,
        "estimated_weight": 1,
        "created_by": user["resp_js_new_rest_user"]["data"]["newRestaurantUser"][
            "coreUserId"
        ],
    }
    prod_query = """INSERT INTO product
                (id,
                product_family_id,
                sku,
                upc,
                name,
                description,
                keywords,
                sell_unit,
                conversion_factor,
                buy_unit,
                estimated_weight,
                created_by
                )
                    VALUES
                    (:id,
                    :product_family_id,
                    :sku,
                    :upc,
                    :name,
                    :description,
                    :keywords,
                    :sell_unit,
                    :conversion_factor,
                    :buy_unit,
                    :estimated_weight,
                    :created_by)
                """

    await SQLDatabase.execute(
        query=prod_query,
        values=prod_values,
    )
    await db_shutdown()
    return prod_values


async def delete_restaurant_supplier(
    resp_js: Dict[Any, Any],
    supplier_product_id: Dict[Any, Any],
):
    await db_startup()
    supp_unit_cat_query = """DELETE FROM supplier_unit_category
                WHERE supplier_unit_id = :supplier_unit_id"""

    rest_supp_relation_query = """DELETE FROM restaurant_supplier_relation
                WHERE supplier_business_id = :supplier_business_id"""

    supp_prod_price_query = """DELETE FROM supplier_product_price
                WHERE id = :supp_prod_price_id"""

    supp_product_query = """DELETE FROM supplier_product
                WHERE id = :supplier_product_id"""

    supp_unit_query = """DELETE FROM supplier_unit
                WHERE supplier_business_id = :supplier_business_id"""

    supp_business_query = """DELETE FROM supplier_business
                WHERE id = :supplier_business_id"""

    supplier_values = {
        "supplier_business_id": resp_js["data"]["newRestaurantSupplerCreation"][
            "supplierBusiness"
        ]["id"]
    }

    unit_values = {
        "supplier_unit_id": resp_js["data"]["newRestaurantSupplerCreation"]["unit"][0][
            "supplierUnit"
        ]["id"]
    }
    supp_product_values = {"supplier_product_id": supplier_product_id["product"]["id"]}
    supp_prod_price_values = {"supp_prod_price_id": supplier_product_id["price"]["id"]}

    await SQLDatabase.execute(
        query=supp_unit_cat_query,
        values=unit_values,
    )
    await SQLDatabase.execute(
        query=rest_supp_relation_query,
        values=supplier_values,
    )
    await SQLDatabase.execute(
        query=supp_prod_price_query,
        values=supp_prod_price_values,
    )
    await SQLDatabase.execute(
        query=supp_product_query,
        values=supp_product_values,
    )
    await SQLDatabase.execute(
        query=supp_unit_query,
        values=supplier_values,
    )
    await SQLDatabase.execute(
        query=supp_business_query,
        values=supplier_values,
    )
    myclient = pymongo.MongoClient(MONGO_URI)
    mydb = myclient[MONGO_DB_NAME]

    collection = mydb["supplier_business_account"]
    query = {
        "supplier_business_id": Binary.from_uuid(
            UUID(
                resp_js["data"]["newRestaurantSupplerCreation"]["supplierBusiness"][
                    "id"
                ]
            )
        )
    }
    collection.delete_one(query)

    await db_shutdown()


async def delete_new_supplier_price(
    supplier_product_id: Dict[Any, Any],
):
    await db_startup()

    supp_prod_price_query = """DELETE FROM supplier_product_price
                WHERE id = :supp_prod_price_id"""

    supp_prod_price_values = {"supp_prod_price_id": supplier_product_id["price"]["id"]}

    await SQLDatabase.execute(
        query=supp_prod_price_query,
        values=supp_prod_price_values,
    )

    await db_shutdown()


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_supplier_ok(
    test_ficture_set_restaurant_branch_ok: Dict[str, Any],  # noqa
    test_ficture_get_category_supplier: Dict[Any, Any],  # noqa
):  # noqa
    _user = test_ficture_set_restaurant_branch_ok["user"]
    token = _user["idToken"]
    category_id = test_ficture_get_category_supplier["resp_category"]["id"]
    mock_rest_supplier["branchId"] = test_ficture_set_restaurant_branch_ok[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    mock_rest_supplier["catId"] = str(category_id)
    # execute endpoint for new restaurant user
    resp_js_new_rest_supp = fixture_gql_api(
        token=token,
        query=query_test_new_rest_supplier,
        variables=mock_rest_supplier,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_set_restaurant_branch_ok["user"],
        "resp_js_new_rest_user": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_set_restaurant_branch_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_set_restaurant_branch_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_set_restaurant_branch_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_set_restaurant_branch_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_set_restaurant_branch_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_set_restaurant_branch_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_set_restaurant_branch_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_category_supplier["resp_category"],
        "resp_js_new_rest_supp": resp_js_new_rest_supp,
    }

    asyncio.run(
        delete_restaurant_supplier(
            resp_js_new_rest_supp,
            resp_js_new_rest_supp["data"]["newRestaurantSupplerCreation"]["products"][
                0
            ],
        )
    )


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_supplier_error(
    test_ficture_new_restaurant_supplier_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_new_restaurant_supplier_ok["user"]
    token = _user["idToken"]

    mock_rest_supplier["branchId"] = test_ficture_new_restaurant_supplier_ok[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    mock_rest_supplier["catId"] = str(uuid.uuid4())

    # execute endpoint for new restaurant user
    resp_js_new_rest_supp_error = fixture_gql_api(
        token=token,
        query=query_test_new_rest_supplier,
        variables=mock_rest_supplier,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_new_restaurant_supplier_ok["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_restaurant_supplier_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_new_restaurant_supplier_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_new_restaurant_supplier_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_new_restaurant_supplier_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_new_restaurant_supplier_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_new_restaurant_supplier_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_new_restaurant_supplier_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_new_restaurant_supplier_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_new_restaurant_supplier_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": resp_js_new_rest_supp_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_active_supplier_ok(
    test_ficture_new_restaurant_supplier_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_new_restaurant_supplier_error["user"]
    token = _user["idToken"]
    resp_js_get_active_supp = fixture_gql_api(
        query=query_test_get_active_supp,
        method="POST",
        authorization="restobasic",
        token=token,
    )
    yield {
        "user": test_ficture_new_restaurant_supplier_error["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_restaurant_supplier_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_new_restaurant_supplier_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_new_restaurant_supplier_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_new_restaurant_supplier_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_new_restaurant_supplier_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_new_restaurant_supplier_error[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_new_restaurant_supplier_error[
            "resp_category"
        ],
        "resp_js_new_rest_supp": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_new_restaurant_supplier_error[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": resp_js_get_active_supp,
    }


@pytest.fixture(scope="session")
def test_ficture_get_supplier_categories_ok(
    test_ficture_get_active_supplier_ok: Dict[str, Any]  # noqa
):  # noqa
    # execute endpoint for new restaurant user
    resp_js_get_supp_cat = fixture_gql_api(
        query=query_test_get_supp_cat,
        method="POST",
    )

    yield {
        "user": test_ficture_get_active_supplier_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_active_supplier_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_active_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_active_supplier_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_active_supplier_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_active_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_active_supplier_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_active_supplier_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_active_supplier_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_active_supplier_ok["resp_js_new_branch"],
        "resp_category": test_ficture_get_active_supplier_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_active_supplier_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_active_supplier_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_active_supplier_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_active_supplier_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_active_supplier_ok["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_get_active_supplier_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_active_supplier_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_active_supplier_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_active_supplier_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_active_supplier_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_active_supplier_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_active_supplier_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_active_supplier_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_active_supplier_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_active_supplier_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_active_supplier_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_get_active_supplier_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_active_supplier_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_active_supplier_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": resp_js_get_supp_cat,
    }


@pytest.fixture(scope="session")
def test_ficture_get_supplier_error(
    test_ficture_get_supplier_categories_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_supplier_categories_ok["user"]
    token = _user["idToken"]
    resp_js_get_supp_error = fixture_gql_api(
        query=query_test_get_supp_profile,
        method="POST",
        variables={"supplierId": str(uuid.uuid4())},
        authorization="restobasic",
        token=token,
    )

    yield {
        "user": test_ficture_get_supplier_categories_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_supplier_categories_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_supplier_categories_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_supplier_categories_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_supplier_categories_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_supplier_categories_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_supplier_categories_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_supplier_categories_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_supplier_categories_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_supplier_categories_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_supplier_categories_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_supplier_categories_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_supplier_categories_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_supplier_categories_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_supplier_categories_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_supplier_categories_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_supplier_categories_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_supplier_categories_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_supplier_categories_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_supplier_categories_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_supplier_categories_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_supplier_categories_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_supplier_categories_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_supplier_categories_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_supplier_categories_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_supplier_categories_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_supplier_categories_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_get_supplier_categories_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_supplier_categories_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_supplier_categories_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_supplier_categories_ok[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": resp_js_get_supp_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_supplier_ok(
    test_ficture_get_supplier_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_supplier_error["user"]
    token = _user["idToken"]
    resp_js_get_supp = fixture_gql_api(
        query=query_test_get_supp_profile,
        method="POST",
        variables={
            "supplierId": test_ficture_get_supplier_error["resp_js_new_rest_supp"][
                "data"
            ]["newRestaurantSupplerCreation"]["supplierBusiness"]["id"]
        },
        authorization="restobasic",
        token=token,
    )

    yield {
        "user": test_ficture_get_supplier_error["user"],
        "resp_js_new_rest_user": test_ficture_get_supplier_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_supplier_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_supplier_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_supplier_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_supplier_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_supplier_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_supplier_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_supplier_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_supplier_error["resp_js_new_branch"],
        "resp_category": test_ficture_get_supplier_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_supplier_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_supplier_error["resp_js_get_rest_cat"],
        "resp_js_new_branch_tax_id": test_ficture_get_supplier_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_supplier_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_supplier_error["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_get_supplier_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_supplier_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_supplier_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_supplier_error["resp_js_edit_branch"],
        "resp_js_edit_branch_error": test_ficture_get_supplier_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_supplier_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_supplier_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_supplier_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_supplier_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_supplier_error[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_supplier_error["resp_category"],
        "resp_js_new_rest_supp": test_ficture_get_supplier_error[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_supplier_error[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_supplier_error[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_supplier_error["resp_js_get_supp_cat"],
        "resp_js_get_supp_error": test_ficture_get_supplier_error[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": resp_js_get_supp,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_supplier_ok(
    test_ficture_get_supplier_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_supplier_ok["user"]
    token = _user["idToken"]

    mock_rest_supplier["branchId"] = test_ficture_get_supplier_ok["resp_js_new_branch"][
        "data"
    ]["newRestaurantBranch"]["id"]

    mock_rest_supplier["catId"] = str(
        test_ficture_get_supplier_ok["resp_supp_category"]["id"]
    )
    mock_rest_supplier["supId"] = test_ficture_get_supplier_ok["resp_js_new_rest_supp"][
        "data"
    ]["newRestaurantSupplerCreation"]["supplierBusiness"]["id"]
    mock_rest_supplier["country"] = "EU"

    mock_rest_supplier["catalog"]["product"]["id"] = test_ficture_get_supplier_ok[
        "resp_js_new_rest_supp"
    ]["data"]["newRestaurantSupplerCreation"]["supplierBusiness"]["id"]
    mock_rest_supplier["catalog"]["product"]["id"] = test_ficture_get_supplier_ok[
        "resp_js_new_rest_supp"
    ]["data"]["newRestaurantSupplerCreation"]["products"][0]["product"]["id"]

    mock_rest_supplier["catalog"]["product"]["sku"] = "321"
    mock_rest_supplier["catalog"]["price"]["price"] = 2.5
    # execute endpoint for new restaurant user
    resp_js_edit_rest_supp = fixture_gql_api(
        token=token,
        query=query_test_edit_rest_supp,
        variables=mock_rest_supplier,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_supplier_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_supplier_ok["resp_js_new_rest_user"],
        "resp_js_new_rest_user_error": test_ficture_get_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_supplier_ok["resp_js_get_rest_user"],
        "resp_js_new_restaurant_business": test_ficture_get_supplier_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_supplier_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_supplier_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_supplier_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_supplier_ok["resp_js_new_branch"],
        "resp_category": test_ficture_get_supplier_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_supplier_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_supplier_ok["resp_js_get_rest_cat"],
        "resp_js_new_branch_tax_id": test_ficture_get_supplier_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_supplier_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_supplier_ok["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_get_supplier_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_supplier_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_supplier_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_supplier_ok["resp_js_edit_branch"],
        "resp_js_edit_branch_error": test_ficture_get_supplier_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_supplier_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_supplier_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_supplier_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_supplier_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_supplier_ok["resp_js_set_branch_ok"],
        "resp_supp_category": test_ficture_get_supplier_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_get_supplier_ok["resp_js_new_rest_supp"],
        "resp_js_new_rest_supp_error": test_ficture_get_supplier_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_supplier_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_supplier_ok["resp_js_get_supp_cat"],
        "resp_js_get_supp_error": test_ficture_get_supplier_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_supplier_ok["resp_js_get_supp"],
        "resp_js_edit_rest_supp": resp_js_edit_rest_supp,
    }
    asyncio.run(
        delete_new_supplier_price(
            resp_js_edit_rest_supp["data"]["updateRestaurantSupplerCreation"][
                "products"
            ][0]
        )
    )


# @pytest.fixture(scope="session")
# def test_ficture_new_restaurant_supplier_file_ok(
#     test_ficture_edit_restaurant_supplier_ok: Dict[str, Any]  # noqa
# ):  # noqa
#     _user = test_ficture_new_restaurant_branch["user"]
#     token = _user["idToken"]
#     mock_rest_supplier_file = {}
#     mock_rest_supplier_file["restaurantBranchId"] = test_ficture_new_restaurant_branch[
#         "resp_js_new_branch"
#     ]["data"]["newRestaurantBranch"]["id"]

#     prefix_supp = "ProveedoresTest"
#     fd, path_supp = tempfile.mkstemp(
#         prefix=prefix_supp, suffix=".xlsx", dir=os.getcwd()
#     )
#     prefix_prod = "ProdsTest"
#     fd, path_prod = tempfile.mkstemp(
#         prefix=prefix_prod, suffix=".xlsx", dir=os.getcwd()
#     )

#     df_supp = pd.DataFrame(
#         data=[
#             [
#                 "FerchoTest",
#                 "email",
#                 "5544332211",
#                 "FerchoTest@alima.la",
#                 "SupplierCategoryTest",
#             ]
#         ],
#         index=["supplier_business_name"],
#         columns=[
#             "supplier_business_name",
#             "notification_preference",
#             "phone_number",
#             "email",
#             "category",
#         ],
#     )
#     df_prod = pd.DataFrame(
#         data=[["FerchoTest", "ProdTest", "Kg", 1]],
#         index=["supplier_business_name"],
#         columns=["supplier_business_name", "description", "sell_unit", "price"],
#     )
#     try:
#         with pd.ExcelWriter(path_supp, engine="openpyxl") as supp_writer:
#             df_supp.to_excel(supp_writer, "Sheet1", index=False)
#         print(path_supp)
#         print(path_prod.split("/")[-1])
#         with pd.ExcelWriter(path_prod, engine="openpyxl") as prod_writer:
#             df_prod.to_excel(prod_writer, "Sheet1", index=False)

#         payload = {"operations": "mutation uploadBatchRestoSuppliers( $productsfile: Upload!, $restaurantBranchId: UUID!, $supplierFile: Upload!) { newSupplierFile( productFile: $productsfile, restaurantBranchId: $restaurantBranchId, supplierFile: $supplierFile ) { ... on RestaurantSupplierBatchGQL { resMsg: msg products { description msg status sku supplierName} suppliers { uuid status name msg } } ... on RestaurantSupplierError { code } } }, 'variables': { 'productsfile': null, 'restaurantBranchId': '6fe430ca-c88e-4823-8a9e-7a6948739f54', 'supplierFile': null } }", # noqa
#                    "map": '{ "suppFile": ["variables.supplierFile"], "prodfile": ["variables.productsfile"] }',
#         }
#         files = [
#             (
#                 "prodfile",
#                 (
#                     path_prod.split("/")[-1],
#                     open(path_prod, "rb"),
#                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 ),
#             ),
#             (
#                 "suppFile",
#                 (
#                     path_supp.split("/")[-1],
#                     open(path_supp, "rb"),
#                     "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
#                 ),
#             ),
#         ]

#         headers = {
#             "Authorization": f"restobasic {token}"
#         }

#         response = requests.request(
#             "POST", url_test, headers=headers, data=payload, files=files
#         )

#         print(response.text)
#         # resp_js_new_rest_supp = response.json()

#         # print(resp_js_new_rest_supp)
#     finally:
#         os.remove(path_supp)
#         os.remove(path_prod)

#     # yield {
#     #     "user": test_ficture_new_restaurant_branch["user"],
#     #     "resp_js_new_rest_user": test_ficture_new_restaurant_branch[
#     #         "resp_js_new_rest_user"
#     #     ],
#     #     "resp_js_new_restaurant_business": test_ficture_new_restaurant_branch[
#     #         "resp_js_new_restaurant_business"
#     #     ],
#     #     "resp_js_new_branch": test_ficture_new_restaurant_branch["resp_js_new_branch"],
#     #     "resp_js_category_id": test_ficture_new_restaurant_branch[
#     #         "resp_js_category_id"
#     #     ],
#     #     "resp_js_supp_category_id": str(category_id),
#     #     "resp_js_product": prod_values,
#     #     "resp_js_new_rest_supp": resp_js_new_rest_supp,
#     # }
#     yield True

#     # asyncio.run(
#     #     delete_restaurant_supplier(
#     #         resp_js_new_rest_supp,
#     #         resp_js_new_rest_supp["data"]["newRestaurantSupplerCreation"]["products"][
#     #             0
#     #         ],
#     #     )
#     # )


# # payload = {'operations':
# #         """{ "query": "mutation uploadRestoInvoice(
# #           $pdf: Upload!,
# #           $xml: Upload!,
# #           $ordenId: UUID!) {
# #         uploadInvoice(
# #           ordenId: $ordenId,
# #           pdfFile: $pdf,
# #           xmlFile: $xml) {
# #         ... on MxUploadInvoice {
# #               success msg
# #             }
# #         ... on MxInvoiceError {
# #               code
# #             }
# #           }
# #         },
# #         "variables": { "pdf": null, "ordenId": "6fe430ca-c88e-4823-8a9e-7a6948739f54", "xml": null } }""",

# #       'map':
# #       """{ "xml": ["variables.xml"], "pdf": ["variables.pdf"] }"""}

# # files=[
# #         ('pdf',('Factura-11232-PTA1908265U0.pdf',
# open('/Users/jorgevizcayno/Downloads/Factura-11232-/Factura-11232-PTA1908265U0.pdf','rb'),'application/pdf')),
# #         ('xml',('Factura-11232-PTA1908265U0.xml',
# open('/Users/jorgevizcayno/Downloads/Factura-11232-/Factura-11232-PTA1908265U0.xml','rb'),'text/xml'))
# #       ]
