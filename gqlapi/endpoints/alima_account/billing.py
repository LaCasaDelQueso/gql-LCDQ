from datetime import date
from typing import Optional
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.config import STRIPE_API_SECRET
from gqlapi.repository.alima_account.billing import AlimaBillingInvoiceRepository
from gqlapi.lib.logger.logger.basic_logger import get_logger

import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.alima_account.account import (
    SupplerAlimaStripeIntentSecret,
    SupplerAlimaStripeResponse,
    SupplierAlimaAccountError,
    SupplierAlimaBillingInvoiceResult,
    SupplierAlimaHistoricInvoices,
    SupplierAlimaStripeResponseResult,
    SupplierAlimaStripeSetupIntentResult,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.alima_account.account import AlimaAccountHandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated

# logger
logger = get_logger(get_app())


@strawberry.type
class AlimaBillingQuery:
    @strawberry.field(
        name="getSupplierAlimaHistoricInvoices",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_alima_historic_invoices(
        self,
        info: StrawberryInfo,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
    ) -> SupplierAlimaBillingInvoiceResult:  # type: ignore
        """Get supplier Alima historic invoices

        Args:
            info (StrawberryInfo): info to connect to DB
            from_date (Optional[date], optional): from date. Defaults to None.
            until_date (Optional[date], optional): until date. Defaults to None.

        Returns:
            SupplierAlimaAccountResult
        """
        logger.info("Get supplier Alima historic invoices")
        # instantiate handler
        _handler = AlimaAccountHandler(
            AlimaAccountRepository(info),
            CoreUserRepository(info),
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
            AlimaBillingInvoiceRepository(info),
        )
        # get supplier account by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get supplier alima account
            al_hist_invs = await _handler.fetch_supplier_alima_historic_invoices(
                fb_id, from_date, until_date
            )
            # return supplier historic invoices
            return SupplierAlimaHistoricInvoices(supplier_invoices=al_hist_invs)
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getSupplierAlimaAccountStripeSetupIntentSecret",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_alima_stripe_setup_intent_secret(
        self, info: StrawberryInfo, stripe_customer_id: str
    ) -> SupplierAlimaStripeSetupIntentResult:  # type: ignore
        """Get supplier Alima Stripe Setup Intent from token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:

        """
        logger.info("Get supplier Alima - Stripe setup intent ")
        # instantiate handler
        stripe_client = StripeApi(get_app(), STRIPE_API_SECRET)
        try:
            su_int = stripe_client.create_setup_intent(stripe_customer_id)
            if not su_int:
                return SupplierAlimaAccountError(
                    msg="Failed to create setup intent",
                    code=GQLApiErrorCodeType.STRIPE_ERROR_SETUP_INTENT.value,
                )
            return SupplerAlimaStripeIntentSecret(secret=su_int.client_secret)
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )


@strawberry.type
class AlimaBillingMutation:
    @strawberry.mutation(
        name="deleteSupplierAlimaStripeCreditCard",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def delete_alima_stripe_credit_card(
        self, info: StrawberryInfo, stripe_customer_id: str, stripe_card_id: str
    ) -> SupplierAlimaStripeResponseResult:  # type: ignore
        """Delete supplier Alima Stripe credit card

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            SupplierAlimaStripeResponseResult
        """
        logger.info("Supplier Alima - Delete Stripe Credit Card ")
        # instantiate handler
        stripe_client = StripeApi(get_app(), STRIPE_API_SECRET)
        try:
            su_delete_confirm = stripe_client.delete_card(
                stripe_customer_id, stripe_card_id
            )
            return SupplerAlimaStripeResponse(
                status=su_delete_confirm,
                msg=(
                    "Stripe credit card deleted successfully"
                    if su_delete_confirm
                    else "Failed to delete Stripe credit card"
                ),
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )
