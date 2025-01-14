import base64
import datetime
from io import BytesIO, StringIO
import json
from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchError,
    RestaurantBranchTagInput,
    RestaurantBranchTaxResult,
)
from gqlapi.domain.models.v2.utils import CFDIUse, InvoiceTriggerTime, InvoiceType, RegimenSat
from gqlapi.handlers.b2bcommerce.ecommerce_seller import EcommerceSellerHandler
from gqlapi.handlers.b2bcommerce.ecommerce_user import B2BEcommerceUserHandler
from gqlapi.handlers.restaurant.restaurant_business import RestaurantBusinessHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.handlers.supplier.supplier_product import SupplierProductHandler
from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
from gqlapi.repository.b2bcommerce.ecommerce_seller import (
    EcommerceSellerRepository,
    EcommerceUserRestaurantRelationRepository,
)
from gqlapi.repository.core.invoice import MxSatCertificateRepository
from gqlapi.repository.services.authos import EcommerceUserRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
import pandas as pd

import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    ExportSupplierRestaurantGQL,
    ExportSupplierRestaurantResult,
    SupplierRestaurantAssignationResult,
    SupplierRestaurantCreationResult,
    SupplierRestaurantError,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.handlers.restaurant.restaurant_branch import RestaurantBranchHandler
from gqlapi.repository.core.category import (
    CategoryRepository,
    RestaurantBranchCategoryRepository,
    SupplierUnitCategoryRepository,
)
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.restaurant.restaurant_branch import (
    RestaurantBranchInvoicingOptionsRepository,
    RestaurantBranchRepository,
)
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
    SupplierProductStockRepository,
)
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


@strawberry.type
class SupplierRestaurantsMutation:
    @strawberry.mutation(
        name="newSupplierRestaurantCreation",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_supplier_restaurant_creation(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        # Rest Business Data
        name: str,
        country: str,
        # Rest Branch Data
        email: str,
        phone_number: str,
        contact_name: str,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        zip_code: str,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        tags: Optional[List[RestaurantBranchTagInput]] = None,
    ) -> SupplierRestaurantCreationResult:  # type: ignore
        """Create a new restaurant's supplier

        Args:
            info (StrawberryInfo): info to connect to DB
            supplier_unit_id (UUID): unique restaurant business id
            name (str): name of the restaurant business
            country (str): country of the restaurant business
            category_id (UUID): category id of the restaurant business
            email (str): email of the restaurant business
            phone_number (str): phone number of the restaurant business
            contact_name (str): contact name of the restaurant business
            branch_name (str): branch name of the restaurant business
            full_address (str): full address of the restaurant business
            street (str): street of the restaurant business
            external_num (str): external number of the restaurant business
            internal_num (str): internal number of the restaurant business
            neighborhood (str): neighborhood of the restaurant business
            city (str): city of the restaurant business
            state (str): state of the restaurant business
            zip_code (str): zip code of the restaurant business
            rating (Optional[int], optional): rating of the restaurant business. Defaults to None.
            review (Optional[str], optional): review of the restaurant business. Defaults to None.

        Returns:
            SupplierRestaurantCreationResult: result of the creation
        """
        logger.info("Creating supplier restaurant")
        # validate inputs
        if not name and not country and not email and not phone_number:
            return SupplierRestaurantError(
                msg="Empty values for creating Supplier Restaurant",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if rating:
            if rating not in range(0, 6):
                return SupplierRestaurantError(
                    msg="Rating is out of range",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        tags_dict = None
        if tags is not None:
            tags_dict = [
                {
                    "tag_key": tag.tag,
                    "tag_value": tag.value,
                }
                for tag in tags
            ]
        _handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            product_repo=ProductRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
        )
        # instantiate handler
        try:
            # call validation
            fb_id = info.context["request"].user.firebase_user.firebase_id

            sup_rest_creation = await _handler.new_supplier_restaurant_creation(
                fb_id,
                supplier_unit_id,
                name,
                country,
                email,
                phone_number,
                contact_name,
                branch_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                zip_code,
                rating,
                review,
                tags_dict,
            )
            return sup_rest_creation
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierRestaurantError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierRestaurantError(
                msg="Error creating supplier restaurant",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="updateSupplerRestaurant",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_supplier_restaurant_creation(
        self,
        info: StrawberryInfo,
        supplier_restaurant_relation_id: UUID,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        # Rest Branch Data
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        contact_name: Optional[str] = None,
        branch_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        tags: Optional[List[RestaurantBranchTagInput]] = None,
    ) -> SupplierRestaurantCreationResult:  # type: ignore
        """Update supplier's restaurant
            - It updates restaurant branch values
                & assignation to a different supplier unit

        Args:
            info (StrawberryInfo): info to connect to DB
            supplier_restaurant_relation_id (UUID): unique restaurant supplier relation id
            supplier_unit_id (UUID): unique restaurant business id
            restaurant_branch_id (UUID): unique restaurant branch id
            name (str): name of the restaurant business
            country (str): country of the restaurant business
            category_id (UUID): category id of the restaurant business
            email (str): email of the restaurant business
            phone_number (str): phone number of the restaurant business
            contact_name (str): contact name of the restaurant business
            branch_name (str): branch name of the restaurant business
            full_address (str): full address of the restaurant business
            street (str): street of the restaurant business
            external_num (str): external number of the restaurant business
            internal_num (str): internal number of the restaurant business
            neighborhood (str): neighborhood of the restaurant business
            city (str): city of the restaurant business
            state (str): state of the restaurant business
            zip_code (str): zip code of the restaurant business
            rating (Optional[int], optional): rating of the restaurant business. Defaults to None.
            review (Optional[str], optional): review of the restaurant business. Defaults to None.

        Returns:
            RestaurantBusinessResult
        """
        logger.info("Update supplier restaurant relation")
        # validate inputs
        if rating:
            if rating not in range(0, 6):
                return SupplierRestaurantError(
                    msg="Rating is out of range",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        tags_dict = None
        if tags is not None:
            tags_dict = [
                {
                    "tag_key": tag.tag,
                    "tag_value": tag.value,
                }
                for tag in tags
            ]
        # instantiate handler
        _handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            product_repo=ProductRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
        )
        try:
            # call validation
            fb_id = info.context["request"].user.firebase_user.firebase_id
            edited_res = await _handler.edit_supplier_restaurant_creation(
                fb_id,
                supplier_restaurant_relation_id,
                supplier_unit_id,
                restaurant_branch_id,
                name,
                country,
                email,
                phone_number,
                contact_name,
                branch_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                zip_code,
                rating,
                review,
                tags_dict,
            )
            return edited_res
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierRestaurantError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierRestaurantError(
                msg="Error editing supplier restaurant",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="upsertSupplierRestaurantTaxInfo",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_upsert_supplier_restaurant_tax_info(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
        invoice_pay_type: Optional[str] = None,
        invoice_trigger_type: Optional[str] = None,
    ) -> RestaurantBranchTaxResult:  # type: ignore
        logger.info("Edit supplier restaurant tax info")
        # instantiate handler
        try:
            # call validation
            fb_id = info.context["request"].user.firebase_user.firebase_id
            if invoice_trigger_type and invoice_pay_type:
                try:
                    # if invoicing_trigger_type != ""
                    invoicing_trigger_type = InvoiceTriggerTime(invoice_trigger_type)  # type: ignore
                    invoicing_pay_type = InvoiceType(invoice_pay_type)  # type: ignore
                except Exception:
                    raise GQLApiException(
                        msg="Error Datatype invoicing options",
                        error_code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                    )
            # instantiate handler
            _sr_handler = SupplierRestaurantsHandler(
                supplier_restaurants_repo=SupplierRestaurantsRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
                restaurant_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
                category_repo=CategoryRepository(info),
                restaurant_branch_category_repo=RestaurantBranchCategoryRepository(
                    info
                ),
                product_repo=ProductRepository(info),
                supplier_product_repo=SupplierProductRepository(info),
                supplier_product_price_repo=SupplierProductPriceRepository(info),
            )
            _handler = RestaurantBranchHandler(
                RestaurantBranchRepository(info),
                RestaurantBranchCategoryRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_restaurants_repo=SupplierRestaurantsRepository(info),
                invoicing_options_repo=RestaurantBranchInvoicingOptionsRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
                supplier_restaurant_handler=_sr_handler,
                core_user_repo=CoreUserRepository(info),
            )
            # call validation
            if not restaurant_branch_id and not (
                mx_sat_id
                or email
                or legal_name
                or full_address
                or zip_code
                or sat_regime
                or cfdi_use
                or invoicing_provider_id
                or invoice_pay_type
                or invoice_trigger_type
            ):
                return RestaurantBranchError(
                    msg="Empty values for creating Supplier Restaurant tax info",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # call handler
            # return
            branch_info = await _handler.edit_restaurant_branch_tax_info(
                restaurant_branch_id,
                mx_sat_id,
                email,
                legal_name,
                full_address,
                zip_code,
                sat_regime,
                cfdi_use,
                invoicing_provider_id,
            )
            if invoice_pay_type and invoice_trigger_type:
                await _handler.edit_restaurant_branch_invoicing_options(
                    restaurant_branch_id=restaurant_branch_id,
                    firebase_id=fb_id,
                    invoice_type=invoicing_pay_type,  # type: ignore
                    triggered_at=invoicing_trigger_type,  # type: ignore
                    automated_invoicing=(
                        True
                        if invoicing_trigger_type != InvoiceTriggerTime.DEACTIVATED  # type: ignore
                        else False
                    ),
                )
            return branch_info
        except GQLApiException as ge:
            logger.warning(ge)
            return RestaurantBranchError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return RestaurantBranchError(
                msg="Error creating supplier restaurant tax info",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="upsertAssignedSupplierRestaurant",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_assigned_supplier_restaurant(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        set_supplier_unit_id: UUID,
    ) -> SupplierRestaurantAssignationResult:  # type: ignore
        logger.info("Assigned supplier restaurant")
        fb_id = info.context["request"].user.firebase_user.firebase_id
        # instantiate handler
        try:
            # instantiate handler
            _handler = SupplierRestaurantsHandler(
                supplier_restaurants_repo=SupplierRestaurantsRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
                restaurant_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
                category_repo=CategoryRepository(info),
                restaurant_branch_category_repo=RestaurantBranchCategoryRepository(
                    info
                ),
                product_repo=ProductRepository(info),
                supplier_product_repo=SupplierProductRepository(info),
                supplier_product_price_repo=SupplierProductPriceRepository(info),
            )
            # call validation
            if not restaurant_branch_id or not (set_supplier_unit_id):
                return RestaurantBranchError(
                    msg="Empty values for assigned Supplier Restaurant",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # call handler
            return await _handler.assigned_supplier_restaurant(
                fb_id,
                restaurant_branch_id,
                set_supplier_unit_id,
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierRestaurantError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierRestaurantError(
                msg="Error creating supplier restaurant tax info",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class SupplierRestaurantsQuery:
    @strawberry.field(
        name="getSupplierRestaurants",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_restaurants(
        self,
        info: StrawberryInfo,
        supplier_unit_ids: List[UUID],
    ) -> List[SupplierRestaurantCreationResult]:  # type: ignore
        """Get supplier restaurants from given supplier_units

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_ids : List[UUID]

        Returns
        -------
        List[SupplierRestaurantCreationResult]
        """
        logger.info("Get supplier restaurants")
        # instantiate handler
        _handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            product_repo=ProductRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call validation
            res_sup = await _handler.find_supplier_restaurants(
                supplier_unit_ids=supplier_unit_ids,
                firebase_id=fb_id,
            )
            return res_sup
        except GQLApiException as ge:
            logger.warning(ge)
            return [SupplierRestaurantError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                SupplierRestaurantError(
                    msg="Error fetching supplier restaurants",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getSupplierRestaurantProducts",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_restaurant_products(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
    ) -> SupplierRestaurantCreationResult:  # type: ignore
        """Get supplier restaurant' products with prices

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_ids : List[UUID]

        Returns
        -------
        List[SupplierRestaurantCreationResult]
        """
        logger.info("Get supplier restaurant' products")
        # instantiate handler
        _handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            product_repo=ProductRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
            supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        sup_biz_handler = SupplierBusinessHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            supplier_business_account_repo=SupplierBusinessAccountRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        sup_unit_handler = SupplierUnitHandler(
            supplier_unit_repo=SupplierUnitRepository(info),
            unit_category_repo=SupplierUnitCategoryRepository(info),
            supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
            core_user_repo=CoreUserRepository(info),
            tax_info_repo=MxSatCertificateRepository(info),
        )
        _ecomerce_seller_handler = EcommerceSellerHandler(
            ecommerce_seller_repo=EcommerceSellerRepository(info),
            supplier_business_handler=sup_biz_handler,
            supplier_unit_handler=sup_unit_handler,
        )
        # instance handlers
        res_biz_handler = RestaurantBusinessHandler(
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
        )
        rest_br_handler = RestaurantBranchHandler(
            restaurant_branch_repo=RestaurantBranchRepository(info),
            branch_category_repo=RestaurantBranchCategoryRepository(info),
        )
        ecommerce_user_handler = B2BEcommerceUserHandler(
            authos_ecommerce_user_repo=EcommerceUserRepository(info),
            ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                info
            ),
            restaurant_business_handler=res_biz_handler,
            restaurant_branch_handler=rest_br_handler,
        )

        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call validation
            res_sup = await _handler.find_supplier_restaurant_products(
                fb_id,
                supplier_unit_id=supplier_unit_id,
                restaurant_branch_id=restaurant_branch_id,
            )
            if res_sup.restaurant_business and res_sup.restaurant_business.id:
                ecommerce_user_relation = None
                ecommerce_seller = None
                supplier_unit = []
                ecommerce_user_relation = await ecommerce_user_handler._fetch_ecommerce_rest_business_relation(
                    restaurant_business_id=res_sup.restaurant_business.id
                )
                if ecommerce_user_relation:
                    supplier_unit = await sup_unit_handler.fetch_supplier_units(
                        supplier_unit_id=res_sup.relation.supplier_unit_id
                    )
                if len(supplier_unit) > 0:
                    ecommerce_seller = (
                        await _ecomerce_seller_handler.fetch_ecommerce_seller(
                            "supplier_business_id",
                            supplier_unit[0].supplier_business_id,
                        )
                    )
                if ecommerce_seller and ecommerce_user_relation:
                    ecommerce_user = await ecommerce_user_handler._fetch_ecomm_user(
                        ecommerce_user_id=ecommerce_user_relation.ecommerce_user_id,
                        ref_secret_key=ecommerce_seller.secret_key,
                    )
                    if ecommerce_user:
                        res_sup.ecommerce_user = ecommerce_user

            return res_sup
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierRestaurantError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierRestaurantError(
                msg="Error fetching supplier restaurants",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="exportClientsFile",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def export_clients_files(
        self,
        info: StrawberryInfo,
        export_format: str,
        type: str,
    ) -> ExportSupplierRestaurantResult:  # type: ignore
        """Endpoint to retrieve product type

        Parameters
        ----------
        info : StrawberryInfo
        export_format: str
            Export format (csv or xlsx)

        Returns
        -------
        ExportSupplierRestaurantGQL
        """
        logger.info("Export client file")
        # validate format
        if export_format.lower() not in ["csv", "xlsx"]:
            return SupplierRestaurantError(
                msg="Invalid format",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        if type not in ["clients"]:
            return SupplierRestaurantError(
                msg="Invalid type",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        supplier_product_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
        )
        # instantiate handler MxInvoice
        _handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_handler=supplier_product_handler,
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
            mx_sat_cer_repo=MxSatCertificateRepository(info)
        )
        try:
            file_name = ""
            if type == "clients":
                firebase_id = info.context["request"].user.firebase_user.firebase_id
                # call handler to get products
                clients = await _handler.get_clients_to_export(firebase_id=firebase_id)
                _df = pd.DataFrame(clients)
                file_name = "clientes"

            # export
            if _df.empty:
                return SupplierRestaurantError(
                    msg="empty data",
                    code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                )
            if export_format == "csv":
                in_memory_csv = StringIO()
                _df.to_csv(in_memory_csv, index=False)
                in_memory_csv.seek(0)
                return ExportSupplierRestaurantGQL(
                    file=json.dumps(
                        {
                            "filename": f"{file_name}_{datetime.datetime.utcnow().date().isoformat()}.csv",
                            "mimetype": "text/csv",
                            "content": base64.b64encode(
                                in_memory_csv.read().encode("utf-8")
                            ).decode(),
                        }
                    ),
                    extension="csv",
                )
            elif export_format == "xlsx":
                in_memory_xlsx = BytesIO()
                _df.to_excel(in_memory_xlsx, index=False)
                in_memory_xlsx.seek(0)
                return ExportSupplierRestaurantGQL(
                    file=json.dumps(
                        {
                            "filename": f"{file_name}_{datetime.datetime.utcnow().date().isoformat()}.xlsx",
                            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "content": base64.b64encode(in_memory_xlsx.read()).decode(),
                        }
                    ),
                    extension="xlsx",
                )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierRestaurantError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return SupplierRestaurantError(
                msg="Error retrieving clients",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
