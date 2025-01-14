from datetime import datetime
import logging
from types import NoneType
from typing import Optional, List, Dict, Any
from uuid import UUID
import uuid

from gqlapi.domain.interfaces.v2.restaurant.restaurant_suppliers import (
    RestaurantBusinessSupplierBusinessRelation,
    RestaurantSupplierAssignationRepositoryInterface,
)
from gqlapi.domain.models.v2.restaurant import RestaurantSupplierRelation
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import sql_to_domain


class RestaurantSupplierAssignationRepository(
    CoreRepository, RestaurantSupplierAssignationRepositoryInterface
):
    async def search(
        self,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
    ) -> List[RestaurantSupplierRelation]:
        """Search restaurant supplier relation

        Args:
            restaurant_branch_id (Optional[UUID], optional): unique branch id. Defaults to None.
            supplier_business_id (Optional[UUID], optional): unique supplier id. Defaults to None.

        Returns:
            List[RestaurantSupplierRelation]
        """
        rest_info_values_view = {}
        filter_values = ""
        if restaurant_branch_id:
            rest_info_values_view["restaurant_branch_id"] = restaurant_branch_id
            filter_values += " restaurant_branch_id =:restaurant_branch_id"
        if supplier_business_id:
            if rest_info_values_view:
                filter_values += " AND"
            rest_info_values_view["supplier_business_id"] = supplier_business_id
            filter_values += " supplier_business_id =:supplier_business_id"

        _resp = await super().search(
            core_element_name="Restaurant Supplier Assignation",
            core_element_tablename="""
                restaurant_supplier_relation""",
            filter_values=filter_values,
            core_columns="*",
            values=rest_info_values_view,
        )
        return [
            RestaurantSupplierRelation(**sql_to_domain(r, RestaurantSupplierRelation))
            for r in _resp
        ]

    async def new(
        self,
        restaurant_branch_id: UUID,
        supplier_business_id: UUID,
        core_user_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> UUID:
        """Create new restaurant supplier relation

        Args:
            restaurant_branch_id (UUID): unique rest branch id
            supplier_business_id (UUID): unique supp business id
            core_user_id (UUID): unique core user id
            rating (Optional[int], optional): restaurant satisfaction. Defaults to None.
            review (Optional[str], optional): restaurant comment. Defaults to None.

        Returns:
            UUID: _description_
        """
        # cast to dict
        internal_values_restaurant_supplier = {
            "id": uuid.uuid4(),
            "restaurant_branch_id": restaurant_branch_id,
            "supplier_business_id": supplier_business_id,
            "rating": rating,
            "review": review,
            "created_by": core_user_id,
        }
        # call super method from new
        await super().new(
            core_element_tablename="restaurant_supplier_relation",
            core_element_name="Restaurant_Supplier_Relation",
            core_query="""INSERT INTO restaurant_supplier_relation
                (id,
                restaurant_branch_id,
                supplier_business_id,
                rating,
                review,
                created_by)
                    VALUES
                    (:id,
                    :restaurant_branch_id,
                    :supplier_business_id,
                    :rating,
                    :review,
                    :created_by)
                """,
            core_values=internal_values_restaurant_supplier,
        )
        return internal_values_restaurant_supplier["id"]

    async def update(
        self,
        rest_supp_assig_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> bool:
        """Update restaurant business relation

        Args:
            rest_supp_assig_id (UUID): unique restaurant business relation id
            rating (Optional[int], optional): restaurant satisfaction. Defaults to None.
            review (Optional[str], optional): restaurant comment. Defaults to None.

        Raises:
            GQLApiException: _description_

        Returns:
            bool: _description_
        """
        rsa_atributes = []
        rsa_values_view: Dict[str, Any] = {"id": rest_supp_assig_id}

        if rating:
            rsa_atributes.append(" rating=:rating")
            rsa_values_view["rating"] = rating
        if review:
            rsa_atributes.append(" review=:review")
            rsa_values_view["review"] = review

        if len(rsa_atributes) == 0:
            logging.warning("No values to update Restaurant Supplier Assignation")
            return False

        rsa_atributes.append(" last_updated=:last_updated")
        rsa_values_view["last_updated"] = datetime.utcnow()

        rsa_query = f"""UPDATE restaurant_supplier_relation
                            SET {','.join(rsa_atributes)}
                            WHERE id=:id;
                """
        await super().update(
            core_element_name="Restaurant Supplier Assignation",
            core_query=rsa_query,
            core_values=rsa_values_view,
        )
        return True

    async def get(self, id: UUID) -> Dict[Any, Any]:
        """Get restaurant supplier relation

        Args:
            id (UUID): unique id

        Returns:
            Dict[Any, Any]: restaurant_supplier_relation model dict
        """
        _data = await super().get(
            id=id,
            core_element_tablename="restaurant_supplier_relation",
            core_element_name="Restaurant Supplier Assignation",
            core_columns="*",
        )

        return sql_to_domain(_data, RestaurantSupplierRelation)

    async def exist(self, id: UUID) -> NoneType:
        """validate exists restaurant supplier relation

        Args:
            id (UUID): unique id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=id,
            core_element_tablename="restaurant_supplier_relation",
            core_element_name="Restaurant Supplier Assignation",
            id_key="id",
            core_columns="id",
        )

    async def get_product_supplier_assignation(
        self,
        restaurant_business_id: UUID,
        supplier_business_name: str,
    ) -> List[RestaurantBusinessSupplierBusinessRelation]:
        info_values_view = {}
        info_values_view["restaurant_business_id"] = restaurant_business_id
        info_values_view["name"] = supplier_business_name

        _resp = await super().search(
            core_element_name="Restaurant Suppplier Assignation",
            core_element_tablename="""
            restaurant_supplier_relation rsr
            JOIN restaurant_branch rbr ON rbr.id = rsr.restaurant_branch_id
            JOIN restaurant_business rb ON rb.id = rbr.restaurant_business_id
            JOIN supplier_business sb ON sb.id= rsr.supplier_business_id
            """,
            filter_values=" rb.id=:restaurant_business_id and sb.name=:name",
            core_columns=[
                "rb.id restaurant_business_id",
                "rsr.supplier_business_id supplier_business_id",
            ],
            values=info_values_view,
        )
        relation_dir = []
        for r in _resp:
            relation_dir.append(
                RestaurantBusinessSupplierBusinessRelation(
                    **sql_to_domain(r, RestaurantBusinessSupplierBusinessRelation)
                )
            )
        return relation_dir

    async def find_by_restaurant_business(
        self,
        restaurant_business_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
    ) -> List[RestaurantSupplierRelation]:
        """Search restaurant supplier relation

        Args:
            restaurant_branch_id (Optional[UUID], optional): unique branch id. Defaults to None.
            supplier_business_id (Optional[UUID], optional): unique supplier id. Defaults to None.

        Returns:
            List[RestaurantSupplierRelation]
        """
        rest_info_values_view = {}
        filter_values = ""
        if restaurant_business_id:
            rest_info_values_view["restaurant_business_id"] = restaurant_business_id
            filter_values += """ restaurant_branch_id in
            (SELECT id FROM restaurant_branch WHERE restaurant_business_id = :restaurant_business_id)"""
        if supplier_business_id:
            if rest_info_values_view:
                filter_values += " AND"
            rest_info_values_view["supplier_business_id"] = supplier_business_id
            filter_values += " supplier_business_id =:supplier_business_id"

        _resp = await super().find(
            core_element_name="Restaurant Supplier Assignation",
            core_element_tablename="""
                restaurant_supplier_relation""",
            filter_values=filter_values,
            core_columns="*",
            values=rest_info_values_view,
        )
        return [
            RestaurantSupplierRelation(**sql_to_domain(r, RestaurantSupplierRelation))
            for r in _resp
        ]
