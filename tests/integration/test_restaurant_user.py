from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from .fixtures.restaurant_user import (  # noqa
    test_ficture_new_restaurant_user_ok,  # noqa
    test_fixture_new_restaurant_user_error,  # noqa
    test_ficture_get_restaurant_user_by_token_ok,  # noqa
)
from .fixtures.gqlapi import (  # noqa
    test_ficture_firebase_signin_ok,  # noqa
    test_ficture_firebase_signup_ok_delete_ok,  # noqa
)
from .fixtures.firebase import setup_fb_admin, setup_fb_auth  # noqa


def test_new_restaurant_user_ok(
    test_ficture_new_restaurant_user_ok: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_user_ok["resp_js_new_rest_user"]["data"][
            "newRestaurantUser"
        ].get("id", None)
        is not None
    )


def test_new_restaurant_user_error(
    test_fixture_new_restaurant_user_error: Dict[Any, Any],  # noqa
):  # noqa
    assert (
        test_fixture_new_restaurant_user_error["resp_js_new_rest_user_error"]["data"][
            "newRestaurantUser"
        ].get("msg", None)
        is not None
    )


def test_get_restaurant_user_by_token(
    test_ficture_get_restaurant_user_by_token_ok: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_get_restaurant_user_by_token_ok["resp_js_get_rest_user"]["data"][
            "getRestaurantUserFromToken"
        ].get("id", None)
        is not None
    )
