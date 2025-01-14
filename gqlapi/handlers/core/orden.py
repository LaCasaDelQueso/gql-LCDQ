import base64
from datetime import date, datetime
import json
from types import NoneType
from typing import Any, Dict, Optional, List
from uuid import UUID
import uuid
from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi, StripeCurrency
from gqlapi.repository.scripts.scripts_execution import ScriptExecutionRepository

from gqlapi.domain.interfaces.v2.integrations.integrations import (
    IntegrationWebhookHandlerInterface,
)
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.db import database as SQLDatabase
from gqlapi.domain.interfaces.v2.orden.cart import (
    CartProductGQL,
    CartProductRepositoryInterface,
    CartRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import (
    MxInvoiceComplementRepositoryInterface,
    MxInvoiceGQL,
    MxSatCertificateRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.orden import (
    MxInvoiceComplementGQL,
    OrdenDetailsRepositoryInterface,
    OrdenGQL,
    OrdenHandlerInterface,
    OrdenHookListenerInterface,
    OrdenPaymentStatusRepositoryInterface,
    OrdenPaystatusGQL,
    OrdenRepositoryInterface,
    OrdenStatusRepositoryInterface,
    OrdenSupplierGQL,
    PaymentReceiptGQL,
    PaymentReceiptOrdenGQL,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchGQL,
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepositoryInterface,
    RestaurantBusinessRepositoryInterface,
)

from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessAccountRepositoryInterface,
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    SupplierRestaurantsRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import (
    SupplierUnitGQL,
    SupplierUnitRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.models.v2.core import (
    Cart,
    CartProduct,
    CoreUser,
    Orden,
    OrdenDetails,
    OrdenPayStatus,
    OrdenStatus,
    PaymentReceipt,
    PaymentReceiptOrden,
)
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranch,
    RestaurantBranchTag,
    RestaurantBusiness,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
    SupplierBusinessAccount,
    SupplierProduct,
)
from gqlapi.domain.models.v2.utils import (
    DataTypeDecoder,
    DataTypeTraslate,
    DeliveryTimeWindow,
    OrdenSourceType,
    OrdenStatusType,
    OrdenType,
    PayMethodType,
    PayStatusType,
    SellingOption,
    UOMType,
)
from gqlapi.config import ALIMA_SUPPORT_PHONE, APP_TZ
from gqlapi.config import SENDGRID_SINGLE_SENDER
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.domain_mapper import sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.utils.notifications import (
    send_ecommerce_restaurant_email_confirmation,
    send_restaurant_changed_status_v2,
    send_supplier_changed_status_v2,
    send_supplier_email_confirmation,
    send_supplier_whatsapp_confirmation,
    send_unformat_restaurant_email_confirmation,
)
import pytz
import requests

# logger
logger = get_logger(get_app())


class OrdenHandler(OrdenHandlerInterface):
    def __init__(
        self,
        orden_repo: OrdenRepositoryInterface,
        orden_det_repo: OrdenDetailsRepositoryInterface,
        orden_status_repo: OrdenStatusRepositoryInterface,
        orden_payment_repo: OrdenPaymentStatusRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        rest_branc_repo: Optional[RestaurantBranchRepositoryInterface] = None,
        supp_unit_repo: Optional[SupplierUnitRepositoryInterface] = None,
        cart_repo: Optional[CartRepositoryInterface] = None,
        cart_prod_repo: Optional[CartProductRepositoryInterface] = None,
        rest_buss_acc_repo: Optional[
            RestaurantBusinessAccountRepositoryInterface
        ] = None,
        rest_business_repo: Optional[RestaurantBusinessRepositoryInterface] = None,
        supp_bus_repo: Optional[SupplierBusinessRepositoryInterface] = None,
        supp_bus_acc_repo: Optional[SupplierBusinessAccountRepositoryInterface] = None,
        supplier_restaurants_repo: Optional[
            SupplierRestaurantsRepositoryInterface
        ] = None,
        supplier_user_repo: Optional[SupplierUserRepositoryInterface] = None,
        supplier_user_perms_repo: Optional[
            SupplierUserPermissionRepositoryInterface
        ] = None,
        mx_invoice_complement_repo: Optional[
            MxInvoiceComplementRepositoryInterface
        ] = None,
        mx_sat_cer_repo: Optional[MxSatCertificateRepositoryInterface] = None,
    ):
        self.orden_repo = orden_repo
        self.orden_det_repo = orden_det_repo
        self.orden_status_repo = orden_status_repo
        self.orden_payment_repo = orden_payment_repo
        if rest_branc_repo:
            self.rest_branc_repo = rest_branc_repo
        if supp_unit_repo:
            self.supp_unit_repo = supp_unit_repo
        if cart_repo:
            self.cart_repo = cart_repo
        if cart_prod_repo:
            self.cart_prod_repo = cart_prod_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if rest_buss_acc_repo:
            self.rest_buss_acc_repo = rest_buss_acc_repo
        if rest_business_repo:
            self.rest_business_repo = rest_business_repo
        if supp_bus_repo:
            self.supp_bus_repo = supp_bus_repo
        if supp_bus_acc_repo:
            self.supp_bus_acc_repo = supp_bus_acc_repo
        if supplier_restaurants_repo:
            self.supplier_restaurants_repo = supplier_restaurants_repo
        if supplier_user_repo:
            self.supplier_user_repo = supplier_user_repo
        if supplier_user_perms_repo:
            self.supplier_user_perms_repo = supplier_user_perms_repo
        if mx_invoice_complement_repo:
            self.mx_invoice_repo = mx_invoice_complement_repo
        if mx_sat_cer_repo:
            self.mx_sat_cer_repo = mx_sat_cer_repo

    async def _build_cart(
        self,
        core_user: CoreUser,
        cart_products: List[CartProduct],
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a cart and cart products

        Parameters
        ----------
        core_user : CoreUser
        cart_products : List[CartProduct]
        shipping_cost : Optional[float], optional
        packaging_cost : Optional[float], optional
        service_fee : Optional[float], optional

        Returns
        -------
        Tuple[Any]

        Raises
        ------
        GQLApiException
        """
        # create cart
        cart_id = await self.cart_repo.new(
            Cart(id=uuid.uuid4(), active=True, created_by=core_user.id)
        )
        subtotal = 0
        for cp in cart_products:
            try:
                if cp.quantity < 0.0009:
                    continue
                _subtotal = cp.subtotal
                if cp.quantity is not None and cp.unit_price is not None:
                    _subtotal = cp.quantity * cp.unit_price
                await self.cart_prod_repo.new(
                    CartProduct(
                        cart_id=cart_id,
                        supplier_product_id=cp.supplier_product_id,
                        supplier_product_price_id=cp.supplier_product_price_id,
                        quantity=cp.quantity,
                        created_by=core_user.id,
                        sell_unit=cp.sell_unit,
                        unit_price=cp.unit_price,
                        subtotal=_subtotal,
                        comments=cp.comments,
                    )
                )
                if cp.subtotal:
                    subtotal += cp.subtotal
            except Exception as e:
                logger.error(e)
                # delete cart
                await self.cart_repo.update(
                    cart_id, active=False, closed_at=datetime.utcnow()
                )
                raise GQLApiException(
                    msg="Error creating cart product",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
        # compute totals
        cart_produc_res = []
        taxes = 0
        subtotal_without_tax = 0
        for prod in await self.cart_prod_repo.search_with_tax(cart_id=cart_id):
            supp_prod = dict(prod)
            cprod = CartProductGQL(**sql_to_domain(prod, CartProduct))
            if cprod.quantity < 0.0009:
                continue
            cprod.supp_prod = SupplierProduct(**json.loads(supp_prod["tax_json"]))  # type: ignore
            if cprod.supp_prod:
                if cprod.supp_prod.tax and cprod.subtotal:
                    taxes += cprod.supp_prod.tax * cprod.subtotal
                if cprod.supp_prod.mx_ieps and cprod.subtotal:
                    taxes += cprod.supp_prod.mx_ieps * cprod.subtotal
                if isinstance(cprod.supp_prod.sell_unit, str):
                    cprod.supp_prod.sell_unit = UOMType(cprod.supp_prod.sell_unit)
            cart_produc_res.append(cprod)

        # This change when implement cost methods
        if taxes:
            subtotal_without_tax = subtotal - taxes
        else:
            subtotal_without_tax = subtotal
        total = subtotal
        for cost in [shipping_cost, packaging_cost, service_fee]:
            if cost:
                total += cost

        # [TODO ]if Discount code
        # get discount
        # total -= discount

        # [TODO ]if cashback_transaction_id
        # get cashback
        # total -= cashback

        # close cart
        await self.cart_repo.update(cart_id, active=False, closed_at=datetime.utcnow())
        # return
        return {
            "cart_id": cart_id,
            "cart_product_res": cart_produc_res,
            "subtotal": subtotal,
            "subtotal_without_tax": subtotal_without_tax,
            "tax": taxes,
            "shipping_cost": shipping_cost,
            "packaging_cost": packaging_cost,
            "service_fee": service_fee,
            "total": total,
        }

    async def new_orden_ecommerce(
        self,
        orden_type: OrdenType,
        restaurant_branch_id: UUID,
        cart_products: List[CartProduct],
        supplier_unit_id: UUID,
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,  # noqa
        cashback_transation_id: Optional[UUID] = None,  # noqa
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        # validate pk
        branch_exists = await self.rest_branc_repo.exists(restaurant_branch_id)
        if not branch_exists:
            raise GQLApiException(
                msg="Restaurant Branch not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_unit = await self.supp_unit_repo.fetch(supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Supplier Unit not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_business_id = supplier_unit["supplier_business_id"]
        # [TODO] Exist cashback_transaction_id
        # [TODO] Exist discount code
        # return new orden subroutine
        return await self._new_orden_ecommerce(
            orden_type,
            restaurant_branch_id,
            supplier_unit_id,
            cart_products,
            status=status,
            supplier_business_id=supplier_business_id,
            comments=comments,
            payment_method=payment_method,
            paystatus=paystatus,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            delivery_type=delivery_type,
            approved_by=approved_by,
            discount_code=discount_code,
            cashback_transation_id=cashback_transation_id,
            shipping_cost=shipping_cost,
            packaging_cost=packaging_cost,
            service_fee=service_fee,
            source_type=OrdenSourceType.ECOMMERCE,
        )

    async def new_orden_marketplace(
        self,
        orden_type: OrdenType,
        firebase_id: str,
        restaurant_branch_id: UUID,
        cart_products: List[CartProduct],
        supplier_unit_id: Optional[UUID] = None,
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,  # noqa
        cashback_transation_id: Optional[UUID] = None,  # noqa
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        # validate pk
        branch_exists = await self.rest_branc_repo.exists(restaurant_branch_id)
        if not branch_exists:
            raise GQLApiException(
                msg="Restaurant Branch not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if supplier_unit_id:
            supplier_unit = await self.supp_unit_repo.fetch(supplier_unit_id)
            if not supplier_unit:
                raise GQLApiException(
                    msg="Supplier Unit not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            if not supplier_business_id:
                supplier_business_id = supplier_unit["supplier_business_id"]
            elif supplier_business_id != supplier_unit["supplier_business_id"]:
                raise GQLApiException(
                    msg="Supplier Business ID does not match with Supplier Unit",
                    error_code=GQLApiErrorCodeType.SUPPLIER_BUSINESS_NO_PERMISSIONS.value,
                )
        elif supplier_business_id:
            # if supplier unit is active
            # and which one is assigned to the restaurant branch
            # [TODO] If no branch assigned, take the closest one
            sup_business = await self.supp_bus_repo.fetch(supplier_business_id)
            if not sup_business:
                raise GQLApiException(
                    msg="Supplier Business not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            if not sup_business["active"]:
                raise GQLApiException(
                    msg="Supplier Business not active in Alima Seller",
                    error_code=GQLApiErrorCodeType.SUPPLIER_NOT_ACTIVE.value,
                )
            # get supplier units
            supplier_units = await self.supp_unit_repo.find(
                supplier_business_id=supplier_business_id
            )
            supplier_unit_ids = [
                supplier_unit["id"] for supplier_unit in supplier_units
            ]
            if not supplier_unit_ids:
                raise GQLApiException(
                    msg="Supplier Units not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            # find supplier rest relations
            supplier_restaurants = await self.supplier_restaurants_repo.raw_query(
                query=f"""
                        SELECT supplier_unit_id, restaurant_branch_id
                        FROM supplier_restaurant_relation
                        WHERE supplier_unit_id IN {list_into_strtuple(supplier_unit_ids)}
                        AND restaurant_branch_id = :restaurant_branch_id
                    """,
                values={"restaurant_branch_id": restaurant_branch_id},
            )
            if not supplier_restaurants:
                # take default -> [TODO] eval region to be delivered
                supplier_unit_id = supplier_unit_ids[0]
            else:
                supplier_unit_id = supplier_restaurants[0]["supplier_unit_id"]

        # [TODO] Exist cashback_transaction_id
        # [TODO] Exist discount code
        # return new orden subroutine
        return await self._new_orden(
            orden_type,
            firebase_id,
            restaurant_branch_id,
            supplier_unit_id,  # type: ignore (safe)
            cart_products,
            status=status,
            supplier_business_id=supplier_business_id,
            comments=comments,
            payment_method=payment_method,
            paystatus=paystatus,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            delivery_type=delivery_type,
            approved_by=approved_by,
            discount_code=discount_code,
            cashback_transation_id=cashback_transation_id,
            shipping_cost=shipping_cost,
            packaging_cost=packaging_cost,
            service_fee=service_fee,
            source_type=OrdenSourceType.MARKETPLACE,
        )

    async def new_orden(
        self,
        orden_type: OrdenType,
        firebase_id: str,
        restaurant_branch_id: UUID,
        cart_products: List[CartProduct],
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,  # noqa
        cashback_transation_id: Optional[UUID] = None,  # noqa
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:
        # validate pk
        await self.rest_branc_repo.exist(restaurant_branch_id)
        if supplier_business_id:
            await self.supp_bus_repo.exist(supplier_business_id)
        # [TODO] Exist cashback_transaction_id
        # [TODO] Exist discount code

        if orden_type == OrdenType.DRAFT:
            status = OrdenStatusType.SUBMITTED
            # use alima admin supplier unit
            supplier_unit_id = (await self.supp_unit_repo.search(unit_name="Alima"))[
                0
            ].id
        else:
            # get supplier unit
            # -- [TODO] In next release validate if supplier unit is active
            #           and which one is assigned to the restaurant branch
            supplier_unit_id = (
                await self.supp_unit_repo.search(
                    supplier_business_id=supplier_business_id
                )
            )[0].id
        # return new orden subroutine
        return await self._new_orden(
            orden_type,
            firebase_id,
            restaurant_branch_id,
            supplier_unit_id,
            cart_products,
            status=status,
            supplier_business_id=supplier_business_id,
            comments=comments,
            payment_method=payment_method,
            paystatus=paystatus,
            delivery_date=delivery_date,
            delivery_time=delivery_time,
            delivery_type=SellingOption.SCHEDULED_DELIVERY,
            approved_by=approved_by,
            discount_code=discount_code,
            cashback_transation_id=cashback_transation_id,
            shipping_cost=shipping_cost,
            packaging_cost=packaging_cost,
            service_fee=service_fee,
            source_type=OrdenSourceType.AUTOMATION,
        )

    async def _new_orden(
        self,
        orden_type: OrdenType,
        firebase_id: str,
        restaurant_branch_id: UUID,
        supplier_unit_id: UUID,
        cart_products: List[CartProduct],
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,  # noqa
        cashback_transation_id: Optional[UUID] = None,  # noqa
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
        source_type: Optional[OrdenSourceType] = OrdenSourceType.AUTOMATION,
    ) -> OrdenGQL:  # type: ignore
        # get core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        # create cart
        cart_res = await self._build_cart(
            core_user,
            cart_products,
            shipping_cost=shipping_cost,
            packaging_cost=packaging_cost,
            service_fee=service_fee,
        )
        if supplier_business_id:
            orden_count = await self.orden_repo.count_by_supplier_business(
                supplier_business_id=supplier_business_id
            )
        else:
            raise GQLApiException(
                msg="Error to get orden count",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # create orden
        orden_id = await self.orden_repo.add(
            Orden(
                id=uuid.uuid4(),
                orden_type=orden_type,
                orden_number=str(orden_count + 1),
                source_type=source_type,
                created_by=core_user.id,
            )
        )
        orden = await self.orden_repo.get(orden_id)

        ord_details_uuid = uuid.uuid4()
        if not delivery_time:
            delivery_time = DeliveryTimeWindow(9, 18)
        try:
            await self.orden_det_repo.new(
                OrdenDetails(
                    id=ord_details_uuid,
                    orden_id=orden_id,
                    version=1,
                    restaurant_branch_id=restaurant_branch_id,
                    supplier_unit_id=supplier_unit_id,
                    cart_id=cart_res["cart_id"],
                    delivery_date=delivery_date,
                    delivery_time=delivery_time,
                    delivery_type=delivery_type,
                    subtotal_without_tax=(
                        cart_res["subtotal_without_tax"]
                        if cart_res["subtotal_without_tax"]
                        else None
                    ),
                    tax=cart_res.get("tax", 0),
                    discount=None,
                    discount_code=None,
                    cashback=None,
                    cashback_transation_id=None,
                    shipping_cost=shipping_cost if shipping_cost else None,
                    packaging_cost=packaging_cost if packaging_cost else None,
                    service_fee=service_fee if service_fee else None,
                    total=cart_res["total"] if cart_res["total"] else None,
                    subtotal=cart_res["subtotal"] if cart_res["subtotal"] else None,
                    comments=comments if comments else None,
                    payment_method=payment_method if payment_method else None,
                    approved_by=approved_by,
                    created_by=core_user.id,
                )
            )
            # create delivery status
            await self.orden_status_repo.new(
                OrdenStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=status,
                    created_by=core_user.id,  # type: ignore
                )
            )

            # create payment status
            await self.orden_payment_repo.new(
                OrdenPayStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=paystatus,
                    created_by=core_user.id,  # type: ignore
                )
            )
        except Exception as e:
            logger.error(e)
            # if error creating delete orden
            await self.orden_status_repo.new(
                OrdenStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=OrdenStatusType(
                        DataTypeDecoder.get_orden_status_value("canceled")
                    ),
                    created_by=core_user.id,
                )
            )
            raise GQLApiException(
                msg="Error creating orden details",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

        # construct response
        orden_status = await self.orden_status_repo.get(orden_id)
        orden_status["status"] = DataTypeDecoder.get_orden_status_value(
            orden_status["status"]
        )
        orden["status"] = OrdenStatus(**orden_status)
        orden_details = await self.orden_det_repo.get(ord_details_uuid)
        if orden_details["delivery_time"]:
            orden_details["delivery_time"] = DeliveryTimeWindow.parse(
                orden_details["delivery_time"]
            )
        orden["details"] = OrdenDetails(**orden_details)
        orden_paystatus = await self.orden_payment_repo.get(orden_id)
        if orden_paystatus["status"]:
            orden_paystatus["status"] = DataTypeDecoder.get_orden_paystatus_value(
                orden_paystatus["status"]
            )
        orden["paystatus"] = OrdenPayStatus(**orden_paystatus)
        # branch
        _branch = await self.rest_branc_repo.get(restaurant_branch_id)
        rest_branch = RestaurantBranch(**_branch)
        orden["branch"] = RestaurantBranchGQL(**_branch)
        rest_buss = await self.rest_business_repo.fetch(
            rest_branch.restaurant_business_id
        )
        if not rest_buss:
            raise GQLApiException(
                msg="Issues fetch restaurant business",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        rest_buss_obj = RestaurantBusiness(**rest_buss)
        rest_buss_acc = await self.rest_buss_acc_repo.fetch(
            rest_branch.restaurant_business_id
        )
        if not rest_buss_acc:
            raise GQLApiException(
                msg="Issues fetch restaurant business account",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        # supplier
        sup_business, supp_bus_acc, sup_unit = None, None, None
        if supplier_business_id:
            sup_business = SupplierBusiness(
                **await self.supp_bus_repo.get(supplier_business_id)
            )
            supp_bus_acc = SupplierBusinessAccount(
                **await self.supp_bus_acc_repo.get(sup_business.id)
            )
            try:
                sup_unit = SupplierUnitGQL(
                    **await self.supp_unit_repo.get(supplier_unit_id)
                )
            except Exception as e:
                logger.error(e)
            orden["supplier"] = OrdenSupplierGQL(
                supplier_business=sup_business,
                supplier_business_account=supp_bus_acc,
                supplier_unit=sup_unit,
            )
            # send supplier notification - email
            if (
                sup_business.notification_preference == "email"
                and supp_bus_acc.email
                and orden_type == OrdenType.NORMAL
            ):
                try:
                    await send_supplier_email_confirmation(
                        f"Pedido de {rest_branch.branch_name}",
                        from_email={
                            "email": core_user.email,
                            "name": rest_branch.branch_name,
                        },
                        to_email={
                            "email": supp_bus_acc.email,
                            "name": sup_business.name,
                        },
                        orden_details=OrdenDetails(**orden_details),
                        branch_name=rest_branch.branch_name,
                        contact_number=(
                            supp_bus_acc.phone_number
                            if supp_bus_acc.phone_number
                            else ""
                        ),
                        delivery_address=rest_branch.full_address,
                        cart_products=cart_res["cart_product_res"],
                    )
                    # [TODO] send another email with link to upload invoice
                except Exception as e:
                    logger.warning("Issues sending supplier email")
                    logger.error(e)
            # send supplier notification - whatsapp
            elif (
                sup_business.notification_preference == "whatsapp"
                and supp_bus_acc.phone_number
                and orden_type == OrdenType.NORMAL
            ):
                try:
                    send_supplier_whatsapp_confirmation(
                        to_wa={
                            "phone": supp_bus_acc.phone_number,
                            "name": sup_business.name,
                        },
                        orden_details=OrdenDetails(**orden_details),
                        branch_name=rest_branch.branch_name,
                        contact_number=ALIMA_SUPPORT_PHONE,
                        delivery_address=rest_branch.full_address,
                        cart_products=cart_res["cart_product_res"],
                    )
                    # [TODO] send another wa with link to upload invoice
                except Exception as e:
                    logger.warning("Issues sending supplier email")
                    logger.error(e)
            # send restaurant notification
            if orden_type == OrdenType.NORMAL:
                # send confirmation to the user that created the orden
                try:
                    if rest_buss_acc.email:
                        await send_unformat_restaurant_email_confirmation(
                            f"Pedido para {sup_business.name if sup_business else 'Proveedor'}",
                            from_email={
                                "email": SENDGRID_SINGLE_SENDER,
                                "name": sup_business.name,
                            },
                            to_email={
                                "email": (
                                    rest_buss_acc.email
                                ),
                                "name": rest_buss_obj.name
                                + " - "
                                + rest_branch.branch_name,
                            },
                            orden_details=OrdenDetails(**orden_details),
                            cart_products=cart_res["cart_product_res"],
                            orden_number=orden["orden_number"],
                            rest_branch_name=rest_branch.branch_name,
                            cel_contact=supp_bus_acc.phone_number,  # type: ignore
                        )
                except Exception as e:
                    logger.warning("Issues sending restaurant confirmation email")
                    logger.error(e)
        return OrdenGQL(**orden)

    async def _new_orden_ecommerce(
        self,
        orden_type: OrdenType,
        restaurant_branch_id: UUID,
        supplier_unit_id: UUID,
        cart_products: List[CartProduct],
        status: Optional[OrdenStatusType] = None,
        supplier_business_id: Optional[UUID] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[datetime] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,  # noqa
        cashback_transation_id: Optional[UUID] = None,  # noqa
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
        source_type: Optional[OrdenSourceType] = OrdenSourceType.AUTOMATION,
    ) -> OrdenGQL:  # type: ignore
        # get core user admin for ecommerce transations
        core_user = await self.core_user_repo.fetch_by_email("admin")
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create cart
        cart_res = await self._build_cart(
            core_user,
            cart_products,
            shipping_cost=shipping_cost,
            packaging_cost=packaging_cost,
            service_fee=service_fee,
        )
        if supplier_business_id:
            orden_count = await self.orden_repo.count_by_supplier_business(
                supplier_business_id=supplier_business_id
            )
        else:
            raise GQLApiException(
                msg="Error to get orden count",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )

        # create orden
        orden_id = await self.orden_repo.add(
            Orden(
                id=uuid.uuid4(),
                orden_type=orden_type,
                orden_number=str(orden_count + 1),
                source_type=source_type,
                created_by=core_user.id,
            )
        )
        orden = await self.orden_repo.get(orden_id)

        ord_details_uuid = uuid.uuid4()
        if not delivery_time:
            delivery_time = DeliveryTimeWindow(9, 18)
        try:
            await self.orden_det_repo.new(
                OrdenDetails(
                    id=ord_details_uuid,
                    orden_id=orden_id,
                    version=1,
                    restaurant_branch_id=restaurant_branch_id,
                    supplier_unit_id=supplier_unit_id,
                    cart_id=cart_res["cart_id"],
                    delivery_date=delivery_date,
                    delivery_time=delivery_time,
                    delivery_type=delivery_type,
                    subtotal_without_tax=(
                        cart_res["subtotal_without_tax"]
                        if cart_res["subtotal_without_tax"]
                        else None
                    ),
                    tax=cart_res.get("tax", 0),
                    discount=None,
                    discount_code=None,
                    cashback=None,
                    cashback_transation_id=None,
                    shipping_cost=shipping_cost if shipping_cost else None,
                    packaging_cost=packaging_cost if packaging_cost else None,
                    service_fee=service_fee if service_fee else None,
                    total=cart_res["total"] if cart_res["total"] else None,
                    subtotal=cart_res["subtotal"] if cart_res["subtotal"] else None,
                    comments=comments if comments else None,
                    payment_method=payment_method if payment_method else None,
                    approved_by=approved_by,
                    created_by=core_user.id,
                )
            )
            # create delivery status
            await self.orden_status_repo.new(
                OrdenStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=status,
                    created_by=core_user.id,  # type: ignore
                )
            )

            # create payment status
            await self.orden_payment_repo.new(
                OrdenPayStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=paystatus,
                    created_by=core_user.id,  # type: ignore
                )
            )
        except Exception as e:
            logger.error(e)
            # if error creating delete orden
            await self.orden_status_repo.new(
                OrdenStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=OrdenStatusType(
                        DataTypeDecoder.get_orden_status_value("canceled")
                    ),
                    created_by=core_user.id,
                )
            )
            raise GQLApiException(
                msg="Error creating orden details",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

        # construct response
        orden_status = await self.orden_status_repo.get(orden_id)
        orden_status["status"] = DataTypeDecoder.get_orden_status_value(
            orden_status["status"]
        )
        orden["status"] = OrdenStatus(**orden_status)
        orden_details = await self.orden_det_repo.get(ord_details_uuid)
        if orden_details["delivery_time"]:
            orden_details["delivery_time"] = DeliveryTimeWindow.parse(
                orden_details["delivery_time"]
            )
        orden["details"] = OrdenDetails(**orden_details)
        orden_paystatus = await self.orden_payment_repo.get(orden_id)
        if orden_paystatus["status"]:
            orden_paystatus["status"] = DataTypeDecoder.get_orden_paystatus_value(
                orden_paystatus["status"]
            )
        orden["paystatus"] = OrdenPayStatus(**orden_paystatus)
        # branch
        _branch = await self.rest_branc_repo.get(restaurant_branch_id)
        rest_branch = RestaurantBranch(**_branch)
        _rest_bus_acc = await self.rest_buss_acc_repo.fetch(
            rest_branch.restaurant_business_id
        )
        if not _rest_bus_acc:
            raise GQLApiException(
                msg="Error fetch supplier_business_account",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        _branch = await self.rest_branc_repo.get(restaurant_branch_id)
        rest_branch = RestaurantBranch(**_branch)
        orden["branch"] = RestaurantBranchGQL(**_branch)
        # supplier
        sup_business, supp_bus_acc, sup_unit = None, None, None
        if supplier_business_id:
            sup_business = SupplierBusiness(
                **await self.supp_bus_repo.get(supplier_business_id)
            )
            supp_bus_acc = SupplierBusinessAccount(
                **await self.supp_bus_acc_repo.get(sup_business.id)
            )
            try:

                sup_unit = SupplierUnitGQL(
                    **await self.supp_unit_repo.get(supplier_unit_id),
                )
            except Exception as e:
                logger.error(e)
            orden["supplier"] = OrdenSupplierGQL(
                supplier_business=sup_business,
                supplier_business_account=supp_bus_acc,
                supplier_unit=sup_unit,
            )
            # send supplier notification - email
            if (
                sup_business.notification_preference == "email"
                and supp_bus_acc.email
                and orden_type == OrdenType.NORMAL
            ):
                try:
                    await send_supplier_email_confirmation(
                        f"Pedido de {rest_branch.branch_name}",
                        from_email={
                            "email": core_user.email,
                            "name": rest_branch.branch_name,
                        },
                        to_email={
                            "email": supp_bus_acc.email,
                            "name": sup_business.name,
                        },
                        orden_details=OrdenDetails(**orden_details),
                        branch_name=rest_branch.branch_name,
                        contact_number=(
                            supp_bus_acc.phone_number
                            if supp_bus_acc.phone_number
                            else ""
                        ),
                        delivery_address=rest_branch.full_address,
                        cart_products=cart_res["cart_product_res"],
                    )
                    # [TODO] send another email with link to upload invoice
                except Exception as e:
                    logger.warning("Issues sending supplier email")
                    logger.error(e)
            # send supplier notification - whatsapp
            if (
                sup_business.notification_preference == "whatsapp"
                and supp_bus_acc.phone_number
                and orden_type == OrdenType.NORMAL
            ):
                try:
                    send_supplier_whatsapp_confirmation(
                        to_wa={
                            "phone": supp_bus_acc.phone_number,
                            "name": sup_business.name,
                        },
                        orden_details=OrdenDetails(**orden_details),
                        branch_name=rest_branch.branch_name,
                        contact_number=ALIMA_SUPPORT_PHONE,
                        delivery_address=rest_branch.full_address,
                        cart_products=cart_res["cart_product_res"],
                    )
                    # [TODO] send another wa with link to upload invoice
                except Exception as e:
                    logger.warning("Issues sending supplier email")
                    logger.error(e)
            # send restaurant notification
            if orden_type == OrdenType.NORMAL:
                # send confirmation to the user that created the orden
                try:
                    _from = {
                        "email": SENDGRID_SINGLE_SENDER,
                        "name": sup_business.name if sup_business.name else "Alima",
                    }
                    if source_type == OrdenSourceType.ECOMMERCE:
                        await send_ecommerce_restaurant_email_confirmation(
                            sup_business.name if sup_business else "Proveedor",
                            f"Pedido para {sup_business.name if sup_business else 'Proveedor'}",
                            from_email=_from,
                            to_email={
                                "email": (
                                    _rest_bus_acc.email
                                    if _rest_bus_acc.email
                                    else "admin"
                                ),
                                "name": rest_branch.branch_name,
                            },
                            orden_details=OrdenDetails(**orden_details),
                            cart_products=cart_res["cart_product_res"],
                        )
                    else:
                        await send_ecommerce_restaurant_email_confirmation(
                            sup_business.name if sup_business else "Proveedor",
                            f"Pedido para {sup_business.name if sup_business else 'Proveedor'}",
                            from_email=_from,
                            to_email={
                                "email": core_user.email,
                                "name": f"{core_user.first_name} {core_user.last_name}",
                            },
                            orden_details=OrdenDetails(**orden_details),
                            cart_products=cart_res["cart_product_res"],
                        )
                except Exception as e:
                    logger.warning("Issues sending restaurant confirmation email")
                    logger.error(e)
        return OrdenGQL(**orden)

    async def edit_orden(
        self,
        firebase_id: str,
        orden_id: UUID,
        orden_type: Optional[OrdenType] = None,
        cart_products: Optional[List[CartProduct]] = None,
        status: Optional[OrdenStatusType] = None,
        comments: Optional[str] = None,
        payment_method: Optional[PayMethodType] = None,
        paystatus: Optional[PayStatusType] = None,
        delivery_date: Optional[date] = None,
        delivery_time: Optional[DeliveryTimeWindow] = None,
        delivery_type: Optional[SellingOption] = None,
        approved_by: Optional[UUID] = None,
        discount_code: Optional[str] = None,
        cashback_transation_id: Optional[UUID] = None,
        shipping_cost: Optional[float] = None,
        packaging_cost: Optional[float] = None,
        service_fee: Optional[float] = None,
    ) -> OrdenGQL:  # type: ignore
        # Validate date
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # update data
        orden = {}
        # orden type update
        if orden_type:
            await self.orden_repo.update(orden_id, orden_type)
        # status update
        if status:
            await self.orden_status_repo.new(
                OrdenStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=status,
                    created_by=core_user.id,
                )
            )
        # pay status update
        if paystatus:
            await self.orden_payment_repo.new(
                OrdenPayStatus(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    status=paystatus,
                    created_by=core_user.id,
                )
            )
        # orden details udpate
        modified_details = False
        details_dict = await self.orden_det_repo.get_last(orden_id)
        if details_dict["delivery_time"]:
            details_dict["delivery_time"] = DeliveryTimeWindow.parse(
                details_dict["delivery_time"]
            )
        details = OrdenDetails(**details_dict)
        if (
            comments is not None
            or payment_method
            or delivery_date
            or delivery_time
            or approved_by
            or shipping_cost
            or packaging_cost
            or service_fee
            or cart_products
        ):
            modified_details = True
            # if new products - replace all orden products in new cart
            if cart_products:
                cart_res = await self._build_cart(
                    core_user,
                    cart_products,
                    shipping_cost=shipping_cost,
                    packaging_cost=packaging_cost,
                    service_fee=service_fee,
                )
            else:
                # fetch products from original cart
                cart_produc_res = []
                for prod in await self.cart_prod_repo.search_with_tax(
                    cart_id=details.cart_id
                ):
                    supp_prod = dict(prod)
                    cprod = CartProductGQL(**sql_to_domain(prod, CartProduct))
                    cprod.supp_prod = SupplierProduct(**json.loads(supp_prod["tax_json"]))  # type: ignore
                    if cprod.supp_prod:
                        if isinstance(cprod.supp_prod.sell_unit, str):
                            cprod.supp_prod.sell_unit = UOMType(
                                cprod.supp_prod.sell_unit
                            )
                    cart_produc_res.append(cprod)
                cart_res = {
                    "cart_id": details.cart_id,
                    "cart_product_res": cart_produc_res,
                    "subtotal": details.subtotal,
                    "subtotal_without_tax": details.subtotal_without_tax,
                    "tax": details.tax,
                    "shipping_cost": shipping_cost,
                    "packaging_cost": packaging_cost,
                    "service_fee": service_fee,
                    "total": details.total,
                }

            if not approved_by:
                approved_by = details.approved_by
            if comments is None:
                comments = details.comments
            if not delivery_date:
                delivery_date = details.delivery_date
            if not delivery_time:
                delivery_time = details.delivery_time
            if not payment_method:
                if details.payment_method:
                    payment_method = PayMethodType(details.payment_method)

            await self.orden_det_repo.new(
                OrdenDetails(
                    id=uuid.uuid4(),
                    orden_id=orden_id,
                    version=details.version + 1,
                    restaurant_branch_id=details.restaurant_branch_id,
                    supplier_unit_id=details.supplier_unit_id,  # type: ignore
                    cart_id=cart_res["cart_id"],
                    delivery_date=delivery_date,
                    delivery_time=delivery_time,
                    delivery_type=delivery_type,
                    subtotal_without_tax=(
                        cart_res["subtotal_without_tax"]
                        if cart_res["subtotal_without_tax"]
                        else None
                    ),
                    tax=cart_res.get("tax", 0),
                    discount=None,
                    discount_code=None,
                    cashback=None,
                    cashback_transation_id=None,
                    shipping_cost=shipping_cost,
                    packaging_cost=packaging_cost,
                    service_fee=service_fee,
                    total=cart_res["total"] if cart_res["total"] else None,
                    subtotal=cart_res["subtotal"] if cart_res["subtotal"] else None,
                    comments=comments,
                    payment_method=payment_method,
                    approved_by=approved_by,
                    created_by=core_user.id,
                )
            )
        # build response
        orden = await self.orden_repo.get(orden_id)
        orden_status = await self.orden_status_repo.get_last(orden_id)
        orden_status["status"] = DataTypeDecoder.get_orden_status_value(
            orden_status["status"]
        )
        orden["status"] = OrdenStatus(**orden_status)
        orden_details = await self.orden_det_repo.get_last(orden_id)
        if orden_details["delivery_time"]:
            orden_details["delivery_time"] = DeliveryTimeWindow.parse(
                orden_details["delivery_time"]
            )
        orden["details"] = OrdenDetails(**orden_details)
        orden_paystatus = await self.orden_payment_repo.get_last(orden_id)
        if orden_paystatus["status"]:
            orden_paystatus["status"] = DataTypeDecoder.get_orden_paystatus_value(
                orden_paystatus["status"]
            )
        orden["paystatus"] = OrdenPayStatus(**orden_paystatus)

        # Agregar deleted
        rest_branch = RestaurantBranch(
            **await self.rest_branc_repo.get(orden_details["restaurant_branch_id"])
        )
        orden["branch"] = rest_branch
        rest_business_account = await self.rest_buss_acc_repo.fetch(
            rest_branch.restaurant_business_id
        )
        supp_unit = SupplierUnitGQL(
            **await self.supp_unit_repo.get(orden_details["supplier_unit_id"]),
        )
        supp_bus = SupplierBusiness(
            **await self.supp_bus_repo.get(supp_unit.supplier_business_id)
        )
        supp_bus_acc = SupplierBusinessAccount(
            **await self.supp_bus_acc_repo.get(supp_bus.id)
        )
        orden["supplier"] = OrdenSupplierGQL(
            supplier_business=supp_bus,
            supplier_business_account=supp_bus_acc,
            supplier_unit=supp_unit,
        )
        # send supplier notification - email
        client_email = (
            rest_business_account.email
            if (rest_business_account and rest_business_account.email)
            else core_user.email
        )
        if (
            supp_bus.notification_preference == "email"
            and supp_bus_acc.email
            and modified_details
        ):
            try:
                await send_supplier_email_confirmation(
                    f"Pedido Actualizado de {rest_branch.branch_name}",
                    from_email={
                        "email": client_email,
                        "name": rest_branch.branch_name,
                    },
                    to_email={
                        "email": supp_bus_acc.email,
                        "name": supp_bus.name,
                    },
                    orden_details=OrdenDetails(**orden_details),
                    branch_name=rest_branch.branch_name,
                    contact_number=(
                        supp_bus_acc.phone_number if supp_bus_acc.phone_number else ""
                    ),
                    delivery_address=rest_branch.full_address,
                    cart_products=cart_res["cart_product_res"],  # type: ignore - is guaranteed in logic
                )
                # [TODO] send another email with link to upload invoice
            except Exception as e:
                logger.warning("Issues sending supplier email")
                logger.error(e)
        # send supplier notification - whatsapp
        if (
            supp_bus.notification_preference == "whatsapp"
            and supp_bus_acc.phone_number
            and modified_details
        ):
            try:
                send_supplier_whatsapp_confirmation(
                    to_wa={
                        "phone": supp_bus_acc.phone_number,
                        "name": supp_bus.name,
                    },
                    branch_name=rest_branch.branch_name,
                    orden_details=OrdenDetails(**orden_details),
                    contact_number=ALIMA_SUPPORT_PHONE,
                    delivery_address=rest_branch.full_address,
                    cart_products=cart_res["cart_product_res"],  # type: ignore - is guaranteed in logic
                    notification_type="update_orden",
                )
                # [TODO] send another email with link to upload invoice
            except Exception as e:
                logger.warning("Issues sending supplier whatsapp")
                logger.error(e)
        if modified_details:
            # send confirmation to the user that updated the orden - if changed orden details
            try:
                await send_unformat_restaurant_email_confirmation(
                    f"Pedido Actualizado para {supp_bus.name if supp_bus else 'Proveedor'}",
                    from_email={
                        "email": SENDGRID_SINGLE_SENDER,
                        "name": supp_bus.name,
                    },
                    to_email={
                        "email": core_user.email,
                        "name": f"{core_user.first_name} {core_user.last_name}",
                    },
                    orden_details=OrdenDetails(**orden_details),
                    cart_products=cart_res["cart_product_res"],  # type: ignore - is guaranteed in logic
                    orden_number=orden["orden_number"],
                    rest_branch_name=rest_branch.branch_name,
                    cel_contact=supp_bus_acc.phone_number,  # type: ignore
                )
            except Exception as e:
                logger.warning("Issues sending restaurant confirmation email")
                logger.error(e)
        if status and not modified_details:
            try:
                if (
                    status == OrdenStatusType.CANCELED
                    or status == OrdenStatusType.DELIVERED
                ):
                    if supp_bus_acc.email:
                        # send email to supplier and restaurant
                        await send_supplier_changed_status_v2(
                            to_email={
                                "email": (
                                    supp_bus_acc.email
                                ),
                                "name": supp_bus.name,
                            },
                            status=status,
                            from_email={
                                "email": SENDGRID_SINGLE_SENDER,
                                "name": "Alima",
                            },
                            orden_details=OrdenDetails(**orden_details),
                            orden_number=orden["orden_number"],
                            rest_branch_name=rest_branch.branch_name,
                            cel_contact=supp_bus_acc.phone_number,  # type: ignore
                        )
                await send_restaurant_changed_status_v2(
                    to_email={
                        "email": client_email,
                        "name": rest_branch.branch_name,
                    },
                    from_email={
                        "email": SENDGRID_SINGLE_SENDER,
                        "name": supp_bus.name,
                    },
                    status=status,
                    orden_details=OrdenDetails(**orden_details),
                    orden_number=orden["orden_number"],
                    rest_branch_name=rest_branch.branch_name,
                    cel_contact=supp_bus_acc.phone_number,  # type: ignore
                )
            except Exception as e:
                logger.error(f"Error sending update status email: {e}")

        # return
        return OrdenGQL(**orden)

    async def fetch_orden_status(self, orden_id) -> OrdenStatus:  # type: ignore
        # get order status
        return OrdenStatus(**await self.orden_status_repo.get_last(orden_id))

    async def fetch_orden_paystatus(self, orden_id) -> List[OrdenPaystatusGQL]:
        # get order status
        ops_list = await self.orden_payment_repo.find(orden_id=orden_id)
        if not ops_list:
            raise GQLApiException(
                msg="Orden paystatus not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        _users = await self.core_user_repo.fetch_from_many(
            [ops.created_by for ops in ops_list]
        )
        # get payment recepts
        user_idx = {t.id: t for t in _users}
        # add payment receipts
        p_rects = await self.orden_payment_repo.find_payment_receipts(orden_id)
        # format response

        orden_payment_status_gql = []
        for ops in ops_list:
            core_user = user_idx.get(ops.created_by, None)
            ops.status = PayStatusType(DataTypeDecoder.get_orden_paystatus_value(ops.status))  # type: ignore
            orden_paystatus_gql = OrdenPaystatusGQL(
                paystatus=ops, core_user=core_user, pay_receipts=p_rects
            )
            orden_payment_status_gql.append(orden_paystatus_gql)
        # return
        return orden_payment_status_gql

    async def search_orden(
        self,
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
    ) -> List[OrdenGQL]:
        # data validateion
        if supplier_business_id:
            supplier_unit_id = (
                await self.supp_unit_repo.search(
                    supplier_business_id=supplier_business_id
                )
            )[0].id
        # query construction
        orden_atributes = []
        orden_values_view = {}
        orden_atributes.append(
            "sc.status_row_num = 1 and pc.paystatus_row_num = 1 and dc.details_row_num = 1 and"
        )
        if orden_id:
            orden_atributes.append(" ord.id=:orden_id and")
            orden_values_view["orden_id"] = orden_id
        if restaurant_branch_id:
            orden_atributes.append(" dc.restaurant_branch_id=:restaurant_branch_id and")
            orden_values_view["restaurant_branch_id"] = restaurant_branch_id
        if supplier_unit_id:
            orden_atributes.append(" dc.supplier_unit_id=:supplier_unit_id and")
            orden_values_view["supplier_unit_id"] = supplier_unit_id
        if payment_method:
            orden_atributes.append(" dc.payment_method=:payment_method and")
            orden_values_view["payment_method"] = payment_method.value
        if orden_type:
            orden_atributes.append(" ord.orden_type=:orden_type and")
            orden_values_view["orden_type"] = orden_type.value
        if status:
            orden_atributes.append(" sc.status=:status and")
            orden_values_view["status"] = DataTypeDecoder.get_orden_status_key(
                status.value
            )
        if paystatus:
            orden_atributes.append(" pc.status=:paystatus and")
            orden_values_view["paystatus"] = DataTypeDecoder.get_orden_paystatus_key(
                paystatus.value
            )
        if from_date:
            orden_atributes.append(" dc.delivery_date>=:from_date and")
            orden_values_view["from_date"] = from_date

        if to_date:
            orden_atributes.append(" dc.delivery_date<=:to_date and")
            orden_values_view["to_date"] = to_date

        if len(orden_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(orden_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await self.orden_repo.get_orders(filter_values, orden_values_view)

        ordenes_dir = []
        for r in _resp:
            info_dict = dict(r)
            orden_info = OrdenGQL(**sql_to_domain(r, Orden))
            orden_status = json.loads(info_dict["status_json"])
            orden_status.pop("status_row_num")
            if orden_status["status"]:
                orden_status["status"] = DataTypeDecoder.get_orden_status_value(
                    orden_status["status"]
                )
            orden_paystatus = json.loads(info_dict["paystatus_json"])
            orden_paystatus.pop("paystatus_row_num")
            if orden_paystatus["status"]:
                orden_paystatus["status"] = DataTypeDecoder.get_orden_paystatus_value(
                    orden_paystatus["status"]
                )
            orden_details = json.loads(info_dict["details_json"])
            orden_details.pop("details_row_num")
            if orden_details["delivery_time"]:
                orden_details["delivery_time"] = DeliveryTimeWindow.parse(
                    orden_details["delivery_time"]
                )
            if orden_details["payment_method"]:
                orden_details["payment_method"] = PayMethodType(
                    orden_details["payment_method"]
                )

            orden_info.status = OrdenStatus(**orden_status)
            orden_info.paystatus = OrdenPayStatus(**orden_paystatus)
            orden_info.details = OrdenDetails(**orden_details)
            if orden_info.status.created_at:
                orden_info.status.created_at = from_iso_format(
                    orden_info.status.created_at  # type: ignore
                )

            if orden_info.paystatus.created_at:
                orden_info.paystatus.created_at = from_iso_format(
                    orden_info.paystatus.created_at  # type: ignore
                )
            if orden_info.details.created_at:
                orden_info.details.created_at = from_iso_format(
                    orden_info.details.created_at  # type: ignore
                )
            if orden_info.details.delivery_date:
                orden_info.details.delivery_date = datetime.fromisoformat(
                    orden_info.details.delivery_date  # type: ignore
                )
            # cart products
            _cart = []
            for prod in await self.cart_prod_repo.find_with_tax(
                cart_id=orden_info.details.cart_id
            ):
                supp_prod = dict(prod)
                cprod = CartProductGQL(**sql_to_domain(prod, CartProduct))
                if isinstance(cprod.sell_unit, str):
                    cprod.sell_unit = UOMType(cprod.sell_unit)
                cprod.supp_prod = SupplierProduct(**json.loads(supp_prod["tax_json"]))  # type: ignore
                if cprod.supp_prod:
                    if isinstance(cprod.supp_prod.sell_unit, str):
                        cprod.supp_prod.sell_unit = UOMType(cprod.supp_prod.sell_unit)
                    if isinstance(cprod.supp_prod.buy_unit, str):
                        cprod.supp_prod.buy_unit = UOMType(cprod.supp_prod.buy_unit)
                _cart.append(cprod)
            orden_info.cart = _cart
            # branch
            branch_dict = await self.rest_branc_repo.fetch(
                orden_info.details.restaurant_branch_id
            )
            orden_info.branch = RestaurantBranchGQL(**branch_dict)
            # supplier
            sup_unit_dict = await self.supp_unit_repo.fetch(
                orden_info.details.supplier_unit_id
            )
            sup_unit = SupplierUnitGQL(**sup_unit_dict)
            sup_business = SupplierBusiness(
                **await self.supp_bus_repo.fetch(sup_unit_dict["supplier_business_id"])
            )
            supp_bus_acc = None
            if orden_info.orden_type == OrdenType.NORMAL.value:
                supp_bus_acc = SupplierBusinessAccount(
                    **await self.supp_bus_acc_repo.fetch(sup_business.id)
                )
            orden_info.supplier = OrdenSupplierGQL(
                supplier_business=sup_business,
                supplier_business_account=supp_bus_acc,
                supplier_unit=sup_unit,
            )
            ordenes_dir.append(orden_info)
        return ordenes_dir

    async def find_orden(
        self,
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
    ) -> List[OrdenGQL]:
        # data validateion
        if supplier_business_id:
            supplier_unit_id = (
                await self.supp_unit_repo.search(
                    supplier_business_id=supplier_business_id
                )
            )[0].id
        # query construction
        orden_atributes = []
        orden_values_view = {}
        orden_atributes.append(
            "sc.status_row_num = 1 and pc.paystatus_row_num = 1 and dc.details_row_num = 1 and"
        )
        if orden_id:
            orden_atributes.append(" ord.id=:orden_id and")
            orden_values_view["orden_id"] = orden_id
        if restaurant_branch_id:
            orden_atributes.append(" dc.restaurant_branch_id=:restaurant_branch_id and")
            orden_values_view["restaurant_branch_id"] = restaurant_branch_id
        if supplier_unit_id:
            orden_atributes.append(" dc.supplier_unit_id=:supplier_unit_id and")
            orden_values_view["supplier_unit_id"] = supplier_unit_id
        if payment_method:
            orden_atributes.append(" dc.payment_method=:payment_method and")
            orden_values_view["payment_method"] = payment_method.value
        if orden_type:
            orden_atributes.append(" ord.orden_type=:orden_type and")
            orden_values_view["orden_type"] = orden_type.value
        if status:
            orden_atributes.append(" sc.status=:status and")
            orden_values_view["status"] = DataTypeDecoder.get_orden_status_key(
                status.value
            )
        if paystatus:
            orden_atributes.append(" pc.status=:paystatus and")
            orden_values_view["paystatus"] = DataTypeDecoder.get_orden_paystatus_key(
                paystatus.value
            )
        if from_date:
            orden_atributes.append(" dc.delivery_date>=:from_date and")
            orden_values_view["from_date"] = from_date

        if to_date:
            orden_atributes.append(" dc.delivery_date<=:to_date and")
            orden_values_view["to_date"] = to_date

        if len(orden_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(orden_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await self.orden_repo.find_orders(filter_values, orden_values_view)

        ordenes_dir = []
        for r in _resp:
            info_dict = dict(r)
            orden_info = OrdenGQL(**sql_to_domain(r, Orden))
            orden_status = json.loads(info_dict["status_json"])
            orden_status.pop("status_row_num")
            if orden_status["status"]:
                orden_status["status"] = DataTypeDecoder.get_orden_status_value(
                    orden_status["status"]
                )
            orden_paystatus = json.loads(info_dict["paystatus_json"])
            orden_paystatus.pop("paystatus_row_num")
            if orden_paystatus["status"]:
                orden_paystatus["status"] = DataTypeDecoder.get_orden_paystatus_value(
                    orden_paystatus["status"]
                )
            orden_details = json.loads(info_dict["details_json"])
            orden_details.pop("details_row_num")
            if orden_details["delivery_time"]:
                orden_details["delivery_time"] = DeliveryTimeWindow.parse(
                    orden_details["delivery_time"]
                )
            if orden_details["payment_method"]:
                orden_details["payment_method"] = PayMethodType(
                    orden_details["payment_method"]
                )

            orden_info.status = OrdenStatus(**orden_status)
            orden_info.paystatus = OrdenPayStatus(**orden_paystatus)
            orden_info.details = OrdenDetails(**orden_details)
            if orden_info.status.created_at:
                orden_info.status.created_at = from_iso_format(
                    orden_info.status.created_at  # type: ignore
                )

            if orden_info.paystatus.created_at:
                orden_info.paystatus.created_at = from_iso_format(
                    orden_info.paystatus.created_at  # type: ignore
                )
            if orden_info.details.created_at:
                orden_info.details.created_at = from_iso_format(
                    orden_info.details.created_at  # type: ignore
                )
            if orden_info.details.delivery_date:
                orden_info.details.delivery_date = datetime.fromisoformat(
                    orden_info.details.delivery_date  # type: ignore
                )
            # cart products
            _cart = []
            for prod in await self.cart_prod_repo.find_with_tax(
                cart_id=orden_info.details.cart_id
            ):
                supp_prod = dict(prod)
                cprod = CartProductGQL(**sql_to_domain(prod, CartProduct))
                if isinstance(cprod.sell_unit, str):
                    cprod.sell_unit = UOMType(cprod.sell_unit)
                cprod.supp_prod = SupplierProduct(**json.loads(supp_prod["tax_json"]))  # type: ignore
                if cprod.supp_prod:
                    if isinstance(cprod.supp_prod.sell_unit, str):
                        cprod.supp_prod.sell_unit = UOMType(cprod.supp_prod.sell_unit)
                    if isinstance(cprod.supp_prod.buy_unit, str):
                        cprod.supp_prod.buy_unit = UOMType(cprod.supp_prod.buy_unit)
                _cart.append(cprod)
            orden_info.cart = _cart
            # branch
            branch_dict = await self.rest_branc_repo.fetch(
                orden_info.details.restaurant_branch_id
            )
            orden_info.branch = RestaurantBranchGQL(**branch_dict)
            # supplier
            sup_unit_dict = await self.supp_unit_repo.fetch(
                orden_info.details.supplier_unit_id
            )
            sup_unit = SupplierUnitGQL(**sup_unit_dict)
            sup_business = SupplierBusiness(
                **await self.supp_bus_repo.fetch(sup_unit_dict["supplier_business_id"])
            )
            supp_bus_acc = None
            if orden_info.orden_type == OrdenType.NORMAL.value:
                supp_bus_acc = SupplierBusinessAccount(
                    **await self.supp_bus_acc_repo.fetch(sup_business.id)
                )
            orden_info.supplier = OrdenSupplierGQL(
                supplier_business=sup_business,
                supplier_business_account=supp_bus_acc,
                supplier_unit=sup_unit,
            )
            ordenes_dir.append(orden_info)
        return ordenes_dir

    async def search_ordens_with_many(self, orden_ids: List[UUID]) -> List[OrdenGQL]:
        # query construction
        orden_atributes = []
        orden_values_view = {}
        orden_atributes.append(
            "sc.status_row_num = 1 and pc.paystatus_row_num = 1 and dc.details_row_num = 1 and"
        )
        if orden_ids:
            orden_atributes.append(f" ord.id in {list_into_strtuple(orden_ids)} and")
        if len(orden_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(orden_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await self.orden_repo.get_orders(filter_values, orden_values_view)

        ordenes_dir = []
        for r in _resp:
            info_dict = dict(r)
            orden_info = OrdenGQL(**sql_to_domain(r, Orden))
            orden_status = json.loads(info_dict["status_json"])
            orden_status.pop("status_row_num")
            if orden_status["status"]:
                orden_status["status"] = DataTypeDecoder.get_orden_status_value(
                    orden_status["status"]
                )
            orden_paystatus = json.loads(info_dict["paystatus_json"])
            orden_paystatus.pop("paystatus_row_num")
            if orden_paystatus["status"]:
                orden_paystatus["status"] = DataTypeDecoder.get_orden_paystatus_value(
                    orden_paystatus["status"]
                )
            orden_details = json.loads(info_dict["details_json"])
            orden_details.pop("details_row_num")
            if orden_details["delivery_time"]:
                orden_details["delivery_time"] = DeliveryTimeWindow.parse(
                    orden_details["delivery_time"]
                )
            if orden_details["payment_method"]:
                orden_details["payment_method"] = PayMethodType(
                    orden_details["payment_method"]
                )

            orden_info.status = OrdenStatus(**orden_status)
            orden_info.paystatus = OrdenPayStatus(**orden_paystatus)
            orden_info.details = OrdenDetails(**orden_details)
            if orden_info.status.created_at:
                orden_info.status.created_at = from_iso_format(
                    orden_info.status.created_at  # type: ignore
                )

            if orden_info.paystatus.created_at:
                orden_info.paystatus.created_at = from_iso_format(
                    orden_info.paystatus.created_at  # type: ignore
                )
            if orden_info.details.created_at:
                orden_info.details.created_at = from_iso_format(
                    orden_info.details.created_at  # type: ignore
                )
            if orden_info.details.delivery_date:
                orden_info.details.delivery_date = datetime.fromisoformat(
                    orden_info.details.delivery_date  # type: ignore
                )
            # cart products
            _cart = []
            for prod in await self.cart_prod_repo.find_with_tax(
                cart_id=orden_info.details.cart_id
            ):
                supp_prod = dict(prod)
                cprod = CartProductGQL(**sql_to_domain(prod, CartProduct))
                if isinstance(cprod.sell_unit, str):
                    cprod.sell_unit = UOMType(cprod.sell_unit)
                cprod.supp_prod = SupplierProduct(**json.loads(supp_prod["tax_json"]))  # type: ignore
                if cprod.supp_prod:
                    if isinstance(cprod.supp_prod.sell_unit, str):
                        cprod.supp_prod.sell_unit = UOMType(cprod.supp_prod.sell_unit)
                    if isinstance(cprod.supp_prod.buy_unit, str):
                        cprod.supp_prod.buy_unit = UOMType(cprod.supp_prod.buy_unit)
                _cart.append(cprod)
            orden_info.cart = _cart
            # branch
            branch_dict = await self.rest_branc_repo.fetch(
                orden_info.details.restaurant_branch_id
            )
            orden_info.branch = RestaurantBranchGQL(**branch_dict)
            # supplier
            sup_unit_dict = await self.supp_unit_repo.fetch(
                orden_info.details.supplier_unit_id
            )
            sup_unit = SupplierUnitGQL(**sup_unit_dict)
            sup_business = SupplierBusiness(
                **await self.supp_bus_repo.fetch(sup_unit_dict["supplier_business_id"])
            )
            supp_bus_acc = None
            if orden_info.orden_type == OrdenType.NORMAL.value:
                supp_bus_acc = SupplierBusinessAccount(
                    **await self.supp_bus_acc_repo.fetch(sup_business.id)
                )
            orden_info.supplier = OrdenSupplierGQL(
                supplier_business=sup_business,
                supplier_business_account=supp_bus_acc,
                supplier_unit=sup_unit,
            )
            ordenes_dir.append(orden_info)
        return ordenes_dir

    async def merge_ordenes_invoices(
        self, ordenes: List[OrdenGQL], invoices: List[MxInvoiceGQL]
    ) -> List[Dict[Any, Any]]:
        """Merge ordenes and invoices

        Parameters
        ----------
        ordenes : List[OrdenGQL]
        invoices : List[MxInvoiceGQL]

        Returns
        -------
        List[Dict[Any, Any]]
        """
        # generate invoices idx
        invoices_idx: Dict[str, MxInvoiceGQL] = {}
        for inv in invoices:
            if not inv.orden_id:
                continue
            invoices_idx[str(inv.orden_id)] = inv
        # merge ordenes and invoices
        ordenes_res = []
        for ord in ordenes:
            if not ord.details:
                logger.warning("Orden has no details")
                continue
            # orden details
            _id = str(ord.details.orden_id)
            _dets = {
                k: v
                for k, v in ord.details.__dict__.items()
                if ("id" not in k and "_by" not in k)
            }
            _dets["id"] = _id
            _dets["orden_number"] = ord.orden_number
            _dets["delivery_time"] = str(_dets["delivery_time"])
            _dets["delivery_type"] = (
                "Recolección" if _dets["delivery_type"] == "pickup" else "Entrega"
            )
            _dets["last_updated_at"] = (
                ord.details.created_at.astimezone(APP_TZ).strftime("%Y-%m-%d %H:%M CST")
                if ord.details.created_at
                else ""
            )
            # use Orden created at instead of Orden details created at
            _dets["created_at"] = (
                ord.created_at.astimezone(APP_TZ).strftime("%Y-%m-%d %H:%M CST")
                if ord.created_at
                else ""
            )
            _dets["payment_method"] = DataTypeTraslate.get_pay_method_encode(
                _dets["payment_method"].value
            )
            _dets["subtotal_without_tax"] = (
                round(_dets["subtotal_without_tax"], 2)
                if _dets["subtotal_without_tax"]
                else ""
            )
            _dets["tax"] = round(_dets["tax"], 2) if _dets["tax"] else ""
            # status
            if ord.status is not None and ord.status.status is not None:
                _dets["status"] = DataTypeTraslate.get_orden_status_encode(ord.status.status)  # type: ignore
                # _dets["status_time"] = ord.status.created_at  # asked to be removed
            else:
                _dets["status"], _dets["status_time"] = "", ""
            # paystatus
            if ord.paystatus is not None and ord.paystatus.status is not None:
                _dets["paystatus"] = DataTypeTraslate.get_pay_status_encode(ord.paystatus.status)  # type: ignore
                if ord.paystatus.created_at:
                    _dets["paystatus_time"] = ord.paystatus.created_at.astimezone(
                        APP_TZ
                    ).strftime("%Y-%m-%d %H:%M CST")
                else:
                    _dets["paystatus_time"] = ""
            else:
                _dets["paystatus"], _dets["paystatus_time"] = "", ""
            # supplier
            if ord.supplier is not None and ord.supplier.supplier_business:
                _dets["supplier"] = ord.supplier.supplier_business.name
            else:
                _dets["supplier"] = ""
            # restaurant
            if ord.branch is not None:
                _dets["restaurant_branch"] = ord.branch.branch_name
            else:
                _dets["restaurant_branch"] = ""
            # invoice
            if _id in invoices_idx:
                _inv = invoices_idx[_id]
                _dets["uuid_factura"] = str(_inv.sat_invoice_uuid)
                _dets["folio_factura"] = str(_inv.invoice_number)
                _dets["valor_factura"] = _inv.total
            else:
                _dets["uuid_factura"] = ""
                _dets["folio_factura"] = ""
                _dets["valor_factura"] = ""
            # append
            ordenes_res.append(_dets)
        return ordenes_res

    async def add_auto_payment_receipt(
        self,
        core_user_id: UUID,
        orden_ids: List[UUID],
        payment_value: float,
        payment_day: Optional[date] = None,
        comments: Optional[str] = None,
        receipt_file: Optional[str] = None,
        mx_invoice_complement_id: Optional[UUID] = None,
    ) -> PaymentReceiptGQL:
        """
        Adds a payment receipt to the database and associates it with the given orden IDs.

        Args:
            firebase_id (str): The Firebase ID of the user creating the payment receipt.
            orden_ids (List[UUID]): A list of UUIDs representing the orden IDs to associate with the payment receipt.
            payment_value (float): The value of the payment receipt.
            comments (Optional[str], optional): Optional comments about the payment receipt. Defaults to None.
            receipt_file (Optional[str], optional): The file name of the receipt evidence file. Defaults to None.

        Returns:
            PaymentReceiptGQL
                Created payment receipt and its associated orden IDs.

        Raises:
            GQLApiException
                If the user with the given Firebase ID is not found,
                or if there is an error creating the payment receipt
                or its associations with the orden IDs.
        """
        # create receipt
        rct = PaymentReceipt(
            id=uuid.uuid4(),
            payment_value=payment_value,
            evidence_file=receipt_file,
            comments=comments,
            created_by=core_user_id,
            payment_day=payment_day if payment_day else datetime.utcnow(),
        )
        rct_id = await self.orden_payment_repo.add_payment_receipt(rct)
        if not rct_id:
            raise GQLApiException(
                msg="Error creating payment receipt",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create a receipt order record per each orden id
        rct_ords = []
        for orden_id in orden_ids:
            tmp_rct_ord = PaymentReceiptOrden(
                id=uuid.uuid4(),
                payment_receipt_id=rct.id,
                orden_id=orden_id,
                created_by=core_user_id,
                mx_invoice_complement_id=(
                    mx_invoice_complement_id if mx_invoice_complement_id else None
                ),
            )
            if not await self.orden_payment_repo.add_payment_receipt_association(
                tmp_rct_ord
            ):
                raise GQLApiException(
                    msg="Error creating payment receipt orden",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            rct_ords.append(tmp_rct_ord)
        # build response
        rct_gql = PaymentReceiptGQL(
            id=rct.id,
            payment_value=rct.payment_value,
            evidence_file=rct.evidence_file,
            comments=rct.comments,
            payment_day=rct.payment_day,
            created_by=core_user_id,
            created_at=rct.created_at,
            ordenes=rct_ords,
        )
        return rct_gql

    async def add_payment_receipt(
        self,
        firebase_id: str,
        orden_ids: List[UUID],
        payment_value: float,
        payment_day: Optional[date] = None,
        comments: Optional[str] = None,
        receipt_file: Optional[str] = None,
        mx_invoice_complement_id: Optional[UUID] = None,
    ) -> PaymentReceiptGQL:
        """
        Adds a payment receipt to the database and associates it with the given orden IDs.

        Args:
            firebase_id (str): The Firebase ID of the user creating the payment receipt.
            orden_ids (List[UUID]): A list of UUIDs representing the orden IDs to associate with the payment receipt.
            payment_value (float): The value of the payment receipt.
            comments (Optional[str], optional): Optional comments about the payment receipt. Defaults to None.
            receipt_file (Optional[str], optional): The file name of the receipt evidence file. Defaults to None.

        Returns:
            PaymentReceiptGQL
                Created payment receipt and its associated orden IDs.

        Raises:
            GQLApiException
                If the user with the given Firebase ID is not found,
                or if there is an error creating the payment receipt
                or its associations with the orden IDs.
        """
        # get supplier & core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create receipt
        rct = PaymentReceipt(
            id=uuid.uuid4(),
            payment_value=payment_value,
            evidence_file=receipt_file,
            comments=comments,
            created_by=core_user.id,
            payment_day=payment_day if payment_day else datetime.utcnow(),
        )
        rct_id = await self.orden_payment_repo.add_payment_receipt(rct)
        if not rct_id:
            raise GQLApiException(
                msg="Error creating payment receipt",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create a receipt order record per each orden id
        rct_ords = []
        for orden_id in orden_ids:
            tmp_rct_ord = PaymentReceiptOrden(
                id=uuid.uuid4(),
                payment_receipt_id=rct.id,
                orden_id=orden_id,
                created_by=core_user.id,
                mx_invoice_complement_id=(
                    mx_invoice_complement_id if mx_invoice_complement_id else None
                ),
            )
            if not await self.orden_payment_repo.add_payment_receipt_association(
                tmp_rct_ord
            ):
                raise GQLApiException(
                    msg="Error creating payment receipt orden",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            rct_ords.append(tmp_rct_ord)
        # build response
        rct_gql = PaymentReceiptGQL(
            id=rct.id,
            payment_value=rct.payment_value,
            evidence_file=rct.evidence_file,
            comments=rct.comments,
            payment_day=rct.payment_day,
            created_by=core_user.id,
            created_at=rct.created_at,
            ordenes=rct_ords,
        )
        return rct_gql

    async def edit_payment_receipt(
        self,
        firebase_id: str,
        payment_receipt_id: UUID,
        payment_value: Optional[float] = None,
        comments: Optional[str] = None,
        payment_day: Optional[date] = None,
        receipt_file: Optional[str] = None,
        orden_ids: Optional[List[UUID]] = None,
        # mx_invoice_complement_id: Optional[UUID] = None,
    ) -> PaymentReceiptGQL:
        """
        Edits a payment receipt with the given ID, updating its payment value,
        comments, receipt file, and/or associated orders.
        If any of the given values is None, it will not be updated.

        Raises
            GQLApiException
                If the user or payment receipt is not found,
                or if there is an error updating the receipt or its associations.

        Returns
            PaymentReceiptGQL
                Object with the updated information.
        """
        # get supplier & core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get receipt
        rct = await self.orden_payment_repo.fetch_payment_receipt(payment_receipt_id)
        if not rct:
            raise GQLApiException(
                msg="Error fetching payment receipt",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # update values
        if payment_value is not None:
            rct.payment_value = payment_value
        if comments is not None:
            rct.comments = comments
        else:
            rct.comments = None
        if receipt_file is not None:
            rct.evidence_file = receipt_file
        else:
            rct.evidence_file = None
        if payment_day is not None:
            rct.payment_day = payment_day
        # update receipt
        if not await self.orden_payment_repo.edit_payment_receipt(rct):
            raise GQLApiException(
                msg="Error updating payment receipt",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        # build response
        rct_gql = PaymentReceiptGQL(
            id=rct.id,
            payment_value=rct.payment_value,
            evidence_file=rct.evidence_file,
            comments=rct.comments,
            created_by=core_user.id,
            payment_day=rct.payment_day,
            created_at=rct.created_at,
        )
        # if orden ids - update associations
        if orden_ids is not None and len(orden_ids) > 0:
            ord_receipts = [
                PaymentReceiptOrden(
                    id=uuid.uuid4(),
                    payment_receipt_id=rct.id,
                    orden_id=oid,
                    created_by=core_user.id,
                    # mx_invoice_complement_id=mx_invoice_complement_id if mx_invoice_complement_id else None
                )
                for oid in orden_ids
            ]
            if await self.orden_payment_repo.edit_payment_receipt_association(
                ord_receipts
            ):
                # add receipt to response
                rct_gql.ordenes = ord_receipts  # type: ignore
            else:
                raise GQLApiException(
                    msg="Error updating payment receipt association",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # return
        return rct_gql

    async def get_customer_payments_by_dates(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        comments: Optional[str] = None,
        page: Optional[int] = 1,
        page_size: Optional[int] = 20,
    ) -> List[PaymentReceiptGQL]:
        # fetch supplier user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_user = await self.supplier_user_repo.fetch(core_user.id)
        if not supplier_user:
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch supplier unit and supplier_business permissions
        supplier_unit = await self.supp_unit_repo.fetch(supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Supplier Unit not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        su_perms = await self.supplier_user_perms_repo.fetch_by_supplier_business(
            supplier_unit["supplier_business_id"]
        )
        # verify core user has access to supplier unit
        _user_w_access = False
        if su_perms:
            if supplier_user["id"] in [sup["supplier_user_id"] for sup in su_perms]:
                _user_w_access = True
        if not _user_w_access:
            raise GQLApiException(
                msg="User has no access to this supplier unit",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch payment receipts
        payrecs = await self.orden_payment_repo.find_payment_receipts_by_dates(
            supplier_unit_id, from_date, until_date, comments, page, page_size
        )
        mx_invoice_complement_ids = []
        for p in payrecs:
            if p["mx_invoice_complement_id"] is not None:
                mx_invoice_complement_ids.append(p["mx_invoice_complement_id"])
        if len(mx_invoice_complement_ids) == 0:
            mxi_s = []
        else:
            mxi_s = await self.mx_invoice_repo.find_by_many(list_into_strtuple(mx_invoice_complement_ids))  # type: ignore
        if not payrecs:
            logger.warning("No payment receipts found")
            return []
        # build response
        list_payrecs: List[PaymentReceiptGQL] = []
        pos_idx = {}
        for pr in payrecs:
            if pr["id"] in pos_idx:
                idx = pos_idx[pr["id"]]
                payment_complement = get_payment_complement(mxi_s, pr)
                list_payrecs[idx].ordenes.append(
                    PaymentReceiptOrdenGQL(
                        id=pr["orden_id"],
                        payment_receipt_id=pr["id"],
                        orden_id=pr["orden_id"],
                        created_by=pr["created_by"],
                        mx_invoice_complement_id=(
                            payment_complement.id
                            if isinstance(payment_complement, MxInvoiceComplementGQL)
                            else None
                        ),
                        payment_complement=payment_complement,
                        created_at=pr["created_at"],
                    )
                )
                continue
            pr_gql = PaymentReceiptGQL(
                id=pr["id"],
                payment_value=pr["payment_value"],
                evidence_file=pr["evidence_file"],
                comments=pr["comments"],
                payment_day=pr["payment_day"],
                created_by=pr["created_by"],
                created_at=pr["created_at"],
                last_updated=pr["last_updated"],
            )

            payment_complement = get_payment_complement(mxi_s, pr)
            pr_gql.ordenes = [
                PaymentReceiptOrdenGQL(
                    id=pr["pro_id"],
                    payment_receipt_id=pr["id"],
                    orden_id=pr["orden_id"],
                    deleted=pr["pro_deleted"],
                    created_by=pr["pro_created_by"],
                    created_at=pr["pro_created_at"],
                    mx_invoice_complement_id=(
                        payment_complement.id
                        if isinstance(payment_complement, MxInvoiceComplementGQL)
                        else None
                    ),
                    payment_complement=payment_complement,
                )
            ]
            list_payrecs.append(pr_gql)
            pos_idx[pr["id"]] = len(list_payrecs) - 1
        return list_payrecs

    async def format_payments_to_export(
        self, payments: List[PaymentReceiptGQL]
    ) -> List[Dict[Any, Any]]:
        # sort payments by id
        sorted_pays = sorted(payments, key=lambda pym: pym.id)
        # payments formatted
        frmt_pays = []
        # serialize each invoice
        for s_pay in sorted_pays:
            # skip payemnts already added
            _pay_dict = {}
            for k, v in s_pay.__dict__.items():
                if "_by" in k or k == "ordenes" or "_file" in k:
                    pass
                elif isinstance(v, datetime):
                    _pay_dict[k] = v.astimezone(APP_TZ).strftime("%Y-%m-%d %H:%M CST")
                elif isinstance(v, UUID):
                    _pay_dict[k] = str(v)
                elif k == "payment_value":
                    _pay_dict[k] = str(round(v, 2)) if v else ""
                else:
                    _pay_dict[k] = str(v) if v else ""
            if s_pay.ordenes:
                _pay_dict["orden_ids"] = ",".join(
                    [str(o.orden_id) for o in s_pay.ordenes]
                )
            else:
                _pay_dict["orden_ids"] = ""
            frmt_pays.append(_pay_dict)
        # return
        return frmt_pays

    async def count_daily_ordenes(
        self, supplier_business_id: UUID, tz: pytz.BaseTzInfo = APP_TZ
    ) -> int:
        # Get SCT current date
        cst_now = datetime.now(tz)
        cst_day = cst_now.date()
        # # Get the start of the current date
        # start_of_day_cst = datetime.combine(cst_day, datetime.min.time())
        # # Get the end of the current date
        # end_of_day_cst = datetime.combine(cst_day, datetime.max.time())
        # # convert cst datetimes into utc
        # start_of_day = start_of_day_cst.astimezone(pytz.utc)
        # end_of_day = end_of_day_cst.astimezone(pytz.utc)

        # Get the start and end of the current date in the desired timezone
        start_of_day_cst = tz.localize(
            datetime(cst_day.year, cst_day.month, cst_day.day, 0, 0, 0)
        )
        end_of_day_cst = tz.localize(
            datetime(cst_day.year, cst_day.month, cst_day.day, 23, 59, 59)
        )

        # Convert to UTC
        start_of_day = start_of_day_cst.astimezone(pytz.utc)
        end_of_day = end_of_day_cst.astimezone(pytz.utc)
        ordenes = await self.orden_repo.get_by_created_at_range(
            supplier_business_id=supplier_business_id,
            from_date=datetime(
                start_of_day.year,
                start_of_day.month,
                start_of_day.day,
                start_of_day.hour,
                start_of_day.minute,
                start_of_day.second,
            ),
            until_date=datetime(
                end_of_day.year,
                end_of_day.month,
                end_of_day.day,
                end_of_day.hour,
                end_of_day.minute,
                end_of_day.second,
            ),
        )
        if len(ordenes) == 0:
            return 0
        return len(ordenes)


def get_payment_complement(
    mxi_s: List[Any], pr: Dict[Any, Any]
) -> MxInvoiceComplementGQL | None:
    for mxi in mxi_s:
        if pr["mx_invoice_complement_id"] == mxi["id"]:
            payment_complement = MxInvoiceComplementGQL(
                id=mxi["id"],
                sat_invoice_uuid=mxi["sat_invoice_uuid"],
                total=mxi["total"],
                pdf_file=(
                    base64.b64encode(mxi["pdf_file"]).decode("utf-8")
                    if isinstance(mxi["pdf_file"], bytes)
                    else None
                ),
                xml_file=(
                    base64.b64encode(mxi["xml_file"]).decode("utf-8")
                    if isinstance(mxi["xml_file"], bytes)
                    else None
                ),
            )
            return payment_complement
    return None


def get_stripe_tag(tags: List[RestaurantBranchTag]) -> str | NoneType:
    for tag in tags:
        if tag.tag_key == "StripeId":
            return tag.tag_value
    return None


async def orden_delivered_script_execution_wrapper(
    exec_id: UUID,
    repo: ScriptExecutionRepository,
    _handler: OrdenHandlerInterface,
    integrations_weebhook_partner_handler: IntegrationWebhookHandlerInterface,
    rest_branch_repo: RestaurantBranchRepositoryInterface,
    orden_id: Optional[UUID] = None,
):
    # 3. Dentro del Background task: ejecutar script as a background task
    # 4. Dentro del Background task: Actualizar registro en DB con resultado de script
    try:
        logger.info(f"Executing script: {exec_id}")
        if not orden_id:
            raise GQLApiException(
                msg="Orden ID is required",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        logger.info(f"Orden ID: {orden_id}")
        import pdb

        pdb.set_trace()
        try:
            # call handler
            _resp = await _handler.search_orden(orden_id=orden_id)
            if not _resp:
                logger.info(f"Orden not found: {orden_id}")
                raise GQLApiException(
                    msg="Orden not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            logger.info(f"Orden: {_resp[0]}")
            if (
                not _resp[0].branch
                or not _resp[0].details
                or not _resp[0].supplier
                or not _resp[0].supplier.supplier_business_account
                or not _resp[0].supplier.supplier_business_account.email
                or not _resp[0].supplier.supplier_business
                or _resp[0].details.total is None
            ):
                raise GQLApiException(
                    msg="Error to get branch info",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            logger.info(f"Orden: {_resp[0].orden_number}")
            # verify order is delivered
            if (
                _resp[0].status is None
                or OrdenStatusType(_resp[0].status.status) != OrdenStatusType.DELIVERED
            ):
                raise GQLApiException(
                    msg="Orden is not delivered",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            if _resp[0].details.payment_method != PayMethodType.TRANSFER:
                return True
            workflow_vars = await integrations_weebhook_partner_handler.get_vars(
                _resp[0].supplier.supplier_business.id
            )
            if not workflow_vars:
                raise GQLApiException(
                    msg="Error to get workflow vars",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )

            branch_tags = await rest_branch_repo.fetch_tags(_resp[0].branch.id)
            stripe_value = get_stripe_tag(branch_tags)
            if not stripe_value:
                return True
            workflow_vars_json = json.loads(workflow_vars.vars)
            stripe_api_secret = workflow_vars_json.get("stripe_api_secret")
            if not stripe_api_secret:
                raise GQLApiException(
                    msg="Error to get stripe api secret",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            logger.info(f"Stripe Value: {stripe_value}")
            stripe_api = StripeApi(
                app_name=get_app(), stripe_api_secret=stripe_api_secret
            )
            logger.info(f"Stripe API: {stripe_api}")
            try:
                stripe_api.create_transfer_payment_intent(
                    stripe_customer_id=stripe_value,
                    charge_description=f"PEDIDO: {_resp[0].orden_number}",
                    charge_amount=_resp[0].details.total,
                    email_to_confirm=_resp[0].supplier.supplier_business_account.email,
                    currency=StripeCurrency.MXN,
                    charge_metadata={
                        "orden_id": str(_resp[0].id),
                        "supplier_unit_id": str(_resp[0].details.supplier_unit_id),
                        "restaurant_branch_id": str(
                            _resp[0].details.restaurant_branch_id
                        ),
                    },
                )
            except Exception as e:
                # send email
                await send_email(
                    subject="Error al procesar el pago",
                    email_to=_resp[0].supplier.supplier_business_account.email,
                    content=f"Ocurrio un error al procesar el pago de la orden {_resp[0].orden_number}: {e}",
                )

        except GQLApiException as ge:
            logger.warning(ge)
            raise GQLApiException(
                msg=ge.msg,
                error_code=ge.error_code,
            )
        except Exception as e:
            logger.error(e)
            raise GQLApiException(
                msg=str(e),
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
    except Exception as e:
        logger.warning(f"Error en script_execution_wrapper: {exec_id}")
        logger.error(e)
        result = {"status": "error", "error": str(e)}
    try:
        # [TODO] validate if result ok
        await repo.edit(
            id=exec_id,
            status="finished" if result["status"] == "ok" else "error",
            script_end=datetime.utcnow(),
            data=json.dumps(result),
        )
    except Exception as e:
        logger.warning(f"Error al actualizar registro en DB: {exec_id}")
        logger.error(e)


class OrdenHookListener(OrdenHookListenerInterface):

    @staticmethod
    async def on_orden_created(
        webhook_handler: IntegrationWebhookHandlerInterface,
        orden_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
        restaurant_business_id: Optional[UUID] = None,
    ):
        try:
            logger.info("Orden created, sending webhook")
            webhook = await webhook_handler.get_by_source_type(source_type="orden")
            if not webhook:
                logger.warning("No webhook found for orden")
                raise GQLApiException(
                    msg="No webhook found for orden",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
                )
            logger.info("Sending webhook")
            json_data = {
                "orden_id": str(orden_id) if orden_id else "",
                "restaurant_business_id": (
                    str(restaurant_business_id) if restaurant_business_id else ""
                ),
                "supplier_business_id": (
                    str(supplier_business_id) if supplier_business_id else ""
                ),
                "source_type": webhook.source_type,
            }
            resp_webhook = requests.post(
                webhook.url,
                data=json.dumps(json_data),
                headers={"Content-Type": "application/json"},
                timeout=0.5,
            )
            logger.info("Webhook sent")
            logger.info(f"Resp Code: {resp_webhook.status_code}")
            # logger.info(resp_webhook.content)
        except requests.exceptions.Timeout:
            logger.warning("Webhook request timed out.")
            # Handle the timeout error here
            logger.info("Webhook canceled for timeout connection")
        except Exception as e:
            logger.error(e)

    @staticmethod
    async def on_orden_delivered(
        webhook_handler: IntegrationWebhookHandlerInterface,
        orden_handler: OrdenHandlerInterface,
        restaurant_branch_repo: RestaurantBranchRepositoryInterface,
        orden_id: Optional[UUID] = None,
        supplier_business_id: Optional[UUID] = None,
    ):
        try:
            logger.info("Orden delivered, sending webhook")
            if supplier_business_id:
                workflow_integration = await webhook_handler.get_workflow_integration(
                    task_type="orden_delivered",
                    supplier_business_id=supplier_business_id,
                )
                if not workflow_integration:
                    logger.warning("No webhook found for orden_delivered")
                    return
            logger.info("Sending webhook")
            script_exec_rep = ScriptExecutionRepository(SQLDatabase)
            e_id = await script_exec_rep.add(
                script_name=workflow_integration.script_task, status="running"
            )
            if not e_id:
                raise GQLApiException(
                    msg="Error al crear registro en DB",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            try:
                logger.info(f"Executing script: {e_id}")
                if not orden_id:
                    raise GQLApiException(
                        msg="Orden ID is required",
                        error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )

                # call handler
                _resp = await orden_handler.search_orden(orden_id=orden_id)
                if not _resp:
                    logger.info(f"Orden not found: {orden_id}")
                    raise GQLApiException(
                        msg="Orden not found",
                        error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                    )
                logger.info(f"Orden: {_resp[0].id}")
                if (
                    not _resp[0].branch
                    or not _resp[0].details
                    or not _resp[0].supplier
                    or not _resp[0].supplier.supplier_business_account
                    or not _resp[0].supplier.supplier_business_account.email
                    or not _resp[0].supplier.supplier_business
                    or _resp[0].details.total is None
                ):
                    raise GQLApiException(
                        msg="Error to get branch info",
                        error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                    )
                # verify order is delivered
                if (
                    _resp[0].status is None
                    or OrdenStatusType(_resp[0].status.status)
                    != OrdenStatusType.DELIVERED
                ):
                    raise GQLApiException(
                        msg="Orden is not delivered",
                        error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                    )
                if _resp[0].details.payment_method != PayMethodType.TRANSFER:
                    logger.info(f"Orden is not transfer: {_resp[0].id}")
                    await script_exec_rep.edit(
                        id=e_id,
                        status="finished",
                        script_end=datetime.utcnow(),
                        data='{"status":"ok","data":true}',
                    )
                    return
                workflow_vars = await webhook_handler.get_vars(
                    _resp[0].supplier.supplier_business.id
                )
                if not workflow_vars:
                    raise GQLApiException(
                        msg="Error to get workflow vars",
                        error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                    )

                branch_tags = await restaurant_branch_repo.fetch_tags(
                    _resp[0].branch.id
                )
                stripe_value = get_stripe_tag(branch_tags)
                if not stripe_value:
                    await script_exec_rep.edit(
                        id=e_id,
                        status="finished",
                        script_end=datetime.utcnow(),
                        data='{"status":"ok","data":true}',
                    )
                    return
                workflow_vars_json = json.loads(workflow_vars.vars)
                stripe_api_secret = workflow_vars_json.get("stripe_api_secret")
                if not stripe_api_secret:
                    raise GQLApiException(
                        msg="Error to get stripe api secret",
                        error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                    )
                logger.info(f"Stripe Value: {stripe_value}")
                stripe_api = StripeApi(
                    app_name=get_app(), stripe_api_secret=stripe_api_secret
                )
                logger.info(f"Stripe API: {stripe_api}")
                try:
                    stripe_api.create_transfer_payment_intent(
                        stripe_customer_id=stripe_value,
                        charge_description=f"PEDIDO: {_resp[0].orden_number}",
                        charge_amount=_resp[0].details.total,
                        email_to_confirm=_resp[
                            0
                        ].supplier.supplier_business_account.email,
                        currency=StripeCurrency.MXN,
                        charge_metadata={
                            "orden_id": str(_resp[0].id),
                            "supplier_unit_id": str(_resp[0].details.supplier_unit_id),
                            "restaurant_branch_id": str(
                                _resp[0].details.restaurant_branch_id
                            ),
                        },
                    )
                    result = {"status": "ok"}
                except Exception as e:
                    result = {"status": "error", "error": str(e)}
            except Exception as e:
                logger.warning(f"Error en script_execution_wrapper: {e_id}")
                logger.error(e)
                result = {"status": "error", "error": str(e)}
            try:
                # [TODO] validate if result ok
                await script_exec_rep.edit(
                    id=e_id,
                    status="finished" if result["status"] == "ok" else "error",
                    script_end=datetime.utcnow(),
                    data='{"status":"ok","data":true}',
                )
            except Exception as e:
                logger.warning(f"Error al actualizar registro en DB: {e_id}")
                logger.error(e)
                raise GQLApiException(
                    msg="Error al actualizar registro en DB",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )

            logger.info("Webhook sent")
            logger.info(f"Orden: {orden_id}")
            # logger.info(resp_webhook.content)
        except GQLApiException as ge:
            logger.warning(ge)
            if e_id:
                try:
                    # [TODO] validate if result ok
                    await script_exec_rep.edit(
                        id=e_id,
                        status="error",
                        script_end=datetime.utcnow(),
                        data=ge.msg,
                    )
                except Exception as e:
                    logger.warning(f"Error al actualizar registro en DB: {e_id}")
                    logger.error(e)
        except Exception as e:
            logger.info(e)
