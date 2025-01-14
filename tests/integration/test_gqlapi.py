from gqlapi.db import db_startup # noqa
from typing import Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from .fixtures.firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from .fixtures.gqlapi import ( # noqa
    test_ficture_firebase_signin_ok, # noqa
    test_ficture_firebase_signup_ok_delete_ok, # noqa
)  # noqa
from .mocks.gqlapi import mock_fb_user

# async def delete_all():
#     await db_startup()

#     _rest_cat_data = await SQLDatabase.fetch_one(
#         query="SELECT id FROM category WHERE name = :name",
#         values={"name": "SupplierCategoryTest"},
#     )
#     if _rest_cat_data:
#         _rest_cat_result = dict(_rest_cat_data._mapping.items())
#         _rest_branch_cat_data = await SQLDatabase.fetch_one(
#             query="SELECT * FROM restaurant_branch_category WHERE restaurant_category_id = :restaurant_category_id",
#             values={"restaurant_category_id": _rest_cat_result["id"]},
#         )
#         if _rest_branch_cat_data:
#             await SQLDatabase.execute(
#                 query="""DELETE FROM restaurant_branch_category
#                     WHERE restaurant_category_id = :restaurant_category_id""",
#                 values={"restaurant_category_id": _rest_cat_result["id"]},
#             )
#         await SQLDatabase.execute(
#             query="""DELETE FROM category
#                 WHERE id = :restaurant_categoryid""",
#             values={"restaurant_category_id": _rest_cat_result["id"]},
#         )

#     _rest_branch_data = await SQLDatabase.fetch_one(
#         query="SELECT id FROM restaurant_branch WHERE name = :name",
#         values={"email": mock_rest_branch["name"]},
#     )
#     if _rest_branch_data:
#         _rest_branch_result = dict(_rest_branch_data._mapping.items())
#         _rest_branch_tax_data = await SQLDatabase.fetch_one(
#             query="SELECT * FROM restaurant_branch_mx_tax_info WHERE branch_id = :branch_id",
#             values={"branch_id": _rest_branch_result["id"]},
#         )
#         if _rest_branch_tax_data:
#             await SQLDatabase.execute(
#                 query="""DELETE FROM restaurant_branch_mx_invoice_info
#                     WHERE branch_id = :restaurant_branch_id""",
#                 values={"branch_id": _rest_branch_result["id"]},
#             )
#         await SQLDatabase.execute(
#             query="""DELETE FROM restaurant_branch
#                 WHERE id = :restaurant_branch_id""",
#             values={"restaurant_branch_id": _rest_branch_result["id"]},
#         )

#     _rest_bus_data = await SQLDatabase.fetch_one(
#         query="SELECT id FROM restaurant_business WHERE email = :email",
#         values={"email": mock_rest_supp["email"]},
#     )
#     if _rest_bus_data:
#         _rest_bus_result = dict(_rest_bus_data._mapping.items())
#         _rest_user_perm_data = await SQLDatabase.fetch_one(
#             query="""SELECT id FROM restaurant_user_permission
#                 WHERE restaurant_business = :restarurant_business""",
#             values={"restaurant_business": _rest_bus_data["id"]},
#         )
#         if _rest_user_perm_data:
#             _rest_user_perm_result = dict(_rest_user_perm_data._mapping.items())
#             await SQLDatabase.execute(
#                 query="""DELETE FROM restaurant_user_permission
#                         WHERE id = :restaurant_user_permission_id""",
#                 values={"restaurant_user_permission_id": _rest_user_perm_result["id"]},
#             )
#         await SQLDatabase.execute(
#             query="""DELETE FROM restaurant_business
#                     WHERE id = :restaurant_business_id""",
#             values={"restaurant_business_id": _rest_bus_result["id"]},
#         )

#     _rest_user_data = await SQLDatabase.fetch_one(
#         query="SELECT id FROM restaurant_user WHERE email = :email",
#         values={"email": mock_rest_user["email"]},
#     )
#     if _rest_user_data:
#         _rest_user_result = dict(_rest_user_data._mapping.items())
#         await SQLDatabase.execute(
#             query="""DELETE FROM restaurant_user Where id = :restaurant_user_id""",
#             values={"restaurant_user_id": _rest_user_result["id"]},
#         )

#     _core_user_data = await SQLDatabase.fetch_one(
#         query="SELECT id FROM core_user WHERE email = :email",
#         values={"email": mock_fb_user["email"]},
#     )
#     if _core_user_data:
#         _core_user_result = dict(_core_user_data._mapping.items())
#         await SQLDatabase.execute(
#             query="""DELETE FROM core_user Where id = :core_id""",
#             values={"core_id": _core_user_result["id"]},
#         )

#     await db_shutdown()


def test_version():
    assert isinstance(__version__, str)


def test_firebase_signin_ok(
    test_ficture_firebase_signin_ok: Dict[str, FirebaseAuthApi]  # noqa
):  # noqa
    usr_creds = test_ficture_firebase_signin_ok["user"]
    # assert data type
    assert isinstance(usr_creds, dict)
    assert usr_creds["email"] == mock_fb_user["email"]
    assert "idToken" in usr_creds



# def test_validate_id_token_ok(setup_fb_admin: Dict[str, FirebaseApp], test_firebase_signin_ok: Dict[str, Any]):  # noqa
#     _user = test_firebase_signin_ok['user']
#     _fb = setup_fb_admin['firebase']
#     # execute fb integration
#     mock_repo = FirebaseTokenRepository(_fb)
#     _creds = mock_repo.verify_token(_user['idToken'])
#     assert _creds['token'] == _user['idToken']
#     assert _creds['is_valid']
#     assert _creds['info'].email == _user['email']
