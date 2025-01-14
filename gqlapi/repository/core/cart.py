from datetime import datetime
from types import NoneType
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
from gqlapi.domain.interfaces.v2.orden.cart import (
    CartProductRepositoryInterface,
    CartRepositoryInterface,
)
from gqlapi.domain.models.v2.core import Cart, CartProduct
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain


class CartRepository(CoreRepository, CartRepositoryInterface):
    async def new(
        self,
        cart: Cart,
    ) -> UUID:
        """Create New Cart

        Args:
            cart (Cart): Cart object

        Returns:
            UUID: unique Cart id
        """
        # cast to dict
        core_vals = domain_to_dict(
            cart, skip=["created_at", "last_updated", "closed_at"]
        )
        # call super method from new
        await super().new(
            core_element_tablename="cart",
            core_element_name="Cart",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO cart
                (id,
                active,
                created_by
                )
                    VALUES
                    (:id,
                    :active,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    async def get(
        self,
        cart_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Cart

        Args:
            cart_id (UUID): unique cart id

        Returns:
            Dict: Cart Model
        """
        cat = await super().get(
            id=cart_id,
            core_element_tablename="cart",
            core_element_name="Cart",
            core_columns="*",
        )
        return sql_to_domain(cat, Cart)

    async def update(
        self,
        cart_id: UUID,
        active: Optional[bool] = None,
        closed_at: Optional[datetime] = None,
    ) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": cart_id}

        if isinstance(active, bool):
            core_atributes.append(" active=:active")
            core_values_view["active"] = active
        if closed_at:
            core_atributes.append(" closed_at=:closed_at")
            core_values_view["closed_at"] = closed_at

        if len(core_atributes) == 0:
            raise GQLApiException(
                msg="Issues no data to update in sql",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )

        branch_query = f"""UPDATE cart
                            SET {','.join(core_atributes)}
                            WHERE id=:id;
                """
        await super().update(
            core_element_name="Cart",
            core_query=branch_query,
            core_values=core_values_view,
        )
        return True

    async def exist(
        self,
        cart_id: UUID,
    ) -> NoneType:
        """Validate cart exists

        Args:
            cart_id (UUID): unique cart id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=cart_id,
            core_columns="id",
            core_element_tablename="cart",
            id_key="id",
            core_element_name="Cart",
        )


class CartProductRepository(CoreRepository, CartProductRepositoryInterface):
    async def new(
        self,
        cart_product: CartProduct,
    ) -> bool:
        """Create New CartProduct

        Args:
            cart_product (CartProduct): Cart Product object

        Returns:
            bool: validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(cart_product, skip=["created_at", "last_updated"])
        core_vals["sell_unit"] = core_vals["sell_unit"].value
        # call super method from new
        await super().new(
            core_element_tablename="cart_product",
            core_element_name="Cart Product",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO cart_product
                (cart_id,
                supplier_product_id,
                supplier_product_price_id,
                quantity,
                unit_price,
                subtotal,
                comments,
                sell_unit,
                created_by
                )
                    VALUES
                    (:cart_id,
                    :supplier_product_id,
                    :supplier_product_price_id,
                    :quantity,
                    :unit_price,
                    :subtotal,
                    :comments,
                    :sell_unit,
                    :created_by)
                    """,
            core_values=core_vals,
        )
        return True

    async def search(self, cart_id: Optional[UUID] = None) -> List[CartProduct]:
        cart_atributes = []
        cart_values_view = {}
        if cart_id:
            cart_atributes.append(" cart_id=:cart_id and")
            cart_values_view["cart_id"] = cart_id

        if len(cart_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(cart_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        products = await super().search(
            core_element_name="Cart Product",
            core_element_tablename="cart_product",
            filter_values=filter_values,
            core_columns="*",
            values=cart_values_view,
        )

        return [CartProduct(**sql_to_domain(r, CartProduct)) for r in products]

    async def find(self, cart_id: Optional[UUID] = None) -> List[CartProduct]:
        cart_atributes = []
        cart_values_view = {}
        if cart_id:
            cart_atributes.append(" cart_id=:cart_id and")
            cart_values_view["cart_id"] = cart_id

        if len(cart_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(cart_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        products = await super().find(
            core_element_name="Cart Product",
            core_element_tablename="cart_product",
            filter_values=filter_values,
            core_columns="*",
            values=cart_values_view,
        )
        if not products:
            return []
        return [CartProduct(**sql_to_domain(r, CartProduct)) for r in products]

    async def find_many(
        self,
        cols: List[str],
        filter_values: List[Dict[str, str]],
        tablename: str = "cart_product",
        filter_type: str = "AND",
    ) -> List[Dict[Any, Any]]:
        """Search Supplier Products by multiple filter values

        Parameters
        ----------
        cols : List[str]
        filter_values : List[Dict[str, Any]]
        tablename : str, optional (default: "supplier_product")

        Returns
        -------
        List[Dict[str, Any]]
        """
        # format query
        qry = tablename
        if filter_values:
            _filt = " WHERE "
            for filter_value in filter_values:
                if len(_filt) > 7:  # 7 is len(" WHERE ")
                    _filt += f" {filter_type} "
                _filt += f"{filter_value['column']} {filter_value['operator']} {filter_value['value']}"
            qry += _filt
        prods = await super().find(
            core_element_name="Supplier Product",
            core_element_tablename=qry,
            core_columns=cols,
            values={},
        )
        if not prods:
            return []
        return [dict(r) for r in prods]

    async def search_with_tax(self, cart_id: Optional[UUID] = None) -> Sequence:
        cart_atributes = []
        cart_values_view = {}
        if cart_id:
            cart_atributes.append(" cart_id=:cart_id and")
            cart_values_view["cart_id"] = cart_id

        if len(cart_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(cart_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await super().search(
            core_element_name="Cart",
            core_element_tablename="""
                cart_product cp
                    JOIN supplier_product sp ON cp.supplier_product_id = sp.id""",
            filter_values=filter_values,
            core_columns=[
                "cp.*",
                "row_to_json(sp.*) AS tax_json",
            ],
            values=cart_values_view,
        )

        return _resp

    async def find_with_tax(
        self, cart_id: Optional[UUID] = None
    ) -> List[Dict[Any, Any]]:
        cart_atributes = []
        cart_values_view = {}
        if cart_id:
            cart_atributes.append(" cart_id=:cart_id and")
            cart_values_view["cart_id"] = cart_id

        if len(cart_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(cart_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await super().find(
            core_element_name="Cart",
            core_element_tablename="""
                cart_product cp
                    JOIN supplier_product sp ON cp.supplier_product_id = sp.id""",
            filter_values=filter_values,
            core_columns=[
                "cp.*",
                "row_to_json(sp.*) AS tax_json",
            ],
            values=cart_values_view,
        )
        if not _resp:
            return []
        return [dict(r) for r in _resp]
