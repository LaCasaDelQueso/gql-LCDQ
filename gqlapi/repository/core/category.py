from datetime import datetime
import logging
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.catalog.category import (
    CategoryRepositoryInterface,
    ProductFamilyCategoryRepositoryInterface,
    RestaurantBranchCategoryRepositoryInterface,
    SupplierUnitCategoryRepositoryInterface,
)
from gqlapi.domain.models.v2.core import Category, ProductFamilyCategory
from gqlapi.domain.models.v2.restaurant import RestaurantBranchCategory
from gqlapi.domain.models.v2.supplier import SupplierUnitCategory
from gqlapi.domain.models.v2.utils import CategoryType
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple


class CategoryRepository(CoreRepository, CategoryRepositoryInterface):
    async def new(
        self,
        category: Category,
    ) -> UUID:
        """Create New Category

        Args:
            category (Category): Category object

        Returns:
            UUID: unique Category id
        """
        # cast to dict
        core_vals = domain_to_dict(category, skip=["created_at", "last_updated"])
        # call super method from new
        core_vals["category_type"] = core_vals["category_type"].value

        await super().new(
            core_element_tablename="category",
            core_element_name="Category",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO category
                (id,
                name,
                category_type,
                keywords,
                parent_category_id,
                created_by
                )
                    VALUES
                    (:id,
                    :name,
                    :category_type,
                    :keywords,
                    :parent_category_id,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    async def get(
        self,
        category_id: UUID,
    ) -> Category:
        """Get Category

        Args:
            category_id (UUID): unique category id

        Returns:
            Category: Category Model
        """
        cat = await super().get(
            id=category_id,
            core_element_tablename="category",
            core_element_name="Category",
            core_columns="*",
        )
        return Category(**sql_to_domain(cat, Category))

    async def update(
        self,
        category_id: UUID,
        name: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": category_id}

        if name:
            core_atributes.append(" name=:name")
            core_values_view["name"] = name
        if keywords:
            core_atributes.append(" keywords=:keywords")
            core_values_view["keywords"] = keywords
        if category_type:
            core_atributes.append(" category_type=:category_type")
            core_values_view["category_type"] = category_type.value
        if parent_category_id:
            core_atributes.append(" parent_category_id=:parent_category_id")
            core_values_view["parent_category_id"] = parent_category_id

        if len(core_atributes) == 0:
            raise GQLApiException(
                msg="Issues no data to update in sql",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )

        core_atributes.append(" last_updated=:last_updated")
        core_values_view["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE category
                            SET {','.join(core_atributes)}
                            WHERE id=:id;
                """
        await super().update(
            core_element_name="Category",
            core_query=branch_query,
            core_values=core_values_view,
        )
        return True

    @deprecated("Use exists() instead", "gqlapi.repository")
    async def exist(
        self,
        category_id: UUID,
    ) -> NoneType:
        """Validate category exists

        Args:
            category_id (UUID): unique category id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=category_id,
            core_columns="id",
            core_element_tablename="category",
            id_key="id",
            core_element_name="Category",
        )

    async def exists(
        self,
        category_id: UUID,
    ) -> bool:
        """Validate category exists

        Args:
            category_id (UUID): unique category id

        Returns:
            bool: Validate category exists
        """
        return await super().exists(
            id=category_id,
            core_columns="id",
            core_element_tablename="category",
            id_key="id",
            core_element_name="Category",
        )

    async def get_categories(
        self,
        name: Optional[str] = None,
        search: Optional[str] = None,
        category_type: Optional[CategoryType] = None,
        parent_category_id: Optional[UUID] = None,
    ) -> List[Category]:
        category_atributes = []
        category_values_view = {}
        if search:
            category_atributes.append(
                " exists (select 1 from unnest(keywords) keys where keys ILIKE :search ) and"
            )
            category_values_view["search"] = (
                "%" + "".join(filter(str.isalnum, search.lower())) + "%"
            )
        if name:
            category_atributes.append(" name=:name and")
            category_values_view["name"] = name
        if category_type:
            category_atributes.append(" category_type=:category_type and")
            category_values_view["category_type"] = category_type.value

        if parent_category_id:
            category_values_view["parent_category_id"] = parent_category_id
            category_atributes.append(" parent_category_id=:parent_category_id and")

        if len(category_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(category_atributes).split()
            filter_values = " ".join(filter_values[:-1])
        _resp = await super().find(
            core_element_name="Category",
            core_element_tablename="""category""",
            filter_values=filter_values,
            core_columns=["*"],
            values=category_values_view,
        )
        category_dir = []
        for r in _resp:
            rest_branch = Category(**sql_to_domain(r, Category))
            category_dir.append(rest_branch)
        return category_dir

    async def exists_relation_type_name(
        self, name: str, category_type: CategoryType
    ) -> NoneType:
        """Validate relation exists

        Args:
            name (str): product family name
            category_type (CategoryType): type of category

        Returns:
            NoneType: None
        """
        type_name_values_view = {}
        type_name_atributes = " name=:name and category_type =:category_type"
        type_name_values_view["name"] = name
        type_name_values_view["category_type"] = category_type.value
        _resp = await super().exists_relation(
            core_element_name="Category",
            core_element_tablename="category",
            filter_values=type_name_atributes,
            core_columns=["id"],
            values=type_name_values_view,
        )
        if _resp:
            logging.info(f"realation - {name} - {category_type.value} exists")

    async def get_all(self, category_types: List[CategoryType]) -> List[Category]:
        """Get all categories

        Args:
            category_types (List[CategoryType]): list of category types

        Returns:
            List[Category]: list of Category models
        """
        # create query
        core_query = "SELECT * FROM category"
        try:
            if category_types:
                core_query += " WHERE category_type IN ("
                core_values = {}
                for i, cat_type in enumerate(category_types):
                    core_query += f":cat_type_{i},"
                    core_values[f"cat_type_{i}"] = cat_type.value
                core_query = core_query[:-1] + ")"
                # call super method from get_all
                cats = await self.db.fetch_all(query=core_query, values=core_values)
            else:
                cats = await self.db.fetch_all(query=core_query)
        except Exception as e:
            logging.error(e)
            raise GQLApiException(
                msg="Error fetching categories",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        return [Category(**sql_to_domain(cat, Category)) for cat in cats]


class RestaurantBranchCategoryRepository(
    CoreRepository, RestaurantBranchCategoryRepositoryInterface
):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        branch_category: RestaurantBranchCategory,
    ) -> bool:
        """Create new restaurant branch category

        Args:
            branch_category (RestaurantBranchCategory): RestaurantBranchCategory object

        Returns:
            bool: Validate creation is done
        """
        # cast to dict
        core_user_vals = domain_to_dict(
            branch_category, skip=["created_at", "last_updated"]
        )
        # call super method from new
        await super().new(
            core_element_tablename="restaurant_branch_category",
            core_element_name="Restaurant_Branch_Category",
            core_query="""INSERT INTO restaurant_branch_category
                (restaurant_branch_id,
                restaurant_category_id,
                created_by
                )
                    VALUES
                    (:restaurant_branch_id,
                    :restaurant_category_id,
                    :created_by)
                """,
            core_values=core_user_vals,
        )
        return True

    async def add(
        self,
        branch_category: RestaurantBranchCategory,
    ) -> bool:
        """Create new restaurant branch category

        Args:
            branch_category (RestaurantBranchCategory): RestaurantBranchCategory object

        Returns:
            bool: Validate creation is done
        """
        # cast to dict
        core_user_vals = domain_to_dict(
            branch_category, skip=["created_at", "last_updated"]
        )
        # call super method from new
        res = await super().add(
            core_element_tablename="restaurant_branch_category",
            core_element_name="Restaurant_Branch_Category",
            core_query="""INSERT INTO restaurant_branch_category
                (restaurant_branch_id,
                restaurant_category_id,
                created_by
                )
                    VALUES
                    (:restaurant_branch_id,
                    :restaurant_category_id,
                    :created_by)
                """,
            core_values=core_user_vals,
        )
        return False if res is None else True

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        rest_branch_id: UUID,
    ) -> RestaurantBranchCategory:
        """Get restaurant branch category

        Args:
            rest_branch_id (UUID): unique restaurant_branch:id

        Returns:
            RestaurantBranchCategory: RestaurantBranchCategory model
        """
        cat = await super().get(
            id=rest_branch_id,
            core_element_tablename="restaurant_branch_category",
            core_element_name="Restaurant_Branch_Category",
            core_columns="*",
            id_key="restaurant_branch_id",
        )
        return RestaurantBranchCategory(**sql_to_domain(cat, RestaurantBranchCategory))

    async def fetch(
        self,
        restaurant_branch_id: UUID,
    ) -> RestaurantBranchCategory | NoneType:
        """Get restaurant branch category

        Args:
            rest_branch_id (UUID): unique restaurant_branch:id

        Returns:
            RestaurantBranchCategory: RestaurantBranchCategory model
        """
        cat = await super().fetch(
            id=restaurant_branch_id,
            core_element_tablename="restaurant_branch_category",
            core_element_name="Restaurant_Branch_Category",
            core_columns="*",
            id_key="restaurant_branch_id",
        )
        if not cat:
            return None
        return RestaurantBranchCategory(**sql_to_domain(cat, RestaurantBranchCategory))

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self, restaurant_branch_id: UUID, restaurant_category_id: UUID
    ) -> bool:
        """Update restaurant branch category

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            restaurant_category_id (UUID): unique restaurant category id

        Returns:
            bool: Validate update is done
        """
        # # create update query
        core_query = "UPDATE restaurant_branch_category SET "
        core_values = {}
        if restaurant_category_id:
            core_query += "restaurant_category_id = :restaurant_category_id, "
            core_values["restaurant_category_id"] = restaurant_category_id
        core_query += "last_updated = :last_updated WHERE restaurant_branch_id = :restaurant_branch_id"
        core_values["last_updated"] = datetime.utcnow()
        core_values["restaurant_branch_id"] = restaurant_branch_id
        # # call super method from update
        await super().update(
            core_element_name="Restaurant Branch Category",
            core_query=core_query,
            core_values=core_values,
        )
        return True

    async def edit(
        self, restaurant_branch_id: UUID, restaurant_category_id: UUID
    ) -> bool:
        """Update restaurant branch category

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            restaurant_category_id (UUID): unique restaurant category id

        Returns:
            bool: Validate update is done
        """
        # # create update query
        core_values = {}
        core_values["restaurant_category_id"] = restaurant_category_id
        core_values["last_updated"] = datetime.utcnow()
        core_values["restaurant_branch_id"] = restaurant_branch_id
        # # call super method from update
        return await super().edit(
            core_element_name="Restaurant Branch Category",
            core_query="""
                UPDATE restaurant_branch_category SET
                    restaurant_category_id = :restaurant_category_id,
                    last_updated = :last_updated
                WHERE restaurant_branch_id = :restaurant_branch_id
                """,
            core_values=core_values,
        )

    async def exist(
        self,
        branch_id: UUID,
    ) -> NoneType:
        """Validate restaurant branch category exists

        Args:
            branch_id (UUID): unique restaurant branch id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=branch_id,
            core_columns="*",
            core_element_tablename="restaurant_branch_category",
            id_key="restaurant_branch_id",
            core_element_name="Restaurant Branch Category",
        )


class SupplierUnitCategoryRepository(
    CoreRepository, SupplierUnitCategoryRepositoryInterface
):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        unit_category: SupplierUnitCategory,
    ) -> bool:
        """Create new supplier unit category

        Args:
            unit_category (SupplierUnitCategory): SupplierUnitCategory object

        Returns:
            bool: Validate creation is done
        """
        # cast to dict
        core_vals = domain_to_dict(unit_category, skip=["created_at", "last_updated"])
        # call super method from new
        await super().new(
            core_element_tablename="supplier_unit_category",
            core_element_name="Supplier Unit Category",
            core_query="""INSERT INTO supplier_unit_category
                (supplier_unit_id,
                supplier_category_id,
                created_by
                )
                    VALUES
                    (:supplier_unit_id,
                    :supplier_category_id,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return True

    async def get(
        self,
        supp_unit_id: UUID,
    ) -> SupplierUnitCategory:
        """Get Supplier Unit Category

        Args:
            rest_branch_id (UUID): unique restaurant_branch:id

        Returns:
            RestaurantBranchCategory: RestaurantBranchCategory model
        """
        cat = await super().get(
            id=supp_unit_id,
            core_element_tablename="supplier_unit_category",
            core_element_name="Supplier Unit_Category",
            core_columns="*",
            id_key="supplier_unit_id",
        )
        return SupplierUnitCategory(**sql_to_domain(cat, SupplierUnitCategory))

    async def update(self, supplier_unit_id: UUID, supplier_category_id: UUID) -> bool:
        """Update supplier unit category

        Args:
            supplier_unit_id (UUID): unique supplier id
            supplier_category_id (UUID): unique supplier category id

        Returns:
            bool: Validate update is done
        """
        # # create update query
        core_query = "UPDATE restaurant_branch_category SET "
        core_values = {}
        if supplier_category_id:
            core_query += "supplier_category_id = :supplier_category_id, "
            core_values["supplier_category_id"] = supplier_category_id
        core_query += (
            "last_updated = :last_updated WHERE supplier_unit_id = :supplier_unit_id"
        )
        core_values["last_updated"] = datetime.utcnow()
        core_values["supplier_unit_id"] = supplier_unit_id
        # # call super method from update
        await super().update(
            core_element_name="Supplier_unit Category",
            core_query=core_query,
            core_values=core_values,
        )
        return True

    async def exist(
        self,
        supplier_unit_id: UUID,
    ) -> NoneType:
        """Validate supplier unit category exists

        Args:
            supplier_unit_id (UUID): unique supplier unit id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=supplier_unit_id,
            core_columns="*",
            core_element_tablename="supplier_unit_category",
            id_key="supplier_unit_id",
            core_element_name="Supplier Unit Category",
        )

    async def add(
        self,
        unit_category: SupplierUnitCategory,
    ) -> bool:
        """Create new supplier unit category

        Args:
            unit_category (SupplierUnitCategory): SupplierUnitCategory object

        Returns:
            bool: Validate creation is done
        """
        # cast to dict
        core_vals = domain_to_dict(unit_category, skip=["created_at", "last_updated"])
        # call super method from new
        _id = await super().add(
            core_element_tablename="supplier_unit_category",
            core_element_name="Supplier Unit Category",
            core_query="""INSERT INTO supplier_unit_category
                (supplier_unit_id,
                supplier_category_id,
                created_by
                )
                    VALUES
                    (:supplier_unit_id,
                    :supplier_category_id,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return _id is not None

    async def fetch(
        self,
        supp_unit_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Supplier Unit Category

        Args:
            rest_branch_id (UUID): unique restaurant_branch:id

        Returns:
            Dict[Any, Any]: SupplierUnitCategory model
        """
        cat = await super().fetch(
            id=supp_unit_id,
            core_element_tablename="supplier_unit_category",
            core_element_name="Supplier Unit_Category",
            core_columns="*",
            id_key="supplier_unit_id",
        )
        if not cat:
            return {}
        return sql_to_domain(cat, SupplierUnitCategory)

    async def find(
        self,
        supplier_unit_ids: List[UUID],
    ) -> List[Dict[Any, Any]]:
        """Search supplier unit category

        Parameters
        ----------
        supplier_unit_ids : List[UUID]

        Returns
        -------
        List[Dict[Any, Any]]
        """
        if not supplier_unit_ids:
            logging.info("No supplier unit ids to search on")
            return []
        su_id_str = list_into_strtuple(supplier_unit_ids)
        cats = await super().find(
            core_element_tablename="supplier_unit_category",
            core_element_name="Supplier Unit_Category",
            core_columns="*",
            filter_values=f"supplier_unit_id IN {su_id_str}",
            values={},
        )
        if not cats:
            return []
        return [sql_to_domain(cat, SupplierUnitCategory) for cat in cats]

    async def edit(self, supplier_unit_id: UUID, supplier_category_id: UUID) -> bool:
        """Update supplier unit category

        Args:
            supplier_unit_id (UUID): unique supplier id
            supplier_category_id (UUID): unique supplier category id

        Returns:
            bool: Validate update is done
        """
        # # create update query
        core_query = "UPDATE supplier_unit_category SET "
        core_values = {}
        core_query += "supplier_category_id = :supplier_category_id, "
        core_values["supplier_category_id"] = supplier_category_id
        core_query += (
            "last_updated = :last_updated WHERE supplier_unit_id = :supplier_unit_id"
        )
        core_values["last_updated"] = datetime.utcnow()
        core_values["supplier_unit_id"] = supplier_unit_id
        # # call super method from update
        return await super().edit(
            core_element_name="Supplier_unit Category",
            core_query=core_query,
            core_values=core_values,
        )

    async def exists(
        self,
        supplier_unit_id: UUID,
    ) -> bool:
        """Validate supplier unit category exists

        Args:
            supplier_unit_id (UUID): unique supplier unit id

        Returns:
            bool: Validate supplier unit category exists
        """
        return await super().exists(
            id=supplier_unit_id,
            core_columns="*",
            core_element_tablename="supplier_unit_category",
            id_key="supplier_unit_id",
            core_element_name="Supplier Unit Category",
        )


class ProductFamilyCategoryRepository(
    CoreRepository, ProductFamilyCategoryRepositoryInterface
):
    async def new(
        self,
        prod_fam_category: ProductFamilyCategory,
    ) -> bool:
        """Create new product family category

        Args:
            prod_family_category (ProductFamilyCategory): ProductFamilyCategory object

        Returns:
            bool: Validate creation is done
        """
        # cast to dict
        core_vals = domain_to_dict(
            prod_fam_category, skip=["created_at", "last_updated"]
        )
        # call super method from new
        await super().new(
            core_element_tablename="product_family_category",
            core_element_name="Product Family Category",
            core_query="""INSERT INTO product_family_category
                (product_family_id,
                category_id,
                created_by
                )
                    VALUES
                    (:product_family_id,
                    :category_id,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return True

    async def get(
        self,
        prod_fam_id: UUID,
    ) -> ProductFamilyCategory:
        """Get ProductFamilyCategory

        Args:
            prod_fam_id (UUID): unique ProductFamily id

        Returns:
            ProductFamilyCategory: ProductFamilyCategory model
        """
        prod_fam_cat = await super().get(
            id=prod_fam_id,
            core_element_tablename="product_family_category",
            core_element_name="Product Family Category",
            core_columns="*",
            id_key="product_family_id",
        )
        return ProductFamilyCategory(
            **sql_to_domain(prod_fam_cat, ProductFamilyCategory)
        )

    async def update(self, prod_fam_id: UUID, prod_fam_cat_id: UUID) -> bool:
        """Update ProductFamilyCategory

        Args:
            prod_fam_id (UUID): unique ProductFamily id
            prod_fam_cat_id (UUID): unique ProductFamilyCategory id

        Returns:
            bool: Validate update is done
        """
        # # create update query
        core_query = "UPDATE product_family_category SET "
        core_values = {}
        if prod_fam_id:
            core_query += "category_id = :category_id, "
            core_values["category_id"] = prod_fam_cat_id
        core_query += (
            "last_updated = :last_updated WHERE product_family_id = :product_family_id"
        )
        core_values["last_updated"] = datetime.utcnow()
        core_values["product_family_id"] = prod_fam_id
        # # call super method from update
        await super().update(
            core_element_name="Product Family Category",
            core_query=core_query,
            core_values=core_values,
        )
        return True

    async def exist(
        self,
        prod_fam_id: UUID,
    ) -> NoneType:
        """Validate product family category exists

        Args:
            prod_fam_id (UUID): unique product family id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=prod_fam_id,
            core_columns="*",
            core_element_tablename="product_family_category",
            id_key="product_family_id",
            core_element_name="Product Family Category",
        )

    async def search(
        self,
        product_family_id: Optional[UUID] = None,
        category_id: Optional[UUID] = None,
    ) -> List[ProductFamilyCategory]:
        product_fam_cat_atributes = []
        product_fam_cat_values_view = {}
        if product_family_id:
            product_fam_cat_atributes.append(
                " product_family_id=:product_family_id and"
            )
            product_fam_cat_values_view["product_family_id"] = product_family_id
        if category_id:
            product_fam_cat_atributes.append(" category_id=:category_id and")
            product_fam_cat_values_view["category_id"] = category_id

        if len(product_fam_cat_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(product_fam_cat_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        prod_fam_cat = await super().search(
            core_element_name="Product_Family Category",
            core_element_tablename="product_family_category",
            filter_values=filter_values,
            core_columns="*",
            values=product_fam_cat_values_view,
        )

        return [
            ProductFamilyCategory(**sql_to_domain(r, ProductFamilyCategory))
            for r in prod_fam_cat
        ]
