from datetime import date, datetime
from types import NoneType
from typing import List, Optional
from uuid import UUID
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import ImageType
from gqlapi.domain.interfaces.v2.authos.ecommerce_user import (
    EcommerceUserError,
    EcommerceUserGQLResult,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchContactInfo,
)

from gqlapi.handlers.integrations.integrations import IntegrationsWebhookandler
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
import strawberry
from starlette.background import BackgroundTasks
from strawberry.types import Info as StrawberryInfo
from strawberry.file_uploads import Upload

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    B2BEcommerceOrdenDetailsResult,
    B2BEcommerceOrdenesResult,
    B2BEcommerceUserError,
    B2BEcommerceUserResult,
    EcommerceSellerBusinessResult,
    EcommerceSellerCatalogResult,
    EcommerceSellerError,
    EcommerceSellerImageResult,
    EcommerceSellerImageStatus,
    EcommerceSellerUnitMsgResult,
    EcommerceSellerResult,
    EcommerceSellerUrlResult,
)
from gqlapi.domain.models.v2.utils import (
    CFDIUse,
    DeliveryTimeWindow,
    OrdenStatusType,
    OrdenType,
    PayMethodType,
    PayStatusType,
    RegimenSat,
    SellingOption,
)
from gqlapi.domain.interfaces.v2.orden.orden import (
    CartProductInput,
    DeliveryTimeWindowInput,
    OrdenError,
    OrdenResult,
)
from gqlapi.domain.models.v2.core import CartProduct
from gqlapi.handlers.core.orden import OrdenHandler, OrdenHookListener
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
    SupplierProductStockRepository,
)
from gqlapi.utils.domain_mapper import domain_inp_to_out
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.b2bcommerce.ecommerce_seller import EcommerceSellerHandler
from gqlapi.handlers.b2bcommerce.ecommerce_user import B2BEcommerceUserHandler
from gqlapi.handlers.restaurant.restaurant_branch import RestaurantBranchHandler
from gqlapi.handlers.restaurant.restaurant_business import RestaurantBusinessHandler
from gqlapi.handlers.services.authos import (
    EcommerceSessionHandler,
)
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
from gqlapi.repository.b2bcommerce.ecommerce_seller import (
    EcommerceSellerRepository,
    EcommerceUserRestaurantRelationRepository,
)
from gqlapi.repository.core.category import (
    CategoryRepository,
    RestaurantBranchCategoryRepository,
    SupplierUnitCategoryRepository,
)
from gqlapi.repository.core.invoice import (
    MxInvoiceRepository,
    MxSatCertificateRepository,
)
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.services.authos import (
    EcommerceUserRepository,
    UserSessionRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.authos import serialize_request_headers
from gqlapi.app.permissions import (
    IsAlimaSupplyAuthorized,
    IsAuthenticated,
    IsB2BEcommerceUserAuthorized,
)

# logger
logger = get_logger(get_app())


class B2BEcommerceUserUtility:
    @staticmethod
    async def get_ecommerce_user_id_from_authos_token(
        info: StrawberryInfo,
        session_token: str,
        ref_secret_key: str,
    ) -> UUID | NoneType:
        # session handlers
        usess_handler = EcommerceSessionHandler(
            user_session_repo=UserSessionRepository(info)
        )
        # get session token
        ecomm_sess = await usess_handler.get_session_token(
            session_token, {}, ref_secret_key
        )
        return ecomm_sess.ecommerce_user_id


# ---------------------------------------------------------------
# Query
# ---------------------------------------------------------------


@strawberry.type
class B2BEcommerceUserQuery:
    @strawberry.field(
        name="getEcommerceClientInfo", permission_classes=[IsB2BEcommerceUserAuthorized]
    )
    async def get_b2becommerce_client_info(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
    ) -> B2BEcommerceUserResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] Get ecommerce client info")
        # authos token
        sdata = await serialize_request_headers(info.context["request"])
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        if not token:
            return B2BEcommerceUserError(
                msg="Invalid authos token not found",
                code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        try:
            # instance handlers
            res_biz_handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            rest_br_handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
            )
            _handler = B2BEcommerceUserHandler(
                authos_ecommerce_user_repo=EcommerceUserRepository(info),
                ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                    info
                ),
                restaurant_business_handler=res_biz_handler,
                restaurant_branch_handler=rest_br_handler,
            )
            # fetch ecommerce_user_id
            ecom_user = (
                await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
            )
            if not ecom_user:
                return B2BEcommerceUserError(
                    msg="Invalid ecommerce user id",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # get user info
            resp_uinfo = await _handler.get_b2becommerce_client_info(
                ecommerce_user_id=ecom_user,
                ref_secret_key=ref_secret_key,
            )
            return resp_uinfo
        except GQLApiException as ge:
            logger.warning(ge)
            return B2BEcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return B2BEcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getEcommerceOrdenes",
        permission_classes=[IsB2BEcommerceUserAuthorized],
    )
    async def get_b2bcommerce_ordenes(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> B2BEcommerceOrdenesResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] Get ecommerce orden history info")
        # authos token
        sdata = await serialize_request_headers(info.context["request"])
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        if not token:
            return B2BEcommerceUserError(
                msg="Invalid authos token not found",
                code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        try:
            # instance handlers
            res_biz_handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            rest_br_handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
            )
            ord_handler = OrdenHandler(
                orden_repo=OrdenRepository(info),
                orden_det_repo=OrdenDetailsRepository(info),
                orden_status_repo=OrdenStatusRepository(info),
                orden_payment_repo=OrdenPaymentStatusRepository(info),
                cart_prod_repo=CartProductRepository(info),
                supp_bus_repo=SupplierBusinessRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
                rest_branc_repo=RestaurantBranchRepository(info),
            )
            mxinv_handler = MxInvoiceHandler(
                mx_invoice_repository=MxInvoiceRepository(info),
                orden_details_repo=OrdenDetailsRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                restaurant_branch_repo=RestaurantBranchRepository(info),
            )
            _handler = B2BEcommerceUserHandler(
                authos_ecommerce_user_repo=EcommerceUserRepository(info),
                ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                    info
                ),
                restaurant_business_handler=res_biz_handler,
                restaurant_branch_handler=rest_br_handler,
                orden_handler=ord_handler,
                mxinvoice_handler=mxinv_handler,
            )
            # fetch ecommerce_user_id
            ecom_user = (
                await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
            )
            if not ecom_user:
                return B2BEcommerceUserError(
                    msg="Invalid ecommerce user id",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # call handler
            _resp = await _handler.get_b2becommerce_historic_ordenes(
                ecommerce_user_id=ecom_user,
                ref_secret_key=ref_secret_key,
                from_date=from_date,
                to_date=to_date,
                page=page,
                page_size=page_size,
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return [B2BEcommerceUserError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                B2BEcommerceUserError(
                    msg="Could not retrieve Ecommerce Historic Ordenes",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getEcommerceOrdenDetails",
        permission_classes=[IsB2BEcommerceUserAuthorized],
    )
    async def get_b2bcommerce_orden_details(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        orden_id: UUID,
    ) -> B2BEcommerceOrdenDetailsResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] Get ecommerce orden details info")
        # authos token
        sdata = await serialize_request_headers(info.context["request"])
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        if not token:
            return B2BEcommerceUserError(
                msg="Invalid authos token not found",
                code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        try:
            # instance handlers
            res_biz_handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            rest_br_handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
            )
            ord_handler = OrdenHandler(
                orden_repo=OrdenRepository(info),
                orden_det_repo=OrdenDetailsRepository(info),
                orden_status_repo=OrdenStatusRepository(info),
                orden_payment_repo=OrdenPaymentStatusRepository(info),
                cart_prod_repo=CartProductRepository(info),
                supp_bus_repo=SupplierBusinessRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
                rest_branc_repo=RestaurantBranchRepository(info),
            )
            mxinv_handler = MxInvoiceHandler(
                mx_invoice_repository=MxInvoiceRepository(info),
                orden_details_repo=OrdenDetailsRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                restaurant_branch_repo=RestaurantBranchRepository(info),
            )
            _handler = B2BEcommerceUserHandler(
                authos_ecommerce_user_repo=EcommerceUserRepository(info),
                ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                    info
                ),
                restaurant_business_handler=res_biz_handler,
                restaurant_branch_handler=rest_br_handler,
                orden_handler=ord_handler,
                mxinvoice_handler=mxinv_handler,
            )
            # fetch ecommerce_user_id
            ecom_user = (
                await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
            )
            if not ecom_user:
                return B2BEcommerceUserError(
                    msg="Invalid ecommerce user id",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # call handler
            _resp = await _handler.get_b2becommerce_orden_details(
                ecommerce_user_id=ecom_user,
                ref_secret_key=ref_secret_key,
                orden_id=orden_id,
            )
            # get restaurant branch
            _br = await rest_br_handler.fetch_restaurant_branches(
                restaurant_branch_id=_resp.orden.details.restaurant_branch_id  # type: ignore
            )
            _resp.orden.branch = _br[0]
            # get restaurant business for contact info
            _biz = await res_biz_handler.fetch_restaurant_business(
                _resp.orden.branch.restaurant_business_id
            )
            _resp.orden.branch.contact_info = RestaurantBranchContactInfo(
                business_name=_biz.name,
                display_name=_biz.account.legal_rep_name if _biz.account else "",
                email=_biz.account.email if _biz.account else "",
                phone_number=_biz.account.phone_number if _biz.account else "",
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return B2BEcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return B2BEcommerceUserError(
                msg="Could not retrieve Ecommerce Orden Details",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class B2BEcommerceSellerQuery:
    @strawberry.field(
        name="getEcommerceSellerInfo",
    )
    async def get_b2becommerce_seller_info(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
    ) -> EcommerceSellerResult:  # type: ignore
        (f"[b2bcommerce:{ref_secret_key}] Get ecommerce seller info")
        try:
            # instance handlers
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
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
            )
            # get seller info
            resp_sinfo = await _handler.fetch_seller_info(
                ref_secret_key=ref_secret_key,
            )
            return resp_sinfo
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getEcommerceSellerInfoByToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_b2becommerce_seller_info_by_token(
        self,
        info: StrawberryInfo,
    ) -> EcommerceSellerBusinessResult:  # type: ignore
        ("[b2bcommerce:Get ecommerce seller info")
        try:
            # instance handlers
            sup_biz_handler = SupplierBusinessHandler(
                supplier_business_repo=SupplierBusinessRepository(info),
                supplier_business_account_repo=SupplierBusinessAccountRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            )
            sup_unit_handler = SupplierUnitHandler(
                supplier_unit_repo=SupplierUnitRepository(info),
                unit_category_repo=SupplierUnitCategoryRepository(info),
                supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
                core_user_repo=CoreUserRepository(info),
                tax_info_repo=MxSatCertificateRepository(info),
            )
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
            )
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # get supplier business info by token
            resp_binfo = await _handler.supplier_business_handler.fetch_supplier_business_by_firebase_id(
                fb_id
            )
            # get seller info
            resp_sinfo = await _handler.fetch_ecommerce_seller(
                id_key="supplier_business_id",
                id_value=resp_binfo.id,
            )
            return resp_sinfo
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getEcommerceSellerCatalog",
    )
    async def get_b2becommerce_seller_catalog(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        supplier_unit_id: UUID,
        search: Optional[str] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> EcommerceSellerCatalogResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] Get ecommerce seller catalog")
        # default_values
        _page = page if page is not None else 1
        _page_size = page_size if page_size is not None else 10
        _search = search if search is not None else ""
        # authos token
        sdata = await serialize_request_headers(info.context["request"])
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        try:
            # instance handlers
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
            sup_res_assign_handler = SupplierRestaurantsHandler(
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
                supplier_product_stock_repo=SupplierProductStockRepository(info),
            )
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
                supplier_restaurant_assign_handler=sup_res_assign_handler,
                restaurant_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            if token:
                ecomm_user_id = await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
                # if ecommerce user exists and branch id is provided, get custom catalog
                if ecomm_user_id and restaurant_branch_id:
                    spec_catalog = await _handler.fetch_seller_spec_catalog_info(
                        supplier_unit_id=supplier_unit_id,
                        restaurant_branch_id=restaurant_branch_id,
                        search=_search,
                        page=_page,
                        page_size=_page_size,
                    )
                    logger.info("Ecommerce: Returning user specific catalog")
                    return spec_catalog
            # get default catalog
            def_catalog = await _handler.fetch_seller_default_catalog_info(
                supplier_unit_id=supplier_unit_id,
                search=_search,
                page=_page,
                page_size=_page_size,
            )
            logger.info("Ecommerce: Returning generic catalog")
            return def_catalog
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getEcommerceSellerProductDetails",
    )
    async def get_b2becommerce_seller_product_details(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        supplier_unit_id: UUID,
        supplier_product_id: UUID,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> EcommerceSellerCatalogResult:  # type: ignore
        logger.info(
            f"[b2bcommerce:{ref_secret_key}] Get ecommerce seller product details"
        )
        # authos token
        sdata = await serialize_request_headers(info.context["request"])
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        try:
            # instance handlers
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
            sup_res_assign_handler = SupplierRestaurantsHandler(
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
                supplier_product_stock_repo=SupplierProductStockRepository(info),
            )
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
                supplier_restaurant_assign_handler=sup_res_assign_handler,
                restaurant_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            if token:
                ecomm_user_id = await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
                # if ecommerce user exists and branch id is provided, get custom catalog
                if ecomm_user_id and restaurant_branch_id:
                    spec_catalog = await _handler.fetch_seller_spec_product_details(
                        supplier_unit_id=supplier_unit_id,
                        restaurant_branch_id=restaurant_branch_id,
                        supplier_product_id=supplier_product_id,
                    )
                    return spec_catalog
            # get default catalog
            def_catalog = await _handler.fetch_seller_default_product_details(
                supplier_unit_id=supplier_unit_id,
                supplier_product_id=supplier_product_id,
            )
            return def_catalog
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getCorrespondentEcommerceSellerUnit",
        permission_classes=[IsB2BEcommerceUserAuthorized],
    )
    async def get_assign_correspondent_ecommerce_seller_unit(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        restaurant_branch_id: UUID,
    ) -> EcommerceSellerUnitMsgResult:  # type: ignore
        logger.info(
            f"[b2bcommerce:{ref_secret_key}] Get ecommerce correspondent seller unit msg"
        )
        try:
            # instance handlers
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
            sup_res_assign_handler = SupplierRestaurantsHandler(
                supplier_restaurants_repo=SupplierRestaurantsRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
                restaurant_branch_repo=RestaurantBranchRepository(info),
            )
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
                supplier_restaurant_assign_handler=sup_res_assign_handler,
                restaurant_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            # get unit info
            resp_su_info = await _handler.get_assigned_seller_unit(
                ref_secret_key=ref_secret_key, restaurant_branch_id=restaurant_branch_id
            )
            return resp_su_info
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getPublicSellerUrlInfo",
    )
    async def get_public_seller_url(
        self,
        info: StrawberryInfo,
    ) -> List[EcommerceSellerUrlResult]:  # type: ignore
        logger.info("[b2bcommerce: Get public seller url")
        # authos token
        try:
            # instance handlers
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
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
            )

            supp_info = await _handler.fetch_public_supplier_business_ecommerce_url()
            return supp_info
        except GQLApiException as ge:
            logger.warning(ge)
            return [EcommerceSellerError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                EcommerceSellerError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]


# ---------------------------------------------------------------
# Mutation
# ---------------------------------------------------------------


@strawberry.type
class B2BEcommerceUserMutation:
    @strawberry.mutation(
        name="addEcommerceClientAddress",
        permission_classes=[IsB2BEcommerceUserAuthorized],
    )
    async def post_b2b_ecommerce_add_address(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        category_id: Optional[UUID] = None,
        internal_num: str = "",
        # optional tax info
        mx_sat_id: Optional[str] = None,
        tax_email: Optional[str] = None,
        legal_name: Optional[str] = None,
        tax_full_address: Optional[str] = None,
        tax_zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
    ) -> B2BEcommerceUserResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] Add address for ecommerce user")
        # data validation
        # call validation
        if (
            not branch_name
            or not full_address
            or not street
            or not external_num
            or not zip_code
            or not neighborhood
            or not city
            or not state
            or not country
        ):
            return B2BEcommerceUserError(
                msg="Empty values for creating Ecomerce User address",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # serialized data
        sdata = await serialize_request_headers(info.context["request"])
        # authos token
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        if not token:
            return B2BEcommerceUserError(
                msg="Invalid authos token not found",
                code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        try:
            # instance handlers
            res_biz_handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            rest_br_handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
                category_repo=CategoryRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            _handler = B2BEcommerceUserHandler(
                authos_ecommerce_user_repo=EcommerceUserRepository(info),
                ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                    info
                ),
                restaurant_business_handler=res_biz_handler,
                restaurant_branch_handler=rest_br_handler,
            )
            # fetch ecommerce_user_id
            ecom_user = (
                await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
            )
            if not ecom_user:
                return B2BEcommerceUserError(
                    msg="Invalid ecommerce user id",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # add address
            resp_user = await _handler.add_b2becommerce_client_address(
                ecommerce_user_id=ecom_user,
                ref_secret_key=ref_secret_key,
                branch_name=branch_name,
                full_address=full_address,
                street=street,
                external_num=external_num,
                internal_num=internal_num,
                neighborhood=neighborhood,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                category_id=category_id,
                # optional tax info
                mx_sat_id=mx_sat_id,
                tax_email=tax_email,
                legal_name=legal_name,
                tax_full_address=tax_full_address,
                tax_zip_code=tax_zip_code,
                sat_regime=sat_regime,
                cfdi_use=cfdi_use,
            )
            return resp_user
        except GQLApiException as ge:
            logger.warning(ge)
            return B2BEcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return B2BEcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="updateEcommerceClientAddress",
        permission_classes=[IsB2BEcommerceUserAuthorized],
    )
    async def patch_b2b_ecommerce_edit_address(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        category_id: Optional[UUID] = None,
        # optional tax info
        mx_sat_id: Optional[str] = None,
        tax_email: Optional[str] = None,
        legal_name: Optional[str] = None,
        tax_full_address: Optional[str] = None,
        tax_zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
    ) -> B2BEcommerceUserResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] Edit address for ecommerce user")
        # serialized data
        sdata = await serialize_request_headers(info.context["request"])
        # authos token
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        if not token:
            return B2BEcommerceUserError(
                msg="Invalid authos token not found",
                code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        try:
            # instance handlers
            res_biz_handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            rest_br_handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
                category_repo=CategoryRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            _handler = B2BEcommerceUserHandler(
                authos_ecommerce_user_repo=EcommerceUserRepository(info),
                ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                    info
                ),
                restaurant_business_handler=res_biz_handler,
                restaurant_branch_handler=rest_br_handler,
            )
            # fetch ecommerce_user_id
            ecom_user = (
                await B2BEcommerceUserUtility.get_ecommerce_user_id_from_authos_token(
                    info, token, ref_secret_key
                )
            )
            if not ecom_user:
                return B2BEcommerceUserError(
                    msg="Invalid ecommerce user id",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # add address
            resp_user = await _handler.edit_b2becommerce_client_address(
                ecommerce_user_id=ecom_user,
                ref_secret_key=ref_secret_key,
                restaurant_branch_id=restaurant_branch_id,
                branch_name=branch_name,
                full_address=full_address,
                street=street,
                external_num=external_num,
                internal_num=internal_num,
                neighborhood=neighborhood,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                category_id=category_id,
                # optional tax info
                mx_sat_id=mx_sat_id,
                tax_email=tax_email,
                legal_name=legal_name,
                tax_full_address=tax_full_address,
                tax_zip_code=tax_zip_code,
                sat_regime=sat_regime,
                cfdi_use=cfdi_use,
            )
            return resp_user
        except GQLApiException as ge:
            logger.warning(ge)
            return B2BEcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return B2BEcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="newEcommerceOrden",
        permission_classes=[IsB2BEcommerceUserAuthorized],
    )
    async def post_new_ecommerce_orden(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        restaurant_branch_id: UUID,
        supplier_unit_id: UUID,
        cart_products: List[CartProductInput],
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindowInput] = None,
        delivery_type: Optional[SellingOption] = SellingOption.SCHEDULED_DELIVERY,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenResult:  # type: ignore
        logger.info(f"[b2bcommerce:{ref_secret_key}] New orden for ecommerce user")
        # call validation
        if (
            not status
            or not restaurant_branch_id
            or not cart_products
            or not delivery_time
            or not delivery_date
            or not paystatus
            or not payment_method
        ):
            logger.warning("Empty values for creating Orden")
            return OrdenError(
                msg="Empty values for creating Order",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # delivery time
            if delivery_time:
                delivery_time_out = DeliveryTimeWindow(
                    **domain_inp_to_out(delivery_time, DeliveryTimeWindow)
                )
            else:
                delivery_time_out = delivery_time
            # cart products
            cart_products_out = []
            for cp in cart_products:
                if cp.quantity > 0.0009:
                    cart_products_out.append(
                        CartProduct(**domain_inp_to_out(cp, CartProduct))
                    )
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)

        # serialized data
        sdata = await serialize_request_headers(info.context["request"])
        token_hdr = sdata.get("authorization", None)
        token = token_hdr.split(" ")[-1] if token_hdr else None
        if not token:
            return B2BEcommerceUserError(
                msg="Invalid authos token not found",
                code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )

        # instantiate handler
        orden_handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            cart_repo=CartRepository(info),
            cart_prod_repo=CartProductRepository(info),
            rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            rest_business_repo=RestaurantBusinessRepository(info),
        )
        weebhook_handler = IntegrationsWebhookandler(
            repo=IntegrationWebhookRepository(info)
        )
        try:
            orden_type = OrdenType.NORMAL
            # call handler
            _resp = await orden_handler.new_orden_ecommerce(
                orden_type,
                restaurant_branch_id,
                cart_products_out,
                supplier_unit_id,
                status,
                comments,
                payment_method,
                paystatus,
                delivery_date,
                delivery_time_out,
                delivery_type,
                approved_by,
                discount_code,
                cashback_transation_id,
                shipping_cost,
                packaging_cost,
                service_fee,
            )
            # add background task
            bg_tasks = BackgroundTasks()
            bg_tasks.add_task(
                OrdenHookListener.on_orden_created,
                weebhook_handler,
                _resp.id,
                (
                    _resp.supplier.supplier_business.id
                    if _resp.supplier and _resp.supplier.supplier_business
                    else None
                ),
                _resp.branch.restaurant_business_id if _resp.branch else None,
            )
            info.context["response"].background = bg_tasks
            logger.info("Orden created")
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not create Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="newEcommerceRestaurantUser",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_ecommerce_restaurant_user(
        self, info: StrawberryInfo, restaurant_branch_id: UUID, email: str
    ) -> EcommerceUserGQLResult:  # type: ignore
        # call validation
        if not restaurant_branch_id or not email:
            logger.warning("Empty values for creating Ecommerce Restaurant User")
            return OrdenError(
                msg="Empty values for Ecommerce Restaurant User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # instance handlers
        res_biz_handler = RestaurantBusinessHandler(
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
        )
        rest_br_handler = RestaurantBranchHandler(
            restaurant_branch_repo=RestaurantBranchRepository(info),
            branch_category_repo=RestaurantBranchCategoryRepository(info),
            category_repo=CategoryRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        _handler = B2BEcommerceUserHandler(
            authos_ecommerce_user_repo=EcommerceUserRepository(info),
            ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                info
            ),
            restaurant_business_handler=res_biz_handler,
            restaurant_branch_handler=rest_br_handler,
            ecomerce_seller_repo=EcommerceSellerRepository(info),
            supplier_restaurant_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
        )

        try:
            # call handler
            _resp = await _handler.new_ecommerce_restaurant_user(
                restaurant_branch_id, email
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceUserError(
                msg="Could not create Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="editEcommerceRestaurantUser",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_edit_ecommerce_restaurant_user(
        self, info: StrawberryInfo, restaurant_branch_id: UUID, email: str
    ) -> EcommerceUserGQLResult:  # type: ignore
        # call validation
        if not restaurant_branch_id or not email:
            logger.warning("Empty values for creating Ecommerce Restaurant User")
            return OrdenError(
                msg="Empty values for Ecommerce Restaurant User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # instance handlers
        res_biz_handler = RestaurantBusinessHandler(
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
        )
        rest_br_handler = RestaurantBranchHandler(
            restaurant_branch_repo=RestaurantBranchRepository(info),
            branch_category_repo=RestaurantBranchCategoryRepository(info),
            category_repo=CategoryRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        _handler = B2BEcommerceUserHandler(
            authos_ecommerce_user_repo=EcommerceUserRepository(info),
            ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                info
            ),
            restaurant_business_handler=res_biz_handler,
            restaurant_branch_handler=rest_br_handler,
            ecomerce_seller_repo=EcommerceSellerRepository(info),
            supplier_restaurant_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
        )

        try:
            # call handler
            _resp = await _handler.edit_ecommerce_restaurant_user(
                restaurant_branch_id, email
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceUserError(
                msg="Could not create Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class B2BEcommerceSellerMutation:
    @strawberry.mutation(
        name="updateEcommerceSellerInfo",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_update_b2b_ecommerce_params(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        seller_name: Optional[str] = None,
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
    ) -> EcommerceSellerBusinessResult:  # type: ignore
        logger.info(f"[b2bcommerce:{str(supplier_business_id)}] Edit params")
        # data validation
        # call validation
        if not supplier_business_id:
            return EcommerceSellerError(
                msg="Empty values for creating Ecomerce User address",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # serialized data
        if (
            seller_name is None
            and banner_img_href is None
            and categories is None
            and rec_prods is None
            and styles_json is None
            and shipping_enabled is None
            and shipping_rule_verified_by is None
            and shipping_threshold is None
            and shipping_cost is None
            and search_placeholder is None
            and footer_msg is None
            and footer_cta is None
            and footer_phone is None
            and footer_is_wa is None
            and footer_email is None
            and seo_description is None
            and seo_keywords is None
            and default_supplier_unit_id is None
            and commerce_display is None
            and account_active is None
            and currency is None
        ):
            return EcommerceSellerError(
                msg="Empty values for update Ecomerce seller",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # instance handlers
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
            _handler = EcommerceSellerHandler(
                ecommerce_seller_repo=EcommerceSellerRepository(info),
                supplier_business_handler=sup_biz_handler,
                supplier_unit_handler=sup_unit_handler,
            )
            resp_user = await _handler.update_ecommerce_seller_params(
                supplier_business_id=supplier_business_id,
                seller_name=seller_name,
                banner_img_href=banner_img_href,
                categories=categories,
                rec_prods=rec_prods,
                styles_json=styles_json,
                shipping_enabled=shipping_enabled,
                shipping_rule_verified_by=shipping_rule_verified_by,
                shipping_threshold=shipping_threshold,
                shipping_cost=shipping_cost,
                search_placeholder=search_placeholder,
                footer_msg=footer_msg,
                footer_cta=footer_cta,
                footer_phone=footer_phone,
                footer_is_wa=footer_is_wa,
                footer_email=footer_email,
                seo_description=seo_description,
                seo_keywords=seo_keywords,
                default_supplier_unit_id=default_supplier_unit_id,
                commerce_display=commerce_display,
                account_active=account_active,
                currency=currency,
            )
            return resp_user
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="addEcommerceSellerImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_add_ecommerce_seller_image(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        img_file: Upload,
        image_type: ImageType,
    ) -> EcommerceSellerImageResult:  # type: ignore
        logger.info("Edit seller info image")
        # data validation
        if not img_file or not supplier_business_id or not image_type:
            return EcommerceSellerError(
                msg="Nothing add seller image",
                code=GQLApiErrorCodeType.EMPTY_DATA.value,
            )
        # instantiate handler
        # instance handlers
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
        _handler = EcommerceSellerHandler(
            ecommerce_seller_repo=EcommerceSellerRepository(info),
            supplier_business_handler=sup_biz_handler,
            supplier_unit_handler=sup_unit_handler,
        )
        try:
            # call validation
            result = await _handler.patch_add_ecommerce_seller_image(
                supplier_business_id, img_file, image_type.value
            )
            return EcommerceSellerImageStatus(
                msg="Upload supplier business image", status=result
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="deleteEcommerceSellerImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def delete_ecommerce_seller_image(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        image_type: ImageType,
    ) -> EcommerceSellerImageResult:  # type: ignore
        logger.info("Edit seller info image")
        # data validation
        if not supplier_business_id or not image_type:
            return EcommerceSellerError(
                msg="Nothing add seller image",
                code=GQLApiErrorCodeType.EMPTY_DATA.value,
            )
        # instantiate handler
        # instance handlers
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
        _handler = EcommerceSellerHandler(
            ecommerce_seller_repo=EcommerceSellerRepository(info),
            supplier_business_handler=sup_biz_handler,
            supplier_unit_handler=sup_unit_handler,
        )
        try:
            # call validation
            result = await _handler.patch_delete_ecommerce_seller_image(
                supplier_business_id, image_type.value
            )
            return EcommerceSellerImageStatus(
                msg="Upload supplier business image", status=result
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSellerError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSellerError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )
