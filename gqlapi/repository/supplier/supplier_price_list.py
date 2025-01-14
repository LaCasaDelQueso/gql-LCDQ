import json
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

from gqlapi.domain.interfaces.v2.supplier.supplier_price_list import (
    SupplierPriceListRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import SupplierPriceList
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict

DEFAULT_SP_PRICE_LIST_NAME: str = "Lista General de Precios"

logger = get_logger(get_app())


class SupplierPriceListRepository(CoreRepository, SupplierPriceListRepositoryInterface):
    def _serialize_supplier_price_list(
        self, supplier_price_list: SupplierPriceList
    ) -> Dict[str, Any]:
        # cast to dict
        vals_dict = domain_to_dict(
            supplier_price_list, skip=["created_at", "last_updated"]
        )
        # format data
        vals_dict["supplier_restaurant_relation_ids"] = json.dumps(
            [str(r) for r in vals_dict["supplier_restaurant_relation_ids"]]
        )
        vals_dict["supplier_product_price_ids"] = json.dumps(
            [str(p) for p in vals_dict["supplier_product_price_ids"]]
        )
        return vals_dict

    async def add(
        self,
        supplier_price_list: SupplierPriceList,
    ) -> UUID | NoneType:
        """Create a new SupplierPriceList

        Parameters
        ----------
        supplier_price_list : SupplierPriceList

        Returns
        -------
        UUID | NoneType
        """
        # cast to dict
        vals_dict = self._serialize_supplier_price_list(supplier_price_list)
        # call super method
        _id = await super().add(
            core_element_tablename="supplier_price_list",
            core_element_name="Supplier Price List",
            core_query="""
                INSERT INTO supplier_price_list (
                    id, supplier_unit_id, name,
                    supplier_restaurant_relation_ids,
                    supplier_product_price_ids,
                    is_default,
                    valid_from,
                    valid_upto,
                    created_by
                ) VALUES (
                    :id, :supplier_unit_id, :name,
                    :supplier_restaurant_relation_ids,
                    :supplier_product_price_ids,
                    :is_default,
                    :valid_from,
                    :valid_upto,
                    :created_by
                )
                """,
            core_values=vals_dict,
        )
        if not _id:
            return None
        return supplier_price_list.id

    async def exists(
        self,
        supplier_price_list_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_default: Optional[bool] = None,
    ) -> bool:
        """Verify if supplier price list exists

        Parameters
        ----------
        supplier_price_list_id : UUID
        supplier_unit_id : Optional[UUID], optional
        name : Optional[str], optional
        is_default : Optional[bool], optional

        Returns
        -------
        bool
        """
        values = {}
        filters_str = ""
        if supplier_price_list_id:
            values["id"] = supplier_price_list_id
            filters_str = "id = :id"
        if supplier_unit_id:
            values["supplier_unit_id"] = supplier_unit_id
            if filters_str != "":
                filters_str += " AND "
            filters_str = "supplier_unit_id = :supplier_unit_id"
        if name:
            values["name"] = name
            if filters_str != "":
                filters_str += " AND "
            filters_str = "name = :name"
        if is_default is not None:
            values["is_default"] = is_default
            if filters_str != "":
                filters_str += " AND "
            filters_str = "is_default = :is_default"

        if len(values) == 0:
            raise GQLApiException(
                msg="You must provide either supplier_price_list_id or supplier_unit_id",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # call super method
        res = await super().find(
            core_element_name="Supplier Price List",
            core_element_tablename="supplier_price_list",
            core_columns=["id", "is_default"],
            filter_values=filters_str,
            values=values,
        )
        if not res:
            return False
        return True

    async def fetch_price_list_to_export(
        self, supplier_product_price_list_id: UUID, supplier_business_id: UUID
    ) -> List[Dict[str, Any]]:
        # build query filters
        values: Dict[str, Any] = {}
        filters_str = " TRUE ORDER BY 1 "
        # query
        _prods_price_list = await super().find(
            core_element_name="Supplier Product Price List",
            partition=f"""WITH last_price_list AS (
                WITH rcos AS (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY id
                            ORDER BY last_updated DESC
                        ) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
                AND id = '{supplier_product_price_list_id}'
            ),
            -- Expanded prices from Last Price Lists
                expanded_prices_pls AS (
                    SELECT
                        supplier_unit_id, name,
                        json_array_elements(supplier_product_price_ids) as supplier_price_id,
                        valid_upto
                    FROM last_price_list
            ),
            -- Expanded and cleaned prces from Last Price Lists
                expanded_cleaned_prices_pls AS (
                    SELECT
                        supplier_unit_id, name,
                        REPLACE(supplier_price_id::varchar, '"', '')::UUID as supplier_price_id,
                        valid_upto
                    FROM expanded_prices_pls
            ),
            -- Price Lists Price
                pls_prices AS (
                    SELECT
                        ecpp.name price_list_name,
                        ecpp.supplier_price_id,
                        spp.supplier_product_id,
                        spp.price
                    FROM expanded_cleaned_prices_pls ecpp
                    JOIN supplier_product_price spp ON spp.id = ecpp.supplier_price_id
                    WHERE true
            ),
            -- Suppliers' product catalog
                supplier_catalog as (
                    SELECT
                        sp.id as supplier_product_id,
                        sp.sku,
                        sp.description,
                        (
                            CASE WHEN sp.sell_unit = 'kg' THEN 'Kg'
                            WHEN sp.sell_unit = 'unit' THEN 'Pieza'
                            WHEN sp.sell_unit = 'liter' THEN 'Litro'
                            WHEN sp.sell_unit = 'dozens' then 'Docena'
                            WHEN sp.sell_unit = 'pack' THEN 'Paquete'
                            ELSE sp.sell_unit
                            END
                        ) as sell_unit
                    FROM supplier_product sp
                    WHERE sp.supplier_business_id = '{supplier_business_id}'
            ), category_tag as (
                select
                    supplier_product_id,
                    string_agg(tag_value, ', ') as category
                FROM supplier_product_tag
                WHERE tag_key = 'category'
                GROUP BY 1
            ), catalog_download as (
                SELECT
                    sp.id,
                    sp.sku,
                    '' as upc_barcode,
                    sp.description,
                    (
                        case when sp.sell_unit = 'unit' then 'Pieza'
                        when sp.sell_unit = 'kg' then 'Kg'
                        when sp.sell_unit = 'liter' then 'Litro'
                        when sp.sell_unit = 'dozens' then 'Docena'
                        when sp.sell_unit = 'pack' then 'Paquete'
                        else sp.sell_unit end
                    ) as sell_unit,
                    sp.conversion_factor,
                    (
                        case when sp.buy_unit = 'unit' then 'Pieza'
                        when sp.buy_unit = 'kg' then 'Kg'
                        when sp.buy_unit = 'liter' then 'Litro'
                        when sp.buy_unit = 'dozens' then 'Docena'
                        when sp.buy_unit = 'pack' then 'Paquete'
                        else sp.buy_unit end
                    ) as buy_unit,
                    sp.unit_multiple,
                    sp.min_quantity,
                    sp.estimated_weight,
                    sp.tax_id as sat_product_code,
                    sp.tax as tax_iva_percent
                    -- '' as product_price,
                    -- (case when ct.category is null then '' else 'category' end) as tag_key,
                    -- ct.category as tag_value
                FROM supplier_product sp
                LEFT JOIN category_tag ct ON ct.supplier_product_id = sp.id
                WHERE sp.supplier_business_id =  '{supplier_business_id}'
                ORDER BY 3
            )""",
            core_element_tablename="""
                catalog_download scat
                JOIN pls_prices pls ON pls.supplier_product_id = scat.id
            """,
            core_columns=[
                "scat.*",
                "'' as max_daily_stock",
                "pls.price as product_price",
            ],
            filter_values=filters_str,
            values=values,
        )
        spll = []
        if _prods_price_list:
            for _prod_price_list in _prods_price_list:
                _prod_price_list_dict = dict(_prod_price_list)
                if "id" in _prod_price_list_dict:
                    del _prod_price_list_dict["id"]
                spll.append(_prod_price_list_dict)
            return spll
        else:
            return []

    async def fetch_all_price_list_to_export(
        self, supplier_business_id: UUID
    ) -> List[Dict[str, Any]]:
        # build query filters
        values: Dict[str, Any] = {}
        filters_str = " TRUE ORDER BY 1 "
        # query
        _prods_price_list = await super().find(
            core_element_name="Supplier Product Price List",
            partition=f"""WITH last_price_list AS (
                WITH rcos AS (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY name, supplier_unit_id
                            ORDER BY last_updated DESC
                        ) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
                AND supplier_unit_id IN (
                    SELECT id FROM supplier_unit WHERE supplier_business_id = '{supplier_business_id}'
                )
            ),
            -- get supplier Unit
                units_pls AS (
                    SELECT
                        id, unit_name
                    FROM supplier_unit WHERE supplier_business_id = '{supplier_business_id}'
                    AND deleted = 'f'
            ),
            -- Expanded prices from Last Price Lists
                expanded_prices_pls AS (
                    SELECT
                        supplier_unit_id, name,
                        json_array_elements(supplier_product_price_ids) as supplier_price_id,
                        valid_upto
                    FROM last_price_list
            ),
            -- Expanded and cleaned prces from Last Price Lists
                expanded_cleaned_prices_pls AS (
                    SELECT
                        supplier_unit_id, name,
                        REPLACE(supplier_price_id::varchar, '"', '')::UUID as supplier_price_id,
                        valid_upto
                    FROM expanded_prices_pls
            ),
            -- Price Lists Price
                pls_prices AS (
                    SELECT
                        ecpp.name price_list_name,
                        ecpp.supplier_price_id,
                        spp.supplier_product_id,
                        spp.price,
                        ecpp.supplier_unit_id
                    FROM expanded_cleaned_prices_pls ecpp
                    JOIN supplier_product_price spp ON spp.id = ecpp.supplier_price_id
                    WHERE true
            ),
            -- Suppliers' product catalog
                supplier_catalog as (
                    SELECT
                        sp.id as supplier_product_id,
                        sp.sku,
                        sp.description,
                        (
                            CASE WHEN sp.sell_unit = 'kg' THEN 'Kg'
                            WHEN sp.sell_unit = 'unit' THEN 'Pieza'
                            WHEN sp.sell_unit = 'liter' THEN 'Litro'
                            WHEN sp.sell_unit = 'dozens' THEN 'Docena'
                            WHEN sp.sell_unit = 'pack' THEN 'Paquete'
                            ELSE sp.sell_unit
                            END
                        ) as sell_unit
                    FROM supplier_product sp
                    WHERE sp.supplier_business_id = '{supplier_business_id}'
            )
            """,
            core_element_tablename="""
                supplier_catalog scat
                LEFT JOIN pls_prices pls ON pls.supplier_product_id = scat.supplier_product_id
                LEFT JOIN units_pls up ON up.id = pls.supplier_unit_id
            """,
            core_columns=[
                """(
                    -- scat.sku || ' | ' ||
                    scat.description || ' | ' ||
                    scat.sell_unit
                ) as product""",
                "COALESCE(pls.price_list_name, 'Sin Precio') price_list_name",
                "pls.price",
                "up.unit_name",
            ],
            filter_values=filters_str,
            values=values,
        )
        if _prods_price_list:
            return [dict(_prod_price_list) for _prod_price_list in _prods_price_list]
        else:
            return []

    async def delete (
        self,
        supplier_price_list_name: str,
        supplier_business_id: UUID
    ) -> bool | NoneType:
        """Delete SupplierPriceList

        Parameters
        ----------
        supplier_price_list_name: str
        supplier_business_id : UUID

        Returns
        -------
        UUID | NoneType
        """
        # call super method
        await super().execute(
            core_element_name = "supplier_price_list",
            query="""
                DELETE FROM supplier_price_list
                WHERE name = :name AND supplier_unit_id IN (
                    SELECT id FROM supplier_unit WHERE supplier_business_id = :supplier_business_id
                )
                """,
            values={
                    "name": supplier_price_list_name,
                    "supplier_business_id": supplier_business_id},
        )
        return True