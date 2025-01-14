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
from .fixtures.restaurant_branch import ( # noqa
    test_ficture_new_restaurant_branch, # noqa
    test_ficture_new_restaurant_branch_error, # noqa
    test_ficture_get_restaurant_category_ok, # noqa
    test_ficture_new_restaurant_branch_tax_id_ok, # noqa
    test_ficture_new_restaurant_branch_tax_id_error, # noqa
    test_ficture_get_restaurant_branch_by_id_error, # noqa
    test_ficture_get_restaurant_branch_by_id_ok, # noqa
    test_ficture_get_restaurant_branch_error, # noqa
    test_ficture_get_restaurant_branch_ok, # noqa
    test_ficture_delete_restaurant_branch_error, # noqa
    test_ficture_delete_restaurant_branch_ok, # noqa
    test_ficture_edit_restaurant_branch_tax_id_error, # noqa
    test_ficture_edit_restaurant_branch_tax_id_ok, # noqa
    test_ficture_edit_restaurant_branch_error, # noqa
    test_ficture_edit_restaurant_branch_ok, # noqa

)
from .fixtures.category import test_ficture_get_categoty_restaurant # noqa


def test_new_restaurant_branch_ok(
    test_ficture_new_restaurant_branch: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_branch["resp_js_new_branch"]["data"][
            "newRestaurantBranch"
        ].get("id", None)
        is not None
    )


def test_new_restaurant_branch_error(
    test_ficture_new_restaurant_branch_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_branch_error["resp_js_new_branch_error"]["data"][
            "newRestaurantBranch"
        ].get("code", None)
        is not None
    )


def test_get_restaurant_category_ok(
    test_ficture_get_restaurant_category_ok: Dict[Any, Any] # noqa
):  # noqa
    if (
        "categories"
        in test_ficture_get_restaurant_category_ok["resp_js_get_rest_cat"]["data"][
            "getRestaurantCategories"
        ]
    ):
        assert (
            test_ficture_get_restaurant_category_ok["resp_js_get_rest_cat"]["data"][
                "getRestaurantCategories"
            ]["categories"][0].get("value", None)
            is not None
        )
    else:
        assert (
            test_ficture_get_restaurant_category_ok["resp_js_get_rest_cat"]["data"][
                "getRestaurantCategories"
            ].get("msg", None)
            is not None
        )


def test_new_restaurant_branch_tax_info_ok(
    test_ficture_new_restaurant_branch_tax_id_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_branch_tax_id_ok["resp_js_new_branch_tax_id"][
            "data"
        ]["newRestaurantBranchTaxInfo"].get("taxId", None)
        is not None
    )


def test_new_restaurant_branch_tax_info_error(
    test_ficture_new_restaurant_branch_tax_id_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_branch_tax_id_error[
            "resp_js_new_branch_tax_id_error"
        ]["data"]["newRestaurantBranchTaxInfo"].get("code", None)
        is not None
    )


def test_get_restaurant_branch_ok(
    test_ficture_get_restaurant_branch_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_restaurant_branch_ok["resp_js_get_branch"]["data"][
            "getRestaurantBranchesFromToken"
        ][0].get("id", None)
        is not None
    )


def test_get_restaurant_branch_error(
    test_ficture_get_restaurant_branch_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_restaurant_branch_error["resp_js_get_branch_error"]["data"][
            "getRestaurantBranchesFromToken"
        ][0].get("code", None)
        is not None
    )


def test_get_restaurant_branch_by_id_ok(
    test_ficture_get_restaurant_branch_by_id_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_restaurant_branch_by_id_ok["resp_js_get_branch"]["data"][
            "getRestaurantBranchesFromToken"
        ][0].get("id", None)
        is not None
    )


def test_get_restaurant_branch_by_id_error(
    test_ficture_get_restaurant_branch_by_id_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_restaurant_branch_by_id_error["resp_js_get_branch_error"][
            "data"
        ]["getRestaurantBranchesFromToken"][0].get("code", None)
        is not None
    )


def test_edit_restaurant_branch_ok(
    test_ficture_edit_restaurant_branch_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_branch_ok["resp_js_edit_branch"]["data"][
            "updateRestaurantBranch"
        ].get("id", None)
        is not None
    )
    assert (
        test_ficture_edit_restaurant_branch_ok["resp_js_edit_branch"]["data"][
            "updateRestaurantBranch"
        ].get("zipCode", None)
        == "12345"
    )


def test_edit_restaurant_branch_error(
    test_ficture_edit_restaurant_branch_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_branch_error["resp_js_edit_branch_error"]["data"][
            "updateRestaurantBranch"
        ].get("code", None)
        is not None
    )


def test_edit_restaurant_branch_tax_id_ok(
    test_ficture_edit_restaurant_branch_tax_id_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_branch_tax_id_ok["resp_js_edit_branch_tax_id"][
            "data"
        ]["updateRestaurantBranchTaxInfo"].get("cfdiUse", None)
        is not None
    )
    assert (
        test_ficture_edit_restaurant_branch_tax_id_ok["resp_js_edit_branch_tax_id"][
            "data"
        ]["updateRestaurantBranchTaxInfo"].get("taxZipCode", None)
        == "54321"
    )


def test_edit_restaurant_branch_tax_id_error(
    test_ficture_edit_restaurant_branch_tax_id_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_branch_tax_id_error["resp_js_edit_branch_error"][
            "data"
        ]["updateRestaurantBranch"].get("code", None)
        is not None
    )


def test_delete_restaurant_branch_ok(
    test_ficture_delete_restaurant_branch_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_delete_restaurant_branch_ok["resp_js_delete_branch_ok"]["data"][
            "updateRestaurantBranch"
        ].get("id", None)
        is not None
    )
    assert (
        test_ficture_delete_restaurant_branch_ok["resp_js_delete_branch_ok"]["data"][
            "updateRestaurantBranch"
        ].get("deleted", None)
    )


def test_delete_restaurant_branch_error(
    test_ficture_delete_restaurant_branch_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_delete_restaurant_branch_error["resp_js_delete_branch_error"][
            "data"
        ]["updateRestaurantBranch"].get("code", None)
        is not None
    )
