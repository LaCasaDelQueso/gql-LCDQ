from abc import ABC, abstractmethod
from datetime import date
from types import NoneType
from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.orden.invoice import MxInvoiceGQL
from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import RestaurantBranchGQL
from gqlapi.domain.interfaces.v2.supplier.supplier_product import SupplierProductDetails
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitGQL
from gqlapi.domain.models.v2.authos import IEcommerceUser
from gqlapi.domain.models.v2.restaurant import RestaurantBusiness
from gqlapi.domain.models.v2.supplier import MinimumOrderValue, SupplierBusiness
from gqlapi.domain.models.v2.utils import (
    CFDIUse,
    PayMethodType,
    RegimenSat,
    SupplierBusinessType,
)

import strawberry
from strawberry.file_uploads import Upload
from gqlapi.domain.models.v2.b2bcommerce import (
    EcommerceSeller,
    EcommerceUserRestaurantRelation,
)


@strawberry.type
class EcommerceSellerError:
    msg: str
    code: int


@strawberry.type
class B2BEcommerceUserError:
    msg: str
    code: int


@strawberry.type
class EcommerceAssignSellerUnitMsg:
    status: bool
    msg: str
    supplier_unit_id: Optional[UUID] = None


@strawberry.type
class EcommerceSellerGQL(SupplierBusiness):
    business_type: Optional[SupplierBusinessType] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    minimum_order_value: MinimumOrderValue
    allowed_payment_methods: List[PayMethodType]
    policy_terms: str
    account_number: Optional[str] = None
    units: List[SupplierUnitGQL]
    ecommerce_params: EcommerceSeller


@strawberry.type
class EcommerceSellerCatalog:
    supplier_unit_id: UUID
    restaurant_branch_id: Optional[UUID] = None
    catalog_type: str
    products: List[SupplierProductDetails]
    categories: List[str]
    total_results: int


@strawberry.type
class B2BEcommerceUserInfo:
    user: IEcommerceUser
    client: RestaurantBusiness
    addresses: List[RestaurantBranchGQL]


@strawberry.type
class B2BEcommerceOrdenInfo:
    orden: OrdenGQL
    invoice: Optional[MxInvoiceGQL] = None


@strawberry.type
class B2BEcommerceHistorialOrdenes:
    ordenes: List[B2BEcommerceOrdenInfo]
    total_results: int


@strawberry.type
class EcommerceSellerImageStatus:
    msg: str
    status: bool


@strawberry.type
class EcommercePublicSellerUrlInfo:
    supplier_business_id: UUID
    ecommerce_url: str


EcommerceSellerResult = strawberry.union(
    "EcommerceSellerResult",
    (EcommerceSellerGQL, EcommerceSellerError),
)

EcommerceSellerBusinessResult = strawberry.union(
    "EcommerceSellerBusinessResult",
    (EcommerceSeller, EcommerceSellerError),
)

EcommerceSellerUnitMsgResult = strawberry.union(
    "EcommerceSellerMsgResult",
    (EcommerceAssignSellerUnitMsg, EcommerceSellerError),
)

EcommerceSellerCatalogResult = strawberry.union(
    "EcommerceSellerCatalogResult",
    (EcommerceSellerCatalog, EcommerceSellerError),
)

B2BEcommerceUserResult = strawberry.union(
    "B2BEcommerceUserResult",
    (B2BEcommerceUserInfo, B2BEcommerceUserError),
)

B2BEcommerceOrdenDetailsResult = strawberry.union(
    "B2BEcommerceOrdenDetailsResult",
    (B2BEcommerceOrdenInfo, B2BEcommerceUserError),
)

B2BEcommerceOrdenesResult = strawberry.union(
    "B2BEcommerceOrdenesResult",
    (B2BEcommerceHistorialOrdenes, B2BEcommerceUserError),
)

EcommerceSellerImageResult = strawberry.union(
    "EcommerceSellerImageResult", (EcommerceSellerError, EcommerceSellerImageStatus)
)

EcommerceSellerUrlResult = strawberry.union(
    "EcommerceSellerUrlResult", (EcommerceSellerError, EcommercePublicSellerUrlInfo)
)


# handler interfaces
class EcommerceSellerHandlerInterface(ABC):
    @abstractmethod
    async def fetch_seller_info(
        self,
        ref_secret_key: str,
    ) -> EcommerceSellerGQL:
        raise NotImplementedError

    @abstractmethod
    async def get_assigned_seller_unit(
        self,
        ref_secret_key: str,
        restaurant_branch_id: UUID,
    ) -> EcommerceAssignSellerUnitMsg:
        raise NotImplementedError

    @abstractmethod
    async def fetch_seller_spec_catalog_info(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> EcommerceSellerCatalog:
        raise NotImplementedError

    @abstractmethod
    async def fetch_seller_default_catalog_info(
        self,
        supplier_unit_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> EcommerceSellerCatalog:
        raise NotImplementedError

    @abstractmethod
    async def fetch_seller_spec_product_details(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        supplier_product_id: UUID,
    ) -> EcommerceSellerCatalog:
        raise NotImplementedError

    @abstractmethod
    async def fetch_seller_default_product_details(
        self,
        supplier_unit_id: UUID,
        supplier_product_id: UUID,
    ) -> EcommerceSellerCatalog:
        raise NotImplementedError

    @abstractmethod
    async def fetch_ecommerce_seller(
        self,
        id_key: str,
        id_value: UUID | str,
    ):
        raise NotImplementedError

    @abstractmethod
    async def add_ecommerce_seller(
        self,
        ecommerce_seller: EcommerceSeller,
    ) -> EcommerceSeller | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit_ecommerce_seller(self, ecommerce_seller: EcommerceSeller) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def update_ecommerce_seller_params(
        self,
        supplier_business_id: UUID,
        seller_name: str,
        banner_img_href: Optional[str] = None,
        categories: Optional[str] = None,
        rec_prods: Optional[str] = None,
        styles_json: Optional[str] = None,
        shipping_enabled: Optional[bool] = None,
        shipping_rule_verified_by: Optional[str] = None,
        shipping_threshold: Optional[float] = None,
        shipping_cost: Optional[float] = None,
        search_placeholder: Optional[str] = None,
        footer_msg: Optional[str] = None,
        footer_cta: Optional[str] = None,
        footer_phone: Optional[str] = None,
        footer_is_wa: Optional[bool] = None,
        footer_email: Optional[str] = None,
        seo_description: Optional[str] = None,
        seo_keywords: Optional[str] = None,
        default_supplier_unit_id: Optional[UUID] = None,
        commerce_display: Optional[str] = None,
        account_active: Optional[bool] = None,
        currency: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def patch_add_ecommerce_seller_image(
        self, supplier_business_id, image: Upload, image_type: str
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def patch_delete_ecommerce_seller_image(
        self, supplier_business_id, image_type: str
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_public_supplier_business_ecommerce_url(
        self,
    ) -> List[EcommercePublicSellerUrlInfo]:
        raise NotImplementedError


class B2BEcommerceUserHandlerInterface(ABC):
    @abstractmethod
    async def get_b2becommerce_client_info(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
    ) -> B2BEcommerceUserInfo:
        raise NotImplementedError

    @abstractmethod
    async def add_b2becommerce_client_address(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        category_id: Optional[UUID] = None,
        # optional tax info
        mx_sat_id: Optional[str] = None,
        tax_email: Optional[str] = None,
        legal_name: Optional[str] = None,
        tax_full_address: Optional[str] = None,
        tax_zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
    ) -> B2BEcommerceUserInfo:
        raise NotImplementedError

    @abstractmethod
    async def get_b2becommerce_historic_ordenes(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> B2BEcommerceHistorialOrdenes:
        raise NotImplementedError

    @abstractmethod
    async def get_b2becommerce_orden_details(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
        orden_id: UUID,
    ) -> B2BEcommerceOrdenInfo:
        raise NotImplementedError

    @abstractmethod
    async def _fetch_ecommerce_rest_business_relation(
        self,
        id: Optional[UUID] = None,
        restaurant_business_id: Optional[UUID] = None,
        ecommerce_user_id: Optional[UUID] = None,
    ) -> EcommerceUserRestaurantRelation | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def new_ecommerce_restaurant_user(
        self, restaurant_branch_id: UUID, email: str
    ) -> IEcommerceUser:
        raise NotImplementedError

    @abstractmethod
    async def edit_ecommerce_restaurant_user(
        self, restaurant_branch_id: UUID, email: str
    ) -> IEcommerceUser:
        raise NotImplementedError


# Repository Interfaces
class EcommerceSellerRepositoryInterface(ABC):
    @abstractmethod
    async def fetch(
        self,
        id_key: str,
        id_value: UUID | str,
    ) -> EcommerceSeller | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        ecommerce_seller: EcommerceSeller,
    ) -> EcommerceSeller | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        ecommerce_seller: EcommerceSeller,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_business_ecommerce_url(
        self,
    ) -> List[EcommerceSeller]:
        raise NotImplementedError

    @abstractmethod
    async def create_authos_ecommerce_tables(
        self,
        secret_key: str,
    ) -> bool:
        raise NotImplementedError


class EcommerceUserRestaurantRelationRepositoryInterface(ABC):
    @abstractmethod
    async def fetch(
        self,
        id_key: str,
        id_value: UUID | str,
    ) -> EcommerceUserRestaurantRelation | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        ecommerce_user_id: UUID,
        restaurant_business_id: UUID,
    ) -> EcommerceUserRestaurantRelation | NoneType:
        raise NotImplementedError
