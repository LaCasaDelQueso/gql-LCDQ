from typing import List, Optional
from uuid import UUID
import uuid
from gqlapi.domain.interfaces.v2.catalog.category import (
    CategoryHandlerInterface,
    CategoryRepositoryInterface,
)
from gqlapi.domain.models.v2.core import Category
from gqlapi.domain.models.v2.utils import CategoryType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface


class CategoryHandler(CategoryHandlerInterface):
    def __init__(
        self,
        category_repo: CategoryRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
    ):
        self.repository = category_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo

    async def new_category(
        self,
        name: str,
        keywords: List[str],
        category_type: CategoryType,
        firebase_id: str,
        parent_category_id: Optional[UUID] = None,
    ) -> Category:  # type: ignore
        # validate pk
        if parent_category_id:
            await self.repository.exist(parent_category_id)
        await self.repository.exists_relation_type_name(name, category_type)

        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        # post orden
        category_id = await self.repository.new(
            category=Category(
                id=uuid.uuid4(),
                name=name,
                category_type=category_type,
                keywords=keywords,
                parent_category_id=parent_category_id,
                created_by=core_user.id,
            )
        )

        return await self.repository.get(category_id)

    async def edit_category(
        self,
        category_id: UUID,
        name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> Category:  # type: ignore
        if parent_category_id:
            await self.repository.exist(parent_category_id)
        if name or category_type:
            category_val = await self.repository.get(category_id)
            if name:
                category_val.name = name
            if category_type:
                category_val.category_type = category_type

            await self.repository.exists_relation_type_name(
                category_val.name, CategoryType(category_val.category_type)
            )

        if await self.repository.update(
            category_id, name, keywords, category_type, parent_category_id
        ):
            return await self.repository.get(category_id)

    async def search_categories(
        self,
        name: Optional[str] = None,
        search: Optional[str] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> List[Category]:  # type: ignore
        # get order status
        return await self.repository.get_categories(
            name, search, category_type, parent_category_id
        )
