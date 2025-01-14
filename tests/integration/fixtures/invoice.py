# import asyncio
# from uuid import UUID
# import json
# import os
# import tempfile
# import pytest
# import ast
# from typing import Any, Dict
# from gqlapi import __version__  # noqa
# from gqlapi.config import MONGO_DB_NAME, MONGO_URI
# from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp
# import requests  # noqa
# from ..fixtures.firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
# from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa

# from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown  # noqa
# from ..queries.invoice import query_test_get_external_invoice_details, query_test_invoice_details, query_test_upload_invoice


# async def delete_invoice_file(resp_js_new_branch: Dict[Any, Any]):
#     await db_startup()
#     mx_invoice_query = """DELETE FROM mx_invoice
#                 WHERE restaurant_branch_id = :restaurant_branch_id"""

#     branch_values = {
#         "restaurant_branch_id": resp_js_new_branch["data"]["newRestaurantBranch"]["id"]
#     }

#     await SQLDatabase.execute(
#         query=mx_invoice_query,
#         values=branch_values,
#     )
#     await db_shutdown()


# @pytest.fixture
# def test_ficture_new_invoice_file_ok(
#     test_ficture_new_normal_orden_ok: Dict[str, Any]  # noqa
# ):  # noqa
#     try:
#         prefix_prod = "ProdsTest"
#         fd, path_inv = tempfile.mkstemp(prefix=prefix_prod, suffix=".pdf", dir=os.getcwd())
#         payload = {
#             "operations": json.loads(
#         { "query": "mutation uploadRestoInvoice($pdf: Upload!, $xml: Upload!, $ordenId: UUID!)
# { uploadInvoice(ordenId: $ordenId, pdfFile: $pdf, xmlFile: $xml) { ... on MxUploadInvoiceMsg { success msg } ... on MxInvoiceError { code msg}}}", # noqa
#         "variables": { "pdf": None, "ordenId": None, "xml": None}}),

#             "map": '{ "xml": ["variables.xml"], "pdf": ["variables.pdf"] }',
#         }
#         with tempfile.TemporaryFile(prefix=prefix_prod, suffix=".pdf", dir=os.getcwd()) as file:
#             pass

#         files = [
#             ("pdf", (path_inv.split("//")[-1], open(path_inv, "rb"), "application/pdf")),
#             (
#                 "xml",
#                 (
#                     "Factura-11232-PTA1908265U0.xml",
#                     open(
#                         "/home/fernando/Downloads/Factura/Factura-11232-PTA1908265U0.xml",
#                         "rb",
#                     ),
#                     "text/xml",
#                 ),
#             ),
#         ]
#         headers = {}
#         resp_str_new_invoice_file = requests.request(
#             "POST", url_test, headers=headers, data=payload, files=files
#         )
#     finally:
#       os.remove()

#     yield {
#         "user": test_ficture_new_normal_orden_ok["user"],
#         "resp_js_new_rest_user": test_ficture_new_normal_orden_ok[
#             "resp_js_new_rest_user"
#         ],
#         "resp_js_new_restaurant_business": test_ficture_new_normal_orden_ok[
#             "resp_js_new_restaurant_business"
#         ],
#         "resp_js_new_branch": test_ficture_new_normal_orden_ok["resp_js_new_branch"],
#         "resp_js_category_id": test_ficture_new_normal_orden_ok["resp_js_category_id"],
#         "resp_js_supp_category_id": test_ficture_new_normal_orden_ok[
#             "resp_js_supp_category_id"
#         ],
#         "resp_js_product": test_ficture_new_normal_orden_ok["resp_js_product"],
#         "resp_js_new_rest_supp": test_ficture_new_normal_orden_ok[
#             "resp_js_new_rest_supp"
#         ],
#         "resp_js_new_normal_orden": test_ficture_new_normal_orden_ok[
#             "resp_js_new_normal_orden"
#         ],
#         "resp_str_new_invoice_file": resp_str_new_invoice_file.text,
#     }
#     asyncio.run(
#         delete_invoice_file(
#             test_ficture_new_normal_orden_ok["resp_js_new_branch"],
#         )
#     )


# @pytest.fixture
# def test_ficture_new_invoice_file_error(
#     test_ficture_new_normal_orden_ok: Dict[str, Any]  # noqa
# ):  # noqa
#     try:
#         prefix_prod = "Invoice"
#         fd, path_inv = tempfile.mkstemp(prefix=prefix_prod, suffix=".txt", dir=os.getcwd())

#         payload = {
#             "operations": """
#         { "query": "mutation uploadRestoInvoice($pdf: Upload!, $xml: Upload!,
#  $ordenId: UUID!) { uploadInvoice(ordenId: $ordenId, pdfFile: $pdf, xmlFile: $xml)
# { ... on MxUploadInvoiceMsg { success msg } ... on MxInvoiceError { code msg}}}",
# "variables": { "pdf": null, "ordenId": "12d76c37-a360-4d3b-9a8b-990396a95fe3", "xml": null } }""",
#             "map": '{ "xml": ["variables.xml"], "pdf": ["variables.pdf"] }',
#         }

#         files = [
#             ("pdf", (path_inv.split("//")[-1], open(path_inv, "rb"), "application/pdf")),
#             (
#                 "xml",
#                 (
#                     "Factura-11232-PTA1908265U0.xml",
#                     open(
#                         "/home/fernando/Downloads/Factura/Factura-11232-PTA1908265U0.xml",
#                         "rb",
#                     ),
#                     "text/xml",
#                 ),
#             ),
#         ]
#         headers = {}
#         response = requests.request(
#             "POST", url_test, headers=headers, data=payload, files=files
#         )
#         resp_str_new_invoice_file_error = ast.literal_eval(response.text)
#     finally:
#       os.remove(path_inv)
#     yield {
#         "user": test_ficture_new_normal_orden_ok["user"],
#         "resp_js_new_rest_user": test_ficture_new_normal_orden_ok[
#             "resp_js_new_rest_user"
#         ],
#         "resp_js_new_restaurant_business": test_ficture_new_normal_orden_ok[
#             "resp_js_new_restaurant_business"
#         ],
#         "resp_js_new_branch": test_ficture_new_normal_orden_ok["resp_js_new_branch"],
#         "resp_js_category_id": test_ficture_new_normal_orden_ok["resp_js_category_id"],
#         "resp_js_supp_category_id": test_ficture_new_normal_orden_ok[
#             "resp_js_supp_category_id"
#         ],
#         "resp_js_product": test_ficture_new_normal_orden_ok["resp_js_product"],
#         "resp_js_new_rest_supp": test_ficture_new_normal_orden_ok[
#             "resp_js_new_rest_supp"
#         ],
#         "resp_js_new_normal_orden": test_ficture_new_normal_orden_ok[
#             "resp_js_new_normal_orden"
#         ],
#         "resp_str_new_invoice_file_error": resp_str_new_invoice_file_error,
#     }
