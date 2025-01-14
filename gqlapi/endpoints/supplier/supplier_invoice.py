import logging
from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import (
    CustomerMxInvoiceGQLResult,
    SupplierInvoiceError,
    SupplierInvoiceTriggerResult,
)
from gqlapi.domain.models.v2.utils import PayMethodType
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.invoice import MxInvoiceHandler
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.supplier.supplier_invoice import SupplierInvoiceHandler
from gqlapi.repository.core.cart import CartProductRepository
from gqlapi.repository.core.invoice import (
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
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
import strawberry
from strawberry.types import Info as StrawberryInfo


@strawberry.type
class SupplierInvoiceMutation:
    @strawberry.mutation(
        name="createSupplierInvoice",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def new_supplier_invoice(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
    ) -> SupplierInvoiceTriggerResult:  # type: ignore
        logging.info("Create supplier invoice")
        # instantiate handler
        core_user_repo = CoreUserRepository(info)
        supplier_business_repo = SupplierBusinessRepository(info)
        supplier_business_account_repo = SupplierBusinessAccountRepository(info)
        supplier_unit_repo = SupplierUnitRepository(info)
        supplier_unit_delivery_repo = SupplierUnitDeliveryRepository(info)
        restaurant_branch_repo = RestaurantBranchRepository(info)
        orden_repo = OrdenRepository(info)
        orden_details_repo = OrdenDetailsRepository(info)
        orden_status_repo = OrdenStatusRepository(info)
        orden_payment_repo = OrdenPaymentStatusRepository(info)
        cart_product_repo = CartProductRepository(info)
        supp_prod_repo = SupplierProductRepository(info)
        mx_sat_cer_repo = MxSatCertificateRepository(info)
        mx_invoice_repository = MxInvoiceRepository(info)
        mx_invoicing_exec_repo = MxInvoicingExecutionRepository(info)
        ord_handler = OrdenHandler(
            orden_repo=orden_repo,
            orden_det_repo=orden_details_repo,
            orden_status_repo=orden_status_repo,
            orden_payment_repo=orden_payment_repo,
            cart_prod_repo=cart_product_repo,
            supp_bus_repo=supplier_business_repo,
            supp_unit_repo=supplier_unit_repo,
            supp_bus_acc_repo=supplier_business_account_repo,
            rest_branc_repo=restaurant_branch_repo,
        )
        mxinv_handler = MxInvoiceHandler(
            mx_invoice_repository=mx_invoice_repository,
            orden_details_repo=orden_details_repo,
            core_user_repo=core_user_repo,
            supplier_unit_repo=supplier_unit_repo,
            restaurant_branch_repo=restaurant_branch_repo,
            supplier_business_repo=supplier_business_repo,
            orden_repo=orden_repo,
            cart_product_repo=cart_product_repo,
            supp_prod_repo=supp_prod_repo,
            mx_sat_cer_repo=mx_sat_cer_repo,
        )
        # supplier invoice handler
        sup_invo_handler = SupplierInvoiceHandler(
            orden_handler=ord_handler,
            mx_invoice_handler=mxinv_handler,
            restaurant_branch_repo=restaurant_branch_repo,
            supplier_unit_repo=supplier_unit_repo,
            supplier_unit_delivery_repo=supplier_unit_delivery_repo,
            mx_sat_cer_repo=mx_sat_cer_repo,
            mx_invoicing_exec_repo=mx_invoicing_exec_repo,
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # fetch orden details
            ord_details = await sup_invo_handler.fetch_orden_details(orden_id=orden_id)
            # call invoice execution
            invo_exec = await sup_invo_handler.trigger_supplier_invoice(
                firebase_id=fb_id, orden=ord_details
            )
            return invo_exec
        except GQLApiException as ge:
            logging.warning(f"Error creating supplier invoice: {ge.msg}")
            return SupplierInvoiceError(
                msg=f"Hubo un error creando la factura ({ge.msg})",
                code=ge.error_code,
            )
        except Exception as e:
            logging.error(e)
            return SupplierInvoiceError(
                msg=f"Hubo un error creando la factura ({str(e)})",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="createConsolidatedSupplierInvoice",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def new_consolidated_supplier_invoice(
        self,
        info: StrawberryInfo,
        orden_ids: List[UUID],
        payment_method: PayMethodType,
        public_general_invoice_flag: Optional[bool] = None,
    ) -> List[CustomerMxInvoiceGQLResult]:  # type: ignore
        logging.info("Create supplier invoice")
        # instantiate handler
        core_user_repo = CoreUserRepository(info)
        supplier_business_repo = SupplierBusinessRepository(info)
        supplier_business_account_repo = SupplierBusinessAccountRepository(info)
        supplier_unit_repo = SupplierUnitRepository(info)
        supplier_unit_delivery_repo = SupplierUnitDeliveryRepository(info)
        restaurant_branch_repo = RestaurantBranchRepository(info)
        orden_repo = OrdenRepository(info)
        orden_details_repo = OrdenDetailsRepository(info)
        orden_status_repo = OrdenStatusRepository(info)
        orden_payment_repo = OrdenPaymentStatusRepository(info)
        cart_product_repo = CartProductRepository(info)
        supp_prod_repo = SupplierProductRepository(info)
        mx_sat_cer_repo = MxSatCertificateRepository(info)
        mx_invoice_repository = MxInvoiceRepository(info)
        mx_invoicing_exec_repo = MxInvoicingExecutionRepository(info)
        ord_handler = OrdenHandler(
            orden_repo=orden_repo,
            orden_det_repo=orden_details_repo,
            orden_status_repo=orden_status_repo,
            orden_payment_repo=orden_payment_repo,
            cart_prod_repo=cart_product_repo,
            supp_bus_repo=supplier_business_repo,
            supp_unit_repo=supplier_unit_repo,
            supp_bus_acc_repo=supplier_business_account_repo,
            rest_branc_repo=restaurant_branch_repo,
        )
        mxinv_handler = MxInvoiceHandler(
            mx_invoice_repository=mx_invoice_repository,
            orden_details_repo=orden_details_repo,
            core_user_repo=core_user_repo,
            supplier_unit_repo=supplier_unit_repo,
            restaurant_branch_repo=restaurant_branch_repo,
            supplier_business_repo=supplier_business_repo,
            orden_repo=orden_repo,
            cart_product_repo=cart_product_repo,
            supp_prod_repo=supp_prod_repo,
            mx_sat_cer_repo=mx_sat_cer_repo,
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
        )
        # supplier invoice handler
        sup_invo_handler = SupplierInvoiceHandler(
            orden_handler=ord_handler,
            mx_invoice_handler=mxinv_handler,
            restaurant_branch_repo=restaurant_branch_repo,
            supplier_unit_repo=supplier_unit_repo,
            supplier_unit_delivery_repo=supplier_unit_delivery_repo,
            mx_sat_cer_repo=mx_sat_cer_repo,
            mx_invoicing_exec_repo=mx_invoicing_exec_repo,
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
        )
        try:
            if not isinstance(public_general_invoice_flag, bool):
                public_general_invoice_flag = False
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # fetch orden details
            ord_details = await ord_handler.search_ordens_with_many(orden_ids=orden_ids)
            # call invoice execution
            invo_exec = await sup_invo_handler.trigger_supplier_consolidated_invoice(
                firebase_id=fb_id,
                ordenes=ord_details,
                payment_method=payment_method,
                public_general_invoice_flag=public_general_invoice_flag,
            )
            return invo_exec
        except GQLApiException as ge:
            logging.warning(f"Error creating supplier invoice: {ge.msg}")
            return [
                SupplierInvoiceError(
                    msg=f"Hubo un error creando la factura consolidada ({ge.msg})",
                    code=ge.error_code,
                )
            ]
        except Exception as e:
            logging.error(e)
            return [
                SupplierInvoiceError(
                    msg=f"Hubo un error creando la factura consolidada({str(e)})",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]


@strawberry.type
class SupplierInvoiceQuery:
    @strawberry.field(
        name="getSupplierInvoiceExecutionStatus",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_invoice_execution_status(
        self,
        info: StrawberryInfo,
        orden_id: UUID,
    ) -> SupplierInvoiceTriggerResult:  # type: ignore
        logging.info("Get supplier invoice execution status")
        # instantiate handler
        core_user_repo = CoreUserRepository(info)
        supplier_business_repo = SupplierBusinessRepository(info)
        supplier_business_account_repo = SupplierBusinessAccountRepository(info)
        supplier_unit_repo = SupplierUnitRepository(info)
        supplier_unit_delivery_repo = SupplierUnitDeliveryRepository(info)
        restaurant_branch_repo = RestaurantBranchRepository(info)
        orden_repo = OrdenRepository(info)
        orden_details_repo = OrdenDetailsRepository(info)
        orden_status_repo = OrdenStatusRepository(info)
        orden_payment_repo = OrdenPaymentStatusRepository(info)
        cart_product_repo = CartProductRepository(info)
        supp_prod_repo = SupplierProductRepository(info)
        mx_sat_cer_repo = MxSatCertificateRepository(info)
        mx_invoice_repository = MxInvoiceRepository(info)
        mx_invoicing_exec_repo = MxInvoicingExecutionRepository(info)
        ord_handler = OrdenHandler(
            orden_repo=orden_repo,
            orden_det_repo=orden_details_repo,
            orden_status_repo=orden_status_repo,
            orden_payment_repo=orden_payment_repo,
            cart_prod_repo=cart_product_repo,
            supp_bus_repo=supplier_business_repo,
            supp_unit_repo=supplier_unit_repo,
            supp_bus_acc_repo=supplier_business_account_repo,
            rest_branc_repo=restaurant_branch_repo,
        )
        mxinv_handler = MxInvoiceHandler(
            mx_invoice_repository=mx_invoice_repository,
            orden_details_repo=orden_details_repo,
            core_user_repo=core_user_repo,
            supplier_unit_repo=supplier_unit_repo,
            restaurant_branch_repo=restaurant_branch_repo,
            supplier_business_repo=supplier_business_repo,
            orden_repo=orden_repo,
            cart_product_repo=cart_product_repo,
            supp_prod_repo=supp_prod_repo,
            mx_sat_cer_repo=mx_sat_cer_repo,
        )
        # supplier invoice handler
        sup_invo_handler = SupplierInvoiceHandler(
            orden_handler=ord_handler,
            mx_invoice_handler=mxinv_handler,
            restaurant_branch_repo=restaurant_branch_repo,
            supplier_unit_repo=supplier_unit_repo,
            supplier_unit_delivery_repo=supplier_unit_delivery_repo,
            mx_sat_cer_repo=mx_sat_cer_repo,
            mx_invoicing_exec_repo=mx_invoicing_exec_repo,
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_restaurant_relation_mx_invoice_options_repo=RestaurantBranchInvoicingOptionsRepository(
                info
            ),
        )
        try:
            exec_info = await sup_invo_handler.fetch_supplier_invoice_exec_status(
                orden_id=orden_id
            )
            return exec_info
        except GQLApiException as ge:
            logging.warning(
                f"Error fetching supplier invoice execution status: {ge.msg}"
            )
            return SupplierInvoiceError(
                msg=f"Issues fetching Invoice Exection info ({ge.msg})",
                code=ge.error_code,
            )
        except Exception as e:
            logging.error(e)
            return SupplierInvoiceError(
                msg=f"Issues fetching Invoice Exection info ({str(e)})",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
