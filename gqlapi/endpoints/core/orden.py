import base64
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
import json
from typing import Optional, List
from uuid import UUID
import uuid
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import INVOICE_PAYMENT_MAP
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.handlers.integrations.integrations import IntegrationsWebhookandler
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
from gqlapi.utils.helpers import serialize_encoded_file
from gqlapi.utils.notifications import send_supplier_whatsapp_invoice_reminder
from gqlapi.lib.logger.logger.basic_logger import get_logger

import pandas as pd
import strawberry
from strawberry.types import Info as StrawberryInfo
from starlette.background import BackgroundTasks
from strawberry.file_uploads import Upload

from gqlapi.domain.models.v2.supplier import SupplierRestaurantRelation
from gqlapi.handlers.restaurant.restaurant_suppliers import (
    RestaurantSupplierAssignationHandler,
)
from gqlapi.handlers.supplier.supplier_invoice import (
    SupplierInvoiceHandler,
    SupplierInvoiceHookListener,
)
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.models.preorden_optimizer import PreOrdenOptimizer
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.restaurant.restaurant_suppliers import (
    RestaurantSupplierAssignationRepository,
)
from gqlapi.repository.restaurant.restaurant_user import (
    RestaurantUserPermissionRepository,
    RestaurantUserRepository,
)
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
)
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)

from gqlapi.domain.interfaces.v2.orden.orden import (
    CartProductInput,
    DeliveryTimeWindowInput,
    ExportOrdenGQL,
    ExportOrdenResult,
    OrdenError,
    OrdenPaystatusGQL,
    OrdenPaystatusResult,
    OrdenResult,
    OrdenStatusConfirmMsg,
    OrdenStatusExternalResult,
    OrdenStatusResult,
    PaymentAmountInput,
    PaymentReceiptResult,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchContactInfo,
)
from gqlapi.domain.models.v2.core import CartProduct, OrdenDetails, OrdenStatus
from gqlapi.domain.models.v2.utils import (
    CFDIType,
    DataTypeDecoder,
    DeliveryTimeWindow,
    InvoiceType,
    OrdenStatusType,
    OrdenType,
    PayMethodType,
    PayStatusType,
    SellingOption,
)
from gqlapi.app.permissions import (
    IsAlimaRestaurantAuthorized,
    IsAuthenticated,
    IsAlimaSupplyAuthorized,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.invoice import MxInvoiceHandler, MxSatCertificateHandler
from gqlapi.handlers.core.orden import OrdenHandler, OrdenHookListener
from gqlapi.handlers.restaurant.restaurant_branch import RestaurantBranchHandler
from gqlapi.handlers.restaurant.restaurant_business import RestaurantBusinessHandler
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.category import (
    CategoryRepository,
    RestaurantBranchCategoryRepository,
    SupplierUnitCategoryRepository,
)
from gqlapi.repository.core.invoice import (
    MxInvoiceComplementRepository,
    MxInvoiceRepository,
    MxInvoicingExecutionRepository,
    MxSatCertificateRepository,
)

from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.restaurant.restaurant_branch import (
    RestaurantBranchInvoicingOptionsRepository,
    RestaurantBranchRepository,
)
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.domain_mapper import domain_inp_to_out

# logger
logger = get_logger(get_app())


@strawberry.type
class OrdenMutation:
    @strawberry.mutation(
        name="newOrden",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_orden(
        self,
        info: StrawberryInfo,
        orden_type: OrdenType,
        restaurant_branch_id: UUID,
        cart_products: List[CartProductInput],
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindowInput] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenResult:  # type: ignore
        logger.info("Create new orden")
        # call validation
        if not orden_type:
            return OrdenError(
                msg="Empty values for creating Order",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if orden_type == OrdenType.NORMAL:
            if (
                not status
                or not restaurant_branch_id
                or not supplier_business_id
                or not cart_products
                or not delivery_time
                or not delivery_date
                or not paystatus
                or not payment_method
            ):
                return OrdenError(
                    msg="Empty values for creating Order",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        if orden_type == OrdenType.DRAFT:
            if not restaurant_branch_id or not cart_products:
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
            cart_products_out = [
                CartProduct(**domain_inp_to_out(cp, CartProduct))
                for cp in cart_products
            ]
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not update Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

        # instantiate handler
        _handler = OrdenHandler(
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
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_orden(
                orden_type,
                fb_id,
                restaurant_branch_id,
                cart_products_out,
                status,
                supplier_business_id,
                comments,
                payment_method,
                paystatus,
                delivery_date,
                delivery_time_out,
                approved_by,
                discount_code,
                cashback_transation_id,
                shipping_cost,
                packaging_cost,
                service_fee,
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(f"Could not generate new orden: {ge}")
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not create Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="updateOrden",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_orden(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
        orden_type: OrdenType,
        cart_products: Optional[List[CartProductInput]] = None,
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[date] = None,
        delivery_time: Optional[DeliveryTimeWindowInput] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenResult:  # type: ignore
        logger.info("Edit orden")
        # call validation
        if orden_type == OrdenType.NORMAL:
            if not (
                cart_products
                or status
                or comments
                or payment_method
                or paystatus
                or delivery_date
                or delivery_time
                or approved_by
                or discount_code
                or cashback_transation_id
                or shipping_cost
                or packaging_cost
                or service_fee
            ):
                return OrdenError(
                    msg="No values to Update Order",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        if orden_type == OrdenType.DRAFT:
            if not cart_products:
                return OrdenError(
                    msg="No values to Update Order",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        try:
            if delivery_time:
                delivery_time_out = DeliveryTimeWindow(
                    **domain_inp_to_out(delivery_time, DeliveryTimeWindow)
                )
            else:
                delivery_time_out = delivery_time
            # cart products
            if cart_products:
                cart_products_out = [
                    CartProduct(**domain_inp_to_out(cp, CartProduct))
                    for cp in cart_products
                ]
            else:
                cart_products_out = []
        except GQLApiException as ge:
            return OrdenError(msg=ge.msg, code=ge.error_code)
        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            cart_repo=CartRepository(info),
            cart_prod_repo=CartProductRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),
            rest_business_repo=RestaurantBusinessRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.edit_orden(
                fb_id,
                orden_id,
                orden_type,
                cart_products_out,
                status,
                comments,
                payment_method,
                paystatus,
                delivery_date,
                delivery_time_out,
                SellingOption.SCHEDULED_DELIVERY,
                approved_by,
                discount_code,
                cashback_transation_id,
                shipping_cost,
                packaging_cost,
                service_fee,
            )
            # implement bg routine - to trigger factura
            if status in [
                OrdenStatusType.DELIVERED,
            ]:
                if (
                    not _resp.supplier
                    or not _resp.supplier.supplier_business_account
                    or not _resp.supplier.supplier_business_account.phone_number
                    or not _resp.supplier.supplier_business
                    or not _resp.details
                    or not _resp.branch
                ):
                    logger.warning(
                        "Could not send whatsapp reminder, missing supplier business account"
                    )
                else:
                    bg_tasks = BackgroundTasks()
                    bg_tasks.add_task(
                        send_supplier_whatsapp_invoice_reminder,
                        {
                            "phone": _resp.supplier.supplier_business_account.phone_number,
                            "name": _resp.supplier.supplier_business.name,
                        },
                        _resp.details,
                        _resp.branch.branch_name,
                    )
                    info.context["response"].background = bg_tasks
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not update Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="newOrdenMarketplace",
        permission_classes=[IsAuthenticated],
    )
    async def post_new_orden_marketplace(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        cart_products: List[CartProductInput],
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
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
        logger.info("Create new orden marketplace")
        # call validation
        if (
            not status
            or not restaurant_branch_id
            or not supplier_business_id
            or not cart_products
            or not delivery_time
            or not delivery_date
            or not paystatus
            or not payment_method
        ):
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
            return OrdenError(msg=ge.msg, code=ge.error_code)

        # instantiate handler
        _handler = OrdenHandler(
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
        srs_handler = SupplierRestaurantsHandler(
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
        rsr_handler = RestaurantSupplierAssignationHandler(
            rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
            rest_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
        )
        weebhook_handler = IntegrationsWebhookandler(
            repo=IntegrationWebhookRepository(info)
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            orden_type = OrdenType.NORMAL
            # call handler
            _resp = await _handler.new_orden_marketplace(
                orden_type,
                fb_id,
                restaurant_branch_id,
                cart_products_out,
                supplier_unit_id,
                status,
                supplier_business_id,
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
            # create supplier restaurant relation
            try:
                srels = await srs_handler.search_supplier_business_restaurant(
                    supplier_business_id, restaurant_branch_id=restaurant_branch_id
                )
                srel_exists = False
                if len(srels) > 0:
                    for _srel in srels:
                        if _srel.supplier_unit_id == supplier_unit_id:
                            srel_exists = True
                            break
                if not srel_exists:
                    # if relation doesnt exist -> create it
                    sr_rel = SupplierRestaurantRelation(
                        id=uuid.uuid4(),
                        supplier_unit_id=_resp.details.supplier_unit_id,  # type: ignore (safe)
                        restaurant_branch_id=restaurant_branch_id,
                        approved=False,
                        priority=1,
                        created_by=_resp.details.created_by,  # type: ignore (safe)
                    )
                    if not await srs_handler.supplier_restaurants_repo.add(sr_rel):
                        raise Exception("Issues inserting supplier restaurant relation")
            except Exception as e:
                logger.warning("Could not create supplier restaurant relation")
                logger.error(e)
            # create restaurant supplier relation
            try:
                if not _resp.branch or not _resp.branch.restaurant_business_id:
                    logger.warning(
                        "Could not create restaurant supplier relation, missing restaurant business"
                    )
                else:
                    rrels = await rsr_handler.search_restaurant_business_supplier(
                        restaurant_business_id=_resp.branch.restaurant_business_id,
                        supplier_unit_id=_resp.details.supplier_unit_id,  # type: ignore (safe)
                    )
                    if (
                        not _resp.supplier
                        or not _resp.supplier.supplier_business
                        or not _resp.supplier.supplier_business.id
                    ):
                        sup_bus_id = None
                    else:
                        sup_bus_id = _resp.supplier.supplier_business.id
                    rrel_exists = False
                    if len(rrels) > 0 and sup_bus_id:
                        for _rrel in rrels:
                            if _rrel.supplier_business_id == sup_bus_id:
                                rrel_exists = True
                                break
                    if not rrel_exists and sup_bus_id:
                        # if relation doesnt exist -> create it
                        await rsr_handler.new_restaurant_supplier_assignation(
                            restaurant_branch_id=restaurant_branch_id,
                            supplier_business_id=sup_bus_id,
                            firebase_id=fb_id,
                        )

            except Exception as e:
                logger.warning("Could not create restaurant supplier relation")
                logger.error(e)

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
                msg="Could not update Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="updateOrdenMarketplace",
        permission_classes=[IsAuthenticated],
    )
    async def patch_edit_orden_marketplace(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
        cart_products: Optional[List[CartProductInput]] = None,
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[date] = None,
        delivery_time: Optional[DeliveryTimeWindowInput] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenResult:  # type: ignore
        logger.info("Edit orden marketplace")
        # call validation
        if not (
            cart_products
            or status
            or comments
            or payment_method
            or paystatus
            or delivery_date
            or delivery_time
            or approved_by
            or discount_code
            or cashback_transation_id
            or shipping_cost
            or packaging_cost
            or service_fee
        ):
            return OrdenError(
                msg="No values to Update Order",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            if delivery_time:
                delivery_time_out = DeliveryTimeWindow(
                    **domain_inp_to_out(delivery_time, DeliveryTimeWindow)
                )
            else:
                delivery_time_out = delivery_time
            # cart products
            if cart_products:
                cart_products_out = [
                    CartProduct(**domain_inp_to_out(cp, CartProduct))
                    for cp in cart_products
                ]
            else:
                cart_products_out = []
        except GQLApiException as ge:
            return OrdenError(msg=ge.msg, code=ge.error_code)
        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            cart_repo=CartRepository(info),
            cart_prod_repo=CartProductRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),
            rest_business_repo=RestaurantBusinessRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        mxi_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        si_handler = SupplierInvoiceHandler(
            orden_handler=_handler,
            mx_invoice_handler=mxi_handler,
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoicing_exec_repo=MxInvoicingExecutionRepository(info),
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
        )
        webhook_handler = IntegrationsWebhookandler(
            repo=IntegrationWebhookRepository(info)
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.edit_orden(
                fb_id,
                orden_id,
                None,  # orden_type
                cart_products_out,
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
            # implement bg routine - to trigger factura
            if status is not None and status in [
                OrdenStatusType.ACCEPTED,
                OrdenStatusType.DELIVERED,
            ]:
                bg_tasks = BackgroundTasks()
                bg_tasks.add_task(
                    SupplierInvoiceHookListener.on_orden_status_changed,
                    si_handler,
                    fb_id,
                    orden_id,
                    status,
                )
                # if status is delivered, trigger event on orden delivered
                if status == OrdenStatusType.DELIVERED:
                    restaurant_branch_repo = RestaurantBranchRepository(info)
                    bg_tasks.add_task(
                        OrdenHookListener.on_orden_delivered,
                        webhook_handler,
                        _handler,
                        restaurant_branch_repo,
                        orden_id,
                        (
                            _resp.supplier.supplier_business.id
                            if _resp.supplier and _resp.supplier.supplier_business
                            else None
                        ),
                    )
                info.context["response"].background = bg_tasks
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not update Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="confirmOrden",
        permission_classes=[],
    )
    async def external_confirm_orden(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
    ) -> OrdenStatusExternalResult:  # type: ignore
        logger.info("Confirm orden")
        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            cart_repo=CartRepository(info),
            cart_prod_repo=CartProductRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),
            rest_business_repo=RestaurantBusinessRepository(info),
        )
        try:
            # call repo
            status_dict = await _handler.orden_status_repo.fetch_last(orden_id)
            alima_bot = await _handler.core_user_repo.fetch_by_email("admin")
            if status_dict:
                curr_st = OrdenStatusType(
                    DataTypeDecoder.get_orden_status_value(status_dict["status"])
                )
                if curr_st.value > OrdenStatusType.ACCEPTED.value:
                    return OrdenStatusConfirmMsg(
                        msg="El pedido ya fue confirmado", status=True
                    )
                if not await _handler.orden_status_repo.add(
                    OrdenStatus(
                        id=uuid.uuid4(),
                        orden_id=orden_id,
                        status=OrdenStatusType.ACCEPTED,
                        created_by=alima_bot.id,  # type: ignore (safe)
                    )
                ):
                    return OrdenStatusConfirmMsg(
                        msg="No se pudo confirmar el pedido", status=False
                    )
                return OrdenStatusConfirmMsg(
                    msg="Pedido confirmado correctamente", status=True
                )
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not update Orden Status",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="addConsolidatedPaymentReceipt",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_add_consolidated_payment_receipt(
        self,
        info: StrawberryInfo,
        ordenes: List[PaymentAmountInput],
        payment_day: Optional[date] = None,
        comments: Optional[str] = None,
        receipt_file: Optional[Upload] = None,
        payment_complement: Optional[bool] = False,
    ) -> OrdenPaystatusResult:  # type: ignore
        logger.info("Add payment receipt")
        # validate input
        orden_ids: List[UUID] = []
        amount_sum: float = 0
        for orden in ordenes:
            if orden.amount <= 0:
                return OrdenError(
                    msg="Payment value must be greater than 0",
                    code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                )
            orden_ids.append(orden.orden_id)
            amount_sum += orden.amount
        # Build a dictionary with id as the key and amount_float as the value
        ordenes_dict = {orden.orden_id: orden.amount for orden in ordenes}
        try:
            rec_file_str = None
            if receipt_file is not None:
                rec_file_str = await serialize_encoded_file(receipt_file)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not read uploaded file",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler MxInvoice
        mx_inv_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
        )
        orden_det_repo = OrdenDetailsRepository(info)
        if payment_complement:
            try:
                ord_details = await orden_det_repo.fetch_last(orden_id=orden_ids[0])
                invoice_type = await mx_inv_handler.get_invoice_type(ord_details["id"])
            except Exception as e:
                logger.error(e)
                return OrdenError(
                    msg="Error to get invoice type",
                    code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                )
            if not invoice_type:
                return OrdenError(
                    msg="This order is not invoiced",
                    code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                )
            if invoice_type == InvoiceType.PUE.value:
                return OrdenError(
                    msg="This order is not avalible to add complement, is PUE",
                    code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
                )

        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=orden_det_repo,
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # instantiate handler MxInvoice
        mxi_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
        )
        try:
            # call handler
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # amount sum
            _resp = await _handler.add_payment_receipt(
                firebase_id=fb_id,
                payment_value=amount_sum,
                comments=comments,
                payment_day=payment_day,
                receipt_file=rec_file_str,
                orden_ids=orden_ids,
            )
            if payment_complement:
                if _resp.ordenes:
                    ord_details = await orden_det_repo.fetch_last(
                        orden_id=_resp.ordenes[0].orden_id
                    )
                    ord_det = OrdenDetails(**ord_details)
                    # call handler to upload invoice
                    await mxi_handler.new_consolidated_customer_invoice_complement(
                        _resp,
                        ord_det,
                        amounts=ordenes_dict,
                        firebase_id=fb_id,
                    )
            # return res_cert
            return OrdenPaystatusGQL(
                pay_receipts=[_resp],
            )

        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not create Payment Receipt",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="editPaymentReceipt",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_payment_receipt(
        self,
        info: StrawberryInfo,
        payment_receipt_id: UUID,
        orden_ids: Optional[List[UUID]] = None,
        payment_value: Optional[float] = None,
        comments: Optional[str] = None,
        payment_day: Optional[date] = None,
        receipt_file: Optional[Upload] = None,
        payment_complement: Optional[bool] = False,
    ) -> OrdenPaystatusResult:  # type: ignore
        logger.info("Edit payment receipt")
        # validate input
        if payment_value is not None and payment_value <= 0:
            return OrdenError(
                msg="Payment value must be greater than 0",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        try:
            rec_file_str = None
            if receipt_file is not None:
                rec_file_str = await serialize_encoded_file(receipt_file)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not read uploaded file",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler
        orden_det_repo = OrdenDetailsRepository(info)
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # instantiate handler MxInvoice
        mx_inv_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
        )
        try:
            # call handler
            fb_id = info.context["request"].user.firebase_user.firebase_id
            _resp = await _handler.edit_payment_receipt(
                firebase_id=fb_id,
                payment_receipt_id=payment_receipt_id,
                payment_value=payment_value,
                comments=comments,
                payment_day=payment_day,
                receipt_file=rec_file_str,
                orden_ids=orden_ids,
            )
            if payment_complement and orden_ids:
                ord_details = await orden_det_repo.fetch_last(orden_id=orden_ids[0])
                if not ord_details:
                    return OrdenError(
                        msg="Could not get order details",
                        code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value
                        )
                ord_details = OrdenDetails(**ord_details)
                invoice_type = await mx_inv_handler.get_invoice_type(ord_details.id)
                if not invoice_type:
                    return OrdenError(
                        msg="This order is not invoiced",
                        code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                    )
                if invoice_type == InvoiceType.PUE.value:
                    return OrdenError(
                        msg="This order is not avalible to add complement, is PUE",
                        code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
                    )
                if _resp.ordenes:
                    if payment_value is None:
                        logger.warning(
                            "Could not create payment complement, missing payment value"
                        )
                    else:
                        # call handler to upload invoice
                        await mx_inv_handler.new_customer_invoice_complement(
                            payment_info=_resp,
                            ord_details=ord_details,
                            amount=payment_value,
                            firebase_id=fb_id,
                        )
            return OrdenPaystatusGQL(
                pay_receipts=[_resp],
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not update Payment Receipt",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="addPaymentReceipt",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_add_payment_receipt(
        self,
        info: StrawberryInfo,
        orden_ids: List[UUID],
        payment_value: float,
        payment_day: Optional[date] = None,
        comments: Optional[str] = None,
        receipt_file: Optional[Upload] = None,
        payment_complement: Optional[bool] = False,
    ) -> OrdenPaystatusResult:  # type: ignore
        logger.info("Add payment receipt")
        # validate input
        if payment_value <= 0:
            return OrdenError(
                msg="Payment value must be greater than 0",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        try:
            rec_file_str = None
            if receipt_file is not None:
                rec_file_str = await serialize_encoded_file(receipt_file)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not read uploaded file",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler MxInvoice
        mx_inv_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
        )
        orden_det_repo = OrdenDetailsRepository(info)
        if payment_complement:
            try:
                ord_details = await orden_det_repo.fetch_last(orden_id=orden_ids[0])
                invoice_type = await mx_inv_handler.get_invoice_type(ord_details["id"])
            except Exception as e:
                logger.error(e)
                return OrdenError(
                    msg="Error to get invoice type",
                    code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                )
            if not invoice_type:
                return OrdenError(
                    msg="This order is not invoiced",
                    code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                )
            if invoice_type == InvoiceType.PUE.value:
                return OrdenError(
                    msg="This order is not avalible to add complement, is PUE",
                    code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
                )

        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=orden_det_repo,
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # instantiate handler MxInvoice
        mxi_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
        )
        try:
            # call handler
            fb_id = info.context["request"].user.firebase_user.firebase_id
            _resp = await _handler.add_payment_receipt(
                firebase_id=fb_id,
                payment_value=payment_value,
                comments=comments,
                payment_day=payment_day,
                receipt_file=rec_file_str,
                orden_ids=orden_ids,
            )
            if payment_complement:
                if _resp.ordenes:
                    ord_details = await orden_det_repo.fetch_last(
                        orden_id=_resp.ordenes[0].orden_id
                    )
                    ord_det = OrdenDetails(**ord_details)
                    # call handler to upload invoice
                    await mxi_handler.new_customer_invoice_complement(
                        _resp,
                        ord_det,
                        amount=payment_value,
                        firebase_id=fb_id,
                    )
            # return res_cert
            return OrdenPaystatusGQL(
                pay_receipts=[_resp],
            )

        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not create Payment Receipt",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="reInvoiceOrder",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_re_invoice_order(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
        cart_products: Optional[List[CartProductInput]] = None,
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[date] = None,
        delivery_time: Optional[DeliveryTimeWindowInput] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenResult:  # type: ignore
        logger.info("Re Invoice Order marketplace")
        # call validation
        if not (
            cart_products
            or status
            or comments
            or payment_method
            or paystatus
            or delivery_date
            or delivery_time
            or approved_by
            or discount_code
            or cashback_transation_id
            or shipping_cost
            or packaging_cost
            or service_fee
        ):
            return OrdenError(
                msg="No values to Update Order",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            if delivery_time:
                delivery_time_out = DeliveryTimeWindow(
                    **domain_inp_to_out(delivery_time, DeliveryTimeWindow)
                )
            else:
                delivery_time_out = delivery_time
            # cart products
            if cart_products:
                cart_products_out = [
                    CartProduct(**domain_inp_to_out(cp, CartProduct))
                    for cp in cart_products
                ]
            else:
                cart_products_out = []
        except GQLApiException as ge:
            return OrdenError(msg=ge.msg, code=ge.error_code)
        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            cart_repo=CartRepository(info),
            cart_prod_repo=CartProductRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            rest_buss_acc_repo=RestaurantBusinessAccountRepository(info),
            rest_business_repo=RestaurantBusinessRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
        )
        mxi_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            orden_repo=OrdenRepository(info),
            cart_product_repo=CartProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            mx_sat_cer_repo=MxSatCertificateRepository(info),
            mx_invoice_complement_repository=MxInvoiceComplementRepository(info),
        )
        # instantiate handler MxInvoice
        _sat_cer_handler = MxSatCertificateHandler(
            mx_sat_certificate_repository=MxSatCertificateRepository(info),
        )
        sup_res_assign_handler = SupplierRestaurantsHandler(
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
            invoicing_options_repo=RestaurantBranchInvoicingOptionsRepository(info),
        )
        try:
            old_orden_det = await _handler.orden_det_repo.fetch_last(orden_id)
            if not old_orden_det:
                raise GQLApiException(
                    msg="issues to find orden details",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                )
            old_orden_det_obj = OrdenDetails(**old_orden_det)
            fb_id = info.context["request"].user.firebase_user.firebase_id
            await mxi_handler.validate_complements_by_orders([orden_id])
            # call handler
            _resp = await _handler.edit_orden(
                fb_id,
                orden_id,
                None,  # orden_type
                cart_products_out,
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
            if (
                _resp.details
                and _resp.details.payment_method
                and _resp.supplier
                and _resp.supplier.supplier_unit
                and _resp.supplier.supplier_unit.supplier_business_id
                and _resp.branch
            ):
                rest_io = await sup_res_assign_handler.fetch_restaurant_branch_infocing_options(
                    supplier_business_id=_resp.supplier.supplier_unit.supplier_business_id,
                    restaurant_branch_id=_resp.branch.id,
                )
                sat_cer = await _sat_cer_handler.get_mx_sat_invocing_certificate(
                    _resp.supplier.supplier_unit.id
                )
                if not sat_cer or not sat_cer.invoicing_options.invoice_type:
                    raise GQLApiException(
                        msg="missing info to invoice",
                        error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
                payment_form = None
                if rest_io and rest_io.invoice_type:
                    if rest_io.invoice_type.value == "PPD":
                        payment_form = PayMethodType(PayMethodType.TBD)
                    else:
                        payment_form = PayMethodType(_resp.details.payment_method)
                    if rest_io.invoice_type:
                        payment_method_inv = rest_io.invoice_type.value
                else:
                    if sat_cer.invoicing_options.invoice_type.value == "PPD":
                        payment_form = PayMethodType(PayMethodType.TBD)
                    else:
                        payment_form = PayMethodType(_resp.details.payment_method)
                    payment_method_inv = sat_cer.invoicing_options.invoice_type.value

                await mxi_handler.new_customer_invoice(
                    orden_details_id=_resp.details.id,
                    cfdi_type=CFDIType.INGRESO.value,
                    payment_form=INVOICE_PAYMENT_MAP[payment_form].value,
                    expedition_place=sat_cer.zip_code,
                    issue_date=datetime.utcnow() - timedelta(hours=6),
                    payment_method=payment_method_inv,
                    firebase_id=fb_id,
                )

                if await mxi_handler.re_invoice(
                    old_ordn_det=old_orden_det_obj, motive="01", orden_id=orden_id
                ):

                    return _resp
            else:
                raise GQLApiException(
                    msg="missing info to invoice",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not update Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class OrdenQuery:
    @strawberry.field(
        name="getOrdenStatus",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_orden_status(
        self, info: StrawberryInfo, orden_id: UUID
    ) -> OrdenStatusResult:  # type: ignore
        logger.info("Create new orden")
        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
        )
        # call validation
        if not orden_id:
            return OrdenError(
                msg="Empty values for creating Order",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.fetch_orden_status(orden_id)
            return _resp
        except GQLApiException as ge:
            return OrdenError(msg=ge.msg, code=ge.error_code)

    @strawberry.field(
        name="getOrdenPaystatus",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_orden_paystatus(
        self, info: StrawberryInfo, orden_id: UUID
    ) -> List[OrdenPaystatusResult]:  # type: ignore
        logger.info("Get orden pay status")
        # instantiate handler
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # call validation
        if not orden_id:
            return [
                OrdenError(
                    msg="Empty values for creating Order",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            ]
        try:
            # call handler
            _resp = await _handler.fetch_orden_paystatus(orden_id)
            return _resp
        except GQLApiException as ge:
            return [OrdenError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                OrdenError(
                    msg="Could not retrieve Orden",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getOrdenes",
        permission_classes=[IsAuthenticated],
    )
    async def get_ordenes(
        self,
        info: StrawberryInfo,
        orden_id: Optional[UUID] = None,
        orden_type: Optional[OrdenType] = None,
        status: Optional[OrdenStatusType] = None,
        paystatus: Optional[PayStatusType] = None,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        payment_method: Optional[PayMethodType] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[OrdenResult]:  # type: ignore
        logger.info("get ordenes")
        # instantiate handler
        _handler = OrdenHandler(
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
        # call validation
        try:
            # [TODO] - verify if request user has access to see these filters
            # call handler
            _resp = await _handler.search_orden(
                orden_id,
                orden_type,
                status,
                paystatus,
                restaurant_branch_id,
                supplier_business_id,
                supplier_unit_id,
                payment_method,
                from_date,
                to_date,
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return [OrdenError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                OrdenError(
                    msg="Could not retrieve Orden",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getExternalOrden",
        permission_classes=[],
    )
    async def get_orden_from_ext(
        self,
        info: StrawberryInfo,
        orden_id: Optional[UUID] = None,
    ) -> OrdenResult:  # type: ignore
        logger.info("get external orden")
        # instantiate handler
        _handler = OrdenHandler(
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
        br_handler = RestaurantBranchHandler(
            restaurant_branch_repo=RestaurantBranchRepository(info),
            branch_category_repo=RestaurantBranchCategoryRepository(info),
        )
        biz_handler = RestaurantBusinessHandler(
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
        )
        # call validation
        try:
            # call handler
            _resp = await _handler.search_orden(
                orden_id,
            )
            if len(_resp) > 0 and _resp[0].details:
                # get restaurant branch
                _br = await br_handler.fetch_restaurant_branches(
                    restaurant_branch_id=_resp[0].details.restaurant_branch_id
                )
                _orden = _resp[0]
                _orden.branch = _br[0]
                # get restaurant business for contact info
                _biz = await biz_handler.fetch_restaurant_business(
                    _orden.branch.restaurant_business_id
                )
                _orden.branch.contact_info = RestaurantBranchContactInfo(
                    business_name=_biz.name,
                    display_name=_biz.account.legal_rep_name if _biz.account else "",
                    email=_biz.account.email if _biz.account else "",
                    phone_number=_biz.account.phone_number if _biz.account else "",
                )
                return _orden
            else:
                return OrdenError(
                    msg="No Orden found",
                    code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
        except GQLApiException as ge:
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not retrieve Orden",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="exportOrdenes",
        permission_classes=[IsAuthenticated],
    )
    async def export_ordenes(
        self,
        info: StrawberryInfo,
        export_format: str,
        orden_id: Optional[UUID] = None,
        orden_type: Optional[OrdenType] = None,
        status: Optional[OrdenStatusType] = None,
        paystatus: Optional[PayStatusType] = None,
        restaurant_branch_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        payment_method: Optional[PayMethodType] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> ExportOrdenResult:  # type: ignore
        logger.info("export ordenes")
        # validate format
        if export_format.lower() not in ["csv", "xlsx"]:
            return OrdenError(
                msg="Invalid format",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # instantiate handler
        _handler = OrdenHandler(
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
        # instantiate handler MxInvoice
        inv_handler = MxInvoiceHandler(
            mx_invoice_repository=MxInvoiceRepository(info),
            orden_details_repo=OrdenDetailsRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
        )
        # call validation
        try:
            # [TODO] - verify if request user has access to see these filters
            # call handler
            _ords = await _handler.search_orden(
                orden_id,
                orden_type,
                status,
                paystatus,
                restaurant_branch_id,
                supplier_business_id,
                supplier_unit_id,
                payment_method,
                from_date,
                to_date,
            )
            res_inv = []
            if len(_ords) > 0:
                # call handler to get invoices
                res_inv = await inv_handler.fetch_invoices(
                    [o.details.orden_id for o in _ords if o.details]
                )
            # merge ordenes and invoices
            _resp = await _handler.merge_ordenes_invoices(_ords, res_inv)
            # build DF
            ddf = pd.DataFrame(_resp)
            ddf.set_index("id", inplace=True)
            _df = ddf[
                [
                    "orden_number",
                    "supplier",
                    "restaurant_branch",
                    "delivery_date",
                    "delivery_time",
                    "delivery_type",
                    "status",
                    "subtotal_without_tax",
                    "tax",
                    "subtotal",
                    "discount",
                    "shipping_cost",
                    "total",
                    "comments",
                    "payment_method",
                    "created_at",
                    "last_updated_at",
                    "paystatus",
                    "paystatus_time",
                    "uuid_factura",
                    "folio_factura",
                    "valor_factura",
                ]
            ].rename(
                columns={
                    "orden_number": "# Pedido",
                    "supplier": "Proveedor",
                    "restaurant_branch": "Cliente",
                    "delivery_date": "Fecha de Entrega",
                    "delivery_time": "Hora de Entrega",
                    "delivery_type": "Tipo de Entrega",
                    "status": "Estátus",
                    "subtotal_without_tax": "Subtotal sin IVA",
                    "tax": "IVA",
                    "subtotal": "Subtotal",
                    "discount": "Descuento",
                    "shipping_cost": "Costo de Envío",
                    "total": "Total",
                    "comments": "Comentarios",
                    "payment_method": "M. de Pago",
                    "paystatus": "Estátus de Pago",
                    "paystatus_time": "Fecha de Pago",
                    "created_at": "Fecha de Creación",
                    "last_updated_at": "Última Actualización",
                    "uuid_factura": "UUID Factura",
                    "folio_factura": "Folio Factura",
                    "valor_factura": "Valor Factura",
                }
            )
            _df.reset_index(inplace=True)
            # export
            if export_format == "csv":
                in_memory_csv = StringIO()
                _df.to_csv(in_memory_csv, index=False)
                in_memory_csv.seek(0)
                return ExportOrdenGQL(
                    file=json.dumps(
                        {
                            "filename": f"reporte_ordenes_{datetime.utcnow().date().isoformat()}.csv",
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
                return ExportOrdenGQL(
                    file=json.dumps(
                        {
                            "filename": f"reporte_ordenes_{datetime.utcnow().date().isoformat()}.xlsx",
                            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "content": base64.b64encode(in_memory_xlsx.read()).decode(),
                        }
                    ),
                    extension="xlsx",
                )
        except GQLApiException as ge:
            return OrdenError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Could not retrieve Export file",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="getOptimizedDraftOrdenes",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_optimized_draft_ordenes(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[OrdenResult]:  # type: ignore
        logger.info("get optimized draft ordenes")
        # instantiate handlers
        _handler = OrdenHandler(
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
        sup_handler = RestaurantSupplierAssignationHandler(
            core_user_repo=CoreUserRepository(info),
            rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
            rest_branch_repo=RestaurantBranchRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            supplier_business_account_repo=SupplierBusinessAccountRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_unit_category_repo=SupplierUnitCategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
            restaurant_perm_repo=RestaurantUserPermissionRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
        )

        try:
            # [TODO] - verify if request user has access to see these filters
            # call handler to get ordenes
            draft_ords = await _handler.search_orden(
                restaurant_branch_id=restaurant_branch_id,
                orden_type=OrdenType.DRAFT,
                from_date=from_date,
                to_date=to_date,
            )
            # call handler to get suppliers
            fb_id = info.context["request"].user.firebase_user.firebase_id
            res_suppliers = await sup_handler.fetch_restaurant_suppliers(
                fb_id,
            )
            # cll optimizer
            optim = PreOrdenOptimizer(draft_ords, res_suppliers)
            _resp = optim.optimize()
            return _resp
        except GQLApiException as ge:
            return [OrdenError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                OrdenError(
                    msg="Could not retrieve Ordenes",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getPaymentDetailsByDates",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_customer_payments_by_dates(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        comments: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[PaymentReceiptResult]:  # type: ignore
        """Endpoint to retrieve list of payment receipts
            based on filtered dates and comments

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_id: UUID
            Supplier Unit Id
        from_date: Optional[date]
            From Date
        until_date: Optional[date]
            Until Date
        comments: Optional[str]
            Comments
        page: Optional[int]
            Page number
        page_size: Optional[int]
            Page size

        Returns
        -------
        List[MxInvoiceResult]
        """
        logger.info("Get payments list by filters")
        # instantiate handler Orden
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            cart_prod_repo=CartProductRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_perms_repo=SupplierUserPermissionRepository(info),
            mx_invoice_complement_repo=MxInvoiceComplementRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get invoices
            res_pay = await _handler.get_customer_payments_by_dates(
                firebase_id=fb_id,
                supplier_unit_id=supplier_unit_id,
                from_date=from_date,
                until_date=until_date,
                comments=comments,
                page=page,
                page_size=page_size,
            )
            return res_pay
        except GQLApiException as ge:
            logger.warning(ge)
            return [
                OrdenError(
                    msg=ge.msg,
                    code=int(ge.error_code),
                )
            ]
        except Exception as e:
            logger.error(e)
            return [
                OrdenError(
                    msg="Error retrieving payments",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="exportPaymentDetailsByDates",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def export_customer_payments_by_dates(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        export_format: str,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        comments: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> ExportOrdenResult:  # type: ignore
        """Endpoint to retrieve list of payments
            based on filtered dates and comments

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_id: UUID
            Supplier Unit Id
        export_format: str
            Export format (csv or xlsx)
        from_date: Optional[date]
            From Date
        until_date: Optional[date]
            Until Date
        comments: Optional[str]
            Comments
        page: Optional[int]
            Page number
        page_size: Optional[int]
            Page size

        Returns
        -------
        List[MxInvoiceResult]
        """
        logger.info("Export payments list by filters")
        # validate format
        if export_format.lower() not in ["csv", "xlsx"]:
            return OrdenError(
                msg="Invalid format",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        _handler = OrdenHandler(
            orden_repo=OrdenRepository(info),
            orden_det_repo=OrdenDetailsRepository(info),
            orden_status_repo=OrdenStatusRepository(info),
            orden_payment_repo=OrdenPaymentStatusRepository(info),
            cart_prod_repo=CartProductRepository(info),
            supp_bus_repo=SupplierBusinessRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            supp_bus_acc_repo=SupplierBusinessAccountRepository(info),
            rest_branc_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_perms_repo=SupplierUserPermissionRepository(info),
            mx_invoice_complement_repo=MxInvoiceComplementRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get invoices
            res_pay = await _handler.get_customer_payments_by_dates(
                firebase_id=fb_id,
                supplier_unit_id=supplier_unit_id,
                from_date=from_date,
                until_date=until_date,
                comments=comments,
                page=page,
                page_size=page_size,
            )
            res_table = await _handler.format_payments_to_export(res_pay)
            _df = pd.DataFrame(res_table).rename(
                columns={
                    "id": "ID Pago",
                    "payment_value": "Monto",
                    "comments": "Comentario del Pago",
                    "payment_day": "Fecha de Pago",
                    "orden_ids": "Pedidos Asociados",
                    "created_at": "Fecha de Creación",
                    "last_updated": "Últ. Actualización",
                }
            )
            _df.sort_values(by="Fecha de Creación", ascending=True, inplace=True)
            _df.reset_index(inplace=True, drop=True)
            # export
            if export_format == "csv":
                in_memory_csv = StringIO()
                _df.to_csv(in_memory_csv, index=False)
                in_memory_csv.seek(0)
                return ExportOrdenGQL(
                    file=json.dumps(
                        {
                            "filename": f"reporte_pagos_{datetime.utcnow().date().isoformat()}.csv",
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
                return ExportOrdenGQL(
                    file=json.dumps(
                        {
                            "filename": f"reporte_pagos_{datetime.utcnow().date().isoformat()}.xlsx",
                            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "content": base64.b64encode(in_memory_xlsx.read()).decode(),
                        }
                    ),
                    extension="xlsx",
                )
        except GQLApiException as ge:
            logger.warning(ge)
            return OrdenError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return OrdenError(
                msg="Error retrieving payments",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
