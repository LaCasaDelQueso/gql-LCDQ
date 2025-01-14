from datetime import datetime
import logging
from types import NoneType
from typing import Any, Dict, List, Optional, Type
from uuid import UUID
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductPriceRepositoryInterface,
    SupplierProductRepositoryInterface,
    SupplierProductStockRepositoryInterface,
    SupplierProductStockWithAvailability,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierProduct,
    SupplierProductPrice,
    SupplierProductStock,
    SupplierProductTag,
)
from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple


class SupplierProductRepository(CoreRepository, SupplierProductRepositoryInterface):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        supplier_product: SupplierProduct,
    ) -> UUID:
        """Create New Supplier Product

        Args:
            supplier_product (SupplierProduct): SupplierProduct object

        Returns:
            UUID: unique Product id
        """
        # cast to dict
        core_vals = domain_to_dict(
            supplier_product, skip=["created_at", "last_updated"]
        )
        # call super method from new
        core_vals["sell_unit"] = core_vals["sell_unit"].value
        core_vals["buy_unit"] = core_vals["buy_unit"].value
        await super().new(
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO supplier_product
                (id,
                product_id,
                supplier_business_id,
                sku,
                upc,
                description,
                tax_id,
                sell_unit,
                tax_unit,
                tax,
                conversion_factor,
                buy_unit,
                unit_multiple,
                min_quantity,
                estimated_weight,
                is_active,
                created_by
                )
                    VALUES
                    (:id,
                    :product_id,
                    :supplier_business_id,
                    :sku,
                    :upc,
                    :description,
                    :tax_id,
                    :sell_unit,
                    :tax_unit,
                    :tax,
                    :conversion_factor,
                    :buy_unit,
                    :unit_multiple,
                    :min_quantity,
                    :estimated_weight,
                    :is_active,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        supplier_product_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Category

        Args:
            category_id (UUID): unique category id

        Returns:
            Category: Category Model
        """
        supp_product = await super().get(
            id=supplier_product_id,
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            core_columns="*",
        )
        return sql_to_domain(supp_product, SupplierProduct)

    async def fetch(
        self,
        supplier_product_id: UUID,
    ) -> Dict[Any, Any]:
        """Fetch Supplier Product

        Args:
            supplier_product_id (UUID): supplier product id

        Returns:
            Supplier Product Model dict
        """
        supp_product = await super().fetch(
            id=supplier_product_id,
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            core_columns="*",
        )
        if supp_product:
            return sql_to_domain(supp_product, SupplierProduct)
        return {}

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        id: UUID,
        product_id: Optional[UUID] = None,  # (optional)
        supplier_business_id: Optional[UUID] = None,  # (optional)
        sku: Optional[str] = None,  # (optional)
        upc: Optional[str] = None,  # (optional)
        description: Optional[str] = None,  # (optional)
        tax_id: Optional[str] = None,  # (optional)
        sell_unit: Optional[UOMType] = None,  # (optional)
        tax_unit: Optional[str] = None,  # (optional)
        tax: Optional[float] = None,  # (optional)
        conversion_factor: Optional[float] = None,  # (optional)
        buy_unit: Optional[UOMType] = None,  # (optional)
        unit_multiple: Optional[float] = None,  # (optional)
        min_quantity: Optional[float] = None,  # (optional)
        estimated_weight: Optional[float] = None,  # (optional)
        is_active: Optional[bool] = None,  # (optional)
    ) -> bool:  # noqa: E501
        """Update Supplier Product

        Parameters
        ----------
        id : UUID
            Supplier Product Id
        product_id : Optional[UUID], optional
            Product Id, by default None

        Returns
        -------
        bool
        """
        # cast to dict
        core_vals: Dict[str, Any] = {"id": id}
        upd_fields = ""
        for key in SupplierProduct.__annotations__.keys():
            if key in ["id", "created_at", "last_updated", "created_by"]:
                continue
            _val = locals()[key]  # get value from local variables in scope
            if _val is not None:
                core_vals[key] = _val
                if upd_fields:
                    upd_fields += ", "
                upd_fields += f"{key} = :{key}"
        # nothing to update return
        if len(core_vals) == 1:
            logging.warning("Nothing to update in Supplier Product")
            return False
        # call super method from new
        if "sell_unit" in core_vals:
            core_vals["sell_unit"] = core_vals["sell_unit"].value
        if "buy_unit" in core_vals:
            core_vals["buy_unit"] = core_vals["buy_unit"].value
        # update
        await super().update(
            core_element_name="Supplier Product",
            core_query=f"""
                UPDATE supplier_product SET
                {upd_fields}
                WHERE id = :id
            """,
            core_values=core_vals,
            core_element_tablename="supplier_product",
        )
        return True

    async def edit(
        self,
        supplier_product: SupplierProduct,
    ) -> bool:
        """UPdate Supplier Product

        Args:
            supplier_product (SupplierProduct): SupplierProduct object

        Returns:
            UUID: unique Product id
        """
        # cast to dict
        core_vals = domain_to_dict(
            supplier_product, skip=["created_at", "last_updated", "created_by"]
        )
        core_vals["sell_unit"] = core_vals["sell_unit"].value
        core_vals["buy_unit"] = core_vals["buy_unit"].value
        core_vals["last_updated"] = datetime.utcnow()
        # super method on edit
        return await super().edit(
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            core_query="""
                UPDATE supplier_product
                SET
                    product_id = :product_id,
                    supplier_business_id = :supplier_business_id,
                    sku = :sku,
                    upc = :upc,
                    description = :description,
                    tax_id = :tax_id,
                    sell_unit = :sell_unit,
                    tax_unit = :tax_unit,
                    tax = :tax,
                    conversion_factor = :conversion_factor,
                    buy_unit = :buy_unit,
                    unit_multiple = :unit_multiple,
                    min_quantity = :min_quantity,
                    estimated_weight = :estimated_weight,
                    is_active = :is_active,
                    last_updated = :last_updated,
                    long_description = :long_description,
                    mx_ieps= :mx_ieps
                WHERE id = :id
            """,
            core_values=core_vals,
        )

    async def exist(
        self,
        supplier_product_id: UUID,
    ) -> NoneType:
        """Validate category exists

        Args:
            supplier_product_id (UUID): unique supplier product id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=supplier_product_id,
            core_columns="id",
            core_element_tablename="supplier_product",
            id_key="id",
            core_element_name="Supplier Product",
        )

    async def validate(
        self,
        supplier_product_id: UUID,
    ) -> bool:
        """Validate category exists

        Args:
            supplier_product_id (UUID): unique supplier product id

        Returns:
            NoneType: None
        """
        return await super().exists(
            id=supplier_product_id,
            core_columns="id",
            core_element_tablename="supplier_product",
            id_key="id",
            core_element_name="Supplier Product",
        )

    async def add(
        self,
        supplier_product: SupplierProduct,
    ) -> UUID:
        """Create New Supplier Product

        Args:
            supplier_product (SupplierProduct): SupplierProduct object

        Returns:
            UUID: unique Product id
        """
        # cast to dict
        core_vals = domain_to_dict(
            supplier_product, skip=["created_at", "last_updated"]
        )
        # call super method from new
        core_vals["sell_unit"] = core_vals["sell_unit"].value
        core_vals["buy_unit"] = core_vals["buy_unit"].value
        await super().add(
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO supplier_product
                (id,
                product_id,
                supplier_business_id,
                sku,
                upc,
                description,
                tax_id,
                sell_unit,
                tax_unit,
                tax,
                conversion_factor,
                buy_unit,
                unit_multiple,
                min_quantity,
                estimated_weight,
                long_description,
                is_active,
                created_by,
                mx_ieps
                )
                    VALUES
                    (:id,
                    :product_id,
                    :supplier_business_id,
                    :sku,
                    :upc,
                    :description,
                    :tax_id,
                    :sell_unit,
                    :tax_unit,
                    :tax,
                    :conversion_factor,
                    :buy_unit,
                    :unit_multiple,
                    :min_quantity,
                    :estimated_weight,
                    :long_description,
                    :is_active,
                    :created_by,
                    :mx_ieps)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    @deprecated("Use find() instead", "gqlapi.repository")
    async def search(
        self,
        supplier_business_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        description: Optional[str] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> List[SupplierProduct]:
        """Search Supplier Products

        Parameters
        ----------
        supplier_business_id : Optional[UUID], optional
            Supplier Business Id, by default None
        product_id : Optional[UUID], optional
            Product Id, by default None

        Returns
        -------
        List[SupplierProduct]
        """
        filter_values = ""
        sp_values = {}
        if supplier_business_id:
            filter_values += " supplier_business_id = :supplier_business_id"
            sp_values["supplier_business_id"] = supplier_business_id
        if product_id:
            if filter_values:
                filter_values += " AND"
            filter_values += " product_id = :product_id"
            sp_values["product_id"] = product_id
        if description:
            if filter_values:
                filter_values += " AND"
            filter_values += " description= :description"
            sp_values["description"] = description
        if sku:
            if filter_values:
                filter_values += " AND"
            filter_values += " sku= :sku"
            sp_values["sku"] = sku
        if upc:
            if filter_values:
                filter_values += " AND"
            filter_values += " upc= :upc"
            sp_values["upc"] = upc

        prods = await super().search(
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            core_columns="*",
            filter_values=filter_values,
            values=sp_values,
        )
        return [
            SupplierProduct(**sql_to_domain(prod, SupplierProduct)) for prod in prods
        ]

    async def find(
        self,
        supplier_business_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        supplier_product_id: Optional[UUID] = None,
        description: Optional[str] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search Supplier Products

        Parameters
        ----------
        supplier_business_id : Optional[UUID], optional
            Supplier Business Id, by default None
        product_id : Optional[UUID], optional
            Product Id, by default None

        Returns
        -------
        List[Dict[str, Any]]
        """
        filter_values = ""
        sp_values = {}
        if supplier_business_id:
            filter_values += " supplier_business_id = :supplier_business_id"
            sp_values["supplier_business_id"] = supplier_business_id
        if product_id:
            if filter_values:
                filter_values += " AND"
            filter_values += " product_id = :product_id"
            sp_values["product_id"] = product_id
        if supplier_product_id:
            if filter_values:
                filter_values += " AND"
            filter_values += " id = :supplier_product_id"
            sp_values["supplier_product_id"] = supplier_product_id
        if description:
            if filter_values:
                filter_values += " AND"
            filter_values += " description= :description"
            sp_values["description"] = description
        if sku:
            if filter_values:
                filter_values += " AND"
            filter_values += " sku= :sku"
            sp_values["sku"] = sku
        if upc:
            if filter_values:
                filter_values += " AND"
            filter_values += " upc= :upc"
            sp_values["upc"] = upc

        prods = await super().find(
            core_element_tablename="supplier_product",
            core_element_name="Supplier Product",
            core_columns="*",
            filter_values=filter_values,
            values=sp_values,
        )
        return [sql_to_domain(prod, SupplierProduct) for prod in prods]

    async def find_many(
        self,
        cols: List[str],
        filter_values: List[Dict[str, str]],
        tablename: str = "supplier_product",
        filter_type: str = "AND",
        cast_type: Type = SupplierProduct,
    ) -> List[Dict[str, Any]]:
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
        return [sql_to_domain(prod, cast_type) for prod in prods]

    async def raw_query(
        self, query: str, vals: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute raw query -> fetch_all

        Parameters
        ----------
        query : str
        vals : Dict[str, Any]

        Returns
        -------
        List[Dict[str, Any]]
            _description_

        Raises
        ------
        GQLApiException
        """
        try:
            res = await self.db.fetch_all(query=query, values=vals)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues executing raw query")
            raise GQLApiException(
                msg="Error executing raw query",
                error_code=GQLApiErrorCodeType.EXECUTE_SQL_DB_ERROR.value,
            )
        return res

    async def add_tags(
        self,
        supplier_product_id: UUID,
        tags: List[SupplierProductTag],
    ) -> bool:
        # verify which tags are already in the db
        db_tags = await self.fetch_tags(supplier_product_id=supplier_product_id)
        # if db tags delete them
        if db_tags:
            try:
                await self.db.execute_many(
                    query="""
                        DELETE FROM supplier_product_tag
                        WHERE id = :id
                    """,
                    values=[{"id": tag.id} for tag in db_tags],
                )
            except Exception as e:
                logging.warning("Error deleting supplier product tags")
                logging.error(e)
                return False
        # insert new tags
        try:
            if len(tags) == 0:
                return True
            await self.db.execute_many(
                query="""
                    INSERT INTO supplier_product_tag
                    (id, supplier_product_id, tag_key, tag_value)
                    VALUES
                    (:id, :supplier_product_id, :tag_key, :tag_value)
                """,
                values=[domain_to_dict(tag, skip=["created_at"]) for tag in tags],
            )
            return True
        except Exception as e:
            logging.warning("Error inserting supplier product tags")
            logging.error(e)
        return False

    def get_validation_tag(
        self, tag: SupplierProductTag, db_tags: List[SupplierProductTag]
    ) -> bool:
        for old_tag in db_tags:
            if tag.tag_key == old_tag.tag_key and tag.tag_value == old_tag.tag_value:
                return False
        return True

    def filter_tags(
        self, db_tags: List[SupplierProductTag], new_tags: List[SupplierProductTag]
    ):
        filter_tags: List[SupplierProductTag] = []
        old_tags_values = []
        old_tags_keys = []
        for tag in db_tags:
            old_tags_values.append(tag.tag_value)
            old_tags_keys.append(tag.tag_key)
        for tag in new_tags:
            if self.get_validation_tag(tag, db_tags):
                filter_tags.append(tag)

        return filter_tags

    async def add_file_tags(
        self,
        supplier_product_id: UUID,
        tags: List[SupplierProductTag],
    ) -> bool:
        # verify which tags are already in the db
        db_tags = await self.fetch_tags(supplier_product_id=supplier_product_id)
        # if db tags delete them
        if db_tags:
            filter_tags = self.filter_tags(db_tags, tags)
            if len(filter_tags) > 0:
                try:
                    await self.db.execute_many(
                        query="""
                            INSERT INTO supplier_product_tag
                            (id, supplier_product_id, tag_key, tag_value)
                            VALUES
                            (:id, :supplier_product_id, :tag_key, :tag_value)
                        """,
                        values=[
                            domain_to_dict(tag, skip=["created_at"])
                            for tag in filter_tags
                        ],
                    )
                except Exception as e:
                    logging.warning("Error deleting supplier product tags")
                    logging.error(e)
                    return False
            else:
                logging.warning("Nothing tag to update")
                return True
        else:
            # insert new tags
            try:
                if len(tags) == 0:
                    return True
                await self.db.execute_many(
                    query="""
                        INSERT INTO supplier_product_tag
                        (id, supplier_product_id, tag_key, tag_value)
                        VALUES
                        (:id, :supplier_product_id, :tag_key, :tag_value)
                    """,
                    values=[domain_to_dict(tag, skip=["created_at"]) for tag in tags],
                )
                return True
            except Exception as e:
                logging.warning("Error inserting supplier product tags")
                logging.error(e)
                return False
        return True

    async def fetch_tags(
        self,
        supplier_product_id: UUID,
    ) -> List[SupplierProductTag]:
        """Fetch Supplier Product Tags

        Args:
            supplier_product_id (UUID): supplier product id

        Returns:
            List[SupplierProductTag]: list of SupplierProductTag objects
        """
        db_tags = await self.find_many(
            cols=["id", "supplier_product_id", "tag_key", "tag_value", "created_at"],
            filter_values=[
                {
                    "column": "supplier_product_id",
                    "operator": "=",
                    "value": f"'{str(supplier_product_id)}'",
                }
            ],
            tablename="supplier_product_tag",
            cast_type=SupplierProductTag,
        )
        if not db_tags:
            return []
        return [
            SupplierProductTag(**sql_to_domain(tag, SupplierProductTag))
            for tag in db_tags
        ]

    async def fetch_tags_from_many(
        self,
        supplier_product_ids: List[UUID],
    ) -> List[SupplierProductTag]:
        """Fetch Supplier Product Tags

        Args:
            supplier_product_ids (List[UUID]): supplier product ids

        Returns:
            List[SupplierProductTag]: list of SupplierProductTag objects
        """
        db_tags = await self.find_many(
            cols=["id", "supplier_product_id", "tag_key", "tag_value", "created_at"],
            filter_values=[
                {
                    "column": "supplier_product_id",
                    "operator": "in",
                    "value": list_into_strtuple(supplier_product_ids),
                }
            ],
            tablename="supplier_product_tag",
            cast_type=SupplierProductTag,
        )
        if not db_tags:
            return []
        return [
            SupplierProductTag(**sql_to_domain(tag, SupplierProductTag))
            for tag in db_tags
        ]

    async def fetch_products_to_export(
        self,
        supplier_business_id: UUID,
        receiver: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        """Get products by supplier business

        Parameters
        ----------
        supplier_business_id : UUID
        receiver : Optional[str]

        Returns
        -------
        List[Dict[str, Any]]
        """
        # build query filters
        filters = [" sp.supplier_business_id = :supplier_business_id "]
        values: Dict[str, Any] = {"supplier_business_id": supplier_business_id}
        if receiver:
            filters.append(
                """ (sp.sku ILIKE :receiver
                    OR sp.description ILIKE :receiver)
                """
            )
            values["receiver"] = "%" + receiver + "%"
        filters_str = " AND ".join(filters)
        filters_str += " ORDER BY 3 "
        # query
        _prods = await super().find(
            core_element_name="Products",
            partition="""with category_tag as (
                select
                    supplier_product_id,
                    string_agg(tag_value, ', ') as category
                FROM supplier_product_tag
                WHERE tag_key = 'category'
                GROUP BY 1
            )""",
            core_element_tablename="""
                supplier_product sp
                LEFT JOIN category_tag ct ON ct.supplier_product_id = sp.id
            """,
            core_columns=[
                "sp.sku",
                "'' as upc_barcode",
                "sp.description",
                """(
                    case when sp.sell_unit = 'unit' then 'Pieza'
                    when sp.sell_unit = 'kg' then 'Kg'
                    when sp.sell_unit = 'liter' then 'Litro'
                    when sp.sell_unit = 'dozens' then 'Docena'
                    when sp.sell_unit = 'pack' then 'Paquete'
                    else sp.sell_unit end
                ) as sell_unit""",
                "sp.conversion_factor",
                """(
                    case when sp.buy_unit = 'unit' then 'Pieza'
                    when sp.buy_unit = 'kg' then 'Kg'
                    when sp.buy_unit = 'liter' then 'Litro'
                    when sp.buy_unit = 'dozens' then 'Docena'
                    when sp.buy_unit = 'pack' then 'Paquete'
                    else sp.buy_unit end
                ) as buy_unit""",
                "sp.unit_multiple",
                "sp.min_quantity",
                "sp.estimated_weight",
                "sp.tax_id as sat_product_code",
                "sp.tax as tax_iva_percent",
                "'' as product_price",
                "'' as max_daily_stock",
                """(case when ct.category is null then '' else 'category' end) as tag_key,
                ct.category as tag_value""",
            ],
            filter_values=filters_str,
            values=values,
        )
        if _prods:
            return [dict(_prod) for _prod in _prods]
        else:
            return []


class SupplierProductPriceRepository(
    CoreRepository, SupplierProductPriceRepositoryInterface
):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID:
        """Create New Product Price

        Args:
            supp_prod_price (SupplierProductPrice): SupplierProductPrice object

        Returns:
            UUID: unique SupplierProductPrice id
        """
        # cast to dict
        core_vals = domain_to_dict(product_price, skip=["created_at"])
        # call super method from new
        core_vals["currency"] = core_vals["currency"].value
        core_vals["valid_from"] = core_vals["valid_from"].replace(tzinfo=None)
        core_vals["valid_upto"] = core_vals["valid_upto"].replace(tzinfo=None)

        await super().new(
            core_element_tablename="supplier_product_price",
            core_element_name="Supplier Product Price",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO supplier_product_price
                (id,
                supplier_product_id,
                price,
                currency,
                valid_from,
                valid_upto,
                created_by
                )
                    VALUES
                    (:id,
                    :supplier_product_id,
                    :price,
                    :currency,
                    :valid_from,
                    :valid_upto,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    async def add(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID | NoneType:
        """Create New Product Price

        Args:
            supp_prod_price (SupplierProductPrice): SupplierProductPrice object

        Returns:
            UUID | NoneType
                unique SupplierProductPrice id

        """
        # cast to dict
        core_vals = domain_to_dict(product_price, skip=["created_at"])
        # call super method from new
        core_vals["currency"] = core_vals["currency"].value
        core_vals["valid_from"] = core_vals["valid_from"].replace(tzinfo=None)
        core_vals["valid_upto"] = core_vals["valid_upto"].replace(tzinfo=None)

        _uuid = await super().add(
            core_element_tablename="supplier_product_price",
            core_element_name="Supplier Product Price",
            core_query="""INSERT INTO supplier_product_price
                (id,
                supplier_product_id,
                price,
                currency,
                valid_from,
                valid_upto,
                created_by
                )
                    VALUES
                    (:id,
                    :supplier_product_id,
                    :price,
                    :currency,
                    :valid_from,
                    :valid_upto,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"] if _uuid else None

    async def get(
        self,
        product_price: UUID,
    ) -> Dict[Any, Any]:
        """Get Supplier Product Price

        Args:
            product_price (UUID): unique supplier product price id

        Returns:
            Supplier Product Price Model dict
        """
        supp_product = await super().get(
            id=product_price,
            core_element_tablename="supplier_product_price",
            core_element_name="Supplier Product Price",
            core_columns="*",
        )
        return sql_to_domain(supp_product, SupplierProductPrice)

    async def update(
        self,
        product_price: SupplierProductPrice,
    ) -> UUID:
        """Update Supplier Product Price
            - For this case, it is a insert-only model

        Parameters
        ----------
        supplier_product_price : SupplierProductPrice
            Supplier Product Price Model

        Returns
        -------
        bool
        """
        return await self.new(
            product_price=product_price,
        )

    async def exist(
        self,
        supp_prod_price_id: UUID,
    ) -> NoneType:
        """Validate supplier product pricr id exists

        Args:
            supp_prod_price_i (UUID): unique supplier product price id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=supp_prod_price_id,
            core_columns="id",
            core_element_tablename="supplier_product_price",
            id_key="id",
            core_element_name="Supplier Product Price",
        )

    async def get_latest_active(
        self, supplier_product_id: UUID
    ) -> SupplierProductPrice | NoneType:
        """Get latest active price for a supplier product

        Parameters
        ----------
        supplier_product_id : UUID

        Returns
        -------
        SupplierProductPrice
        """
        supp_product = await super().find(
            core_element_tablename="supplier_product_price",
            core_element_name="Supplier Product Price",
            core_columns="*",
            filter_values="""
                supplier_product_id = :supplier_product_id
                AND valid_upto > :now
                ORDER BY valid_upto DESC LIMIT 1
            """,
            values={
                "now": datetime.utcnow(),
                "supplier_product_id": supplier_product_id,
            },
        )
        if supp_product:
            return SupplierProductPrice(
                **sql_to_domain(supp_product[0], SupplierProductPrice)
            )
        return None


class SupplierProductStockRepository(
    CoreRepository, SupplierProductStockRepositoryInterface
):
    async def add(
        self,
        supp_prod_stock: SupplierProductStock,
    ) -> UUID | NoneType:
        """Create New Product Stock

        Args:
            supp_prod_stock (SupplierProductStock): SupplierProductStock object

        Returns:
            UUID: unique SupplierProductStockid
        """
        # cast to dict
        core_vals = domain_to_dict(supp_prod_stock, skip=["created_at"])
        if await super().add(
            core_element_tablename="supplier_product_stock",
            core_element_name="Supplier Product Stock",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO supplier_product_stock
                (id,
                supplier_product_id,
                supplier_unit_id,
                stock,
                stock_unit,
                keep_selling_without_stock,
                created_by,
                active
                )
                    VALUES
                    (:id,
                    :supplier_product_id,
                    :supplier_unit_id,
                    :stock,
                    :stock_unit,
                    :keep_selling_without_stock,
                    :created_by,
                    :active)
                """,
            core_values=core_vals,
        ):
            return core_vals["id"]
        return None

    async def fetch_latest(
        self, supplier_product_id: UUID, supplier_unit_id: UUID
    ) -> SupplierProductStock | NoneType:
        """Get latest active stock for a supplier product

        Parameters
        ----------
        supplier_product_id : UUID

        Returns
        -------
        SupplierProductStock
        """
        supp_product_stock = await super().find(
            core_element_tablename="supplier_product_stock",
            core_element_name="Supplier Product Stock",
            core_columns="*",
            filter_values="""
                supplier_product_id = :supplier_product_id AND supplier_unit_id = :supplier_unit_id
                ORDER BY created_at DESC LIMIT 1
            """,
            values={
                "supplier_product_id": supplier_product_id,
                "supplier_unit_id": supplier_unit_id,
            },
        )
        if supp_product_stock:
            return SupplierProductStock(
                **sql_to_domain(supp_product_stock[0], SupplierProductStock)
            )
        return None

    async def fetch_latest_by_unit(
        self, supplier_unit_id: UUID
    ) -> List[SupplierProductStock]:
        """Get latest active stock for a supplier product

        Parameters
        ----------
        supplier_product_id : UUID

        Returns
        -------
        SupplierProductStock
        """
        supp_product_stock = await super().find(
            core_element_tablename=f"""(
                    SELECT *,
                        ROW_NUMBER() OVER (PARTITION BY supplier_product_id ORDER BY created_at DESC) AS rn
                    FROM supplier_product_stock
                    WHERE supplier_unit_id = '{str(supplier_unit_id)}'
                ) AS sub""",
            core_element_name="Supplier Product Stock",
            core_columns="*",
            values={},
            filter_values="rn = 1",
        )
        if supp_product_stock:
            supp_product_stock_list = []
            for stock in supp_product_stock:
                supp_product_stock_list.append(
                    SupplierProductStock(**sql_to_domain(stock, SupplierProductStock))
                )
            return supp_product_stock_list
        return []

    async def find_availability(
        self,
        supplier_unit_id: UUID,
        stock_products: List[SupplierProductStock],
    ) -> List[SupplierProductStockWithAvailability]:
        """Find availability of stock products

        Args:
            supplier_unit_id (UUID): _description_
            stock_products (List[SupplierProductStock]): _description_

        Returns:
            List[SupplierProductStockWithAvailability]
        """
        if len(stock_products) == 0:
            return []
        min_purchase_date = min(
            [stock.created_at for stock in stock_products if stock.created_at]
        )
        sup_prods = list_into_strtuple(
            [stock.supplier_product_id for stock in stock_products]
        )
        # query - fetch sold products since last inventory update
        sold_prods = await super().find(
            core_element_name="Product Stock Availability",
            partition="""
            WITH orden_details_view as (
                    WITH last_orden_status AS (
                        WITH rcos AS (
                            SELECT
                                orden_id,
                                status,
                                ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
                            FROM orden_status
                            WHERE created_at >= (NOW() - INTERVAL '2 months')
                    )
                        SELECT * FROM rcos WHERE row_num = 1
                    ),
                    last_orden_version AS (
                        WITH last_upd AS (
                            SELECT
                                orden_id,
                                id as orden_details_id,
                                ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
                            FROM orden_details
                            WHERE supplier_unit_id = :supplier_unit_id
                            AND created_at >= (NOW() - INTERVAL '2 months')
                        )
                        SELECT * FROM last_upd WHERE row_num = 1
                    )
                    SELECT
                        orden_details.*,
                        los.status
                    FROM last_orden_version lov
                    JOIN orden_details ON orden_details.id = lov.orden_details_id
                    JOIN last_orden_status los ON los.orden_id = lov.orden_id
            )
            """,
            core_element_tablename="""
                cart_product cp
                JOIN orden_details_view odv ON odv.cart_id = cp.cart_id
            """,
            core_columns=["cp.supplier_product_id", "cp.created_at", "cp.quantity"],
            filter_values=f"""
                odv.status <> 'canceled'
                AND odv.supplier_unit_id = :supplier_unit_id
                AND cp.supplier_product_id IN {sup_prods}
                AND cp.created_at >= :min_purchase_date
            """,
            values={
                "supplier_unit_id": supplier_unit_id,
                "min_purchase_date": min_purchase_date,
            },
        )
        # build availability
        sps_avail: List[SupplierProductStockWithAvailability] = []
        for sprod in stock_products:
            # compute sold qty given specific product stock update
            sold_qty = 0.0
            for sp in sold_prods:
                if (
                    sp["supplier_product_id"] == sprod.supplier_product_id
                    and sp["created_at"] >= sprod.created_at
                ):
                    sold_qty += float(sp["quantity"])
            # compute availability
            avail = sprod.stock - sold_qty
            sps_avail.append(
                SupplierProductStockWithAvailability(
                    **sprod.__dict__,
                    availability=round(avail, 3) if avail >= 0.0 else 0.0,
                )
            )
        return sps_avail
