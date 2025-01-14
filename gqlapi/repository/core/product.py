from datetime import datetime
import logging
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.catalog.product import ProductRepositoryInterface
from gqlapi.domain.interfaces.v2.catalog.product_family import ProductFamilyRepositoryInterface
from gqlapi.domain.models.v2.core import Product, ProductFamily
from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain


class ProductRepository(CoreRepository, ProductRepositoryInterface):
    async def new(
        self, product: Product, validate_by: str, validate_against: Any
    ) -> UUID:
        """Create New Product

        Args:
            product (Product): Product object

        Returns:
            UUID: unique Product id
        """
        # cast to dict
        core_vals = domain_to_dict(product, skip=["created_at", "last_updated"])
        core_vals["sell_unit"] = core_vals["sell_unit"].value
        core_vals["buy_unit"] = core_vals["buy_unit"].value
        # call super method from new
        await super().new(
            core_element_tablename="product",
            core_element_name="Product",
            validate_by=validate_by,
            validate_against=validate_against,
            core_query="""INSERT INTO product
                (id,
                product_family_id,
                sku,
                upc,
                name,
                description,
                keywords,
                sell_unit,
                conversion_factor,
                buy_unit,
                estimated_weight,
                created_by
                )
                    VALUES
                    (:id,
                    :product_family_id,
                    :sku,
                    :upc,
                    :name,
                    :description,
                    :keywords,
                    :sell_unit,
                    :conversion_factor,
                    :buy_unit,
                    :estimated_weight,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        product_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Product

        Args:
            product_id (UUID): unique product id

        Returns:
            Product: Product Model Dict
        """
        product = await super().get(
            id=product_id,
            core_element_tablename="product",
            core_element_name="Product",
            core_columns="*",
        )
        return sql_to_domain(product, Product)

    async def fetch(
        self,
        product_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Product

        Args:
            product_id (UUID): unique product id

        Returns:
            Product: Product Model Dict
        """
        product = await super().fetch(
            id=product_id,
            core_element_tablename="product",
            core_element_name="Product",
            core_columns="*",
        )
        if not product:
            return {}
        return sql_to_domain(product, Product)

    async def update(
        self,
        product_id: UUID,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sku: Optional[int] = None,
        keywords: Optional[List[str]] = None,
        sell_unit: Optional[UOMType] = None,
        conversion_factor: Optional[float] = None,
        buy_unit: Optional[UOMType] = None,
        estimated_weight: Optional[float] = None,
        upc: Optional[str] = None,
        validate_by: Optional[str] = None,
        validate_agains: Optional[Any] = None,
    ) -> bool:
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": product_id}

        if name:
            core_atributes.append(" name=:name")
            core_values_view["name"] = name
        if buy_unit:
            core_atributes.append(" buy_unit=:buy_unit")
            core_values_view["buy_unit"] = buy_unit.value
        if product_family_id:
            core_atributes.append(" product_family_id:product_family_id")
            core_values_view["product_family_id"] = product_family_id
        if description:
            core_atributes.append(" description=:description")
            core_values_view["description"] = description
        if sku:
            core_atributes.append(" sku=:sku")
            core_values_view["sku"] = sku
        if keywords:
            core_atributes.append(" keywords=:keywords")
            core_values_view["keywords"] = keywords
        if sell_unit:
            core_atributes.append(" sell_unit=:sell_unit")
            core_values_view["sell_unit"] = sell_unit.value
        if conversion_factor:
            core_atributes.append(" conversion_factor=:conversion_factor")
            core_values_view["conversion_factor"] = conversion_factor
        if estimated_weight:
            core_atributes.append(" estimated_weight=:estimated_weight")
            core_values_view["estimated_weight"] = estimated_weight
        if upc:
            core_atributes.append(" upc=:upc")
            core_values_view["upc"] = upc

        if len(core_atributes) == 0:
            raise GQLApiException(
                msg="Issues no data to update in sql",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )

        core_atributes.append(" last_updated=:last_updated")
        core_values_view["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE product
                            SET {','.join(core_atributes)}
                            WHERE id=:id;
                """

        await super().update(
            core_element_name="Product",
            core_query=branch_query,
            core_values=core_values_view,
            validate_by=validate_by,
            validate_against=validate_agains,
            core_element_tablename="product",
        )
        return True

    async def exist(
        self,
        product_id: Optional[UUID] = None,
        upc: Optional[str] = None,
        sku: Optional[int] = None,
    ) -> NoneType:
        """Validate category exists

        Args:
            supplier_product_id (UUID): unique supplier product id

        Returns:
            NoneType: None
        """
        id = "id"
        id_key = "id"

        if product_id:
            id = product_id
            id_key = "id"
        if upc:
            id = upc
            id_key = "upc"
        if sku:
            id = sku
            id_key = "sku"

        await super().exist(
            id=id,
            core_columns="id",
            core_element_tablename="product",
            id_key=id_key,
            core_element_name="Product",
        )

    async def get_products(
        self,
        product_id: Optional[UUID] = None,
        name: Optional[str] = None,
        search: Optional[str] = None,
        product_family_id: Optional[UUID] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        current_page: int = 1,
        page_size: int = 200,
    ) -> List[Product]:
        product_atributes = []
        product_values_view = {}
        if search:
            product_atributes.append(
                " exists (select 1 from unnest(keywords) keys where keys ILIKE :search ) and"
            )
            product_values_view["search"] = (
                "%" + "".join(filter(str.isalnum, search.lower())) + "%"
            )
        if name:
            product_atributes.append(" name=:name and")
            product_values_view["name"] = name
        if upc:
            product_atributes.append(" upc=:upc and")
            product_values_view["upc"] = upc
        if sku:
            product_atributes.append(" sku=:sku and")
            product_values_view["sku"] = sku

        if product_id:
            product_values_view["product_id"] = product_id
            product_atributes.append(" id= :product_id and")
        if product_family_id:
            product_values_view["product_family_id"] = product_family_id
            product_atributes.append(" product_family_id=:product_family_id and")

        if len(product_atributes) == 0:
            filter_values = ""
        else:
            filter_values = " ".join(product_atributes).split()
            filter_values = " ".join(filter_values[:-1])
        # adds offset & limit
        _offset = (current_page - 1) * page_size
        _limit = page_size
        filter_values = filter_values + f" OFFSET {_offset} LIMIT {_limit}"

        _resp = await super().find(
            core_element_name="Product",
            core_element_tablename="""product""",
            filter_values=filter_values,
            core_columns=["*"],
            values=product_values_view,
        )
        product_dir = []
        for r in _resp:
            prodc = Product(**sql_to_domain(r, Product))
            product_dir.append(prodc)
        return product_dir

    async def find(self, name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find products, if name is not None, return all products

        Args:
            name (str): product name, optionsl

        Returns:
            List[Dict[str, Any]]: List of products
        """
        filter_str = ""
        query_vals = {}
        if name:
            filter_str = " name=:name or description=:name"
            query_vals["name"] = name
        _resp = await super().find(
            core_element_name="Product",
            core_element_tablename="product",
            filter_values=filter_str,
            core_columns=["*"],
            values=query_vals,
        )
        if not _resp:
            return []
        # format
        res_list = []
        for r in _resp:
            p = dict(r)
            p["buy_unit"] = UOMType(p["buy_unit"])
            p["sell_unit"] = UOMType(p["sell_unit"])
            res_list.append(p)
        return res_list


class ProductFamilyRepository(CoreRepository, ProductFamilyRepositoryInterface):
    async def new(
        self,
        product_family: ProductFamily,
    ) -> UUID:
        """Create New ProductFamily

        Args:
            product_family (ProductFamily): ProductFamily object

        Returns:
            UUID: unique ProductFamily id
        """
        # cast to dict
        core_vals = domain_to_dict(product_family, skip=["created_at", "last_updated"])
        # call super method from new
        core_vals["buy_unit"] = core_vals["buy_unit"].value

        await super().new(
            core_element_tablename="product_family",
            core_element_name="Product Family",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO product_family
                (id,
                name,
                buy_unit,
                created_by
                )
                    VALUES
                    (:id,
                    :name,
                    :buy_unit,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    async def get(
        self,
        product_family_id: UUID,
    ) -> Dict[Any, Any]:
        """Get ProductFamily

        Args:
            product_family_id (UUID): unique ProductFamily id

        Returns:
            Dict: ProductFamily Model
        """
        prod_fam = await super().get(
            id=product_family_id,
            core_element_tablename="product_family",
            core_element_name="ProductFamily",
            core_columns="*",
        )
        return sql_to_domain(prod_fam, ProductFamily)

    async def update(
        self,
        product_family_id: UUID,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
    ) -> bool:
        """Update Product Family

        Args:
            product_family_id (UUID): unique ProductFamily id
            name (str): ProductFamily name
            buy_unit (OYMType): unit tipe to buy product

        Returns:
            bool: Validate update id done
        """
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": product_family_id}

        if name:
            core_atributes.append(" name=:name")
            core_values_view["name"] = name
        if buy_unit:
            core_atributes.append(" buy_unit=:buy_unit")
            core_values_view["buy_unit"] = buy_unit.value

        if len(core_atributes) == 0:
            raise GQLApiException(
                msg="Issues no data to update in sql",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )

        core_atributes.append(" last_updated=:last_updated")
        core_values_view["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE product_family
                            SET {','.join(core_atributes)}
                            WHERE id=:id;
                """
        await super().update(
            core_element_name="ProductFamily",
            core_query=branch_query,
            core_values=core_values_view,
        )
        return True

    async def exist(
        self,
        product_family_id: UUID,
    ) -> NoneType:
        """Validate ProductFamily exists

        Args:
            product_family_id (UUID): unique product_family_id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=product_family_id,
            core_columns="id",
            core_element_tablename="product_family",
            id_key="id",
            core_element_name="ProductFamily",
        )

    async def get_product_families(
        self,
        product_family_id: UUID,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
        search: Optional[str] = None,
    ) -> List[ProductFamily]:
        pf_atributes = []
        pf_values_view = {}
        if search:
            pf_atributes.append(
                " Lower(regexp_replace(name, '[^\\w]','','g')) ilike :search and"
            )
            pf_values_view["search"] = (
                "%" + "".join(filter(str.isalnum, search.lower())) + "%"
            )
        if name:
            pf_atributes.append(" name=:name and")
            pf_values_view["name"] = name
        if buy_unit:
            pf_atributes.append(" buy_unit=:buy_unit and")
            pf_values_view["buy_unit"] = buy_unit.value

        if product_family_id:
            pf_values_view["product_family_id"] = product_family_id
            pf_atributes.append(" id=:product_family_id and")

        if len(pf_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(pf_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await super().search(
            core_element_name="ProductFamily",
            core_element_tablename="""product_family""",
            filter_values=filter_values,
            core_columns=["*"],
            values=pf_values_view,
        )
        category_dir = []
        for r in _resp:
            rest_branch = ProductFamily(**sql_to_domain(r, ProductFamily))
            category_dir.append(rest_branch)
        return category_dir

    async def exists_relation_buy_name(self, name: str, buy_unit: UOMType) -> NoneType:
        """Validate relation exists

        Args:
            name (str): product family name
            buy_unit (UOMType): unit to buy product family

        Returns:
            NoneType: None
        """
        buy_name_values_view = {}
        buy_name_atributes = " name=:name and buy_unit =:buy_unit"
        buy_name_values_view["name"] = name
        buy_name_values_view["buy_unit"] = buy_unit.value
        _resp = await super().exists_relation(
            core_element_name="Product Family",
            core_element_tablename="product_family",
            filter_values=buy_name_atributes,
            core_columns=["id"],
            values=buy_name_values_view,
        )
        if _resp:
            logging.info(f"realation - {name} - {buy_unit.value} exists")

    async def find_mx_sat_product_codes(
        self,
        search: Optional[str] = None,
        current_page: int = 1,
        page_size: int = 200,
    ) -> List[Dict[str, Any]]:
        """Find Mx Sat codes with Family code

        Args:
            search (str): search string
            current_page (int): current page
            page_size (int): page size

        Returns:
            List[Dict[Any, Any]]: List of Mx Sat codes
        """
        # map query vars
        _search = (
            f"""AND (
                UPPER(sat_description) ILIKE UPPER('%{search}%')
                OR UPPER(sat_code) ILIKE UPPER('%{search}%'))"""
            if search is not None
            else ""
        )
        _offset = (current_page - 1) * page_size
        _limit = page_size
        # query
        qry = f"""
            SELECT id AS "id",
                    substring("sat_code", 1, 6) as "sat_code_family",
                    sat_code AS "sat_code",
                    sat_description AS "sat_description",
                    created_at AS "created_at"
            FROM mx_sat_product_code
            WHERE true
            {_search}
            ORDER BY 2 DESC
            OFFSET {_offset} LIMIT {_limit}
        """
        _resp = await super().raw_query(query=qry, vals={})
        return [dict(r) for r in _resp]
