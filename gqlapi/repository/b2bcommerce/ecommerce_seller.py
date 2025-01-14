from datetime import datetime
import logging
from types import NoneType
from typing import Any, Dict, List
from uuid import UUID, uuid4
from gqlapi.domain.models.v2.b2bcommerce import (
    EcommerceSeller,
    EcommerceUserRestaurantRelation,
)
from gqlapi.utils.domain_mapper import sql_to_domain
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    EcommerceSellerRepositoryInterface,
    EcommerceUserRestaurantRelationRepositoryInterface,
)
from gqlapi.repository import CoreRepository
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


class EcommerceSellerRepository(CoreRepository, EcommerceSellerRepositoryInterface):
    def __init__(self, info: StrawberryInfo) -> None:
        try:
            _db = info.context["db"].authos
        except Exception as e:
            logging.error(e)
            logging.warning("Issues connect Authos DB")
            raise GQLApiException(
                msg="Error creating connect Authos DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        self.db = _db

    async def fetch(
        self,
        id_key: str,
        id_value: UUID | str,
    ) -> EcommerceSeller | NoneType:
        """Fetch EcommerceSeller by
            - id (UUID)
            - supplier_business_id (UUID)
            - secret_key (str)

        Args:
            id_key (str): ID Key ({id, supplier_business_id, secret_key})
            id_value (UUID | str): ID Value

        Returns:
            EcommerceSeller | NoneType
                EcommerceSeller object
        """
        if id_key == "id" and not isinstance(id_value, UUID):
            logging.warning("Invalid id_value, id_key = 'id' -> id_value must be UUID")
            return None
        elif id_key == "supplier_business_id" and not isinstance(id_value, UUID):
            logging.warning(
                "Invalid id_value, id_key = 'supplier_business_id' -> id_value must be UUID"
            )
            return None
        elif id_key == "secret_key" and not isinstance(id_value, str):
            logging.warning(
                "Invalid id_value, id_key = 'secret_key' -> id_value must be str"
            )
            return None
        _rp = await super().fetch(
            core_element_name="Ecommerce Seller",
            core_element_tablename="ecommerce_seller",
            id_key=id_key,
            id=id_value,
            core_columns=["*"],
        )
        if not _rp:
            return None
        return EcommerceSeller(**sql_to_domain(_rp, EcommerceSeller))

    async def edit(
        self,
        ecommerce_seller: EcommerceSeller,
    ) -> bool:
        ecommerce_attributes = []
        supplier_values_view: Dict[str, Any] = {"id": ecommerce_seller.id}
        if ecommerce_seller.seller_name:
            ecommerce_attributes.append("seller_name=:seller_name")
            supplier_values_view["seller_name"] = ecommerce_seller.seller_name
        if ecommerce_seller.ecommerce_url:
            ecommerce_attributes.append("ecommerce_url=:ecommerce_url")
            supplier_values_view["ecommerce_url"] = ecommerce_seller.ecommerce_url
        if ecommerce_seller.project_name:
            ecommerce_attributes.append("project_name=:project_name")
            supplier_values_view["project_name"] = ecommerce_seller.project_name
        if ecommerce_seller.banner_img:
            ecommerce_attributes.append("banner_img=:banner_img")
            supplier_values_view["banner_img"] = ecommerce_seller.banner_img
        if ecommerce_seller.banner_img_href:
            ecommerce_attributes.append("banner_img_href=:banner_img_href")
            supplier_values_view["banner_img_href"] = ecommerce_seller.banner_img_href
        if ecommerce_seller.categories:
            ecommerce_attributes.append("categories=:categories")
            supplier_values_view["categories"] = ecommerce_seller.categories
        else:
            ecommerce_attributes.append("categories=:categories")
            supplier_values_view["categories"] = ""
        if ecommerce_seller.rec_prods:
            ecommerce_attributes.append("rec_prods=:rec_prods")
            supplier_values_view["rec_prods"] = ecommerce_seller.rec_prods
        else:
            ecommerce_attributes.append("rec_prods=:rec_prods")
            supplier_values_view["rec_prods"] = ""
        if ecommerce_seller.styles_json:
            ecommerce_attributes.append("styles_json=:styles_json")
            supplier_values_view["styles_json"] = ecommerce_seller.styles_json
        if isinstance(ecommerce_seller.shipping_enabled, bool):
            ecommerce_attributes.append("shipping_enabled=:shipping_enabled")
            supplier_values_view["shipping_enabled"] = ecommerce_seller.shipping_enabled
        else:
            ecommerce_attributes.append("shipping_enabled=:shipping_enabled")
            supplier_values_view["shipping_enabled"] = False
        if ecommerce_seller.shipping_rule_verified_by:
            ecommerce_attributes.append(
                "shipping_rule_verified_by=:shipping_rule_verified_by"
            )
            supplier_values_view["shipping_rule_verified_by"] = (
                ecommerce_seller.shipping_rule_verified_by
            )
        if ecommerce_seller.shipping_threshold:
            ecommerce_attributes.append("shipping_threshold=:shipping_threshold")
            supplier_values_view["shipping_threshold"] = (
                ecommerce_seller.shipping_threshold
            )
        else:
            ecommerce_attributes.append("shipping_threshold=:shipping_threshold")
            supplier_values_view["shipping_threshold"] = 0.0
        if ecommerce_seller.shipping_cost:
            ecommerce_attributes.append("shipping_cost=:shipping_cost")
            supplier_values_view["shipping_cost"] = ecommerce_seller.shipping_cost
        else:
            ecommerce_attributes.append("shipping_cost=:shipping_cost")
            supplier_values_view["shipping_cost"] = 0.0
        if ecommerce_seller.search_placeholder:
            ecommerce_attributes.append("search_placeholder=:search_placeholder")
            supplier_values_view["search_placeholder"] = (
                ecommerce_seller.search_placeholder
            )
        if ecommerce_seller.footer_msg:
            ecommerce_attributes.append("footer_msg=:footer_msg")
            supplier_values_view["footer_msg"] = ecommerce_seller.footer_msg
        if ecommerce_seller.footer_cta:
            ecommerce_attributes.append("footer_cta=:footer_cta")
            supplier_values_view["footer_cta"] = ecommerce_seller.footer_cta
        if ecommerce_seller.footer_phone:
            ecommerce_attributes.append("footer_phone=:footer_phone")
            supplier_values_view["footer_phone"] = ecommerce_seller.footer_phone
        if isinstance(ecommerce_seller.footer_is_wa, bool):
            ecommerce_attributes.append("footer_is_wa=:footer_is_wa")
            supplier_values_view["footer_is_wa"] = ecommerce_seller.footer_is_wa
        else:
            ecommerce_attributes.append("footer_is_wa=:footer_is_wa")
            supplier_values_view["footer_is_wa"] = False
        if ecommerce_seller.footer_email:
            ecommerce_attributes.append("footer_email=:footer_email")
            supplier_values_view["footer_email"] = ecommerce_seller.footer_email
        if ecommerce_seller.seo_description:
            ecommerce_attributes.append("seo_description=:seo_description")
            supplier_values_view["seo_description"] = ecommerce_seller.seo_description
        if ecommerce_seller.seo_keywords:
            ecommerce_attributes.append("seo_keywords=:seo_keywords")
            supplier_values_view["seo_keywords"] = ecommerce_seller.seo_keywords
        if ecommerce_seller.default_supplier_unit_id:
            ecommerce_attributes.append(
                "default_supplier_unit_id=:default_supplier_unit_id"
            )
            supplier_values_view["default_supplier_unit_id"] = (
                ecommerce_seller.default_supplier_unit_id
            )
        if ecommerce_seller.commerce_display:
            ecommerce_attributes.append("commerce_display=:commerce_display")
            supplier_values_view["commerce_display"] = ecommerce_seller.commerce_display
        if isinstance(ecommerce_seller.account_active, bool):
            ecommerce_attributes.append("account_active=:account_active")
            supplier_values_view["account_active"] = ecommerce_seller.account_active
        else:
            ecommerce_attributes.append("account_active=:account_active")
            supplier_values_view["account_active"] = False
        if ecommerce_seller.currency:
            ecommerce_attributes.append("currency=:currency")
            supplier_values_view["currency"] = ecommerce_seller.currency

        if len(ecommerce_attributes) == 0:
            logging.warning("Issues no data to update in sql: supplier user")
            return False
        ecommerce_attributes.append(" last_updated=:last_updated")
        supplier_values_view["last_updated"] = datetime.utcnow()
        ecommerce_query = f"""UPDATE ecommerce_seller
                        SET {','.join(ecommerce_attributes)}
                         WHERE id = :id;
            """
        flag = await super().edit(
            core_element_name="Ecommerce Seller",
            core_element_tablename="ecommerce_seller",
            core_query=ecommerce_query,
            core_values=supplier_values_view,
        )
        return flag

    async def fetch_supplier_business_ecommerce_url(
        self,
    ) -> List[EcommerceSeller]:
        _rp = await super().find(
            core_element_name="Ecommerce Seller",
            core_element_tablename="ecommerce_seller",
            core_columns=["*"],
            filter_values="ecommerce_url IS NOT NULL",
            values={},
        )
        res = []
        for _r in _rp:
            res.append(EcommerceSeller(**sql_to_domain(_r, EcommerceSeller)))
        return res

    async def add(
        self,
        ecommerce_seller: EcommerceSeller,
    ) -> EcommerceSeller | NoneType:
        _uid = uuid4()
        dict_vals = {
            es_key: es_prop
            for es_key, es_prop in ecommerce_seller.__dict__.items()
            if es_key in ["seller_name", "supplier_business_id", "secret_key"]
        }
        dict_vals["id"] = _uid
        flag = await super().add(
            core_element_name="Ecommerce Seller",
            core_element_tablename="ecommerce_seller",
            core_query="""
                INSERT INTO ecommerce_seller (
                    id,
                    seller_name,
                    supplier_business_id,
                    secret_key
                ) VALUES (
                    :id,
                    :seller_name,
                    :supplier_business_id,
                    :secret_key
                )
                """,
            core_values=dict_vals,
        )
        if flag:
            return EcommerceSeller(**sql_to_domain(dict_vals, EcommerceSeller))
        return None

    async def create_authos_ecommerce_tables(
        self,
        secret_key: str,
    ) -> bool:
        """Create Authos Ecommerce Tables

        Args:
            secret_key (str): Secret Key

        Returns:
            bool
            True if success
        """
        creation_queries = [
            """
            CREATE TABLE IF NOT EXISTS ecommerce_user_{esecret_key} (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                first_name varchar NOT NULL,
                last_name varchar NOT NULL,
                email varchar(255) NOT NULL,
                phone_number varchar(255),
                password varchar(255) NOT NULL,
                disabled boolean DEFAULT 'f' NOT NULL,
                created_at timestamp NOT NULL DEFAULT NOW(),
                last_updated timestamp NOT NULL DEFAULT NOW()
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS user_session_{esecret_key} (
                session_token text PRIMARY KEY NOT NULL,
                ecommerce_user_id uuid references ecommerce_user_{esecret_key} (id),
                session_data json,
                expiration timestamp NOT NULL,
                created_at timestamp DEFAULT NOW() NOT NULL,
                last_updated timestamp DEFAULT NOW() NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS pwd_restore_{esecret_key} (
                restore_token text PRIMARY KEY NOT NULL,
                ecommerce_user_id uuid REFERENCES ecommerce_user_{esecret_key} (id),
                expiration timestamp NOT NULL
            );
            """,
        ]
        try:
            for q in creation_queries:
                await self.db.execute(q.format(esecret_key=secret_key))
            return True
        except Exception as e:
            logging.error(e)
            logging.warning("Issues to create Authos Ecommerce Tables")
            return False


class EcommerceUserRestaurantRelationRepository(
    CoreRepository, EcommerceUserRestaurantRelationRepositoryInterface
):
    async def fetch(
        self,
        id_key: str,
        id_value: UUID | str,
    ) -> EcommerceUserRestaurantRelation | NoneType:
        res = await super().fetch(
            core_element_name="Ecommerce User Restaurant Relation",
            core_element_tablename="ecommerce_user_restaurant_relation",
            core_columns=["*"],
            id_key=id_key,
            id=id_value,
        )
        if not res:
            return None
        return EcommerceUserRestaurantRelation(
            **sql_to_domain(res, EcommerceUserRestaurantRelation)
        )

    async def add(
        self,
        ecommerce_user_id: UUID,
        restaurant_business_id: UUID,
    ) -> EcommerceUserRestaurantRelation | NoneType:
        _uid = uuid4()
        dict_vals = {
            "id": _uid,
            "ecommerce_user_id": ecommerce_user_id,
            "restaurant_business_id": restaurant_business_id,
        }
        flag = await super().add(
            core_element_name="Ecommerce User Restaurant Relation",
            core_element_tablename="ecommerce_user_restaurant_relation",
            core_query="""
                INSERT INTO ecommerce_user_restaurant_relation (
                    id,
                    ecommerce_user_id,
                    restaurant_business_id
                ) VALUES (
                    :id,
                    :ecommerce_user_id,
                    :restaurant_business_id
                )
                """,
            core_values=dict_vals,
        )
        if flag:
            return EcommerceUserRestaurantRelation(
                **sql_to_domain(dict_vals, EcommerceUserRestaurantRelation)
            )
        return None
