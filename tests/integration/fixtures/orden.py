import asyncio
import uuid
import pytest
from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp
from ..fixtures.gqlapi import fixture_gql_api  # noqa
from ..fixtures.firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown  # noqa
from ..mocks.orden import muck_new_normal_orden
from ..queries.orden import (
    query_test_cancel_orden,
    query_test_get_active_ordens_by_branch,
    query_test_get_historic_orden_by_branch,
    query_test_get_orden_details,
    query_test_new_normal_orden,
)


async def delete_orden(resp_js_new_normal_orden: Dict[Any, Any]):
    await db_startup()
    orden_status_query = """DELETE FROM orden_status
                WHERE orden_id = :orden_id"""
    orden_paystatus_query = """DELETE FROM orden_paystatus
                WHERE orden_id = :orden_id"""
    orden_details_query = """DELETE FROM orden_details
                WHERE orden_id = :orden_id"""
    cart_product_query = """DELETE FROM cart_product
                WHERE cart_id = :cart_id"""
    cart_query = """DELETE FROM cart
                WHERE id = :cart_id"""
    orden_query = """DELETE FROM orden
                WHERE id = :orden_id"""

    orden_values = {"orden_id": resp_js_new_normal_orden["data"]["newOrden"]["id"]}
    cart_prod_values = {
        "cart_id": resp_js_new_normal_orden["data"]["newOrden"]["details"]["cartId"]
    }

    await SQLDatabase.execute(
        query=orden_status_query,
        values=orden_values,
    )
    await SQLDatabase.execute(
        query=orden_paystatus_query,
        values=orden_values,
    )
    await SQLDatabase.execute(
        query=orden_details_query,
        values=orden_values,
    )
    await SQLDatabase.execute(
        query=cart_product_query,
        values=cart_prod_values,
    )
    await SQLDatabase.execute(
        query=cart_query,
        values=cart_prod_values,
    )
    await SQLDatabase.execute(
        query=orden_query,
        values=orden_values,
    )
    await db_shutdown()


@pytest.fixture(scope="session")
def test_ficture_new_normal_orden_ok(
    test_ficture_edit_restaurant_supplier_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_edit_restaurant_supplier_ok["user"]
    token = _user["idToken"]
    muck_new_normal_orden["supBId"] = test_ficture_edit_restaurant_supplier_ok[
        "resp_js_new_rest_supp"
    ]["data"]["newRestaurantSupplerCreation"]["supplierBusiness"]["id"]
    muck_new_normal_orden[
        "restaurantBranchId"
    ] = test_ficture_edit_restaurant_supplier_ok["resp_js_new_branch"]["data"][
        "newRestaurantBranch"
    ][
        "id"
    ]
    muck_new_normal_orden["cartProds"][
        "supplierProductId"
    ] = test_ficture_edit_restaurant_supplier_ok["resp_js_new_rest_supp"]["data"][
        "newRestaurantSupplerCreation"
    ][
        "products"
    ][
        0
    ][
        "product"
    ][
        "id"
    ]
    muck_new_normal_orden["cartProds"][
        "supplierProductPriceId"
    ] = test_ficture_edit_restaurant_supplier_ok["resp_js_new_rest_supp"]["data"][
        "newRestaurantSupplerCreation"
    ][
        "products"
    ][
        0
    ][
        "price"
    ][
        "id"
    ]
    # execute endpoint for new restaurant user
    resp_js_new_normal_orden = fixture_gql_api(
        token=token,
        query=query_test_new_normal_orden,
        variables=muck_new_normal_orden,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_edit_restaurant_supplier_ok["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_edit_restaurant_supplier_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_edit_restaurant_supplier_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_get_supp"
        ],
        "resp_js_edit_rest_supp": test_ficture_edit_restaurant_supplier_ok[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: algo["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": resp_js_new_normal_orden,
    }
    asyncio.run(delete_orden(resp_js_new_normal_orden))


@pytest.fixture(scope="session")
def test_ficture_new_normal_orden_error(
    test_ficture_new_normal_orden_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_new_normal_orden_ok["user"]
    token = _user["idToken"]
    muck_new_normal_orden["supBId"] = str(uuid.uuid4())
    muck_new_normal_orden["restaurantBranchId"] = str(uuid.uuid4())
    muck_new_normal_orden["cartProds"]["supplierProductId"] = str(uuid.uuid4())
    muck_new_normal_orden["cartProds"]["supplierProductPriceId"] = str(uuid.uuid4())
    # execute endpoint for new restaurant user
    resp_js_new_normal_orden_error = fixture_gql_api(
        token=token,
        query=query_test_new_normal_orden,
        variables=muck_new_normal_orden,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_new_normal_orden_ok["user"],
        "resp_js_new_rest_user": test_ficture_new_normal_orden_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_normal_orden_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_normal_orden_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_normal_orden_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_normal_orden_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_normal_orden_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_normal_orden_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_normal_orden_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_normal_orden_ok["resp_js_new_branch"],
        "resp_category": test_ficture_new_normal_orden_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_new_normal_orden_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_new_normal_orden_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_new_normal_orden_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_new_normal_orden_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_new_normal_orden_ok["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_new_normal_orden_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_new_normal_orden_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_new_normal_orden_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_new_normal_orden_ok["resp_js_edit_branch"],
        "resp_js_edit_branch_error": test_ficture_new_normal_orden_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_new_normal_orden_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_new_normal_orden_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_new_normal_orden_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_new_normal_orden_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_new_normal_orden_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_new_normal_orden_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_new_normal_orden_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_new_normal_orden_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_new_normal_orden_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_new_normal_orden_ok[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_new_normal_orden_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_new_normal_orden_ok["resp_js_get_supp"],
        "resp_js_edit_rest_supp": test_ficture_new_normal_orden_ok[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_new_normal_orden_ok["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_new_normal_orden_ok[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": resp_js_new_normal_orden_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_active_ordens_by_branch_ok(
    test_ficture_new_normal_orden_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_new_normal_orden_error["user"]
    token = _user["idToken"]
    muck_get_active_ordens = {}
    muck_get_active_ordens["branchId"] = test_ficture_new_normal_orden_error[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    muck_get_active_ordens["fromDate"] = "2023-01-01"
    # execute endpoint for new restaurant user
    resp_js_get_active_ordens = fixture_gql_api(
        token=token,
        query=query_test_get_active_ordens_by_branch,
        variables=muck_get_active_ordens,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_new_normal_orden_error["user"],
        "resp_js_new_rest_user": test_ficture_new_normal_orden_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_normal_orden_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_normal_orden_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_normal_orden_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_normal_orden_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_normal_orden_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_normal_orden_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_normal_orden_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_normal_orden_error["resp_js_new_branch"],
        "resp_category": test_ficture_new_normal_orden_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_new_normal_orden_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_new_normal_orden_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_new_normal_orden_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_new_normal_orden_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_new_normal_orden_error["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_new_normal_orden_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_new_normal_orden_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_new_normal_orden_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_new_normal_orden_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_new_normal_orden_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_new_normal_orden_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_new_normal_orden_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_new_normal_orden_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_new_normal_orden_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_new_normal_orden_error[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_new_normal_orden_error["resp_category"],
        "resp_js_new_rest_supp": test_ficture_new_normal_orden_error[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_new_normal_orden_error[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_new_normal_orden_error[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_new_normal_orden_error[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_new_normal_orden_error[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_new_normal_orden_error["resp_js_get_supp"],
        "resp_js_edit_rest_supp": test_ficture_new_normal_orden_error[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_new_normal_orden_ok["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_new_normal_orden_error[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_new_normal_orden_error[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": resp_js_get_active_ordens,
    }


@pytest.fixture(scope="session")
def test_ficture_get_active_ordens_by_branch_error(
    test_ficture_get_active_ordens_by_branch_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_active_ordens_by_branch_ok["user"]
    token = _user["idToken"]
    muck_get_active_ordens = {}
    muck_get_active_ordens["branchId"] = test_ficture_get_active_ordens_by_branch_ok[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    muck_get_active_ordens["fromDate"] = "2030-01-01"
    # execute endpoint for new restaurant user
    resp_js_get_active_ordens_error = fixture_gql_api(
        token=token,
        query=query_test_get_active_ordens_by_branch,
        variables=muck_get_active_ordens,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_active_ordens_by_branch_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_active_ordens_by_branch_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_active_ordens_by_branch_ok[
            "resp_category"
        ],
        "resp_js_new_rest_supp": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_supp"
        ],
        "resp_js_edit_rest_supp": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_new_normal_orden_ok["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_get_active_ordens_by_branch_ok[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": resp_js_get_active_ordens_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_orden_details_ok(
    test_ficture_get_active_ordens_by_branch_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_active_ordens_by_branch_error["user"]
    token = _user["idToken"]
    muck_get_ordens_details = {}
    muck_get_ordens_details["ordenId"] = test_ficture_get_active_ordens_by_branch_error[
        "resp_js_new_normal_orden"
    ]["data"]["newOrden"]["id"]

    # execute endpoint for new restaurant user
    resp_js_get_orden_details = fixture_gql_api(
        token=token,
        query=query_test_get_orden_details,
        variables=muck_get_ordens_details,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_active_ordens_by_branch_error["user"],
        "resp_js_new_rest_user": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_active_ordens_by_branch_error[
            "resp_category"
        ],
        "resp_js_new_branch_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_active_ordens_by_branch_error[
            "resp_category"
        ],
        "resp_js_new_rest_supp": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_supp"
        ],
        "resp_js_edit_rest_supp": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_new_normal_orden_ok["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_active_ordens_error"
        ],
        "resp_js_get_orden_details": resp_js_get_orden_details,
    }


@pytest.fixture
def test_ficture_get_orden_details_error(
    test_ficture_get_orden_details_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_orden_details_ok["user"]
    token = _user["idToken"]
    muck_get_ordens_details = {}
    muck_get_ordens_details["ordenId"] = str(uuid.uuid4())

    # execute endpoint for new restaurant user
    resp_js_get_orden_details_error = fixture_gql_api(
        token=token,
        query=query_test_get_orden_details,
        variables=muck_get_ordens_details,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_orden_details_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_orden_details_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_orden_details_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_orden_details_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_orden_details_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_orden_details_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_orden_details_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_orden_details_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_orden_details_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_orden_details_ok["resp_js_new_branch"],
        "resp_category": test_ficture_get_orden_details_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_orden_details_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_orden_details_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_orden_details_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_orden_details_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_orden_details_ok["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_get_orden_details_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_orden_details_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_orden_details_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_orden_details_ok["resp_js_edit_branch"],
        "resp_js_edit_branch_error": test_ficture_get_orden_details_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_orden_details_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_orden_details_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_orden_details_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_orden_details_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_orden_details_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_orden_details_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_get_orden_details_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_orden_details_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_orden_details_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_orden_details_ok[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_get_orden_details_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_orden_details_ok["resp_js_get_supp"],
        "resp_js_edit_rest_supp": test_ficture_get_orden_details_ok[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_get_active_ordens_by_branch_error["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_get_orden_details_ok[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_get_orden_details_ok[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_get_orden_details_ok[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": test_ficture_get_orden_details_ok[
            "resp_js_get_active_ordens_error"
        ],
        "resp_js_get_orden_details": test_ficture_get_orden_details_ok[
            "resp_js_get_orden_details"
        ],
        "resp_js_get_orden_details_error": resp_js_get_orden_details_error,
    }


@pytest.fixture
def test_ficture_get_historic_orden_by_branch_ok(
    test_ficture_get_orden_details_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_orden_details_error["user"]
    token = _user["idToken"]
    muck_get_historic_ordenes = {}
    muck_get_historic_ordenes["fromDate"] = "1000-01-01"
    muck_get_historic_ordenes["toDate"] = "3000-01-01"
    muck_get_historic_ordenes["branchId"] = test_ficture_get_orden_details_error[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    muck_get_historic_ordenes["supBId"] = test_ficture_get_orden_details_error[
        "resp_js_new_rest_supp"
    ]["data"]["newRestaurantSupplerCreation"]["supplierBusiness"]["id"]
    # execute endpoint for new restaurant user
    resp_js_get_historic_ordenes = fixture_gql_api(
        token=token,
        query=query_test_get_historic_orden_by_branch,
        variables=muck_get_historic_ordenes,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_orden_details_error["user"],
        "resp_js_new_rest_user": test_ficture_get_orden_details_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_orden_details_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_orden_details_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_orden_details_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_orden_details_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_orden_details_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_orden_details_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_orden_details_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_orden_details_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_orden_details_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_orden_details_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_orden_details_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_orden_details_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_orden_details_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_orden_details_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_orden_details_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_orden_details_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_orden_details_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_orden_details_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_orden_details_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_orden_details_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_orden_details_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_orden_details_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_orden_details_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_orden_details_error[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_orden_details_error["resp_category"],
        "resp_js_new_rest_supp": test_ficture_get_orden_details_error[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_orden_details_error[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_orden_details_error[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_orden_details_error[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_get_orden_details_error[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_orden_details_error["resp_js_get_supp"],
        "resp_js_edit_rest_supp": test_ficture_get_orden_details_error[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_get_active_ordens_by_branch_error["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_get_orden_details_error[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_get_orden_details_error[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_get_orden_details_error[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": test_ficture_get_orden_details_error[
            "resp_js_get_active_ordens_error"
        ],
        "resp_js_get_orden_details": test_ficture_get_orden_details_error[
            "resp_js_get_orden_details"
        ],
        "resp_js_get_orden_details_error": test_ficture_get_orden_details_error[
            "resp_js_get_orden_details_error"
        ],
        "resp_js_get_historic_ordenes": resp_js_get_historic_ordenes,
    }


@pytest.fixture
def test_ficture_get_historic_orden_by_branch_error(
    test_ficture_get_historic_orden_by_branch_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_historic_orden_by_branch_ok["user"]
    token = _user["idToken"]
    muck_get_historic_ordenes = {}
    muck_get_historic_ordenes["fromDate"] = "2030-01-01"
    muck_get_historic_ordenes["toDate"] = "2034-01-01"
    muck_get_historic_ordenes[
        "branchId"
    ] = test_ficture_get_historic_orden_by_branch_ok["resp_js_new_branch"]["data"][
        "newRestaurantBranch"
    ][
        "id"
    ]
    muck_get_historic_ordenes["supBId"] = test_ficture_get_historic_orden_by_branch_ok[
        "resp_js_new_rest_supp"
    ]["data"]["newRestaurantSupplerCreation"]["supplierBusiness"]["id"]
    # execute endpoint for new restaurant user
    resp_js_get_historic_ordenes_error = fixture_gql_api(
        token=token,
        query=query_test_get_historic_orden_by_branch,
        variables=muck_get_historic_ordenes,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_historic_orden_by_branch_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_historic_orden_by_branch_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_historic_orden_by_branch_ok[
            "resp_category"
        ],
        "resp_js_new_rest_supp": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_supp"
        ],
        "resp_js_edit_rest_supp": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_get_active_ordens_by_branch_error["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_active_ordens_error"
        ],
        "resp_js_get_orden_details": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_orden_details"
        ],
        "resp_js_get_orden_details_error": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_orden_details_error"
        ],
        "resp_js_get_historic_ordenes": test_ficture_get_historic_orden_by_branch_ok[
            "resp_js_get_historic_ordenes"
        ],
        "resp_js_get_historic_ordenes_error": resp_js_get_historic_ordenes_error,
    }


@pytest.fixture
def test_ficture_cancel_orden_ok(
    test_ficture_get_historic_orden_by_branch_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_historic_orden_by_branch_error["user"]
    token = _user["idToken"]

    # execute endpoint for new restaurant user
    resp_js_cancel_orden = fixture_gql_api(
        token=token,
        query=query_test_cancel_orden,
        variables={
            "ordenId": test_ficture_get_historic_orden_by_branch_error[
                "resp_js_new_normal_orden"
            ]["data"]["newOrden"]["id"]
        },
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_historic_orden_by_branch_error["user"],
        "resp_js_new_rest_user": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_historic_orden_by_branch_error[
            "resp_category"
        ],
        "resp_js_new_branch_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_set_branch_ok"
        ],
        "resp_supp_category": test_ficture_get_historic_orden_by_branch_error[
            "resp_category"
        ],
        "resp_js_new_rest_supp": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_rest_supp"
        ],
        "resp_js_new_rest_supp_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_supp_cat"
        ],
        "resp_js_get_supp_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_supp"
        ],
        "resp_js_edit_rest_supp": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_get_active_ordens_by_branch_error["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_active_ordens_error"
        ],
        "resp_js_get_orden_details": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_orden_details"
        ],
        "resp_js_get_orden_details_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_orden_details_error"
        ],
        "resp_js_get_historic_ordenes": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_historic_ordenes"
        ],
        "resp_js_get_historic_ordenes_error": test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_historic_ordenes_error"
        ],
        "resp_js_cancel_orden": resp_js_cancel_orden,
    }


@pytest.fixture
def test_ficture_cancel_orden_error(
    test_ficture_cancel_orden_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_cancel_orden_ok["user"]
    token = _user["idToken"]

    # execute endpoint for new restaurant user
    resp_js_cancel_orden_error = fixture_gql_api(
        token=token,
        query=query_test_cancel_orden,
        variables={"ordenId": str(uuid.uuid4())},
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_cancel_orden_ok["user"],
        "resp_js_new_rest_user": test_ficture_cancel_orden_ok["resp_js_new_rest_user"],
        "resp_js_new_rest_user_error": test_ficture_cancel_orden_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_cancel_orden_ok["resp_js_get_rest_user"],
        "resp_js_new_restaurant_business": test_ficture_cancel_orden_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_cancel_orden_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_cancel_orden_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_cancel_orden_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_cancel_orden_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_cancel_orden_ok["resp_js_new_branch"],
        "resp_category": test_ficture_cancel_orden_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_cancel_orden_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_cancel_orden_ok["resp_js_get_rest_cat"],
        "resp_js_new_branch_tax_id": test_ficture_cancel_orden_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_cancel_orden_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_cancel_orden_ok["resp_js_get_branch"],
        "resp_js_get_branch_error": test_ficture_cancel_orden_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_cancel_orden_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_cancel_orden_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_cancel_orden_ok["resp_js_edit_branch"],
        "resp_js_edit_branch_error": test_ficture_cancel_orden_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_cancel_orden_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_cancel_orden_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_cancel_orden_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_cancel_orden_ok[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": test_ficture_cancel_orden_ok["resp_js_set_branch_ok"],
        "resp_supp_category": test_ficture_cancel_orden_ok["resp_category"],
        "resp_js_new_rest_supp": test_ficture_cancel_orden_ok["resp_js_new_rest_supp"],
        "resp_js_new_rest_supp_error": test_ficture_cancel_orden_ok[
            "resp_js_new_rest_supp_error"
        ],
        "resp_js_get_active_supp": test_ficture_cancel_orden_ok[
            "resp_js_get_active_supp"
        ],
        "resp_js_get_supp_cat": test_ficture_cancel_orden_ok["resp_js_get_supp_cat"],
        "resp_js_get_supp_error": test_ficture_cancel_orden_ok[
            "resp_js_get_supp_error"
        ],
        "resp_js_get_supp": test_ficture_cancel_orden_ok["resp_js_get_supp"],
        "resp_js_edit_rest_supp": test_ficture_cancel_orden_ok[
            "resp_js_edit_rest_supp"
        ],
        # resp_js_rest_supp_file: test_ficture_get_active_ordens_by_branch_error["resp_js_rest_supp_file"]
        "resp_js_new_normal_orden": test_ficture_cancel_orden_ok[
            "resp_js_new_normal_orden"
        ],
        "resp_js_new_normal_orden_error": test_ficture_cancel_orden_ok[
            "resp_js_new_normal_orden_error"
        ],
        "resp_js_get_active_ordens": test_ficture_cancel_orden_ok[
            "resp_js_get_active_ordens"
        ],
        "resp_js_get_active_ordens_error": test_ficture_cancel_orden_ok[
            "resp_js_get_active_ordens_error"
        ],
        "resp_js_get_orden_details": test_ficture_cancel_orden_ok[
            "resp_js_get_orden_details"
        ],
        "resp_js_get_orden_details_error": test_ficture_cancel_orden_ok[
            "resp_js_get_orden_details_error"
        ],
        "resp_js_get_historic_ordenes": test_ficture_cancel_orden_ok[
            "resp_js_get_historic_ordenes"
        ],
        "resp_js_get_historic_ordenes_error": test_ficture_cancel_orden_ok[
            "resp_js_get_historic_ordenes_error"
        ],
        "resp_js_cancel_orden": test_ficture_cancel_orden_ok["resp_js_cancel_orden"],
        "resp_js_cancel_orden_error": resp_js_cancel_orden_error,
    }
