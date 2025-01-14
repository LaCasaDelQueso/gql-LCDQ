import asyncio
from uuid import UUID
import uuid
from gqlapi.domain.models.v2.utils import CategoryType
import pytest
from typing import Any, Dict
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
from gqlapi.db import database as SQLDatabase, db_startup, db_shutdown  # noqa
from .firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from .gqlapi import (  # noqa
    test_ficture_firebase_signin_ok,  # noqa
    test_ficture_firebase_signup_ok_delete_ok,  # noqa
    fixture_gql_api,
)
from .restaurant_user import (  # noqa
    test_ficture_new_restaurant_user_ok,  # noqa
    test_ficture_get_restaurant_user_by_token_ok,  # noqa
    test_fixture_new_restaurant_user_error,  # noqa
)
from .restaurant_business import (  # noqa
    test_ficture_get_restaurant_business_ok,  # noqa
    test_ficture_new_restaurant_business_error,  # noqa
    test_ficture_new_restaurant_business_ok,  # noqa
    test_ficture_edit_restaurant_business_error,  # noqa
    test_ficture_edit_restaurant_business_ok,  # noqa
)
from ..mocks.restaurant_branch import (  # noqa
    mock_branch_tax_info,  # noqa
    mock_branch_tax_info_error,  # noqa
    mock_rest_branch,  # noqa
    mock_rest_branch_error,  # noqa
)
from ..queries.restaurant_branch import (  # noqa
    query_test_delete_branch,  # noqa
    query_test_edit_branch,  # noqa
    query_test_edit_branch_tax_id,  # noqa
    query_test_get_branch_by_id,  # noqa
    query_test_get_branches,  # noqa
    query_test_get_rest_cat,  # noqa
    query_test_new_branch_tax_info,  # noqa
    query_test_new_restaurant_branch,  # noqa
)


async def create_muck_category(user: Dict[Any, Any]) -> UUID:
    await db_startup()
    id = uuid.uuid4()
    # core_user = await get_core_user_by_firebase_id(user)

    values = {
        "id": id,
        "name": "TestCategory2",
        "category_type": CategoryType.RESTAURANT.value,
        "keywords": ["category"],
        "created_by": user["resp_js_new_rest_user"]["data"]["newRestaurantUser"][
            "coreUserId"
        ],
    }
    category_query = """INSERT INTO category
                (id,
                name,
                category_type,
                keywords,
                created_by
                )
                    VALUES
                    (:id,
                    :name,
                    :category_type,
                    :keywords,
                    :created_by)
                """

    await SQLDatabase.execute(
        query=category_query,
        values=values,
    )
    await db_shutdown()
    return id


async def get_category(category_type: CategoryType) -> Dict[Any, Any]:
    await db_startup()
    cat_query = "Select * from category where category_type = :category_type"
    cat_values = {"category_type": category_type.value}
    _data = await SQLDatabase.fetch_one(query=cat_query, values=cat_values)
    await db_shutdown()
    if _data:
        result = dict(_data._mapping.items())
        return result
    else:
        return {}


@pytest.fixture(scope="session")
def test_ficture_get_categoty_restaurant():  # noqa
    category = asyncio.run(get_category(CategoryType.RESTAURANT))

    yield {"resp_category": category}


@pytest.fixture(scope="session")
def test_ficture_get_category_supplier():  # noqa
    category = asyncio.run(get_category(CategoryType.SUPPLIER))

    yield {"resp_category": category}
