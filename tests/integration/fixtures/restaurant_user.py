import asyncio
import pytest
from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp
from .gqlapi import fixture_gql_api  # noqa
from .firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa

# from .gqlapi import (  # noqa
# test_ficture_firebase_signin_ok,  # noqa
# test_ficture_firebase_signup_ok_delete_ok,  # noqa
# )
from ..mocks.restaurant_user import mock_rest_user
from ..queries.restaurant_user import (
    query_test_new_user,
    query_test_get_rest_user_by_token,
)


async def delete_restaurant_user(test_ficture_new_restaurant_user_ok: Dict[Any, Any]):
    await db_startup()
    restaurant_query = """DELETE FROM  restaurant_user
                    WHERE id = :restaurant_id
                    """
    core_query = """DELETE FROM core_user
                    Where id = :core_id"""
    await SQLDatabase.execute(
        query=restaurant_query,
        values={
            "restaurant_id": test_ficture_new_restaurant_user_ok["data"][
                "newRestaurantUser"
            ]["id"]
        },
    )
    await SQLDatabase.execute(
        query=core_query,
        values={
            "core_id": test_ficture_new_restaurant_user_ok["data"]["newRestaurantUser"][
                "coreUserId"
            ]
        },
    )
    await db_shutdown()


@pytest.fixture(scope="session")
def test_ficture_new_restaurant_user_ok(
    test_ficture_firebase_signin_ok: Dict[str, Any]  # noqa
):
    _user = test_ficture_firebase_signin_ok["user"]
    token = _user["idToken"]
    mock_rest_user["firebaseId"] = _user["localId"]
    # execute endpoint for new restaurant user
    resp_js_new_rest_user = fixture_gql_api(
        token=token,
        query=query_test_new_user,
        variables=mock_rest_user,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_firebase_signin_ok["user"],
        "resp_js_new_rest_user": resp_js_new_rest_user,
    }
    asyncio.run(delete_restaurant_user(resp_js_new_rest_user))


@pytest.fixture(scope="session")
def test_fixture_new_restaurant_user_error(
    test_ficture_new_restaurant_user_ok: Dict[str, Any]  # noqa
):
    _user = test_ficture_new_restaurant_user_ok["user"]
    token = _user["idToken"]
    # execute endpoint for new restaurant user
    resp_js_new_rest_user_error = fixture_gql_api(
        token=token,
        query=query_test_new_user,
        variables=mock_rest_user,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_ficture_new_restaurant_user_ok["user"],
        "resp_js_new_rest_user": test_ficture_new_restaurant_user_ok[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": resp_js_new_rest_user_error,
    }


@pytest.fixture(scope="session")
def test_ficture_get_restaurant_user_by_token_ok(
    test_fixture_new_restaurant_user_error: Dict[str, Any]
):  # noqa
    _user = test_fixture_new_restaurant_user_error["user"]
    token = _user["idToken"]
    # execute endpoint for new restaurant user

    resp_js_get_rest_user = fixture_gql_api(
        token=token,
        query=query_test_get_rest_user_by_token,
        method="POST",
        authorization="restobasic",
    )
    yield {
        "user": test_fixture_new_restaurant_user_error["user"],
        "resp_js_new_rest_user": test_fixture_new_restaurant_user_error[
            "resp_js_new_rest_user"
        ],
        "resp_js_new_rest_user_error": test_fixture_new_restaurant_user_error[
            "resp_js_new_rest_user_error"
        ],
        "resp_js_get_rest_user": resp_js_get_rest_user,
    }
