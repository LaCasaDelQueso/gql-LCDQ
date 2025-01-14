import asyncio
from uuid import UUID
import uuid
import pytest
from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown  # noqa
from .firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from .gqlapi import (  # noqa
    test_ficture_firebase_signin_ok,  # noqa
    test_ficture_firebase_signup_ok_delete_ok,  # noqa
    fixture_gql_api,  # noqa
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
from .category import test_ficture_get_categoty_restaurant  # noqa
from ..mocks.restaurant_branch import (
    mock_branch_tax_info,
    mock_branch_tax_info_error,
    mock_rest_branch,
    mock_rest_branch_error,
)
from ..queries.restaurant_branch import (
    query_test_delete_branch,
    query_test_edit_branch,
    query_test_edit_branch_tax_id,
    query_test_get_branch_by_id,
    query_test_get_branches,
    query_test_get_rest_cat,
    query_test_new_branch_tax_info,
    query_test_new_restaurant_branch,
)


async def delete_restauran_branch_tax_info(resp_js: Dict[Any, Any]):
    await db_startup()
    rest_branch_tax_query = """DELETE FROM restaurant_branch_mx_invoice_info
                WHERE branch_id = :restaurant_branch_id"""
    branch_values = {
        "restaurant_branch_id": resp_js["data"]["newRestaurantBranch"]["id"]
    }
    await SQLDatabase.execute(
        query=rest_branch_tax_query,
        values=branch_values,
    )
    await db_shutdown()


async def delete_restaurant_branch(resp_js: Dict[Any, Any], category_id: UUID):
    await db_startup()
    rest_category_query = """DELETE FROM restaurant_branch_category
                WHERE restaurant_branch_id = :restaurant_branch_id"""
    branch_query = """DELETE FROM restaurant_branch
                WHERE id = :restaurant_branch_id"""
    branch_values = {
        "restaurant_branch_id": resp_js["data"]["newRestaurantBranch"]["id"]
    }
    await SQLDatabase.execute(
        query=rest_category_query,
        values=branch_values,
    )
    await SQLDatabase.execute(
        query=branch_query,
        values=branch_values,
    )
    await db_shutdown()


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_branch(
    test_ficture_edit_restaurant_business_error: Dict[str, Any],  # noqa
    test_ficture_get_categoty_restaurant: Dict[Any, Any], # noqa
):  # noqa
    _user = test_ficture_edit_restaurant_business_error["user"]
    token = _user["idToken"]
    category_id = test_ficture_get_categoty_restaurant["resp_category"]["id"]
    mock_rest_branch["resBId"] = test_ficture_edit_restaurant_business_error[
        "resp_js_new_restaurant_business"
    ]["data"]["newRestaurantBusiness"]["id"]
    mock_rest_branch["categoryId"] = str(category_id)
    # execute endpoint for new restaurant user

    resp_js_new_branch = fixture_gql_api(
        token=token,
        query=query_test_new_restaurant_branch,
        variables=mock_rest_branch,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_edit_restaurant_business_error["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_business_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_business_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_business_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_business_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_business_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_business_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_business_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_edit_restaurant_business_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": resp_js_new_branch,
        "resp_category": test_ficture_get_categoty_restaurant["resp_category"],
    }

    asyncio.run(delete_restaurant_branch(resp_js_new_branch, category_id))


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_branch_error(
    test_ficture_new_restaurant_branch: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_new_restaurant_branch["user"]
    token = _user["idToken"]
    mock_rest_branch_error["resBId"] = test_ficture_new_restaurant_branch[
        "resp_js_new_restaurant_business"
    ]["data"]["newRestaurantBusiness"]["id"]
    mock_rest_branch_error["categoryId"] = str(uuid.uuid4())
    # execute endpoint for new restaurant user

    resp_js_new_branch_error = fixture_gql_api(
        token=token,
        query=query_test_new_restaurant_branch,
        variables=mock_rest_branch_error,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_new_restaurant_branch["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_branch[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_branch[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_branch[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_branch[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_branch[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_restaurant_branch[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_restaurant_branch[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_restaurant_branch[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_restaurant_branch["resp_js_new_branch"],
        "resp_category": test_ficture_new_restaurant_branch["resp_category"],
        "resp_js_new_branch_error": resp_js_new_branch_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_category_ok(
    test_ficture_new_restaurant_branch_error: Dict[str, Any]  # noqa
):
    resp_js_get_rest_cat = fixture_gql_api(
        query=query_test_get_rest_cat,
        method="POST",
    )
    yield {
        "user": test_ficture_new_restaurant_branch_error["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_branch_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_branch_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_branch_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_restaurant_branch_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_restaurant_branch_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_restaurant_branch_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_restaurant_branch_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_new_restaurant_branch_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_new_restaurant_branch_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": resp_js_get_rest_cat,
    }


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_branch_tax_id_ok(
    test_ficture_get_restaurant_category_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_restaurant_category_ok["user"]
    token = _user["idToken"]
    mock_branch_tax_info["branchId"] = test_ficture_get_restaurant_category_ok[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    # execute endpoint for new restaurant user
    resp_js_new_branch_tax_id = fixture_gql_api(
        token=token,
        query=query_test_new_branch_tax_info,
        variables=mock_branch_tax_info,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_restaurant_category_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_category_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_category_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_category_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_restaurant_category_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_restaurant_category_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_restaurant_category_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_restaurant_category_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_restaurant_category_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_restaurant_category_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_restaurant_category_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_restaurant_category_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_restaurant_category_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": resp_js_new_branch_tax_id,
    }
    asyncio.run(
        delete_restauran_branch_tax_info(
            test_ficture_get_restaurant_category_ok["resp_js_new_branch"]
        )
    )


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_branch_tax_id_error(
    test_ficture_new_restaurant_branch_tax_id_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_new_restaurant_branch_tax_id_ok["user"]
    token = _user["idToken"]
    mock_branch_tax_info_error[
        "branchId"
    ] = test_ficture_new_restaurant_branch_tax_id_ok["resp_js_new_branch"]["data"][
        "newRestaurantBranch"
    ][
        "id"
    ]
    # execute endpoint for new restaurant user
    resp_js_new_branch_tax_id_error = fixture_gql_api(
        token=token,
        query=query_test_new_branch_tax_info,
        variables=mock_branch_tax_info_error,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_new_restaurant_branch_tax_id_ok["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_new_restaurant_branch_tax_id_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_new_restaurant_branch_tax_id_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": resp_js_new_branch_tax_id_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_branch_ok(
    test_ficture_new_restaurant_branch_tax_id_error: Dict[str, Any]  # noqa
):
    _user = test_ficture_new_restaurant_branch_tax_id_error["user"]
    token = _user["idToken"]

    mock_get_branch = {
        "resBId": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_restaurant_business"
        ]["data"]["newRestaurantBusiness"]["id"]
    }
    resp_js_get_branch = fixture_gql_api(
        query=query_test_get_branches,
        method="POST",
        variables=mock_get_branch,
        token=token,
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_new_restaurant_branch_tax_id_error["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_category"
        ],
        "resp_js_new_branch_error": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": resp_js_get_branch,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_branch_error(
    test_ficture_get_restaurant_branch_ok: Dict[str, Any]  # noqa
):
    _user = test_ficture_get_restaurant_branch_ok["user"]
    token = _user["idToken"]

    resp_js_get_branch_error = fixture_gql_api(
        query=query_test_get_branches,
        method="POST",
        variables={"resBId": str(uuid.uuid4())},
        token=token,
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_get_restaurant_branch_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_branch_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_restaurant_branch_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_restaurant_branch_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_restaurant_branch_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_restaurant_branch_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_restaurant_branch_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_restaurant_branch_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_restaurant_branch_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": resp_js_get_branch_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_branch_by_id_ok(
    test_ficture_get_restaurant_branch_error: Dict[str, Any]  # noqa
):
    _user = test_ficture_get_restaurant_branch_error["user"]
    token = _user["idToken"]

    mock_get_branch = {
        "branchId": test_ficture_get_restaurant_branch_error["resp_js_new_branch"][
            "data"
        ]["newRestaurantBranch"]["id"]
    }
    resp_js_get_branch_by_id = fixture_gql_api(
        query=query_test_get_branch_by_id,
        method="POST",
        variables=mock_get_branch,
        token=token,
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_get_restaurant_branch_error["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_branch_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_branch_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_restaurant_branch_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_restaurant_branch_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_restaurant_branch_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_restaurant_branch_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_restaurant_branch_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_restaurant_branch_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_restaurant_branch_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_restaurant_branch_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_restaurant_branch_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_restaurant_branch_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_restaurant_branch_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_restaurant_branch_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": resp_js_get_branch_by_id,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_branch_by_id_error(
    test_ficture_get_restaurant_branch_by_id_ok: Dict[str, Any]  # noqa
):
    _user = test_ficture_get_restaurant_branch_by_id_ok["user"]
    token = _user["idToken"]

    resp_js_get_branch_by_id_error = fixture_gql_api(
        query=query_test_get_branch_by_id,
        method="POST",
        variables={"branchId": str(uuid.uuid4())},
        token=token,
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_get_restaurant_branch_by_id_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_restaurant_branch_by_id_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_restaurant_branch_by_id_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": resp_js_get_branch_by_id_error,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_branch_ok(
    test_ficture_get_restaurant_branch_by_id_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_restaurant_branch_by_id_error["user"]
    token = _user["idToken"]

    mock_rest_branch["resBId"] = test_ficture_get_restaurant_branch_by_id_error[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    mock_rest_branch["categoryId"] = str(
        test_ficture_get_restaurant_branch_by_id_error["resp_category"]["id"]
    )
    # execute endpoint for new restaurant user
    mock_rest_branch["zipCode"] = "12345"

    resp_js_edit_branch = fixture_gql_api(
        token=token,
        query=query_test_edit_branch,
        variables=mock_rest_branch,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_restaurant_branch_by_id_error["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_get_restaurant_branch_by_id_error[
            "resp_category"
        ],
        "resp_js_new_branch_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_get_restaurant_branch_by_id_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": resp_js_edit_branch,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_branch_error(
    test_ficture_edit_restaurant_branch_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_edit_restaurant_branch_ok["user"]
    token = _user["idToken"]

    mock_rest_branch_error["resBId"] = test_ficture_edit_restaurant_branch_ok[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    mock_rest_branch_error["categoryId"] = str(uuid.uuid4())
    # execute endpoint for new restaurant user
    mock_rest_branch["zipCode"] = "12345"

    resp_js_edit_branch_error = fixture_gql_api(
        token=token,
        query=query_test_edit_branch,
        variables=mock_rest_branch_error,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_edit_restaurant_branch_ok["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_branch_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_edit_restaurant_branch_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_edit_restaurant_branch_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_edit_restaurant_branch_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": resp_js_edit_branch_error,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_branch_tax_id_ok(
    test_ficture_edit_restaurant_branch_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_edit_restaurant_branch_error["user"]
    token = _user["idToken"]

    mock_branch_tax_info["branchId"] = test_ficture_edit_restaurant_branch_error[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    # execute endpoint for new restaurant user
    mock_branch_tax_info["taxZip"] = "54321"

    resp_js_edit_branch_tax_id = fixture_gql_api(
        token=token,
        query=query_test_edit_branch_tax_id,
        variables=mock_branch_tax_info,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_edit_restaurant_branch_error["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_branch_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_edit_restaurant_branch_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_edit_restaurant_branch_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_edit_restaurant_branch_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": resp_js_edit_branch_tax_id,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_branch_tax_id_error(
    test_ficture_edit_restaurant_branch_tax_id_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_edit_restaurant_branch_tax_id_ok["user"]
    token = _user["idToken"]

    mock_rest_branch_error["resBId"] = test_ficture_edit_restaurant_branch_tax_id_ok[
        "resp_js_new_branch"
    ]["data"]["newRestaurantBranch"]["id"]
    mock_rest_branch_error["categoryId"] = str(uuid.uuid4())
    # execute endpoint for new restaurant user
    mock_rest_branch["zipCode"] = "12345"

    resp_js_edit_branch_tax_id_error = fixture_gql_api(
        token=token,
        query=query_test_edit_branch,
        variables=mock_rest_branch_error,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_edit_restaurant_branch_tax_id_ok["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_edit_restaurant_branch_tax_id_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_edit_restaurant_branch_tax_id_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": resp_js_edit_branch_tax_id_error,
    }


@pytest.fixture(scope="session")
def test_ficture_delete_restaurant_branch_ok(
    test_ficture_edit_restaurant_branch_tax_id_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_edit_restaurant_branch_tax_id_error["user"]
    token = _user["idToken"]

    mock_delete_rest_branch = {
        "branchId": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_branch"
        ]["data"]["newRestaurantBranch"]["id"],
        "delete": True,
    }
    # execute endpoint for new restaurant user
    resp_js_delete_branch_ok = fixture_gql_api(
        token=token,
        query=query_test_delete_branch,
        variables=mock_delete_rest_branch,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_edit_restaurant_branch_tax_id_error["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_category"
        ],
        "resp_js_new_branch_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_edit_restaurant_branch_tax_id_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": resp_js_delete_branch_ok,
    }


@pytest.fixture(scope="session")
def test_ficture_delete_restaurant_branch_error(
    test_ficture_delete_restaurant_branch_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_delete_restaurant_branch_ok["user"]
    token = _user["idToken"]

    mock_delete_rest_branch_error = {"branchId": str(uuid.uuid4()), "delete": True}

    resp_js_delete_branch_error = fixture_gql_api(
        token=token,
        query=query_test_delete_branch,
        variables=mock_delete_rest_branch_error,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_delete_restaurant_branch_ok["user"],
        "resp_js_new_rest_user": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_delete_restaurant_branch_ok[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_delete_restaurant_branch_ok["resp_category"],
        "resp_js_new_branch_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_delete_restaurant_branch_ok[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_delete_restaurant_branch_ok[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_delete_restaurant_branch_ok[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_delete_restaurant_branch_ok[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": resp_js_delete_branch_error,
    }


@pytest.fixture(scope="session")
def test_ficture_set_restaurant_branch_ok(
    test_ficture_delete_restaurant_branch_error: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_delete_restaurant_branch_error["user"]
    token = _user["idToken"]

    mock_delete_rest_branch = {
        "branchId": test_ficture_delete_restaurant_branch_error["resp_js_new_branch"][
            "data"
        ]["newRestaurantBranch"]["id"],
        "delete": False,
    }
    # execute endpoint for new restaurant user
    resp_js_set_branch_ok = fixture_gql_api(
        token=token,
        query=query_test_delete_branch,
        variables=mock_delete_rest_branch,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_delete_restaurant_branch_error["user"],
        "resp_js_new_rest_user": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_rest_user"
        ],
        "resp_js_new_restaurant_business": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_restaurant_business": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_restaurant_business"
        ],
        "resp_js_edit_restaurant_business": test_ficture_delete_restaurant_branch_error[
            "resp_js_edit_restaurant_business"
        ],
        "resp_js_edit_restaurant_business_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_edit_restaurant_business_error"
        ],
        "resp_js_new_branch": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_branch"
        ],
        "resp_category": test_ficture_delete_restaurant_branch_error["resp_category"],
        "resp_js_new_branch_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_branch_error"
        ],
        "resp_js_get_rest_cat": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_rest_cat"
        ],
        "resp_js_new_branch_tax_id": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_branch_tax_id"
        ],
        "resp_js_new_branch_tax_id_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_new_branch_tax_id_error"
        ],
        "resp_js_get_branch": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_branch"
        ],
        "resp_js_get_branch_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_branch_error"
        ],
        "resp_js_get_branch_by_id": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_branch_by_id"
        ],
        "resp_js_get_branch_by_id_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_get_branch_by_id_error"
        ],
        "resp_js_edit_branch": test_ficture_delete_restaurant_branch_error[
            "resp_js_edit_branch"
        ],
        "resp_js_edit_branch_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_edit_branch_error"
        ],
        "resp_js_edit_branch_tax_id": test_ficture_delete_restaurant_branch_error[
            "resp_js_edit_branch_tax_id"
        ],
        "resp_js_edit_branch_tax_id_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_edit_branch_tax_id_error"
        ],
        "resp_js_delete_branch_ok": test_ficture_delete_restaurant_branch_error[
            "resp_js_delete_branch_ok"
        ],
        "resp_js_delete_branch_error": test_ficture_delete_restaurant_branch_error[
            "resp_js_delete_branch_error"
        ],
        "resp_js_set_branch_ok": resp_js_set_branch_ok,
    }
