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
from .fixtures.supplier import ( # noqa
    test_ficture_new_restaurant_supplier_ok,# noqa
    test_ficture_new_restaurant_supplier_error, # noqa
    test_ficture_get_active_supplier_ok, # noqa
    test_ficture_get_supplier_categories_ok, # noqa
    test_ficture_get_supplier_error, # noqa
    test_ficture_get_supplier_ok, # noqa
    test_ficture_edit_restaurant_supplier_ok, # noqa
    # test_ficture_new_restaurant_supplier_file_ok,  # noqa
)


def test_new_restaurant_supplier_ok(
    test_ficture_new_restaurant_supplier_ok: Dict[Any, Any]  # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_supplier_ok["resp_js_new_rest_supp"]["data"][
            "newRestaurantSupplerCreation"
        ]["supplierBusiness"].get("id", None)
        is not None
    )


def test_new_restaurant_supplier_error(
    test_ficture_new_restaurant_supplier_error: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_new_restaurant_supplier_error["resp_js_new_rest_supp_error"][
            "data"
        ]["newRestaurantSupplerCreation"].get("code", None)
        is not None
    )


def test_get_active_supplier_ok(
    test_ficture_get_active_supplier_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_active_supplier_ok["resp_js_get_active_supp"]["data"][
            "getRestaurantSuppliers"
        ][0]["supplierBusiness"].get("id", None)
        is not None
    )


def test_get_supplier_categories_ok(
    test_ficture_get_supplier_categories_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_get_supplier_categories_ok["resp_js_get_supp_cat"]["data"][
            "getCategories"
        ][0].get("value", None)
        is not None
    )


def test_get_supplier_ok(test_ficture_get_supplier_ok: Dict[Any, Any]):  # noqa
    assert (
        test_ficture_get_supplier_ok["resp_js_get_supp"]["data"][
            "getRestaurantSuppliers"
        ][0]["supplierBusiness"].get("id", None)
        is not None
    )


def test_get_supplier_error(test_ficture_get_supplier_error: Dict[Any, Any]):  # noqa
    assert (
        test_ficture_get_supplier_error["resp_js_get_supp_error"]["data"][
            "getRestaurantSuppliers"
        ][0].get("code", None)
        is not None
    )


def test_edit_restaurant_supplier_ok(
    test_ficture_edit_restaurant_supplier_ok: Dict[Any, Any] # noqa
):  # noqa
    assert (
        test_ficture_edit_restaurant_supplier_ok["resp_js_edit_rest_supp"]["data"][
            "updateRestaurantSupplerCreation"
        ]["supplierBusiness"].get("id", None)
        is not None
    )
    assert (
        test_ficture_edit_restaurant_supplier_ok["resp_js_edit_rest_supp"]["data"][
            "updateRestaurantSupplerCreation"
        ]["supplierBusiness"].get("country", None)
        == "EU"
    )


# def test_new_restaurant_supplier_file_ok(
#     test_ficture_new_restaurant_supplier_file_ok: Dict[Any, Any]
# ):  # noqa
#     assert True


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
