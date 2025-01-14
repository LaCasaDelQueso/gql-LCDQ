from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from .fixtures.firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from .fixtures.restaurant_user import (  # noqa
    test_ficture_new_restaurant_user_ok,  # noqa
    test_fixture_new_restaurant_user_error,  # noqa
    test_ficture_get_restaurant_user_by_token_ok,  # noqa
)
from .fixtures.gqlapi import (  # noqa
    test_ficture_firebase_signin_ok,  # noqa
    test_ficture_firebase_signup_ok_delete_ok,  # noqa
)
from .fixtures.restaurant_business import (  # noqa
    test_ficture_edit_restaurant_business_ok,  # noqa
    test_ficture_edit_restaurant_business_error,  # noqa
    test_ficture_new_restaurant_business_ok,  # noqa
    test_ficture_new_restaurant_business_error,  # noqa
    test_ficture_get_restaurant_business_ok,  # noqa
)
from .fixtures.restaurant_branch import (  # noqa
    test_ficture_new_restaurant_branch,  # noqa
    test_ficture_new_restaurant_branch_error,  # noqa
    test_ficture_get_restaurant_category_ok,  # noqa
    test_ficture_new_restaurant_branch_tax_id_ok,  # noqa
    test_ficture_new_restaurant_branch_tax_id_error,  # noqa
    test_ficture_get_restaurant_branch_by_id_error,  # noqa
    test_ficture_get_restaurant_branch_by_id_ok,  # noqa
    test_ficture_get_restaurant_branch_error,  # noqa
    test_ficture_get_restaurant_branch_ok,  # noqa
    test_ficture_delete_restaurant_branch_error,  # noqa
    test_ficture_edit_restaurant_branch_tax_id_error,  # noqa
    test_ficture_edit_restaurant_branch_tax_id_ok,  # noqa
    test_ficture_edit_restaurant_branch_error,  # noqa
    test_ficture_edit_restaurant_branch_ok,  # noqa
    test_ficture_delete_restaurant_branch_ok,  # noqa
    test_ficture_set_restaurant_branch_ok,  # noqa
)
from .fixtures.category import (  # noqa
    test_ficture_get_categoty_restaurant,  # noqa
    test_ficture_get_category_supplier,  # noqa
)  # noqa
from .fixtures.supplier import (  # noqa
    test_ficture_new_restaurant_supplier_ok,  # noqa
    test_ficture_new_restaurant_supplier_error,  # noqa
    test_ficture_get_active_supplier_ok,  # noqa
    test_ficture_get_supplier_categories_ok,  # noqa
    test_ficture_get_supplier_error,  # noqa
    test_ficture_get_supplier_ok,  # noqa
    test_ficture_edit_restaurant_supplier_ok,  # noqa
    # test_ficture_new_restaurant_supplier_file_ok,  # noqa
)
from .fixtures.orden import ( # noqa
    test_ficture_new_normal_orden_ok, # noqa
    test_ficture_new_normal_orden_error, # noqa
    test_ficture_get_active_ordens_by_branch_ok, # noqa
    test_ficture_get_active_ordens_by_branch_error, # noqa
    test_ficture_get_orden_details_ok, # noqa
    test_ficture_get_orden_details_error, # noqa
    test_ficture_get_historic_orden_by_branch_ok, # noqa
    test_ficture_get_historic_orden_by_branch_error, # noqa
    test_ficture_cancel_orden_ok, # noqa
    test_ficture_cancel_orden_error, # noqa
)


def test_new_normal_orden_ok(test_ficture_new_normal_orden_ok: Dict[Any, Any]):  # noqa
    assert (
        test_ficture_new_normal_orden_ok["resp_js_new_normal_orden"]["data"][
            "newOrden"
        ].get("id", None)
        is not None
    )


def test_new_normal_orden_error(
    test_ficture_new_normal_orden_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_normal_orden_error["resp_js_new_normal_orden_error"]["data"][
            "newOrden"
        ].get("code", None)
        is not None
    )


def test_get_active_ordens_by_branch_ok(
    test_ficture_get_active_ordens_by_branch_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_active_ordens_by_branch_ok["resp_js_get_active_ordens"][
            "data"
        ]["getOrdenes"][0].get("id", None)
        is not None
    )


def test_get_active_ordens_by_branch_error(
    test_ficture_get_active_ordens_by_branch_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_active_ordens_by_branch_error[
            "resp_js_get_active_ordens_error"
        ]["data"]["getOrdenes"][0].get("code", None)
        is not None
    )


def test_get_orden_details_ok(
    test_ficture_get_orden_details_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_orden_details_ok["resp_js_get_orden_details"]["data"][
            "getOrdenes"
        ][0].get("id", None)
        is not None
    )


def test_get_orden_details_error(
    test_ficture_get_orden_details_error: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_get_orden_details_error["resp_js_get_orden_details_error"]["data"][
            "getOrdenes"
        ][0].get("code", None)
        is not None
    )


def test_get_historic_ordenes_by_branch_ok(
    test_ficture_get_historic_orden_by_branch_ok: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_get_historic_orden_by_branch_ok["resp_js_get_historic_ordenes"][
            "data"
        ]["getOrdenes"][0].get("id", None)
        is not None
    )


def test_get_historic_orden_by_branch_error(
    test_ficture_get_historic_orden_by_branch_error: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_get_historic_orden_by_branch_error[
            "resp_js_get_historic_ordenes_error"
        ]["data"]["getOrdenes"][0].get("code", None)
        is not None
    )


def test_cancel_orden_ok(test_ficture_cancel_orden_ok: Dict[Any, Any]):  # noqa
    assert (
        test_ficture_cancel_orden_ok["resp_js_cancel_orden"]["data"]["updateOrden"].get(
            "id", None
        )
        is not None
    )

    assert (
        test_ficture_cancel_orden_ok["resp_js_cancel_orden"]["data"]["updateOrden"][
            "status"
        ].get("status", None)
        == "CANCELED"
    )


def test_cancel_orden_error(
    test_ficture_cancel_orden_error: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_cancel_orden_error["resp_js_cancel_orden_error"]["data"][
            "updateOrden"
        ].get("code", None)
        is not None
    )
