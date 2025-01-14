from datetime import datetime
from types import NoneType
from typing import Literal, Optional
from uuid import UUID
from abc import ABC
from strawberry import type as strawberry_type


@strawberry_type
class EcommerceSeller(ABC):
    id: UUID
    supplier_business_id: UUID
    seller_name: str
    secret_key: str
    ecommerce_url: Optional[str] = None
    project_name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    banner_img: Optional[str] = None
    banner_img_href: Optional[str] = None
    categories: Optional[str] = None
    rec_prods: Optional[str] = None
    styles_json: Optional[str] = None
    shipping_enabled: Optional[bool] = None
    shipping_rule_verified_by: Optional[str] = None
    shipping_threshold: Optional[float] = None
    shipping_cost: Optional[float] = None
    search_placeholder: Optional[str] = None
    footer_msg: Optional[str] = None
    footer_cta: Optional[str] = None
    footer_phone: Optional[str] = None
    footer_is_wa: Optional[bool] = None
    footer_email: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    default_supplier_unit_id: Optional[UUID] = None
    commerce_display: Optional[str] = None
    account_active: Optional[bool] = None
    currency: Optional[str] = None

    def new(self, *args) -> "EcommerceSeller":
        raise NotImplementedError

    @staticmethod
    def get(id: UUID | NoneType = None) -> "EcommerceSeller":
        raise NotImplementedError


@strawberry_type
class EcommerceUserRestaurantRelation(ABC):
    id: UUID
    ecommerce_user_id: UUID
    restaurant_business_id: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "EcommerceUserRestaurantRelation":
        raise NotImplementedError

    @staticmethod
    def get(id: UUID | NoneType = None) -> "EcommerceUserRestaurantRelation":
        raise NotImplementedError


@strawberry_type
class EcommerceEnvVars(ABC):
    # Public Envs
    NEXT_PUBLIC_PROJECT_URL: str
    NEXT_PUBLIC_SELLER_NAME: str
    NEXT_PUBLIC_SELLER_LOGO: str
    NEXT_PUBLIC_BANNER_IMG: str
    NEXT_PUBLIC_BANNER_IMG_HREF: str
    NEXT_PUBLIC_CATEGORIES: str
    NEXT_PUBLIC_REC_PRODS: str
    NEXT_PUBLIC_STYLES_JSON: str
    # Shipping
    NEXT_PUBLIC_SHIPPING_ENABLED: str
    NEXT_PUBLIC_SHIPPING_RULE_VERIFIED_BY: str
    NEXT_PUBLIC_SHIPPING_THRESHOLD: str
    NEXT_PUBLIC_SHIPPING_COST: str
    # -- Website copies
    NEXT_PUBLIC_SEARCH_PLACEHOLDER: str
    NEXT_PUBLIC_FOOTER_MSG: str
    NEXT_PUBLIC_FOOTER_CTA: str
    NEXT_PUBLIC_FOOTER_PHONE: str
    NEXT_PUBLIC_FOOTER_IS_WA: str
    NEXT_PUBLIC_FOOTER_EMAIL: str
    # -- Metadata
    NEXT_PUBLIC_SEO_TITLE: str
    NEXT_PUBLIC_SEO_DESCRIPTION: str
    NEXT_PUBLIC_SEO_KEYWORDS: str
    NEXT_PUBLIC_SEO_IMAGE: str

    # Private Envs
    NEXT_PUBLIC_SELLER_ID: str
    NEXT_PUBLIC_SUNIT_ID: str
    NEXT_PUBLIC_COMMERCE_DISPLAY: str
    NEXT_PUBLIC_ACCOUNT_ACTIVE: str
    NEXT_PUBLIC_CURRENCY: str
    # API environment: staging | production
    NEXT_PUBLIC_GQLAPI_ENV: str


@strawberry_type
class NewEcommerceEnvVars(ABC):
    # Public Envs
    NEXT_PUBLIC_SELLER_NAME: str
    NEXT_PUBLIC_SELLER_ID: str
    NEXT_PUBLIC_SUNIT_ID: str
    NEXT_PUBLIC_GQLAPI_ENV: str


@strawberry_type
class EcommerceParams(ABC):
    ecommerce_url: Optional[str] = None
    project_name: Optional[str] = None
    banner_img: Optional[str] = None
    banner_img_href: Optional[str] = None
    categories: Optional[str] = None
    rec_prods: Optional[str] = None
    styles_json: Optional[str] = None
    shipping_enabled: Optional[bool] = None
    shipping_rule_verified_by: Optional[str] = None
    shipping_threshold: Optional[float] = None
    shipping_cost: Optional[float] = None
    search_placeholder: Optional[str] = None
    footer_msg: Optional[str] = None
    footer_cta: Optional[str] = None
    footer_phone: Optional[str] = None
    footer_is_wa: Optional[bool] = None
    footer_email: Optional[str] = None
    seo_description: Optional[str] = None
    seo_keywords: Optional[str] = None
    commerce_display: Optional[Literal['open', 'closed-with-catalog', 'closed']] = None
    account_active: Optional[bool] = None
    currency: Optional[str] = None
