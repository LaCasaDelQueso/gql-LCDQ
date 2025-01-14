import asyncio
from uuid import UUID
from bson import Binary
import pytest
import pymongo
from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.config import MONGO_DB_NAME, MONGO_URI
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from .firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from .gqlapi import (  # noqa
    test_ficture_firebase_signin_ok,  # noqa
    test_ficture_firebase_signup_ok_delete_ok,  # noqa
    fixture_gql_api,
)
from .restaurant_user import (  # noqa
    test_ficture_new_restaurant_user_ok,  # noqa
    test_ficture_get_restaurant_user_by_token_ok,
    test_fixture_new_restaurant_user_error,
)
from ..mocks.restaurant_business import mock_rest_bus, mock_rest_supp_error
from ..queries.restaurant_business import (
    query_edit_rest_business,
    query_new_rest_business,
    query_rest_business,
)


async def delete_restaurant_business(values: Dict[Any, Any]):
    await db_startup()
    rest_business_query = """DELETE FROM restaurant_business
                    Where id = :restaurant_business_id"""
    rest_user_perm_query = """DELETE FROM restaurant_user_permission
                    Where restaurant_business_id = :restaurant_business_id"""
    await SQLDatabase.execute(
        query=rest_user_perm_query,
        values={
            "restaurant_business_id": values["resp_js_new_restaurant_business"]["data"][
                "newRestaurantBusiness"
            ]["id"]
        },
    )
    await SQLDatabase.execute(
        query=rest_business_query,
        values={
            "restaurant_business_id": values["resp_js_new_restaurant_business"]["data"][
                "newRestaurantBusiness"
            ]["id"]
        },
    )

    myclient = pymongo.MongoClient(MONGO_URI)
    mydb = myclient[MONGO_DB_NAME]

    collection = mydb["restaurant_business_account"]
    query = {
        "restaurant_business_id": Binary.from_uuid(
            UUID(
                values["resp_js_new_restaurant_business"]["data"][
                    "newRestaurantBusiness"
                ]["id"]
            )
        )
    }
    collection.delete_one(query)

    await db_shutdown()


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_business_ok(
    test_ficture_get_restaurant_user_by_token_ok: Dict[str, Any]  # noqa
):  # noqa
    _user = test_ficture_get_restaurant_user_by_token_ok["user"]
    token = _user["idToken"]

    resp_js_new_restaurant_business = fixture_gql_api(
        token=token,
        query=query_new_rest_business,
        variables=mock_rest_bus,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_get_restaurant_user_by_token_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_user_by_token_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_user_by_token_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_user_by_token_ok,
        "resp_js_new_restaurant_business": resp_js_new_restaurant_business,
    }
    asyncio.run(
        delete_restaurant_business(
            {
                "user": test_ficture_get_restaurant_user_by_token_ok["user"],
                "resp_js_new_restaurant_business": resp_js_new_restaurant_business,
            }
        )
    )


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_business_error(
    test_ficture_new_restaurant_business_ok: Dict[str, Any]  # noqa
):
    _user = test_ficture_new_restaurant_business_ok["user"]
    token = _user["idToken"]

    resp_js_new_restaurant_business_error = fixture_gql_api(
        token=token,
        query=query_new_rest_business,
        variables=mock_rest_supp_error,
        method="POST",
        authorization="restobasic",
    )

    yield {
        "user": test_ficture_new_restaurant_business_ok["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_business_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_business_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_business_ok['resp_js_get_rest_user'],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_business_ok['resp_js_new_restaurant_business'],
        "resp_js_new_restaurant_business_error": resp_js_new_restaurant_business_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_business_ok(
    test_ficture_new_restaurant_business_error: Dict[str, Any]
):  # noqa
    _user = test_ficture_new_restaurant_business_error["user"]
    token = _user["idToken"]

    resp_js_get_restaurant_business = fixture_gql_api(
        token=token,
        query=query_rest_business,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_new_restaurant_business_error["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_business_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_new_restaurant_business_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_new_restaurant_business_error['resp_js_get_rest_user'],
        "resp_js_new_restaurant_business": test_ficture_new_restaurant_business_error[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_new_restaurant_business_error['resp_js_new_rest_user_error'],
        "resp_js_get_restaurant_business": resp_js_get_restaurant_business,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_business_ok(
    test_ficture_get_restaurant_business_ok: Dict[str, Any]
):  # noqa
    _user = test_ficture_get_restaurant_business_ok["user"]
    token = _user["idToken"]
    # execute endpoint for new restaurant user

    mock_rest_bus["restoId"] = test_ficture_get_restaurant_business_ok[
        "resp_js_new_restaurant_business"
    ]["data"]["newRestaurantBusiness"]["id"]
    mock_rest_bus["active"] = True  # type: ignore

    resp_js_edit_restaurant_business = fixture_gql_api(
        token=token,
        query=query_edit_rest_business,
        variables=mock_rest_bus,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_get_restaurant_business_ok["user"],
        "resp_js_new_rest_user": test_ficture_get_restaurant_business_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_get_restaurant_business_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_get_restaurant_business_ok['resp_js_get_rest_user'],
        "resp_js_new_restaurant_business": test_ficture_get_restaurant_business_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_get_restaurant_business_ok['resp_js_new_rest_user_error'],
        "resp_js_get_restaurant_business": test_ficture_get_restaurant_business_ok["resp_js_get_restaurant_business"],
        "resp_js_edit_restaurant_business": resp_js_edit_restaurant_business,
    }


@pytest.fixture(scope="session")
def test_ficture_edit_restaurant_business_error(
    test_ficture_edit_restaurant_business_ok: Dict[str, Any]
):  # noqa
    _user = test_ficture_edit_restaurant_business_ok["user"]
    token = _user["idToken"]
    # execute endpoint for new restaurant user

    mock_edit_rest_supp_error = {
        "restoId": test_ficture_edit_restaurant_business_ok[
            "resp_js_new_restaurant_business"
        ]["data"]["newRestaurantBusiness"]["id"]
    }
    resp_js_edit_restaurant_business_error = fixture_gql_api(
        token=token,
        query=query_edit_rest_business,
        variables=mock_edit_rest_supp_error,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_edit_restaurant_business_ok["user"],
        "resp_js_new_rest_user": test_ficture_edit_restaurant_business_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_ficture_edit_restaurant_business_ok[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": test_ficture_edit_restaurant_business_ok['resp_js_get_rest_user'],
        "resp_js_new_restaurant_business": test_ficture_edit_restaurant_business_ok[
            "resp_js_new_restaurant_business"
        ],
        "resp_js_new_restaurant_business_error": test_ficture_edit_restaurant_business_ok['resp_js_new_rest_user_error'],
        "resp_js_get_restaurant_business": test_ficture_edit_restaurant_business_ok["resp_js_get_restaurant_business"],
        "resp_js_edit_restaurant_business": test_ficture_edit_restaurant_business_ok["resp_js_edit_restaurant_business"],
        "resp_js_edit_restaurant_business_error": resp_js_edit_restaurant_business_error,
    }
