from datetime import datetime
import json
from uuid import UUID
import uuid
from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.lib.clients.clients.facturamaapi.facturama import PaymentForm
from gqlapi.domain.models.v2.core import OrdenPayStatus
from gqlapi.domain.models.v2.utils import DataTypeDecoder, PayStatusType
from gqlapi.handlers.alima_account.account import AlimaAccountHandler
from gqlapi.handlers.core.orden import OrdenHandler
from gqlapi.handlers.integrations.integrations import IntegrationsWebhookandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.alima_account.billing import (
    AlimaBillingInvoiceComplementRepository,
    AlimaBillingInvoiceRepository,
)
from gqlapi.repository.core.cart import CartProductRepository, CartRepository
from gqlapi.repository.core.orden import (
    OrdenDetailsRepository,
    OrdenPaymentStatusRepository,
    OrdenRepository,
    OrdenStatusRepository,
)
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from starlette.requests import Request

from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.handlers.services.mails import send_reports_alert
from gqlapi.utils.notifications import format_email_table
from gqlapi import config
from gqlapi.db import database as sqldatabase, authos_database
from gqlapi.mongo import mongo_db as mongodatabase

logger = get_logger(get_app())


class StripeWebHookListener(HTTPEndpoint):
    """Stripe Webhook Listener

    Parameters
    ----------
    request : starlette.requests.Request

    Returns
    -------
    starlette.responses.JSONResponse
    """

    async def post(self, request: Request) -> PlainTextResponse:
        try:
            payload = await request.body()
            # Event verified
            stripe_apiclient = StripeApi(get_app(), config.STRIPE_API_KEY)
            stripe_event = stripe_apiclient.construct_event(payload)
            if not stripe_event:
                return PlainTextResponse(
                    "Error:  Could not retrieve event details",
                    400,
                )
            # payment not transfer
            if "customer_balance" not in stripe_event.data.object.payment_method_types:
                return PlainTextResponse("OK", 200)
            # Repository
            _info = InjectedStrawberryInfo(
                db=sqldatabase, authos=authos_database, mongo=mongodatabase
            )
            a_billing_repo = AlimaBillingInvoiceRepository(info=_info)  # type: ignore (safe)
            cu_repo = CoreUserRepository(info=_info)  # type: ignore
            supplier_business_repo = SupplierBusinessRepository(info=_info)  # type: ignore
            supplier_business_account_repo = SupplierBusinessAccountRepository(info=_info)  # type: ignore
            paid_account_repo = AlimaAccountRepository(info=_info)  # type: ignore
            su_repo = SupplierUserRepository(info=_info)  # type: ignore
            su_perm_repo = SupplierUserPermissionRepository(info=_info)  # type: ignore
            alima_billing_comp_repo = AlimaBillingInvoiceComplementRepository(info=_info)  # type: ignore
            alima_acc_hdler = AlimaAccountHandler(
                core_user_repository=cu_repo,
                alima_account_repository=paid_account_repo,
                supplier_business_repository=supplier_business_repo,
                supplier_business_account_repository=supplier_business_account_repo,
                supplier_user_repository=su_repo,
                supplier_user_permission_repository=su_perm_repo,
                alima_billing_invoice_repository=a_billing_repo,
                alima_billing_complement_repository=alima_billing_comp_repo,
            )
            # Handle the event
            if stripe_event.type == "payment_intent.requires_action":
                payment_intent = (
                    stripe_event.data.object
                )  # contains a stripe.PaymentIntent
                logger.info("PaymentIntent requires action: %s", payment_intent.id)
                # The payment intent was not fully funded due to insufficient funds on the
                # customer balance. Define and call a method to handle the payment intent.
                html_table = format_email_table(
                    pd.DataFrame(
                        [
                            {
                                "paid_account_id": "",
                                "supplier": payment_intent.receipt_email,
                                "invoice_name": payment_intent.description,
                                "status": False,
                                "reason": f"PaymentIntent: {payment_intent.id} requires action",
                                "data": str(payment_intent),
                                "execution_time": datetime.utcnow(),
                            }
                        ]
                    ).to_html(
                        index=False, classes="table table-bordered table-striped "
                    )
                )
            elif stripe_event.type == "payment_intent.partially_funded":
                payment_intent = (
                    stripe_event.data.object
                )  # contains a stripe.PaymentIntent
                logger.info("PaymentIntent partially funded: %s", payment_intent.id)
                # Then define and call a method to handle the payment intent being partially funded.
                html_table = format_email_table(
                    pd.DataFrame(
                        [
                            {
                                "paid_account_id": "",
                                "supplier": payment_intent.receipt_email,
                                "invoice_name": payment_intent.description,
                                "status": False,
                                "reason": f"""PaymentIntent: {
                                    payment_intent.id
                                } was partially funded (${payment_intent.amount / 100})""",
                                "data": str(payment_intent),
                                "execution_time": datetime.utcnow(),
                            }
                        ]
                    ).to_html(
                        index=False, classes="table table-bordered table-striped "
                    )
                )
            elif stripe_event.type == "payment_intent.succeeded":
                payment_intent = (
                    stripe_event.data.object
                )  # contains a stripe.PaymentIntent
                logger.info("PaymentIntent succeeded: %s", payment_intent.id)
                # Then define and call a method to handle the successful payment intent.
                # fetch invoice
                invoice, invoice_paystatus = (
                    await a_billing_repo.find_by_transaction_id(
                        transaction_id=payment_intent.id
                    )
                )
                updated_invoice_flag = False
                # update invoice status
                if invoice and invoice_paystatus:
                    updated_invoice_flag = await a_billing_repo.edit_alima_invoice(
                        billing_invoice=invoice,
                        paystatus=PayStatusType.PAID,
                        billing_payment_method_id=invoice_paystatus.billing_payment_method_id,
                        transaction_id=invoice_paystatus.transaction_id,
                    )
                    # get paid_account
                    paid_account = await paid_account_repo.fetch_alima_account_by_id(
                        paid_account_id=invoice.paid_account_id
                    )
                    if paid_account is not None:
                        # generate invoice complement
                        complement_flag = (
                            await alima_acc_hdler.new_alima_invoice_complement(
                                supplier_business_id=paid_account.customer_business_id,
                                payment_form=PaymentForm.TRANSFER,
                                amount=payment_intent.amount / 100,
                                active_invoice=invoice,
                            )
                        )
                        if complement_flag:
                            logger.info(
                                "Invoice Complement created for Invoice: %s",
                                invoice.invoice_number,
                            )
                        else:
                            logger.error(
                                "Could not create Invoice Complement for Invoice: %s",
                                invoice.invoice_number,
                            )
                    else:
                        logger.error(
                            "Paid Account not found for Invoice: %s",
                            invoice.invoice_number,
                        )
                else:
                    logger.warning(
                        "Invoice not found for PaymentIntent: %s", payment_intent.id
                    )

                # generate report
                html_table = format_email_table(
                    pd.DataFrame(
                        [
                            {
                                "paid_account_id": (
                                    invoice.paid_account_id
                                    if invoice is not None
                                    else ""
                                ),
                                "supplier": payment_intent.receipt_email,
                                "invoice_name": payment_intent.description,
                                "status": (updated_invoice_flag),
                                "reason": (
                                    f"""PaymentIntent: {payment_intent.id} correctly paid Invoice: {
                                        invoice.invoice_number
                                    } (${payment_intent.amount / 100})"""
                                    if invoice is not None
                                    and invoice_paystatus is not None
                                    else f"""Invoice Not Found, but there is a PaymentIntent: {
                                        payment_intent.id
                                    } paid (${payment_intent.amount / 100})"""
                                ),
                                "data": str(payment_intent),
                                "execution_time": datetime.utcnow(),
                            }
                        ]
                    ).to_html(
                        index=False, classes="table table-bordered table-striped "
                    )
                )
            else:
                logger.error("Unhandled event type {}".format(stripe_event.type))
                raise Exception("Error:  Unhandled event type")
            return PlainTextResponse("OK", 200)
        except Exception as e:
            logger.error(e)
            html_table = format_email_table(
                pd.DataFrame(
                    [
                        {
                            "paid_account_id": "",
                            "supplier": "",
                            "invoice_name": "",
                            "status": True,
                            "reason": "Stripe Event: unexpected",
                            "data": str(stripe_event),
                            "execution_time": datetime.utcnow(),
                        }
                    ]
                ).to_html(index=False, classes="table table-bordered table-striped ")
            )
            return PlainTextResponse(f"Error: {str(e)}", 400)


class StripeWebHookListenerTransferAutoPayments(HTTPEndpoint):
    """Stripe Webhook Listener

    Parameters
    ----------
    request : starlette.requests.Request

    Returns
    -------
    starlette.responses.JSONResponse
    """

    async def post(self, request: Request) -> PlainTextResponse:
        try:
            supplier_business_id = request.path_params['supplier_business_id']
            _info = InjectedStrawberryInfo(
                db=sqldatabase, authos=authos_database, mongo=mongodatabase
            )
            integrations_weebhook_partner_handler = IntegrationsWebhookandler(
                repo=IntegrationWebhookRepository(_info)  # type: ignore
            )
            workflow_vars = await integrations_weebhook_partner_handler.get_vars(
                UUID(supplier_business_id)
            )
            if not workflow_vars:
                raise Exception("Error: Workflow vars not found")
            workflow_vars_json = json.loads(workflow_vars.vars)
            stripe_api_key = workflow_vars_json.get("stripe_api_secret")
            if not stripe_api_key:
                raise Exception("Error: Stripe API secret not found")
            orden_paystatus_repo = OrdenPaymentStatusRepository(info=_info)  # type: ignore
            core_repo = CoreUserRepository(info=_info)  # type: ignore
            _handler = OrdenHandler(
                orden_repo=OrdenRepository(_info),  # type: ignore
                orden_det_repo=OrdenDetailsRepository(_info),  # type: ignore
                orden_status_repo=OrdenStatusRepository(_info),  # type: ignore
                orden_payment_repo=OrdenPaymentStatusRepository(_info),  # type: ignore
                core_user_repo=CoreUserRepository(_info),  # type: ignore
                rest_branc_repo=RestaurantBranchRepository(_info),  # type: ignore
                supp_unit_repo=SupplierUnitRepository(_info),  # type: ignore
                cart_repo=CartRepository(_info),  # type: ignore
                cart_prod_repo=CartProductRepository(_info),  # type: ignore
                rest_buss_acc_repo=RestaurantBusinessAccountRepository(_info),  # type: ignore
                supp_bus_acc_repo=SupplierBusinessAccountRepository(_info),  # type: ignore
                supp_bus_repo=SupplierBusinessRepository(_info),  # type: ignore
                rest_business_repo=RestaurantBusinessRepository(_info),  # type: ignore
            )
            payload = await request.body()
            # Event verified
            stripe_apiclient = StripeApi(get_app(), stripe_api_key)
            stripe_event = stripe_apiclient.construct_event(payload)
            if not stripe_event:
                return PlainTextResponse(
                    "Error:  Could not retrieve event details",
                    400,
                )
            # Handle the event
            if stripe_event.type == "payment_intent.succeeded":
                payment_intent = (
                    stripe_event.data.object
                )  # contains a stripe.PaymentIntent
                metadata = payment_intent.get("metadata", None)
                logger.info(metadata)
                if not metadata:
                    raise Exception("Error:  Metadata not found")
                orden_id = metadata.get("orden_id", None)
                if not orden_id:
                    raise Exception("Error: Orden ID not found")
                logger.info("PaymentIntent succeeded: %s", payment_intent.id)
                orden_id = UUID(orden_id)
                orden = await _handler.search_orden(orden_id)
                if (
                    not orden[0]
                    or not orden[0].details
                    or not orden[0].details.total
                    or not orden[0].paystatus
                    or not orden[0].paystatus.created_at
                ):
                    raise Exception("Error: Orden not found")
                # sign as automated transaction
                core_bot = await core_repo.fetch_by_email("admin")
                if not core_bot or not core_bot.id:
                    raise Exception("Error: Core user not found")
                if DataTypeDecoder.get_orden_paystatus_key(orden[0].paystatus.status) != "paid":  # type: ignore
                    if await orden_paystatus_repo.add(
                        OrdenPayStatus(
                            id=uuid.uuid4(),
                            orden_id=orden_id,
                            status=PayStatusType.PAID,
                            created_by=core_bot.id,
                        )
                    ):
                        await _handler.add_auto_payment_receipt(
                            orden_ids=[orden_id],
                            payment_value=orden[0].details.total,
                            payment_day=datetime.now(),
                            core_user_id=core_bot.id,
                            # comments=comments,
                        )
                    else:
                        logger.error(f"Error adding orden paystatus {orden_id}")
                        raise Exception(
                            f"Error: Error adding orden paystatus {orden_id}"
                        )
                # Then define and call a method to handle the successful payment intent.

            return PlainTextResponse("OK", 200)
        except Exception as e:
            logger.error(e)
            return PlainTextResponse(f"Error: {str(e)}", 400)
