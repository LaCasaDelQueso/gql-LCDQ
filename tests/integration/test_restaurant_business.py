from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from .fixtures.firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from .fixtures.restaurant_user import ( # noqa
    test_ficture_new_restaurant_user_ok, # noqa
    test_fixture_new_restaurant_user_error, # noqa
    test_ficture_get_restaurant_user_by_token_ok, # noqa
)
from .fixtures.gqlapi import ( # noqa
    test_ficture_firebase_signin_ok, # noqa
    test_ficture_firebase_signup_ok_delete_ok, # noqa
)
from .fixtures.restaurant_business import ( # noqa
    test_ficture_edit_restaurant_business_ok, # noqa
    test_ficture_edit_restaurant_business_error, # noqa
    test_ficture_new_restaurant_business_ok, # noqa
    test_ficture_new_restaurant_business_error, # noqa
    test_ficture_get_restaurant_business_ok, # noqa
)


def test_new_restaurant_business_ok(
    test_ficture_new_restaurant_business_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_business_ok["resp_js_new_restaurant_business"][
            "data"
        ]["newRestaurantBusiness"].get("id", None)
        is not None
    )


def test_new_restaurant_business_error(
    test_ficture_new_restaurant_business_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_business_error[
            "resp_js_new_restaurant_business_error"
        ]["data"]["newRestaurantBusiness"].get("code", None)
        is not None
    )


def test_get_restaurant_business_ok(
    test_ficture_get_restaurant_business_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_restaurant_business_ok["resp_js_get_restaurant_business"][
            "data"
        ]["getRestaurantBusinessFromToken"].get("id", None)
        is not None
    )


def test_edit_restaurant_business_ok(
    test_ficture_edit_restaurant_business_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_business_ok["resp_js_edit_restaurant_business"][
            "data"
        ]["updateRestaurantBusiness"].get("id", None)
        is not None
    )
    assert test_ficture_edit_restaurant_business_ok["resp_js_edit_restaurant_business"][
        "data"
    ]["updateRestaurantBusiness"]["active"]


def test_edit_restaurant_business_error(
    test_ficture_edit_restaurant_business_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_business_error[
            "resp_js_edit_restaurant_business_error"
        ].get("errors", None)
        is not None
    )
