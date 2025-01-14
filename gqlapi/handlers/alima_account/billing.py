import calendar
from datetime import datetime, timedelta, timezone
from types import NoneType
from typing import Any, Dict, List, Literal, Set, Tuple, Type
from gqlapi.lib.clients.clients.stripeapi.stripe_api import (
    StripeApi,
    StripeCurrency,
    StripePaymentIntentError,
)
from gqlapi.domain.models.v2.alima_business import BillingPaymentMethod
from gqlapi.config import STRIPE_API_SECRET
from gqlapi.handlers.alima_account.account import (
    AlimaAccountHandler,
    AlimaComercialAccountHandler,
    AlimaComercialAnualAccountHandler,
    AlimaProAccountHandler,
    AlimaProAnualAccountHandler,
    alima_supply_valid_plans,
)
from gqlapi.handlers.services.mails import (
    send_account_inactive,
    send_alima_invoice_pending_notification,
    send_card_payment_failed_notification,
    send_new_alima_invoice_notification_v2,
)
from gqlapi.repository.b2bcommerce.ecommerce_seller import EcommerceSellerRepository
from gqlapi.repository.integrarions.integrations import IntegrationWebhookRepository
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.alima_account.account import (
    BillingAccount,
    BillingReport,
    BillingTotalDue,
)
from gqlapi.domain.models.v2.utils import (
    InvoiceStatusType,
    InvoiceType,
    PayProviderType,
    PayStatusType,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.alima_account.billing import (
    AlimaBillingInvoiceComplementRepository,
    AlimaBillingInvoiceRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import (
    CoreUserRepository,
)

logger = get_logger(get_app())


class AlimaBillingRunner:
    plan_handler_map: Dict[str, Type[AlimaAccountHandler]] = {
        "alima_comercial": AlimaComercialAccountHandler,
        "alima_comercial_anual": AlimaComercialAnualAccountHandler,
        "alima_pro": AlimaProAccountHandler,
        "alima_pro_anual": AlimaProAnualAccountHandler,
    }
    available_payproviders = [
        PayProviderType.CARD_STRIPE,
        PayProviderType.TRANSFER_STRIPE,
    ]

    def __init__(
        self, info: StrawberryInfo, plans: Set[str], pay_providers: Set[PayProviderType]
    ):
        for plan in plans:
            if plan not in alima_supply_valid_plans:
                raise Exception(f"Alima Supply: Invalid Plan: {plan}")
        self.plans = list(plans)
        self.pay_providers = list(pay_providers)
        self.stripe = StripeApi(app_name=get_app(), stripe_api_secret=STRIPE_API_SECRET)
        self._initialize_handlers(info)
        logger.info(f"Alima Billing Runner Initialized for: ({self.plans})")
        logger.info(f"Pay Providers: ({self.pay_providers})")

    def _initialize_handlers(self, info: StrawberryInfo):
        self.handlers: Dict[str, AlimaAccountHandler] = {}
        # prepare repos
        alima_account_repo = AlimaAccountRepository(info)
        core_user_repo = CoreUserRepository(info)
        sb_repo = SupplierBusinessRepository(info)
        sb_acc_repo = SupplierBusinessAccountRepository(info)
        suser_repo = SupplierUserRepository(info)
        suser_perm_repo = SupplierUserPermissionRepository(info)
        ab_invoice_repo = AlimaBillingInvoiceRepository(info)
        ab_complement_repo = AlimaBillingInvoiceComplementRepository(info)
        ecommerce_seller_repo = EcommerceSellerRepository(info)
        integration_repo = IntegrationWebhookRepository(info)
        # initialize handlers
        for plan in self.plans:
            self.handlers[plan] = self.plan_handler_map[plan](
                alima_account_repository=alima_account_repo,
                core_user_repository=core_user_repo,
                supplier_business_repository=sb_repo,
                supplier_business_account_repository=sb_acc_repo,
                supplier_user_repository=suser_repo,
                supplier_user_permission_repository=suser_perm_repo,
                alima_billing_invoice_repository=ab_invoice_repo,
                alima_billing_complement_repository=ab_complement_repo,
                ecommerce_seller_repository=ecommerce_seller_repo,
                integration_webhook_repo=integration_repo,
            )
        self.default_handler = self.handlers[self.plans[0]]

    @staticmethod
    def is_monthly_billing_past_due(
        paid_account_created_at: datetime, current_date: datetime
    ) -> Tuple[bool, int, int]:
        """Check if billing is past due

        Args:
            paid_account_created_at (datetime): Paid Account Created At
            current_date (datetime): Current Date

        Returns:
            (bool, int):
                bool - True if past due, False otherwise
                int - Month to bill
                int - Year to bill
        """
        if paid_account_created_at > current_date:
            return False, current_date.month, current_date.year
        is_last_of_month = AlimaAccountHandler.is_month_last_day(current_date)
        if is_last_of_month:
            return True, current_date.month, current_date.year
        if current_date.day >= paid_account_created_at.day:
            return True, current_date.month, current_date.year
        # if paid account created at is > (last_day_of_month_prev_month - 8 days)
        # verify if (curren_date - paid_account.created_at) < 8
        prev_month_date = current_date - timedelta(days=30)
        last_day_prev_month = calendar.monthrange(
            prev_month_date.year, prev_month_date.month
        )[1]
        if paid_account_created_at.day > (last_day_prev_month - 8):
            prev_month_c_day = (
                paid_account_created_at.day
                if (paid_account_created_at.day <= last_day_prev_month)
                else last_day_prev_month
            )
            prev_month_checkday = datetime(
                prev_month_date.year, prev_month_date.month, prev_month_c_day
            )
            if (current_date - prev_month_checkday).days <= 8:
                return True, prev_month_date.month, prev_month_date.year
        return False, current_date.month, current_date.year

    @staticmethod
    def is_annual_billing_past_due(
        paid_account_created_at: datetime, current_date: datetime
    ) -> Tuple[bool, int, int]:
        """Check if annual billing is past due

        Args:
            paid_account_created_at (datetime): Paid Account Created At
            current_date (datetime): Current Date

        Returns:
            (bool, int):
                bool - True if past due, False otherwise
                int - Month to bill
                int - Year to bill
        """
        if paid_account_created_at > current_date:
            return False, current_date.month, current_date.year
        # next date to bill
        next_billdate = datetime(
            current_date.year,
            paid_account_created_at.month,
            paid_account_created_at.day,
        )
        if next_billdate <= current_date:
            return True, next_billdate.month, next_billdate.year
        # if not, verify if paid account was not created within the
        prev_year_date = current_date - timedelta(days=365)
        if paid_account_created_at.day > (prev_year_date.day - 8):
            prev_year_checkday = datetime(
                prev_year_date.year, prev_year_date.month, paid_account_created_at.day
            )
            if (current_date - prev_year_checkday).days <= 8:
                return True, prev_year_date.month, prev_year_date.year
        return False, next_billdate.month, next_billdate.year

    @staticmethod
    def filter_monthly_billing_past_due(
        billing_accounts: List[BillingAccount], current_date: datetime
    ) -> List[Dict[str, Any]]:
        bas_to_bill = []
        for ba in billing_accounts:
            is_past_due, month, year = AlimaBillingRunner.is_monthly_billing_past_due(
                ba.paid_account.created_at, current_date
            )
            if is_past_due:
                bas_to_bill.append(
                    {
                        "billing_account": ba,
                        "month": month,
                        "year": year,
                        "current_date": current_date,
                    }
                )
                logger.info(
                    f"BA: {ba.business.name} ({ba.paid_account.created_at}) [Period: {str(month).zfill(2)}-{year}]"
                )
        return bas_to_bill

    @staticmethod
    def filter_annual_billing_past_due(
        billing_accounts: List[BillingAccount], current_date: datetime
    ) -> List[Dict[str, Any]]:
        bas_to_bill = []
        for ba in billing_accounts:
            is_past_due, month, year = AlimaBillingRunner.is_annual_billing_past_due(
                ba.paid_account.created_at, current_date
            )
            if is_past_due:
                bas_to_bill.append(
                    {
                        "billing_account": ba,
                        "month": month,
                        "year": year,
                        "current_date": current_date,
                    }
                )
                logger.info(
                    f"BA: {ba.business.name} ({ba.paid_account.created_at}) [Period: {str(month).zfill(2)}-{year}]"
                )
        return bas_to_bill

    def prepare_monthly_invoice_elements(
        self,
        billing_account: BillingAccount,
        current_date: datetime,
        billing_month: int,
        billing_year: int,
    ) -> Dict[str, Any]:
        # skip this in case is the first month
        is_first_month = (
            billing_month == billing_account.paid_account.created_at.month
            and billing_year == billing_account.paid_account.created_at.year
        )
        if is_first_month:
            logger.info(
                f"*  BA: {billing_account.business.name}. First Month - Not Charging yet"
            )
            return {
                "first_month": is_first_month,
                "invoice_period": None,
                "days_from_checkday": None,
                "handler": None,
            }
        # invoice period from month and year
        invoice_period = f"{str(billing_month).zfill(2)}-{billing_year}"
        # Execute actions depending on days from checkday
        last_day_of_month = calendar.monthrange(
            billing_year,
            billing_month,
        )[1]
        checkday = datetime(
            billing_year,
            billing_month,
            (
                billing_account.paid_account.created_at.day
                if billing_account.paid_account.created_at.day <= last_day_of_month
                else last_day_of_month
            ),
        )
        days_from_checkday = (current_date - checkday).days
        logger.info(
            f"*  BA: {billing_account.business.name}. Days from Checkday: {days_from_checkday}"
        )
        # setup selected handler
        cplan: str = billing_account.paid_account.account_name
        if cplan not in self.handlers:
            logger.warning(
                f"Plan for {billing_account.business.name} is not valid: {cplan}"
            )
            return {
                "first_month": is_first_month,
                "invoice_period": invoice_period,
                "days_from_checkday": days_from_checkday,
                "handler": None,
            }
        chandler = self.handlers[cplan]
        return {
            "first_month": is_first_month,
            "invoice_period": invoice_period,
            "days_from_checkday": days_from_checkday,
            "handler": chandler,
        }

    def prepare_annual_invoice_elements(
        self,
        billing_account: BillingAccount,
        current_date: datetime,
        billing_month: int,
        billing_year: int,
    ) -> Dict[str, Any]:
        # invoice period from month and year
        invoice_period = f"{str(billing_month).zfill(2)}-{billing_year}"
        # Execute actions depending on days from checkday
        checkday = datetime(
            current_date.year,
            current_date.month,
            billing_account.paid_account.created_at.day,
        )
        days_from_checkday = (current_date - checkday).days
        logger.info(
            f"*  BA: {billing_account.business.name}. Days from Checkday: {days_from_checkday}"
        )
        # setup selected handler
        cplan: str = billing_account.paid_account.account_name
        if cplan not in self.handlers:
            logger.warning(
                f"Plan for {billing_account.business.name} is not valid: {cplan}"
            )
            return {
                "invoice_period": invoice_period,
                "days_from_checkday": days_from_checkday,
                "handler": None,
            }
        chandler = self.handlers[cplan]
        return {
            "invoice_period": invoice_period,
            "days_from_checkday": days_from_checkday,
            "handler": chandler,
        }

    async def filter_not_invoiced_current_monthly_period(
        self, billing_accounts_dict: List[Dict[str, Any]], verify_if_paid: bool = True
    ) -> List[Dict[str, Any]]:
        # guard
        if len(billing_accounts_dict) == 0:
            return []
        current_date = billing_accounts_dict[0]["current_date"]
        from_date = current_date - timedelta(days=60)
        until_date = current_date + timedelta(days=60)
        # accumulator
        bas_not_invoiced = []
        # iterate over all billing_accounts
        for ba_dct in billing_accounts_dict:
            # fetch invoices for the past 2 months and future 2 months
            invoices = await self.default_handler.alima_billing_invoice_repository.fetch_alima_invoices(
                ba_dct["billing_account"].paid_account.id,
                from_date=from_date,
                until_date=until_date,
            )
            # verify if invoice generated for current period is active
            current_period = f"{str(ba_dct['month']).zfill(2)}-{ba_dct['year']}"
            found_invoices = [
                inv
                for inv in invoices
                if inv.invoice_month == current_period
                and inv.status == InvoiceStatusType.ACTIVE
            ]
            if len(found_invoices) == 0:
                bas_not_invoiced.append(ba_dct)
                # go check next billing account
                continue
            # verify if paid account is paid
            if verify_if_paid:
                inv_pay_status = await self.default_handler.alima_billing_invoice_repository.fetch_alima_invoice_paystatus(
                    [inv.id for inv in found_invoices]
                )
                # if no record of PAID paystatus, add to not invoiced
                if (
                    len(
                        [
                            ipy
                            for ipy in inv_pay_status
                            if ipy.status == PayStatusType.PAID
                        ]
                    )
                    == 0
                ):
                    bas_not_invoiced.append(ba_dct)
        # return accumulator
        return bas_not_invoiced

    async def filter_not_invoiced_current_annual_period(
        self, billing_accounts_dict: List[Dict[str, Any]], verify_if_paid: bool = True
    ) -> List[Dict[str, Any]]:
        # guard
        if len(billing_accounts_dict) == 0:
            return []
        current_date = billing_accounts_dict[0]["current_date"]
        from_date = current_date - timedelta(days=60 + 365)
        until_date = current_date + timedelta(days=60)
        # accumulator
        bas_not_invoiced = []
        # iterate over all billing_accounts
        for ba_dct in billing_accounts_dict:
            # fetch invoices for the past 14 months and future 2 months
            invoices = await self.default_handler.alima_billing_invoice_repository.fetch_alima_invoices(
                ba_dct["billing_account"].paid_account.id,
                from_date=from_date,
                until_date=until_date,
            )
            # verify if invoice generated for current period is active
            current_period = f"{ba_dct['year']}"
            found_invoices = [
                inv
                for inv in invoices
                if current_period in inv.invoice_month
                and inv.status == InvoiceStatusType.ACTIVE
            ]
            if len(found_invoices) == 0:
                bas_not_invoiced.append(ba_dct)
                # go check next billing account
                continue
            # verify if paid account is paid
            if verify_if_paid:
                inv_pay_status = await self.default_handler.alima_billing_invoice_repository.fetch_alima_invoice_paystatus(
                    [inv.id for inv in found_invoices]
                )
                # if no record of PAID paystatus, add to not invoiced
                if (
                    len(
                        [
                            ipy
                            for ipy in inv_pay_status
                            if ipy.status == PayStatusType.PAID
                        ]
                    )
                    == 0
                ):
                    bas_not_invoiced.append(ba_dct)
        # return accumulator
        return bas_not_invoiced

    async def is_stripe_spei_payment_intent_created(
        self, billing_account: BillingAccount, invoice_month: str
    ) -> bool:
        # find period invoice
        invoices = await self.default_handler.alima_billing_invoice_repository.find(
            paid_account_id=billing_account.paid_account.id,
            date=invoice_month,
        )
        # if no invoice found, return False
        if len(invoices) == 0:
            return False
        # if it exists, fetch invoice pay status and verify transaction_id is not null
        inv_pay_statuses = await self.default_handler.alima_billing_invoice_repository.fetch_alima_invoice_paystatus(
            [inv.id for inv in invoices]
        )
        if len(inv_pay_statuses) == 0:
            return False
        # if transaction_id is not null, return True
        return inv_pay_statuses[0].transaction_id is not None

    async def create_spei_stripe_payment_intent(
        self,
        billing_account: BillingAccount,
        billing_total_due: BillingTotalDue,
        charge_description: str,
        invoice_name: str,
    ) -> Tuple[bool, str, str | NoneType]:
        # do payment intent
        confirmation_email = (
            billing_account.business.account.email
            if (
                billing_account.business.account
                and billing_account.business.account.email
            )
            else "pagosyfacturas@alima.la"
        )
        # create stripe payment intent
        pi = self.stripe.create_transfer_payment_intent(
            stripe_customer_id=billing_account.payment_method.payment_provider_id,
            charge_description=charge_description,
            charge_amount=billing_total_due.total_due,
            email_to_confirm=confirmation_email,
            currency=StripeCurrency.MXN,
            charge_metadata={
                "invoice_name": invoice_name,
                "business_id": str(billing_account.business.id),
            },
        )
        # If error notify customer
        if isinstance(pi, StripePaymentIntentError):
            logger.info("Could not perform Stripe Payment Intent")
            return False, pi.json_result, None
        # if ok, verify if payment method has already account number
        if not billing_account.payment_method.account_number:
            # verify PI has account number
            if not hasattr(pi, "next_action"):
                return (
                    True,
                    "Payment Intent Created, but could not fetch Account Number",
                    pi.id,
                )
            pi_nextact = pi.next_action
            if not hasattr(
                pi_nextact, "display_bank_transfer_instructions"
            ) and not hasattr(
                pi_nextact.display_bank_transfer_instructions, "financial_addresses"
            ):
                return (
                    True,
                    "Payment Intent Created, but could not fetch Account Number",
                    pi.id,
                )
            pi_bank_instrs = (
                pi_nextact.display_bank_transfer_instructions.financial_addresses
            )
            if len(pi_bank_instrs) == 0:
                return (
                    True,
                    "Payment Intent Created, but could not fetch Account Number",
                    pi.id,
                )
            pi_bank_instr = pi_bank_instrs[0]
            pm_verif = await self.default_handler.repository.edit_payment_method(
                payment_method=BillingPaymentMethod(
                    id=billing_account.payment_method.id,
                    paid_account_id=billing_account.paid_account.id,
                    payment_type=billing_account.payment_method.payment_type,
                    payment_provider=billing_account.payment_method.payment_provider,
                    payment_provider_id=billing_account.payment_method.payment_provider_id,
                    created_by=billing_account.payment_method.created_by,
                    account_number=pi_bank_instr.spei.clabe,
                    account_name=None,
                    bank_name=pi_bank_instr.spei.bank_name,
                    active=True,
                    created_at=billing_account.payment_method.created_at,
                    last_updated=billing_account.payment_method.last_updated,
                )
            )
            # update in-place billing account with new account number
            billing_account.payment_method.account_number = pi_bank_instr.spei.clabe
            billing_account.payment_method.bank_name = pi_bank_instr.spei.bank_name
            billing_account.payment_method.account_name = None
            # if not updated, return True but warning msg
            if not pm_verif:
                return (
                    True,
                    "Payment Intent Created, but could not update Account Number",
                    pi.id,
                )
        # return True
        return True, "Payment successfully charged", pi.id

    async def collect_stripe_payment_intent(
        self,
        billing_account: BillingAccount,
        billing_total_due: BillingTotalDue,
        charge_description: str,
        invoice_name: str,
        intent_number: int,
    ) -> Tuple[bool, str, str | NoneType]:
        self.stripe = StripeApi(app_name=get_app(), stripe_api_secret=STRIPE_API_SECRET)
        # get cards
        ccs = self.stripe.get_cards_list(
            billing_account.payment_method.payment_provider_id
        )
        num_ccs = len(ccs)
        if num_ccs == 0:
            return False, "No cards available in Billing Account", None
        # pick default card
        cc_to_charge = [
            cc
            for cc in ccs
            if self.stripe.is_card_default(
                billing_account.payment_method.payment_provider_id, cc.get("id", "")
            )
        ]
        if len(cc_to_charge) == 0:
            cc_to_charge = ccs[0]
        else:
            cc_to_charge = cc_to_charge[0]
        # if intent number > 3, and num_ccs is > 1. Choose them by idx % num_ccs
        if intent_number > 3 and num_ccs > 1:
            cc_chooser = intent_number % num_ccs
            cc_to_charge = ccs[cc_chooser]
        # do payment intent
        confirmation_email = (
            billing_account.business.account.email
            if (
                billing_account.business.account
                and billing_account.business.account.email
            )
            else "pagosyfacturas@alima.la"
        )
        pi = self.stripe.create_card_payment_intent(
            stripe_customer_id=billing_account.payment_method.payment_provider_id,
            stripe_card_id=cc_to_charge["id"],
            charge_description=charge_description,
            charge_amount=billing_total_due.total_due,
            email_to_confirm=confirmation_email,
            currency=StripeCurrency.MXN,
            charge_metadata={
                "intent_number": str(intent_number),
                "invoice_name": invoice_name,
                "business_id": str(billing_account.business.id),
            },
        )
        # If error notify customer
        if isinstance(pi, StripePaymentIntentError):
            logger.info("Could not perform Stripe Payment Intent")
            #  Warning Notification to Customer of Payment x/N
            if not await send_card_payment_failed_notification(
                confirmation_email,
                billing_account.business.name,
                invoice_name,
                billing_account.paid_account.account_name,
            ):
                logger.warning("Error Sending Payment Failed Notification to Custmer")
            return False, pi.json_result, None
        # if ok, return True
        return True, "Payment successfully charged", pi.id

    async def dispatch_invoice(
        self,
        billing_account: BillingAccount,
        invoice_month: str,  # MM-YYYY
        billing_charges_total: BillingTotalDue,
        invoice_type: InvoiceType,
        is_paid: bool,
        payment_id: str | NoneType = None,
    ) -> Tuple[bool, str]:
        # guard
        if len(billing_charges_total.charges) == 0:
            return False, "Invoice Error: No charges to generate Invoice"
        currency = billing_charges_total.charges[0].currency
        # Generate alima invoice
        try:
            inv_result = await self.default_handler.new_alima_invoice(
                billing_account=billing_account,
                invoice_month=invoice_month,
                billing_charges_total=billing_charges_total,
                currency=currency,
                invoice_type=invoice_type,
                is_paid=is_paid,
                payment_id=payment_id,
            )
            if inv_result is None:
                return False, "Error Generating Alima Invoice"
        except Exception as e:
            logger.error(f"Error Generating Alima Invoice: {str(e)}")
            return False, f"Error Generating Invoice: {str(e)}"
        # Send invoice to Business and PagosyFacturas
        attcht = [
            {
                "content": inv_result["pdf"],
                "filename": f"Factura Alima-{invoice_month}.pdf",
                "mimetype": "application/pdf",
            },
            {
                "content": inv_result["xml"],
                "filename": f"Factura Alima-{invoice_month}.xml",
                "mimetype": "application/xml",
            },
        ]
        email_recs = []
        if inv_result["rfc"] not in ("XAXX010101000", "XEXX010101000"):
            if billing_account.business.account:
                email_recs.append(billing_account.business.account.email)
        email_recs.append("pagosyfacturas@alima.la")
        sent_flag = await send_new_alima_invoice_notification_v2(
            email_to=email_recs,
            name=billing_account.business.name,
            attchs=attcht,
        )
        if not sent_flag:
            return (
                False,
                f"Invoice Generated: {inv_result['id']}, but Error Sending Invoice",
            )
        return True, f"Invoice Generated: {inv_result['id']}, and Sent"

    async def _run_billing_monthly_card_stripe(
        self, billing_accounts: List[BillingAccount], current_date: datetime
    ) -> List[BillingReport]:
        logger.info(f"Running Monthly Billing for Card Stripe ({current_date})")
        # Compare paid account created_at, and verify all accounts that its billing day has arrived
        bas_to_bill = self.filter_monthly_billing_past_due(
            billing_accounts, current_date
        )
        # Verify if Invoice has been generated for the current period
        bas_to_bill_not_paid = await self.filter_not_invoiced_current_monthly_period(
            bas_to_bill, verify_if_paid=False
        )
        logger.info(
            f"Billing Accounts in Period to Bill Invoice: {len(bas_to_bill_not_paid)}"
        )
        bill_reports = []
        # Implement Action depending on # of days without payment
        for ba_dct in bas_to_bill_not_paid:
            prep_dict = self.prepare_monthly_invoice_elements(
                ba_dct["billing_account"],
                current_date,
                ba_dct["month"],
                ba_dct["year"],
            )
            # skip if first month
            if prep_dict["first_month"]:
                continue
            # skip if handler is None
            if prep_dict["handler"] is None:
                bill_reports.append(
                    BillingReport(
                        paid_account_id=ba_dct["billing_account"].paid_account.id,
                        supplier=ba_dct["billing_account"].business.name,
                        invoice_name="",
                        status=False,
                        reason=f"Plan not valid: {ba_dct['billing_account'].paid_account.account_name}",
                        execution_time=datetime.utcnow(),
                    )
                )
                continue
            # unpack
            invoice_period = prep_dict["invoice_period"]
            days_from_checkday = prep_dict["days_from_checkday"]
            chandler = prep_dict["handler"]
            #####
            import uuid
            if ba_dct["billing_account"].business.id != uuid.UUID(
                "0980cac1-3869-4793-a43a-a57381eff15d"
            ):
                logger.info(
                    f"XX  - Skipping Account: {ba_dct['billing_account'].business.name}"
                )
                continue
            #####
            breport_dict = {
                "paid_account_id": ba_dct["billing_account"].paid_account.id,
                "supplier": ba_dct["billing_account"].business.name,
                "invoice_name": invoice_period,
            }
            # Try to Charge from Stripe
            if days_from_checkday < 8:
                logger.info("-" * 30)
                logger.info(
                    f"**  ({days_from_checkday} / 7) - Try to Charge with Payment Intent"
                )
                # Compute Total Due
                total_due = await chandler.compute_total_due(
                    ba_dct["billing_account"], ba_dct["current_date"]
                )
                for _ch in total_due.charges:
                    logger.info(f"** {_ch.charge_type} = ${_ch.total_charge}")
                logger.info(f"** Total Due: ${total_due.total_due}")
                if total_due.total_due == 0:
                    # skip if total due is 0
                    continue
                # Try Payment Intent
                pi_status, msg, pi_id = await self.collect_stripe_payment_intent(
                    ba_dct["billing_account"],
                    total_due,
                    f"{ba_dct['billing_account'].paid_account.account_name.upper().replace('_', ' ')} {invoice_period}",
                    invoice_period,
                    days_from_checkday,
                )
                # If PI not successful, accumulate report
                if not pi_status:
                    bill_reports.append(
                        BillingReport(
                            status=False,
                            reason=msg,
                            execution_time=datetime.utcnow(),
                            **breport_dict,
                        )
                    )
                    continue
                # If Payment Intent is successful, create Invoice (PUE since is already paid)
                inv_status, inv_msg = await self.dispatch_invoice(
                    ba_dct["billing_account"],
                    invoice_month=invoice_period,
                    billing_charges_total=total_due,
                    invoice_type=InvoiceType.PUE,
                    is_paid=True,
                    payment_id=pi_id,
                )
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=inv_status,
                        reason=inv_msg,
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
            # Deactivate Account
            elif days_from_checkday == 8:
                logger.info("**  Deactivating Account")
                # Deactivate Account
                is_disabled = await self.default_handler.disable_alima_account(
                    ba_dct["billing_account"].business.id
                )
                # Send Notice of Closing Account
                email_recs = "automations@alima.la"
                if ba_dct["billing_account"].business.account:
                    email_recs = ba_dct["billing_account"].business.account.email
                notif_sent = await send_account_inactive(
                    email_to=email_recs,
                    name=ba_dct["billing_account"].business.name,
                    month=invoice_period,
                )
                msg = (
                    "Account Deactivated, and "
                    if is_disabled
                    else "Account could not be Deactivated, and "
                )
                msg += (
                    "Warning Notification Sent"
                    if notif_sent
                    else "Error Sending Warning Notification"
                )
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=is_disabled and notif_sent,
                        reason=msg,
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
            # Unexpected case
            else:
                logger.info("**  Scenario not Expected, send error to Admin")
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=False,
                        reason="Ran into unexpected scenario for billing 8+ days from checkday",
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
        return bill_reports

    async def _run_billing_monthly_transfer_stripe(
        self, billing_accounts: List[BillingAccount], current_date: datetime
    ) -> List[BillingReport]:
        logger.info(f"Running Monthly Billing for Transfer Stripe ({current_date})")
        # Compare paid account created_at, and verify all accounts that its billing day has arrived
        bas_to_bill = self.filter_monthly_billing_past_due(
            billing_accounts, current_date
        )
        # Verify if Invoice has been generated and Paid for the current period
        bas_to_bill_not_paid = await self.filter_not_invoiced_current_monthly_period(
            bas_to_bill, verify_if_paid=True
        )
        logger.info(
            f"Billing Accounts in Period to Bill Invoice: {len(bas_to_bill_not_paid)}"
        )
        bill_reports = []
        # Implement Action depending on # of days without payment
        for ba_dct in bas_to_bill_not_paid:
            prep_dict = self.prepare_monthly_invoice_elements(
                ba_dct["billing_account"],
                current_date,
                ba_dct["month"],
                ba_dct["year"],
            )
            # skip if first month
            if prep_dict["first_month"]:
                continue
            # skip if handler is None
            if prep_dict["handler"] is None:
                bill_reports.append(
                    BillingReport(
                        paid_account_id=ba_dct["billing_account"].paid_account.id,
                        supplier=ba_dct["billing_account"].business.name,
                        invoice_name="",
                        status=False,
                        reason=f"Plan not valid: {ba_dct['billing_account'].paid_account.account_name}",
                        execution_time=datetime.utcnow(),
                    )
                )
                continue
            # unpack
            invoice_period = prep_dict["invoice_period"]
            days_from_checkday = prep_dict["days_from_checkday"]
            chandler = prep_dict["handler"]
            #####
            # import uuid
            # if ba_dct["billing_account"].business.id != uuid.UUID(
            #     "f8193dce-2026-492a-9b7d-68824587ddc8"
            # ):
            #     logger.info(
            #         f"XX  - Skipping Account: {ba_dct['billing_account'].business.name}"
            #     )
            #     continue
            #####
            breport_dict = {
                "paid_account_id": ba_dct["billing_account"].paid_account.id,
                "supplier": ba_dct["billing_account"].business.name,
                "invoice_name": invoice_period,
            }
            # Verify if Payment intent for the current period is already created
            is_spei_pi_created = await self.is_stripe_spei_payment_intent_created(
                ba_dct["billing_account"], invoice_period
            )
            # Implement Action depending on # of days without payment
            if days_from_checkday < 8:
                logger.info("-" * 30)
                logger.info(
                    f"**  ({days_from_checkday} / 7) - Try to Charge with Payment Intent"
                )
                # Compute Total Due
                total_due = await chandler.compute_total_due(
                    ba_dct["billing_account"], ba_dct["current_date"]
                )
                for _ch in total_due.charges:
                    logger.info(f"** {_ch.charge_type} = ${_ch.total_charge}")
                logger.info(f"** Total Due: ${total_due.total_due}")
                if total_due.total_due == 0:
                    # skip if total due is 0
                    continue
                # if PI not created, create it in Stripe and Create Invoice PPD
                inv_status = False
                if not is_spei_pi_created:
                    pi_status, msg, pi_id = (
                        await self.create_spei_stripe_payment_intent(
                            ba_dct["billing_account"],
                            total_due,
                            f"""{
                                ba_dct['billing_account'].paid_account.account_name.upper().replace('_', ' ')
                            } {invoice_period}""",
                            invoice_period,
                        )
                    )
                    if not pi_status:
                        bill_reports.append(
                            BillingReport(
                                status=False,
                                reason=msg,
                                execution_time=datetime.utcnow(),
                                **breport_dict,
                            )
                        )
                        continue
                    inv_status, inv_msg = await self.dispatch_invoice(
                        ba_dct["billing_account"],
                        invoice_month=invoice_period,
                        billing_charges_total=total_due,
                        invoice_type=InvoiceType.PPD,
                        is_paid=False,
                        payment_id=pi_id,
                    )
                    if not inv_status:
                        bill_reports.append(
                            BillingReport(
                                status=False,
                                reason="Payment Intent Created but, " + inv_msg,
                                execution_time=datetime.utcnow(),
                                **breport_dict,
                            )
                        )
                        continue
                # Send Reminder to Business to pay
                confirmation_email = (
                    ba_dct["billing_account"].business.account.email
                    if (
                        ba_dct["billing_account"].business.account
                        and ba_dct["billing_account"].business.account.email
                    )
                    else "pagosyfacturas@alima.la"
                )
                sent_status = await send_alima_invoice_pending_notification(
                    email_to=confirmation_email,
                    name=ba_dct["billing_account"].business.name,
                    tolerance=8 - days_from_checkday,
                    month=invoice_period,
                    bank_info={
                        "bank_name": ba_dct["billing_account"].payment_method.bank_name,
                        "account_name": ba_dct[
                            "billing_account"
                        ].payment_method.account_name
                        or "",
                        "account_number": ba_dct[
                            "billing_account"
                        ].payment_method.account_number,
                    },
                )
                report_msg = ""
                if inv_status and sent_status:
                    report_msg = f"Invoice Generated: {invoice_period}, and Sent Payment Reminder"
                if not inv_status and sent_status:
                    report_msg = f"Sent Payment Reminder ({days_from_checkday} / 7)"
                if not sent_status:
                    report_msg = "Error Sending Payment Reminder"
                bill_reports.append(
                    BillingReport(
                        status=sent_status,
                        reason=report_msg,
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
            # Deactivate Account
            elif days_from_checkday == 8:
                logger.info("**  Deactivating Account")
                # Deactivate Account
                is_disabled = await self.default_handler.disable_alima_account(
                    ba_dct["billing_account"].business.id
                )
                # Send Notice of Closing Account
                email_recs = "automations@alima.la"
                if ba_dct["billing_account"].business.account:
                    email_recs = ba_dct["billing_account"].business.account.email
                notif_sent = await send_account_inactive(
                    email_to=email_recs,
                    name=ba_dct["billing_account"].business.name,
                    month=invoice_period,
                )
                msg = (
                    "Account Deactivated, and "
                    if is_disabled
                    else "Account could not be Deactivated, and "
                )
                msg += (
                    "Warning Notification Sent"
                    if notif_sent
                    else "Error Sending Warning Notification"
                )
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=is_disabled and notif_sent,
                        reason=msg,
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
            # Unexpected case
            else:
                logger.info("**  Scenario not Expected, send error to Admin")
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=False,
                        reason="Ran into unexpected scenario for billing 8+ days from checkday",
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )

        return bill_reports

    # [TODO] - needs to be implemented
    async def _run_billing_annual_card_stripe(
        self, billing_accounts: List[BillingAccount], current_date: datetime
    ) -> List[BillingReport]:
        logger.info("Running Annual Billing for Card Stripe")
        logger.info(f"Billing Accounts: {len(billing_accounts)}")
        ba_reports = []
        for ba in billing_accounts:
            # invoice period from month and year
            brep = BillingReport(
                paid_account_id=ba.paid_account.id,
                supplier=ba.business.name,
                invoice_name="",
                status=False,
                reason="Annual Billing not implemented yet",
                execution_time=datetime.utcnow(),
            )
            ba_reports.append(brep)
        return ba_reports

    # [TODO] - needs to be implemented
    async def _run_billing_annual_transfer_stripe(
        self, billing_accounts: List[BillingAccount], current_date: datetime
    ) -> List[BillingReport]:
        logger.info(f"Running Annual Billing for Transfer Stripe ({current_date})")
        # Compare paid account created_at, and verify all accounts that its billing day has arrived
        bas_to_bill = self.filter_annual_billing_past_due(
            billing_accounts, current_date
        )
        # Verify if Invoice has been generated and Paid for the current period
        bas_to_bill_not_paid = await self.filter_not_invoiced_current_annual_period(
            bas_to_bill, verify_if_paid=True
        )
        logger.info(
            f"Billing Accounts in Period to Bill Invoice: {len(bas_to_bill_not_paid)}"
        )
        bill_reports = []
        # Implement Action depending on # of days without payment
        for ba_dct in bas_to_bill_not_paid:
            prep_dict = self.prepare_annual_invoice_elements(
                ba_dct["billing_account"],
                current_date,
                ba_dct["month"],
                ba_dct["year"],
            )
            # skip if handler is None
            if prep_dict["handler"] is None:
                bill_reports.append(
                    BillingReport(
                        paid_account_id=ba_dct["billing_account"].paid_account.id,
                        supplier=ba_dct["billing_account"].business.name,
                        invoice_name="",
                        status=False,
                        reason=f"Plan not valid: {ba_dct['billing_account'].paid_account.account_name}",
                        execution_time=datetime.now(timezone.utc),
                    )
                )
                continue
            # unpack
            invoice_period = prep_dict["invoice_period"]
            days_from_checkday = prep_dict["days_from_checkday"]
            chandler = prep_dict["handler"]
            #####
            import uuid

            if ba_dct["billing_account"].business.id != uuid.UUID(
                "1b350cc2-0c37-46f8-9af7-991d3ccadfe6"
            ):
                logger.info(
                    f"XX  - Skipping Account: {ba_dct['billing_account'].business.name}"
                )
                continue
            #####
            breport_dict = {
                "paid_account_id": ba_dct["billing_account"].paid_account.id,
                "supplier": ba_dct["billing_account"].business.name,
                "invoice_name": invoice_period,
            }
            # Verify if Payment intent for the current period is already created
            is_spei_pi_created = await self.is_stripe_spei_payment_intent_created(
                ba_dct["billing_account"], invoice_period
            )
            # Implement Action depending on # of days without payment
            if days_from_checkday < 8:
                logger.info("-" * 30)
                logger.info(
                    f"**  ({days_from_checkday} / 7) - Try to Charge with Payment Intent"
                )
                # Compute Total Due
                total_due = await chandler.compute_total_due(
                    ba_dct["billing_account"], ba_dct["current_date"]
                )
                for _ch in total_due.charges:
                    logger.info(f"** {_ch.charge_type} = ${_ch.total_charge}")
                logger.info(f"** Total Due: ${total_due.total_due}")
                if total_due.total_due == 0:
                    # skip if total due is 0
                    continue
                # if PI not created, create it in Stripe and Create Invoice PPD
                inv_status = False
                if not is_spei_pi_created:
                    pi_status, msg, pi_id = (
                        await self.create_spei_stripe_payment_intent(
                            ba_dct["billing_account"],
                            total_due,
                            f"""{
                                ba_dct['billing_account'].paid_account.account_name.upper().replace('_', ' ')
                            } {invoice_period}""",
                            invoice_period,
                        )
                    )
                    if not pi_status:
                        bill_reports.append(
                            BillingReport(
                                status=False,
                                reason=msg,
                                execution_time=datetime.utcnow(),
                                **breport_dict,
                            )
                        )
                        continue
                    inv_status, inv_msg = await self.dispatch_invoice(
                        ba_dct["billing_account"],
                        invoice_month=invoice_period,
                        billing_charges_total=total_due,
                        invoice_type=InvoiceType.PPD,
                        is_paid=False,
                        payment_id=pi_id,
                    )
                    if not inv_status:
                        bill_reports.append(
                            BillingReport(
                                status=False,
                                reason="Payment Intent Created but, " + inv_msg,
                                execution_time=datetime.utcnow(),
                                **breport_dict,
                            )
                        )
                        continue
                # Send Reminder to Business to pay
                confirmation_email = (
                    ba_dct["billing_account"].business.account.email
                    if (
                        ba_dct["billing_account"].business.account
                        and ba_dct["billing_account"].business.account.email
                    )
                    else "pagosyfacturas@alima.la"
                )
                sent_status = await send_alima_invoice_pending_notification(
                    email_to=confirmation_email,
                    name=ba_dct["billing_account"].business.name,
                    tolerance=8 - days_from_checkday,
                    month=invoice_period,
                    bank_info={
                        "bank_name": ba_dct["billing_account"].payment_method.bank_name,
                        "account_name": ba_dct[
                            "billing_account"
                        ].payment_method.account_name
                        or "",
                        "account_number": ba_dct[
                            "billing_account"
                        ].payment_method.account_number,
                    },
                )
                report_msg = ""
                if inv_status and sent_status:
                    report_msg = f"Invoice Generated: {invoice_period}, and Sent Payment Reminder"
                if not inv_status and sent_status:
                    report_msg = f"Sent Payment Reminder ({days_from_checkday} / 7)"
                if not sent_status:
                    report_msg = "Error Sending Payment Reminder"
                bill_reports.append(
                    BillingReport(
                        status=sent_status,
                        reason=report_msg,
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
            # Deactivate Account
            elif days_from_checkday == 8:
                logger.info("**  Deactivating Account")
                # Deactivate Account
                is_disabled = await self.default_handler.disable_alima_account(
                    ba_dct["billing_account"].business.id
                )
                # Send Notice of Closing Account
                email_recs = "automations@alima.la"
                if ba_dct["billing_account"].business.account:
                    email_recs = ba_dct["billing_account"].business.account.email
                notif_sent = await send_account_inactive(
                    email_to=email_recs,
                    name=ba_dct["billing_account"].business.name,
                    month=invoice_period,
                )
                msg = (
                    "Account Deactivated, and "
                    if is_disabled
                    else "Account could not be Deactivated, and "
                )
                msg += (
                    "Warning Notification Sent"
                    if notif_sent
                    else "Error Sending Warning Notification"
                )
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=is_disabled and notif_sent,
                        reason=msg,
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )
            # Unexpected case
            else:
                logger.info("**  Scenario not Expected, send error to Admin")
                # Accumulate for Report
                bill_reports.append(
                    BillingReport(
                        status=False,
                        reason="Ran into unexpected scenario for billing 8+ days from checkday",
                        execution_time=datetime.utcnow(),
                        **breport_dict,
                    )
                )

        return bill_reports

    async def run_billing_routine(
        self,
        pay_provider: PayProviderType,
        billing_period: Literal["monthly", "annual"],
        current_date: datetime,
    ) -> List[BillingReport]:
        """Run Billing Annual or Monthly for each pay provider

        Args:
            pay_provider (PayProviderType)

        Returns:
            List[BillingReport]: Result with ok / error message
        """
        # verify pay provider is implemented
        if pay_provider not in self.available_payproviders:
            logger.error(f"Pay Provider not implemented: {pay_provider}")
            return []
        # fetch billing accounts
        billing_accounts = await self.default_handler.fetch_billing_accounts(
            billing_period=billing_period
        )
        # filter accounts that have the payprovider that is provided
        pp_billing_accs = [
            ba
            for ba in billing_accounts
            if ba.payment_method.payment_provider == pay_provider
        ]
        if not pp_billing_accs:
            logger.info(f"No Billing Accounts for {pay_provider} {billing_period}")
            return []
        # apply switch depending on pay provider and billing period
        if pay_provider == PayProviderType.CARD_STRIPE:
            if billing_period == "monthly":
                return await self._run_billing_monthly_card_stripe(
                    pp_billing_accs, current_date
                )
            if billing_period == "annual":
                return await self._run_billing_annual_card_stripe(
                    pp_billing_accs, current_date
                )
        if pay_provider == PayProviderType.TRANSFER_STRIPE:
            if billing_period == "monthly":
                return await self._run_billing_monthly_transfer_stripe(
                    pp_billing_accs, current_date
                )
            if billing_period == "annual":
                return await self._run_billing_annual_transfer_stripe(
                    pp_billing_accs, current_date
                )
        # return empty list if no match
        return []
