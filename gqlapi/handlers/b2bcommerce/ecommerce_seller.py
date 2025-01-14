from types import NoneType
from typing import List, Optional
import unicodedata
from uuid import UUID
from gqlapi.config import ENV as DEV_ENV
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import CloudinaryApi, Folders
from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    EcommerceAssignSellerUnitMsg,
    EcommercePublicSellerUrlInfo,
    EcommerceSellerCatalog,
    EcommerceSellerGQL,
    EcommerceSellerHandlerInterface,
    EcommerceSellerRepositoryInterface,
    EcommerceUserRestaurantRelationRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessHandlerInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    SupplierRestaurantsHandlerInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitHandlerInterface
from gqlapi.domain.models.v2.b2bcommerce import EcommerceSeller
from gqlapi.domain.models.v2.restaurant import RestaurantBranch
from gqlapi.domain.models.v2.supplier import (
    SupplierBusinessAccount,
    SupplierBusinessCommertialConditions,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.models.delivery_zones import get_delivery_zone
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from strawberry.file_uploads import Upload


class EcommerceSellerHandler(EcommerceSellerHandlerInterface):
    def __init__(
        self,
        ecommerce_seller_repo: EcommerceSellerRepositoryInterface,
        supplier_business_handler: SupplierBusinessHandlerInterface,
        supplier_unit_handler: SupplierUnitHandlerInterface,
        supplier_restaurant_assign_handler: Optional[
            SupplierRestaurantsHandlerInterface
        ] = None,
        restaurant_branch_repo: Optional[RestaurantBranchRepositoryInterface] = None,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        ecommerce_user_restaurant_relation_repo: Optional[
            EcommerceUserRestaurantRelationRepositoryInterface
        ] = None,
    ) -> None:
        self.ecommerce_seller_repo = ecommerce_seller_repo
        self.supplier_business_handler = supplier_business_handler
        self.supplier_unit_handler = supplier_unit_handler
        if supplier_restaurant_assign_handler:
            self.supplier_restaurant_assign_handler = supplier_restaurant_assign_handler
        if restaurant_branch_repo:
            self.restaurant_branch_repo = restaurant_branch_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if ecommerce_user_restaurant_relation_repo:
            self.ecommerce_user_restaurant_relation_repo = (
                ecommerce_user_restaurant_relation_repo
            )

    async def fetch_seller_info(
        self,
        ref_secret_key: str,
    ) -> EcommerceSellerGQL:
        """Fetch Seller Info
            - get supplier business id from secret key
            - fetch supplier business
            - fetch supplier units
            - format response

        Args:
            ref_secret_key (str): Secret key

        Returns:
            EcommerceSellerGQL
        """
        ecomm_seller = await self.ecommerce_seller_repo.fetch(
            id_key="secret_key", id_value=ref_secret_key
        )
        if not ecomm_seller:
            raise GQLApiException(
                "Ecommerce seller not found",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch supplier business - it raises error in case it cannot find
        sup_business_gql = await self.supplier_business_handler.fetch_supplier_business(
            ecomm_seller.supplier_business_id
        )
        # fetch supplier units
        supplier_units = await self.supplier_unit_handler.fetch_supplier_units(
            supplier_business_id=ecomm_seller.supplier_business_id
        )
        # format so that tax info is not included
        formatted_units = []
        for su in supplier_units:
            su_cpy = su
            su_cpy.tax_info = None
            if not su_cpy.deleted:
                formatted_units.append(su_cpy)
        # format response
        sup_acc: SupplierBusinessAccount = sup_business_gql.account  # type: ignore (safe)
        commertial_c: SupplierBusinessCommertialConditions = sup_acc.default_commertial_conditions  # type: ignore (safe)
        return EcommerceSellerGQL(
            **{
                k: v
                for k, v in sup_business_gql.__dict__.items()
                if k not in ["account", "permission"]
            },
            business_type=sup_acc.business_type,
            phone_number=sup_acc.phone_number,
            email=sup_acc.email,
            website=sup_acc.website,
            minimum_order_value=commertial_c.minimum_order_value,
            allowed_payment_methods=commertial_c.allowed_payment_methods,
            policy_terms=commertial_c.policy_terms,
            account_number=commertial_c.account_number,
            units=formatted_units,
            ecommerce_params=ecomm_seller,
        )

    async def get_assigned_seller_unit(
        self,
        ref_secret_key: str,
        restaurant_branch_id: UUID,
    ) -> EcommerceAssignSellerUnitMsg:
        """Get Assigned Seller Unit
            - get supplier business from secret key
            - get supplier unit assigned to restaurant branch
            - if it is assigned, return True with supplier unit id
            - else:
            -   get restaurant branch
            -   verify delivery zones, if not in DZ, return False
            -   if it is in DZ,
            -      Create supplier restaurant assignation
            -      return True with supplier unit id

        Args:
            ref_secret_key (str): _description_
            restaurant_branch_id (UUID): _description_

        Returns:
            EcommerceAssignSellerUnitMsg:
                supplier_unit_id (Optional[UUID]) - assigned supplier unit id
                status (bool) - True if assigned, False if no service available
                msg (str) - message
        """
        ecomm_seller = await self.fetch_seller_info(ref_secret_key)
        core_user = await self.core_user_repo.fetch_by_email("admin")
        if not core_user or not core_user.id:
            raise GQLApiException(
                "Admin Core user not found",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # verify if restaurant branch is assigned to supplier unit
        unit_rels = await self.supplier_restaurant_assign_handler.search_supplier_business_restaurant(
            supplier_business_id=ecomm_seller.id,
            restaurant_branch_id=restaurant_branch_id,
        )
        assigned_unit = None
        for au in unit_rels:
            if au.restaurant_branch_id == restaurant_branch_id:
                assigned_unit = au
                break
        if assigned_unit:
            return EcommerceAssignSellerUnitMsg(
                msg="Restaurant Branch has already assigned supplier unit",
                supplier_unit_id=assigned_unit.supplier_unit_id,
                status=True,
            )
        # if not assigned yet, verify if restaurant branch is in delivery zone
        # get restaurant branch
        branch_dict = await self.restaurant_branch_repo.fetch(restaurant_branch_id)
        if not branch_dict:
            return EcommerceAssignSellerUnitMsg(
                msg="Restaurant branch not found",
                supplier_unit_id=None,
                status=False,
            )
        rest_branch = RestaurantBranch(**branch_dict)
        # Custom region validation through files
        dz_idx, dz_type = get_delivery_zone(ref_secret_key)
        assigned_dz = dz_idx.get(rest_branch.zip_code, None)
        if not assigned_dz:
            return EcommerceAssignSellerUnitMsg(
                msg="Restaurant branch not in delivery zone",
                supplier_unit_id=None,
                status=False,
            )
        # verify which supplier unit is assigned to delivery zone
        for su in ecomm_seller.units:
            if su.deleted or not su.delivery_info or not su.delivery_info.regions:
                continue
            if dz_type == "default":
                for dz in su.delivery_info.regions:
                    # [TODO]: fix this validation and store regions homogeneusly with the same format
                    if (
                        str(dz).lower() == assigned_dz.lower()
                        or str(dz).lower() in assigned_dz.lower()
                    ):
                        # create supplier restaurant assignation
                        try:
                            await self.supplier_restaurant_assign_handler.add_supplier_restaurant_relation(
                                supplier_unit_id=su.id,
                                restaurant_branch_id=restaurant_branch_id,
                                approved=False,
                                priority=1,
                                rating=None,
                                review=None,
                                created_by=core_user.id,
                            )
                            return EcommerceAssignSellerUnitMsg(
                                msg="Restaurant branch assigned to supplier unit",
                                supplier_unit_id=su.id,
                                status=True,
                            )
                        except Exception:
                            return EcommerceAssignSellerUnitMsg(
                                msg="Error creating supplier restaurant assignation",
                                supplier_unit_id=None,
                                status=False,
                            )
            if dz_type == "custom":
                # For custom try with the supplier unit names
                normed_su_name = "".join(
                    [
                        c
                        for c in unicodedata.normalize(
                            "NFKD", su.unit_name.lower().replace(" ", "_")
                        )
                        if not unicodedata.combining(c)
                    ]
                )
                if normed_su_name == assigned_dz:
                    try:
                        await self.supplier_restaurant_assign_handler.add_supplier_restaurant_relation(
                            supplier_unit_id=su.id,
                            restaurant_branch_id=restaurant_branch_id,
                            approved=False,
                            priority=1,
                            rating=None,
                            review=None,
                            created_by=core_user.id,
                        )
                        return EcommerceAssignSellerUnitMsg(
                            msg="Restaurant branch assigned to supplier unit",
                            supplier_unit_id=su.id,
                            status=True,
                        )
                    except Exception:
                        return EcommerceAssignSellerUnitMsg(
                            msg="Error creating supplier restaurant assignation",
                            supplier_unit_id=None,
                            status=False,
                        )
        return EcommerceAssignSellerUnitMsg(
            msg="No supplier unit available for restaurant branch",
            supplier_unit_id=None,
            status=False,
        )

    async def fetch_seller_spec_catalog_info(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> EcommerceSellerCatalog:
        prods = await self.supplier_restaurant_assign_handler.get_ecommerce_supplier_restaurant_products(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=restaurant_branch_id,
            search=search,
            page=page,
            page_size=page_size,
        )
        categs = await self.supplier_restaurant_assign_handler.get_ecommerce_categories(
            supplier_unit_id=supplier_unit_id,
        )
        results_num = await self.supplier_restaurant_assign_handler.count_ecommerce_supplier_restaurant_products(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=restaurant_branch_id,
            search=search,
        )
        return EcommerceSellerCatalog(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=restaurant_branch_id,
            products=prods,
            catalog_type="SPECIFIC",
            categories=categs,
            total_results=results_num,
        )

    async def fetch_seller_default_catalog_info(
        self,
        supplier_unit_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> EcommerceSellerCatalog:
        prods = await self.supplier_restaurant_assign_handler.get_ecommerce_default_supplier_products(
            supplier_unit_id=supplier_unit_id,
            search=search,
            page=page,
            page_size=page_size,
        )
        categs = await self.supplier_restaurant_assign_handler.get_ecommerce_categories(
            supplier_unit_id=supplier_unit_id,
        )
        results_num = await self.supplier_restaurant_assign_handler.count_ecommerce_default_supplier_products(
            supplier_unit_id=supplier_unit_id,
            search=search,
        )
        return EcommerceSellerCatalog(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=None,
            products=prods,
            catalog_type="DEFAULT",
            categories=categs,
            total_results=results_num,
        )

    async def fetch_seller_spec_product_details(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        supplier_product_id: UUID,
    ) -> EcommerceSellerCatalog:
        prod = await self.supplier_restaurant_assign_handler.get_ecommerce_supplier_restaurant_product_details(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=restaurant_branch_id,
            supplier_product_id=supplier_product_id,
        )
        if not prod:
            return EcommerceSellerCatalog(
                supplier_unit_id=supplier_unit_id,
                restaurant_branch_id=restaurant_branch_id,
                products=[],
                catalog_type="SPECIFIC_DETAILS",
                categories=[],
                total_results=0,
            )
        return EcommerceSellerCatalog(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=restaurant_branch_id,
            products=[prod],
            catalog_type="SPECIFIC_DETAILS",
            categories=[],
            total_results=1,
        )

    async def fetch_seller_default_product_details(
        self,
        supplier_unit_id: UUID,
        supplier_product_id: UUID,
    ) -> EcommerceSellerCatalog:
        prod = await self.supplier_restaurant_assign_handler.get_ecommerce_default_supplier_product_detail(
            supplier_unit_id=supplier_unit_id,
            supplier_product_id=supplier_product_id,
        )
        return EcommerceSellerCatalog(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=None,
            products=[prod] if prod is not None else [],
            catalog_type="DEFAULT_DETAILS",
            categories=[],
            total_results=1 if prod is not None else 0,
        )

    async def fetch_ecommerce_seller(
        self,
        id_key: str,
        id_value: UUID | str,
    ):
        return await self.ecommerce_seller_repo.fetch(id_key, id_value)

    async def add_ecommerce_seller(
        self,
        ecommerce_seller: EcommerceSeller,
    ) -> EcommerceSeller | NoneType:
        ecomm_seller = await self.ecommerce_seller_repo.add(ecommerce_seller)
        if not ecomm_seller:
            return None

        # create tables for ecommerce
        if not await self.ecommerce_seller_repo.create_authos_ecommerce_tables(
            ecomm_seller.secret_key
        ):
            return None
        return ecomm_seller

    async def edit_ecommerce_seller(self, ecommerce_seller: EcommerceSeller) -> bool:
        return await self.ecommerce_seller_repo.edit(ecommerce_seller)

    async def update_ecommerce_seller_params(
        self,
        supplier_business_id: UUID,
        seller_name: Optional[str],
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
    ) -> EcommerceSeller | None:
        ecommerce_seller = await self.fetch_ecommerce_seller(
            id_key="supplier_business_id", id_value=supplier_business_id
        )
        if not ecommerce_seller:
            raise GQLApiException(
                "Ecommerce seller not found",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if not await self.edit_ecommerce_seller(
            EcommerceSeller(
                id=ecommerce_seller.id,
                supplier_business_id=supplier_business_id,
                seller_name=(
                    seller_name
                    if seller_name is not None
                    else ecommerce_seller.seller_name
                ),
                secret_key=ecommerce_seller.secret_key,
                banner_img_href=(
                    banner_img_href
                    if banner_img_href is not None
                    else ecommerce_seller.banner_img_href
                ),
                categories=(
                    categories
                    if categories is not None
                    else ecommerce_seller.categories
                ),
                rec_prods=(
                    rec_prods if rec_prods is not None else ecommerce_seller.rec_prods
                ),
                styles_json=(
                    styles_json
                    if styles_json is not None
                    else ecommerce_seller.styles_json
                ),
                shipping_enabled=(
                    shipping_enabled
                    if shipping_enabled is not None
                    else ecommerce_seller.shipping_enabled
                ),
                shipping_rule_verified_by=(
                    shipping_rule_verified_by
                    if shipping_rule_verified_by is not None
                    else ecommerce_seller.shipping_rule_verified_by
                ),
                shipping_threshold=(
                    shipping_threshold
                    if shipping_threshold is not None
                    else ecommerce_seller.shipping_threshold
                ),
                shipping_cost=(
                    shipping_cost
                    if shipping_cost is not None
                    else ecommerce_seller.shipping_cost
                ),
                search_placeholder=(
                    search_placeholder
                    if search_placeholder is not None
                    else ecommerce_seller.search_placeholder
                ),
                footer_msg=(
                    footer_msg
                    if footer_msg is not None
                    else ecommerce_seller.footer_msg
                ),
                footer_cta=(
                    footer_cta
                    if footer_cta is not None
                    else ecommerce_seller.footer_cta
                ),
                footer_phone=(
                    footer_phone
                    if footer_phone is not None
                    else ecommerce_seller.footer_phone
                ),
                footer_is_wa=(
                    footer_is_wa
                    if footer_is_wa is not None
                    else ecommerce_seller.footer_is_wa
                ),
                footer_email=(
                    footer_email
                    if footer_email is not None
                    else ecommerce_seller.footer_email
                ),
                seo_description=(
                    seo_description
                    if seo_description is not None
                    else ecommerce_seller.seo_description
                ),
                seo_keywords=(
                    seo_keywords
                    if seo_keywords is not None
                    else ecommerce_seller.seo_keywords
                ),
                default_supplier_unit_id=(
                    default_supplier_unit_id
                    if default_supplier_unit_id is not None
                    else ecommerce_seller.default_supplier_unit_id
                ),
                commerce_display=(
                    commerce_display
                    if commerce_display is not None
                    else ecommerce_seller.commerce_display
                ),
                account_active=(
                    account_active
                    if account_active is not None
                    else ecommerce_seller.account_active
                ),
                currency=(
                    currency if currency is not None else ecommerce_seller.currency
                ),
            )
        ):
            raise GQLApiException(
                "Error updating ecommerce seller",
                GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return await self.fetch_ecommerce_seller(
            id_key="supplier_business_id", id_value=supplier_business_id
        )

    async def patch_add_ecommerce_seller_image(
        self, supplier_business_id, image: Upload, image_type: str
    ) -> bool:
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        file_data: bytes = await image.read()  # type: ignore
        # Split the path by '/'
        img_key = str(supplier_business_id) + "_" + image_type
        cloudinary_api.delete(
            folder=Folders.MARKETPLACE.value,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
            img_key=img_key,
        )
        route = cloudinary_api.upload(
            folder=Folders.MARKETPLACE.value,
            img_file=file_data,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
            img_key=img_key,
        )
        if "status" in route and route["status"] == "ok" and "data" in route:
            return True
        else:
            raise GQLApiException(
                msg="Error to save supplier profile image url",
                error_code=GQLApiErrorCodeType.INSERT_CLOUDINARY_DB_ERROR.value,
            )

    async def patch_delete_ecommerce_seller_image(
        self, supplier_business_id, image_type: str
    ) -> bool:
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        # Split the path by '/'
        img_key = str(supplier_business_id) + "_" + image_type
        status = cloudinary_api.delete(
            folder=Folders.MARKETPLACE.value,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
            img_key=img_key,
        )
        if "status" in status and status["status"] == "ok" and "msg" in status:
            return True
        else:
            raise GQLApiException(
                msg="Error to delete image url",
                error_code=GQLApiErrorCodeType.INSERT_CLOUDINARY_DB_ERROR.value,
            )

    async def fetch_public_supplier_business_ecommerce_url(
        self,
    ) -> List[EcommercePublicSellerUrlInfo]:
        supp_info_list = []
        supp_info = (
            await self.ecommerce_seller_repo.fetch_supplier_business_ecommerce_url()
        )
        for si in supp_info:
            if si.ecommerce_url:
                supp_info_list.append(
                    EcommercePublicSellerUrlInfo(
                        supplier_business_id=si.supplier_business_id,
                        ecommerce_url=si.ecommerce_url,
                    )
                )
        return supp_info_list
