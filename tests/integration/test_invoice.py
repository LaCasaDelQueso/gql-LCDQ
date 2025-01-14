# from typing import Any, Dict
# from gqlapi import __version__  # noqa
# from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp
# import requests  # noqa
# from .fixtures.firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa



# def test_new_invoice_file_ok(test_ficture_new_invoice_file_ok: Dict[Any, Any]):  # noqa
#     assert (
#         test_ficture_new_invoice_file_ok["resp_str_new_invoice_file"] ==
#  """{"data": {"uploadInvoice": {"success": true, "msg": "La factura ha sido guardada correctamente"}}}"""
#     )


# def test_new_invoice_file_error(
#     test_ficture_new_invoice_file_error: Dict[Any, Any]
# ):  # noqa
#     assert (
#         test_ficture_new_invoice_file_error["resp_str_new_invoice_file_error"]["data"][
#             "uploadInvoice"
#         ].get("code", None)
#         is not None
#     )
