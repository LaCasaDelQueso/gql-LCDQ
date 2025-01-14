import logging
from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.catalog.category import CategoryError, CategoryResult
from gqlapi.domain.models.v2.utils import CategoryType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.category import CategoryHandler
from gqlapi.repository.core.category import CategoryRepository
from gqlapi.repository.user.core_user import CoreUserRepository

import strawberry
from strawberry.types import Info as StrawberryInfo


@strawberry.type
class CategoryMutation:
    @strawberry.mutation(
        name="newCategory",
        # permission_classes=[IsAuthenticated, IsAlimaEmployeeAuthorized],
    )
    async def post_new_category(
        self,
        info: StrawberryInfo,
        name: str,
        keywords: List[str],
        category_type: CategoryType,
        parent_category_id: Optional[UUID] = None,
    ) -> CategoryResult:  # type: ignore
        logging.info("Create new category")

        # instantiate handler
        _handler = CategoryHandler(
            category_repo=CategoryRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # call validation
        if not name or not keywords or not category_type:
            return CategoryError(
                msg="Empty values for creating Category",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_category(
                name,
                keywords,
                category_type,
                fb_id,
                parent_category_id,
            )
            return _resp
        except GQLApiException as ge:
            return CategoryError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="updateCategory",
        # permission_classes=[IsAuthenticated, IsAlimaEmployeeAuthorized],
    )
    async def patch_edit_category(
        self,
        info: StrawberryInfo,
        category_id: UUID,
        name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> CategoryResult:  # type: ignore
        logging.info("Update category")
        # instantiate handler
        _handler = CategoryHandler(
            category_repo=CategoryRepository(info),
        )
        # call validation
        if not category_id or not (
            name or keywords or category_type or parent_category_id
        ):
            return CategoryError(
                msg="Empty values for updating Category",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.edit_category(
                category_id,
                name,
                keywords,
                category_type,
                parent_category_id,
            )
            return _resp
        except GQLApiException as ge:
            return CategoryError(msg=ge.msg, code=ge.error_code)


@strawberry.type
class CategoryQuery:
    @strawberry.field(
        name="getCategories"
    )
    async def get_categories(
        self,
        info: StrawberryInfo,
        name: Optional[str] = None,
        search: Optional[str] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> List[CategoryResult]:  # type: ignore
        logging.info("Search categories")
        # instantiate handler
        _handler = CategoryHandler(
            category_repo=CategoryRepository(info),
        )
        try:
            # call handler
            _resp = await _handler.search_categories(
                name,
                search,
                category_type,
                parent_category_id,
            )
            return _resp
        except GQLApiException as ge:
            return [CategoryError(msg=ge.msg, code=ge.error_code)]
