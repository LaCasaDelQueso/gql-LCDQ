# Repository Interfaces
from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID

import strawberry

from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.domain.models.v2.core import Category, ProductFamilyCategory
from gqlapi.domain.models.v2.restaurant import RestaurantBranchCategory
from gqlapi.domain.models.v2.supplier import SupplierUnitCategory
from gqlapi.domain.models.v2.utils import CategoryType


@strawberry.type
class CategoryError:
    msg: str
    code: int


CategoryResult = strawberry.union(
    "CategoryResult",
    (
        CategoryError,
        Category,
    ),
)


class CategoryHandlerInterface(ABC):
    @abstractmethod
    async def new_category(
        self,
        name: str,
        keywords: List[str],
        category_type: CategoryType,
        alima_user_id: UUID,
        parent_product_category_id: Optional[UUID] = None,
    ) -> Category:
        raise NotImplementedError

    @abstractmethod
    async def edit_category(
        self,
        category_id: UUID,
        name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category_type: Optional[CategoryType] = None,
        parent_product_category_id: Optional[UUID] = None,
    ) -> Category:
        raise NotImplementedError

    @abstractmethod
    async def search_categories(
        self,
        name: Optional[str] = None,
        search: Optional[str] = None,
        category_type: Optional[CategoryType] = None,
        parent_product_category_id: Optional[UUID] = None,
    ) -> List[Category]:
        raise NotImplementedError


class CategoryRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        category: Category,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        category_id: UUID,
        name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        category_id: UUID,
    ) -> Category:
        raise NotImplementedError

    @deprecated("Use exists() instead", "domain")
    @abstractmethod
    async def exist(
        self,
        category_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        category_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self, category_types: List[CategoryType]) -> List[Category]:
        raise NotImplementedError

    @abstractmethod
    async def get_categories(
        self,
        name: Optional[str] = None,
        search: Optional[str] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> List[Category]:
        raise NotImplementedError

    @abstractmethod
    async def exists_relation_type_name(
        self, name: str, category_type: CategoryType
    ) -> NoneType:
        raise NotImplementedError


class RestaurantBranchCategoryRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        branch_category: RestaurantBranchCategory,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        branch_category: RestaurantBranchCategory,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self, restaurant_branch_id: UUID, restaurant_category_id: UUID
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self, restaurant_branch_id: UUID, restaurant_category_id: UUID
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        rest_branch_id: UUID,
    ) -> RestaurantBranchCategory:
        raise NotImplementedError

    @abstractmethod
    async def fetch(
        self,
        rest_branch_id: UUID,
    ) -> RestaurantBranchCategory | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        branch_id: UUID,
    ) -> NoneType:
        raise NotImplementedError


class SupplierUnitCategoryRepositoryInterface(ABC):
    @deprecated("Use add() instead", "domain")
    @abstractmethod
    async def new(
        self,
        unit_category: SupplierUnitCategory,
    ) -> UUID:
        raise NotImplementedError

    @deprecated("Use edit() instead", "domain")
    @abstractmethod
    async def update(self, supplier_unit_id: UUID, supplier_category_id: UUID) -> bool:
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    async def get(
        self,
        supplier_unit_id: UUID,
    ) -> SupplierUnitCategory:
        raise NotImplementedError

    @deprecated("Use exists() instead", "domain")
    @abstractmethod
    async def exist(
        self,
        supplier_unit_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        unit_category: SupplierUnitCategory,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(self, supplier_unit_id: UUID, supplier_category_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, supplier_unit_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        supplier_unit_id: UUID,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        supplier_unit_ids: List[UUID],
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError


class ProductFamilyCategoryRepositoryInterface(ABC):
    @abstractmethod
    async def new(
        self,
        prod_fam_category: ProductFamilyCategory,
    ) -> UUID:
        raise NotImplementedError

    @abstractmethod
    async def update(self, product_family_id: UUID, category_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def get(
        self,
        product_family_id: UUID,
    ) -> ProductFamilyCategory:
        raise NotImplementedError

    @abstractmethod
    async def exists(
        self,
        product_family_id: UUID,
    ) -> NoneType:
        raise NotImplementedError
