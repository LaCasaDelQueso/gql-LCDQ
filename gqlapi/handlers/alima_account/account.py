import base64
import calendar
from datetime import date, datetime, timezone
import json
import random
import string
from types import NoneType
from typing import Any, Dict, List, Literal, Optional, Tuple
from uuid import UUID, uuid4
from dateutil.relativedelta import relativedelta

from bson import Binary

from gqlapi.lib.clients.clients.facturamaapi.facturama import (
    Customer as FacturamaCustomer,
    CustomerAddress as FacturamaCustomerAddress,
    FacturamaClientApi,
    FacturamaComplement,
    FacturamaInternalInvoice,
    FacturamaInternalInvoiceComplement,
    FacturamaPayments,
    GlobalInformationFacturama,
    Item as FacturamaItem,
    PaymentForm,
    RelatedDocuments,
    SatTaxes,
)
from gqlapi.lib.clients.clients.godaddyapi.godaddy import GoDaddyClientApi
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi
from gqlapi.lib.clients.clients.vercelapi.vercel import (
    VercelClientApi,
    VercelEnvironmentVariables,
    VercelGitRepository,
    VercelUtils,
)
from gqlapi.domain.interfaces.v2.alima_account.account import (
    AlimaAccountHandlerInterface,
    AlimaAccountListenerInterface,
    AlimaAccountPlan,
    AlimaAccountPlanDiscount,
    AlimaAccountRepositoryInterface,
    AlimaBillingInvoiceComplementRepositoryInterface,
    AlimaBillingInvoiceRepositoryInterface,
    BillingAccount,
    BillingPaymentMethodGQL,
    BillingTotalDue,
    SupplierAlimaAccount,
    SupplierAlimaAccountConfig,
    SupplierAlimaBillingInvoice,
)
from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    EcommerceSellerHandlerInterface,
    EcommerceSellerRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.integrations.integrations import (
    IntegrationWebhookRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import InvoiceStatus
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessAccountRepositoryInterface,
    SupplierBusinessGQL,
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_invoice import INVOICE_PAYMENT_MAP
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.models.v2.alima_business import (
    BillingInvoice,
    BillingInvoiceCharge,
    BillingPaymentMethod,
    Charge,
    ChargeDiscount,
    PaidAccount,
)
from gqlapi.domain.models.v2.b2bcommerce import (
    EcommerceParams,
    EcommerceSeller,
    NewEcommerceEnvVars,
)
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.supplier import SupplierBusiness, SupplierBusinessAccount
from gqlapi.domain.models.v2.utils import (
    AlimaCustomerType,
    ChargeType,
    CurrencyType,
    InvoiceStatusType,
    InvoiceType,
    PayMethodType,
    PayProviderType,
    PayStatusType,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

from gqlapi.handlers.services.mails import (
    send_alima_invoice_complement_notification_v2,
    send_reports_alert,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
)
from gqlapi.utils.helpers import generate_secret_key, list_into_strtuple
from gqlapi.config import (
    ALIMA_EXPEDITION_PLACE,
    APP_TZ,
    FACT_PWD,
    FACT_USR,
    ENV as DEV_ENV,
    GODADDY_API_KEY,
    GODADDY_API_SECRET,
    GODADDY_DOMAIN,
    STRIPE_API_SECRET,
    VERCEL_TEAM,
    VERCEL_TOKEN,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import (
    CoreUserRepositoryInterface,
)
from gqlapi.utils.domain_mapper import domain_to_dict

logger = get_logger(get_app())

# Constants
included_folios_per_cedis = 200
alima_supply_valid_plans = [
    "alima_comercial",
    "alima_pro",
    "alima_comercial_anual",
    "alima_pro_anual",
]
alima_price_map = {
    "alima_comercial": 1200,
    "alima_pro": 1750,
}


class AlimaAccountHandler(AlimaAccountHandlerInterface):
    valid_monthly_plans = ["alima_comercial", "alima_pro"]
    valid_annual_plans = ["alima_comercial_anual", "alima_pro_anual"]
    plans_with_folios = ["alima_pro", "alima_pro_anual"]
    plans_with_payments = ["alima_pro", "alima_pro_anual"]

    def __init__(
        self,
        alima_account_repository: AlimaAccountRepositoryInterface,
        core_user_repository: CoreUserRepositoryInterface,
        supplier_business_repository: Optional[
            SupplierBusinessRepositoryInterface
        ] = None,
        supplier_business_account_repository: Optional[
            SupplierBusinessAccountRepositoryInterface
        ] = None,
        supplier_user_repository: Optional[SupplierUserRepositoryInterface] = None,
        supplier_user_permission_repository: Optional[
            SupplierUserPermissionRepositoryInterface
        ] = None,
        alima_billing_invoice_repository: Optional[
            AlimaBillingInvoiceRepositoryInterface
        ] = None,
        alima_billing_complement_repository: Optional[
            AlimaBillingInvoiceComplementRepositoryInterface
        ] = None,
        ecommerce_seller_repository: Optional[
            EcommerceSellerRepositoryInterface
        ] = None,
        integration_webhook_repo: Optional[
            IntegrationWebhookRepositoryInterface
        ] = None,
    ) -> None:
        self.repository = alima_account_repository
        self.core_user_repository = core_user_repository
        self.facturama_api = FacturamaClientApi(
            usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV
        )
        if supplier_business_repository:
            self.supplier_business_repository = supplier_business_repository
        if supplier_business_account_repository:
            self.supplier_business_account_repository = (
                supplier_business_account_repository
            )
        if supplier_user_repository:
            self.supplier_user_repository = supplier_user_repository
        if supplier_user_permission_repository:
            self.supplier_user_permission_repository = (
                supplier_user_permission_repository
            )
        if alima_billing_invoice_repository:
            self.alima_billing_invoice_repository = alima_billing_invoice_repository
        if alima_billing_complement_repository:
            self.alima_billing_complement_repository = (
                alima_billing_complement_repository
            )
        if ecommerce_seller_repository:
            self.ecommerce_seller_repository = ecommerce_seller_repository
        if integration_webhook_repo:
            self.integration_webhook_repo = integration_webhook_repo

    @property
    def valid_plans(self) -> List[str]:
        _valid_plans = self.valid_monthly_plans + self.valid_annual_plans
        assert len(_valid_plans) == len(alima_supply_valid_plans)
        return _valid_plans

    # Private Helper functions
    @staticmethod
    def get_active_invoice(invoices: List[BillingInvoice]) -> BillingInvoice | None:
        for inv in invoices:
            if inv.status == InvoiceStatusType.ACTIVE:
                return inv
        return None

    @staticmethod
    def is_month_last_day(current_date: datetime) -> bool:
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        return current_date.day == last_day

    @staticmethod
    def find_discounts(
        charge_id: UUID, charge_discounts: List[ChargeDiscount]
    ) -> List[ChargeDiscount]:
        filter_charge_discounts = []
        for cd in charge_discounts:
            if cd.charge_id == charge_id:
                filter_charge_discounts.append(cd)
        return filter_charge_discounts

    @staticmethod
    def compute_total_with_discounts(
        chtype: str, chtotal_without_discount: float, discount: List[ChargeDiscount]
    ) -> Tuple[float, str]:
        chtype = chtype + " ("
        chtotal = chtotal_without_discount
        for dc in discount:
            if dc.charge_discount_amount_type == "$":
                chtotal = chtotal - dc.charge_discount_amount
                chtype = chtype + f"Descuento de ${dc.charge_discount_amount} /"
            if dc.charge_discount_amount_type == "%":
                chtotal = chtotal * (1 - dc.charge_discount_amount)
                chtype = chtype + f"Descuento de {dc.charge_discount_amount*100}% /"
        chtype = chtype[:-1]
        chtype = chtype + ")"
        return chtotal, chtype

    @staticmethod
    def compute_fee_charge(
        chtype: str, ch: Charge, num_units: int, discount: List[ChargeDiscount]
    ) -> Tuple[float, float, str]:
        """Compute SaaS fee charge

        Args:
            chtype (str): _description_
            ch (Charge): _description_
            num_units (int): _description_
            discount (List[ChargeDiscount]): _description_

        Returns:
            Tuple[float, float, str]: (Total with IVA, Total, Charge type)
        """
        chbase = num_units
        chtotal_without_discount = chbase * ch.charge_amount
        # Saas fee * num units +  16% IVA
        if discount:
            chtotal, chtype = AlimaAccountHandler.compute_total_with_discounts(
                chtype, chtotal_without_discount, discount
            )
        else:
            chtotal = chtotal_without_discount
        chtotal_with_iva = chtotal * 1.16
        return chtotal_with_iva, chtotal, chtype

    @staticmethod
    def compute_reports_charge(
        ch: Charge, discount: List[ChargeDiscount], chbase: int = 1
    ) -> Tuple[float, float, str]:
        """Compute reports charge

        Args:
            ch (Charge): _description_
            discount (List[ChargeDiscount]): _description_

        Returns:
            Tuple[float, float, str]: (Total with IVA, Total, Charge type)
        """
        chtype = "Reporte"
        if ch.charge_description:
            chtype = ch.charge_description

        chtotal_without_discount = chbase * ch.charge_amount
        if discount:
            chtotal, chtype = AlimaAccountHandler.compute_total_with_discounts(
                chtype, chtotal_without_discount, discount
            )
        else:
            chtotal = chtotal_without_discount
        chtotal_with_iva = chtotal * 1.16
        return chtotal_with_iva, chtotal, chtype

    @staticmethod
    def compute_folios_charge(
        folios_extra: int, chtype: str, ch: Charge, discount: List[ChargeDiscount] = []
    ) -> Tuple[float, float, str]:
        """Compute folios charge

        Args:
            folios_extra (int): Additional folios
            chtype (str): Charge type
            ch (Charge): Charge object
            discount (List[ChargeDiscount]): List of discounts

        Returns:
            Tuple[float, float, str]: (Total with IVA, Total, Charge type)
        """
        chtotal_without_discount = folios_extra * ch.charge_amount
        if discount:
            chtotal, chtype = AlimaAccountHandler.compute_total_with_discounts(
                chtype, chtotal_without_discount, discount
            )
        else:
            chtotal = chtotal_without_discount
        chtotal_with_iva = chtotal * 1.16
        return chtotal_with_iva, chtotal, chtype

    @staticmethod
    def compute_payment_charge(
        payments_count: int,
        chtype: str,
        ch: Charge,
        discount: List[ChargeDiscount] = [],
    ) -> Tuple[float, float, str]:
        """Compute folios charge

        Args:
            payments_count (int): Payments count
            chtype (str): Charge type
            ch (Charge): Charge object
            discount (List[ChargeDiscount]): List of discounts

        Returns:
            Tuple[float, float, str]: (Total with IVA, Total, Charge type)
        """
        chtotal_without_discount = payments_count * ch.charge_amount
        if discount:
            chtotal, chtype = AlimaAccountHandler.compute_total_with_discounts(
                chtype, chtotal_without_discount, discount
            )
        else:
            chtotal = chtotal_without_discount
        chtotal_with_iva = chtotal * 1.16
        return chtotal_with_iva, chtotal, chtype

    @staticmethod
    def format_charges_for_invoice(
        total_charges: List[BillingInvoiceCharge],
    ) -> List[FacturamaItem]:
        """Format charges into Facturama items

        Args:
            total_charges (List[BillingInvoiceCharge]): _description_

        Returns:
            List[FacturamaItem]
        """
        item_list = []
        for _ch in total_charges:
            if (
                "Servicio de Software" in _ch.charge_type
                or "Reporte" in _ch.charge_type
            ):
                unit_code = "E48"
                sat_code = "81161501"
                qty = _ch.charge_base_quantity
                uprice = round((_ch.total_charge / qty) / (1 + 0.16), 4)
            else:
                unit_code = "A9"
                sat_code = "80141600"
                qty = _ch.charge_base_quantity
                uprice = round((_ch.total_charge / qty) / (1 + 0.16), 4)

            subtotal = round(uprice * qty, 2)

            item = FacturamaItem(
                ProductCode=sat_code,
                Description=_ch.charge_type,
                UnitCode=unit_code,
                Subtotal=subtotal,
                Quantity=qty,
                TaxObject="02",
                Total=round(subtotal * 1.16, 4),
                Taxes=[
                    SatTaxes(
                        Total=round(0.16 * subtotal, 4),
                        Name="IVA",
                        Base=round(subtotal, 4),
                        Rate=0.16,
                        IsRetention=False,
                    )
                ],
                UnitPrice=uprice,
            )
            item_list.append(item)
        return item_list

    @staticmethod
    def create_global_payment_info() -> (
        Tuple[GlobalInformationFacturama, FacturamaCustomer]
    ):
        """Create Global Payment Information

        Returns:
            Tuple[GlobalInformationFacturama, FacturamaCustomer]: _description_
        """
        issue_date = datetime.utcnow()
        global_information = GlobalInformationFacturama(
            Periodicity="01",
            Months=issue_date.strftime("%m"),
            Year=issue_date.strftime("%Y"),
        )
        gl_fct_client = FacturamaCustomer(
            Email="pagosyfacturas@alima.la",
            Address=FacturamaCustomerAddress(
                ZipCode="06100",
            ),
            Rfc="XAXX010101000",
            Name="PUBLICO EN GENERAL",
            CfdiUse="S01",
            FiscalRegime="616",
            TaxZipCode=ALIMA_EXPEDITION_PLACE,
        )
        return global_information, gl_fct_client

    @staticmethod
    def generate_account_config_data(
        paid_account_name: AlimaAccountPlan,
    ) -> Dict[str, Any]:
        # account name validation
        template_sections = [
            # Home
            {
                "section_id": "0",
                "section_name": "",
                "subsections": [
                    {
                        "subsection_id": "0.1",
                        "subsection_name": "Home",
                        "available": True,
                        "plugins": [],
                    }
                ],
            },
            # Clientes
            {
                "section_id": "1",
                "section_name": "Clientes",
                "subsections": [
                    {
                        "subsection_id": "1.1",
                        "subsection_name": "Clientes",
                        "available": True,
                        "plugins": [],
                    }
                ],
            },
            # Pedidos
            {
                "section_id": "2",
                "section_name": "Pedidos",
                "subsections": [
                    {
                        "subsection_id": "2.1",
                        "subsection_name": "Catálogo",
                        "available": True,
                        "plugins": [],
                    },
                    {
                        "subsection_id": "2.2",
                        "subsection_name": "Pedidos",
                        "available": True,
                        "plugins": [],
                    },
                    {
                        "subsection_id": "2.3",
                        "subsection_name": "Facturas",
                        "available": (
                            True
                            if paid_account_name == AlimaAccountPlan.ALIMA_PRO
                            else False
                        ),
                        "plugins": [],
                    },
                ],
            },
            # Pagos
            {
                "section_id": "3",
                "section_name": "Pagos",
                "subsections": [
                    {
                        "subsection_id": "3.1",
                        "subsection_name": "Pagos",
                        "available": (
                            True
                            if paid_account_name == AlimaAccountPlan.ALIMA_PRO
                            else False
                        ),
                        "plugins": [],
                    }
                ],
            },
            # Reports
            {
                "section_id": "4",
                "section_name": "Reportes",
                "subsections": [
                    {
                        "subsection_id": "4.1",
                        "subsection_name": "Reportes",
                        "available": True,
                        "plugins": [],
                    }
                ],
            },
            # E-commerce B2B
            {
                "section_id": "5",
                "section_name": "E-commerce B2B",
                "subsections": [
                    {
                        "subsection_id": "5.1",
                        "subsection_name": "E-commerce B2B",
                        "available": True,
                        "plugins": [],
                    }
                ],
            },
        ]
        return {
            "sections": template_sections,
        }

    # Private Member functions

    async def _fetch_curr_user(
        self, firebase_id: str
    ) -> Tuple[CoreUser, Dict[Any, Any], Dict[Any, Any]]:
        # fetch core user
        core_user = await self.core_user_repository.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="Core user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch supplier user
        supplier_user = await self.supplier_user_repository.fetch(core_user.id)
        if (
            not supplier_user
            or not isinstance(supplier_user, dict)
            or not supplier_user["id"]
        ):
            raise GQLApiException(
                msg="Supplier user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch supplier user perms
        supplier_user_perms = await self.supplier_user_permission_repository.fetch(
            supplier_user["id"]
        )
        if not supplier_user_perms or not supplier_user_perms["id"]:
            raise GQLApiException(
                msg="Supplier user permission not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        return core_user, supplier_user, supplier_user_perms

    async def _fetch_supplier_businesses(
        self,
        supplier_business_ids: List[UUID],
        active: Optional[bool] = True,
    ) -> List[SupplierBusinessGQL]:
        sbuss: List[SupplierBusinessGQL] = []
        try:
            # find all active supplier_businesses
            sbs_dicts = await self.supplier_business_repository.find(active=active)
            sbs_qd_ids = [
                Binary.from_uuid(sb["id"])
                for sb in sbs_dicts
                if sb.get("id", None) in supplier_business_ids
            ]
            sbs_idx = {sb["id"]: sb for sb in sbs_dicts}
            # find all supplier_business_accounts
            sbas_dicts = await self.supplier_business_account_repository.raw_query(
                collection="supplier_business_account",
                query={"supplier_business_id": {"$in": sbs_qd_ids}},
            )
            # generate supplier business objects
            for sba in sbas_dicts:
                _sba = SupplierBusinessAccountRepository.deserialize_account(sba)
                _sb = SupplierBusinessGQL(**sbs_idx[_sba.supplier_business_id])
                _sb.account = _sba
                sbuss.append(_sb)
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get supplier businesses")
            return []
        return sbuss

    async def _fetch_billing_payment_methods(
        self, paid_account_ids: List[UUID], only_active: bool = True
    ) -> List[BillingPaymentMethod]:
        try:
            query = f"""
                SELECT
                    bpm.*
                FROM billing_payment_method bpm
                WHERE bpm.paid_account_id IN {list_into_strtuple(paid_account_ids)}
            """
            if only_active:
                query += " AND bpm.active = 't'"
            # fetch billing payment methods
            bpms: List[Dict[str, Any]] = (
                await self.alima_billing_invoice_repository.raw_query(query, vals={})
            )
            if not bpms:
                logger.info("No billing payment methods found")
                return []
            bpm_objs = []
            for bpm in bpms:
                _bpm = dict(bpm)
                _bpm["payment_type"] = PayMethodType(bpm["payment_type"])
                _bpm["payment_provider"] = PayProviderType(bpm["payment_provider"])
                bpm_objs.append(BillingPaymentMethod(**_bpm))
            return bpm_objs
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get billing payment methods")
            return []

    async def _complete_billing_accounts(
        self, paid_account_dicts: List[Dict[str, Any]]
    ) -> List[BillingAccount]:
        # retrieve accounts from supplier_businesses
        sb_ids = [pa["customer_business_id"] for pa in paid_account_dicts]
        supplier_businesses = await self._fetch_supplier_businesses(sb_ids)
        if not supplier_businesses:
            logger.info("No supplier businesses found")
            return []
        # retrieve active billing payment methods
        pa_ids = [pa["id"] for pa in paid_account_dicts]
        b_paymethods = await self._fetch_billing_payment_methods(pa_ids)
        # create indexes
        sbs_idx = {sb.id: sb for sb in supplier_businesses}
        bpms_idx = {bpm.paid_account_id: bpm for bpm in b_paymethods}
        # build object
        billing_accounts = []
        for pa in paid_account_dicts:
            _pa = {}
            pa_dict = dict(pa)
            pa_dict["customer_type"] = AlimaCustomerType(pa_dict["customer_type"])
            _pa["paid_account"] = PaidAccount(**pa_dict)
            _pa["business"] = sbs_idx[pa["customer_business_id"]]
            _pa["payment_method"] = bpms_idx[pa["id"]]
            billing_accounts.append(BillingAccount(**_pa))
        return billing_accounts

    async def _complete_business_account(
        self, supplier_business_id: UUID
    ) -> SupplierBusinessGQL | NoneType:
        # retrieve accounts from supplier_businesses
        supplier_businesses = await self._fetch_supplier_businesses(
            [supplier_business_id], active=None
        )
        if not supplier_businesses:
            logger.info("No supplier businesses found")
            return None
        # return supplier business
        return supplier_businesses[0]

    async def _fetch_anual_billing_accounts(
        self,
    ) -> List[BillingAccount]:
        try:
            query = f"""
                    SELECT
                        pa.*
                    FROM paid_account pa
                    JOIN supplier_business sb
                        ON sb.id = pa.customer_business_id
                    WHERE pa.account_name IN {list_into_strtuple(self.valid_annual_plans)}
                    AND sb.active = 't'
                """
            alima_anual_billing_accounts: List[Dict[str, Any]] = (
                await self.alima_billing_invoice_repository.raw_query(query, {})
            )
            if not alima_anual_billing_accounts:
                logger.info("No alima anual billing accounts found")
                return []
            return await self._complete_billing_accounts(alima_anual_billing_accounts)
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get alima anual billing accounts")
            return []

    async def _fetch_monthly_billing_accounts(self) -> List[BillingAccount]:
        try:
            query = f"""
                SELECT
                    pa.*
                FROM paid_account pa
                JOIN supplier_business sb
                    ON sb.id = pa.customer_business_id
                WHERE pa.account_name IN {list_into_strtuple(self.valid_monthly_plans)}
                AND sb.active = 't'
                """
            alima_billing_accounts: List[Dict[str, Any]] = (
                await self.alima_billing_invoice_repository.raw_query(query, {})
            )
            if not alima_billing_accounts:
                logger.info("No alima billing accounts found")
                return []
            return await self._complete_billing_accounts(alima_billing_accounts)
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get alima billing accounts")
            return []

    # --- Member functions

    # app getters
    async def fetch_supplier_alima_account_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierAlimaAccount:
        """Fetch supplier Alima account by firebase id

        Parameters
        ----------
        firebase_id : str

        Returns
        -------
        SupplierAlimaAccount
        """
        # fetch current user
        core_user, supplier_user, supplier_user_perms = await self._fetch_curr_user(
            firebase_id
        )
        # fetch paid account
        paid_account = await self.repository.fetch_alima_account(
            supplier_user_perms["supplier_business_id"]
        )
        if not paid_account:
            # if not paid account, return supplier business id
            return SupplierAlimaAccount(
                supplier_business_id=supplier_user_perms["supplier_business_id"],
                account=None,
                charges=[],
                payment_methods=[],
            )
        # fetch charges
        charges = await self.repository.fetch_charges(paid_account.id)
        discounts = await self.repository.fetch_discounts_charges(paid_account.id)
        # fetch payment methods
        _py_methods = await self.repository.fetch_payment_methods(paid_account.id)
        payment_methods: List[BillingPaymentMethodGQL] = []
        # add provider info for payment method card
        st_client = StripeApi(get_app(), STRIPE_API_SECRET)
        for pm in _py_methods:
            new_pm = BillingPaymentMethodGQL(**domain_to_dict(pm))
            # review for stripe card
            if pm.payment_provider.value == "stripe" and pm.payment_provider_id:
                # fetch payment methods from stripe
                _cards = st_client.get_cards_list(pm.payment_provider_id)
                _cards_dicts = [c.to_dict() for c in _cards]
                new_pm.provider_data = json.dumps(_cards_dicts)
            payment_methods.append(new_pm)
        # return supplier alima account
        return SupplierAlimaAccount(
            supplier_business_id=supplier_user_perms["supplier_business_id"],
            account=paid_account,
            charges=charges,
            payment_methods=payment_methods,
            discounts=discounts,
        )

    async def fetch_supplier_alima_historic_invoices(
        self,
        firebase_id: str,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
    ) -> List[SupplierAlimaBillingInvoice]:
        """Fetch supplier alima historic invoices

        Parameters
        ----------
        firebase_id : str
        from_date : Optional[date], optional
        until_date : Optional[date], optional

        Returns
        -------
        List[SupplierAlimaBillingInvoice]
        """
        # fetch curret user
        core_user, supplier_user, supplier_user_perms = await self._fetch_curr_user(
            firebase_id
        )
        # fetch paid account
        paid_account = await self.repository.fetch_alima_account(
            supplier_user_perms["supplier_business_id"]
        )
        if not paid_account:
            # if not paid account, raise not found exception
            raise GQLApiException(
                msg="Supplier Alima account not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch invoices
        invoices = await self.alima_billing_invoice_repository.fetch_alima_invoices(
            paid_account.id, from_date, until_date
        )
        invoice_idx = {invoice.id: invoice for invoice in invoices}
        invoice_ids_list = list(invoice_idx.keys())
        # fetch invoice charges
        invoice_charges = (
            await self.alima_billing_invoice_repository.fetch_alima_invoice_charges(
                invoice_ids_list
            )
        )
        invoice_charges_idx = {}
        for inv_ch in invoice_charges:
            if inv_ch.billing_invoice_id not in invoice_charges_idx:
                invoice_charges_idx[inv_ch.billing_invoice_id] = []
            invoice_charges_idx[inv_ch.billing_invoice_id].append(inv_ch)
        # fetch invoice paystatus
        invoice_paystatus = (
            await self.alima_billing_invoice_repository.fetch_alima_invoice_paystatus(
                invoice_ids_list
            )
        )
        invoice_paystatus_idx = {
            inv_ps.billing_invoice_id: inv_ps for inv_ps in invoice_paystatus
        }
        # zip all together
        sup_historics = []
        for inv_id in invoice_ids_list:
            sup_historics.append(
                SupplierAlimaBillingInvoice(
                    invoice=invoice_idx[inv_id],
                    invoice_charges=invoice_charges_idx.get(inv_id, []),
                    invoice_paystatus=invoice_paystatus_idx.get(inv_id, None),
                )
            )
        # return supplier alima billing invoices
        return sup_historics

    async def fetch_supplier_alima_account_config_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierAlimaAccountConfig:
        """Fetch supplier alima account config by firebase id

        Args:
            firebase_id (str): firebase id

        Returns:
            SupplierAlimaAccountConfig: supplier alima account config
        """
        # fetch current user
        core_user, supplier_user, supplier_user_perms = await self._fetch_curr_user(
            firebase_id
        )
        # fetch paid account
        paid_account = await self.repository.fetch_alima_account(
            supplier_user_perms["supplier_business_id"]
        )
        if not paid_account:
            # if not paid account, return supplier business id
            return SupplierAlimaAccountConfig(
                supplier_business_id=supplier_user_perms["supplier_business_id"],
            )
        # fetch paid account config
        paid_account_config = await self.repository.fetch_alima_account_config(
            paid_account.id
        )
        if not paid_account_config:
            # if not paid account config, return supplier business id
            return SupplierAlimaAccountConfig(
                supplier_business_id=supplier_user_perms["supplier_business_id"],
                paid_account_id=paid_account.id,
            )
        # return supplier alima account config
        return SupplierAlimaAccountConfig(
            supplier_business_id=supplier_user_perms["supplier_business_id"],
            paid_account_id=paid_account.id,
            config=paid_account_config.config,
            created_at=paid_account_config.created_at,
            last_updated=paid_account_config.last_updated,
        )

    # invoicing functions
    async def new_alima_invoice_complement(
        self,
        supplier_business_id: UUID,
        payment_form: PaymentForm,
        amount: float,
        active_invoice: BillingInvoice,
    ) -> UUID | NoneType:
        supplier = await self.supplier_business_repository.fetch(supplier_business_id)
        if not supplier:
            raise GQLApiException(
                msg="Error to find supplier info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        supp_bus_acc_info = await self.supplier_business_account_repository.fetch(
            supplier_business_id=supplier_business_id
        )
        if not supp_bus_acc_info:
            raise GQLApiException(
                msg="Error to find supplier info",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )
        supp_bus_acc = SupplierBusinessAccount(**supp_bus_acc_info)
        paid_account = await self.repository.fetch_alima_account(supplier_business_id)
        if not paid_account:
            raise GQLApiException(
                msg="Error to find paid account",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )
        if (
            not active_invoice.payment_method
            or active_invoice.payment_method == InvoiceType.PUE
        ):
            raise GQLApiException(
                msg="Invoice is not able to add complement, is PUE",
                error_code=GQLApiErrorCodeType.FACTURAMA_NO_VALID_DATA.value,
            )

        complement_folio = (
            await self.alima_billing_complement_repository.fetch_next_folio()
        )

        related_documents = [
            RelatedDocuments(
                TaxObject="01",
                Folio=active_invoice.invoice_number,
                Uuid=str(active_invoice.sat_invoice_uuid),
                PaymentMethod=InvoiceType.PUE.value,
                PartialityNumber=1,
                PreviousBalanceAmount=amount,
                AmountPaid=amount,
                ImpSaldoInsoluto=0,
            )
        ]

        complement = FacturamaPayments(
            Payments=[
                FacturamaComplement(
                    Date=datetime.utcnow().strftime("%Y-%m-%d"),
                    PaymentForm=payment_form.value,
                    Amount=amount,
                    RelatedDocuments=related_documents,
                )
            ]
        )

        internal_invoice_complement = FacturamaInternalInvoiceComplement(
            Receiver=FacturamaCustomer(
                Name=supp_bus_acc.legal_business_name,  # type: ignore
                Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
                FiscalRegime=supp_bus_acc.mx_sat_regimen,
                TaxZipCode=supp_bus_acc.mx_zip_code,  # type: ignore
                CfdiUse="CP01",
            ),
            CfdiType="P",
            NameId="1",
            Folio=complement_folio,
            ExpeditionPlace=ALIMA_EXPEDITION_PLACE,
            Complemento=complement,
        )
        internal_invoice_complement_create = (
            await facturma_api.new_internal_invoice_complement(
                invoice_complement=internal_invoice_complement
            )
        )

        if internal_invoice_complement_create.get("status") != "ok":
            logger.error(internal_invoice_complement_create["msg"])
            raise GQLApiException(
                msg=internal_invoice_complement_create.get(
                    "msg", "Error to create invoice"
                ),
                error_code=GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value,
            )
        # fetch invoice files
        xml_file = await facturma_api.get_xml_internal_invoice_by_id(
            id=internal_invoice_complement_create["data"].Id
        )
        pdf_file = await facturma_api.get_pdf_internal_invoice_by_id(
            id=internal_invoice_complement_create["data"].Id
        )
        # create billing invoice
        b_invoice_complement_id = await self.alima_billing_complement_repository.add(
            billing_invoice_id=active_invoice.id,
            tax_invoice_id=internal_invoice_complement_create["data"].Id,
            invoice_number=internal_invoice_complement_create["data"].Folio,
            sat_invoice_uuid=internal_invoice_complement_create[
                "data"
            ].Complement.TaxStamp.Uuid,
            pdf_file=pdf_file["data"],
            xml_file=xml_file["data"],
            total=amount,
            status=InvoiceStatusType.ACTIVE,
            currency="MXN",
            result=internal_invoice_complement_create["data"].Result,
        )

        # insert invoice in DB
        pdf_file_str = base64.b64encode(pdf_file["data"]).decode("utf-8")
        xml_file_str = base64.b64encode(xml_file["data"]).decode("utf-8")

        attcht = [
            {
                "content": pdf_file_str,
                "filename": f"Complemento Alima-{active_invoice.invoice_month}.pdf",
                "mimetype": "application/pdf",
            },
            {
                "content": xml_file_str,
                "filename": f"Complemento Alima-{active_invoice.invoice_month}.xml",
                "mimetype": "application/xml",
            },
        ]
        receivers = ["pagosyfacturas@alima.la"]
        if supp_bus_acc and supp_bus_acc.email:
            receivers.append(supp_bus_acc.email)
        if not await send_alima_invoice_complement_notification_v2(
            email_to=receivers,
            name=supplier["name"],
            attchs=attcht,
        ):
            raise Exception("Error to send email")
        if b_invoice_complement_id:
            return b_invoice_complement_id
        else:
            return None

    async def cancel_alima_invoice(
        self,
        supplier_business_id: UUID,
        date: str,
        motive: str,
        uuid_replacement: Optional[str] = None,
    ) -> InvoiceStatus:
        paid_account_obj = await self.repository.fetch_alima_account(
            supplier_business_id
        )
        if not paid_account_obj:
            raise GQLApiException(
                msg="Error to find paid account",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        billing = await self.alima_billing_invoice_repository.find(
            paid_account_id=paid_account_obj.id, date=date
        )
        if not billing:
            raise GQLApiException(
                msg="Error to find billing invoice",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        billing_obj = billing[0]
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        _resp = await facturma_api.cancel_internal_invoice_by_id(
            id=billing_obj.tax_invoice_id,
            motive=motive,
            uuid_replacement=uuid_replacement,
        )
        if "status" not in _resp:
            raise GQLApiException(
                msg="Error data structure",
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
        if _resp["status"] == "error":
            raise GQLApiException(
                msg="Error to cancel invoice from facturama",
                error_code=GQLApiErrorCodeType.FACTURAMA_DELETE_ERROR.value,
            )
        if _resp["status"] == "ok":
            if await self.alima_billing_invoice_repository.edit(
                billing_invoice_id=billing_obj.id, status=InvoiceStatusType.CANCELED
            ):
                return InvoiceStatus(id=billing_obj.tax_invoice_id, canceled=True)
        return InvoiceStatus(id=billing_obj.tax_invoice_id, canceled=False)

    async def new_alima_invoice(
        self,
        billing_account: BillingAccount,
        invoice_month: str,  # MM-YYYY
        billing_charges_total: BillingTotalDue,
        currency: str,
        invoice_type: InvoiceType,
        is_paid: bool = False,
        payment_id: Optional[str] = None,
    ) -> Dict[str, Any] | NoneType:
        """Create new Alima Invoice
            - Create Factura Invoice in Facturama
                - If no Client in Facturama, create cliente
            - Create Invoice in DB
            - Fetch PDF and XML files from Facturama
            - Update Invoice in DB with files

        Args:
            billing_account (BillingAccount): _description_
            invoice_month (str): _description_
            currency (str): _description_
            invoice_type (InvoiceType): _description_

        Returns:
            UUID | NoneType: billing_invoice_id
        """
        # convert charges into invoice charges
        item_charges = self.format_charges_for_invoice(billing_charges_total.charges)
        global_information = None
        # validate business info
        if not billing_account.business.account:
            raise Exception("Missing business Account Info")
        # define payment form -> 04 (card) | 03 (transfer)
        payment_form = INVOICE_PAYMENT_MAP.get(
            billing_account.payment_method.payment_type
        )
        if not payment_form:
            raise Exception("Missing to define payment form in payment method")
        # for PPD invoices are 99
        if invoice_type == InvoiceType.PPD:
            payment_form = PaymentForm.TBD
        # verify if no RFC
        if not billing_account.business.account.mx_sat_rfc:
            raise Exception("Missing business RFC")
        # verify if generic invoice
        if billing_account.business.account.mx_sat_rfc in (
            "XAXX010101000",
            "XEXX010101000",
        ):
            # generate generic client for invoice
            global_information, fct_client = self.create_global_payment_info()
        else:
            # generate client for invoice
            if (
                not billing_account.business.account.legal_business_name
                or not billing_account.business.account.mx_sat_regimen
            ):
                raise Exception("Missing business Invoicing Info")
            # create facturama client
            fct_client = FacturamaCustomer(
                Email=billing_account.business.account.email,
                Address=FacturamaCustomerAddress(
                    ZipCode=billing_account.business.account.mx_zip_code,
                ),
                Rfc=billing_account.business.account.mx_sat_rfc,
                Name=billing_account.business.account.legal_business_name,
                CfdiUse="G03",
                FiscalRegime=billing_account.business.account.mx_sat_regimen,
                TaxZipCode=billing_account.business.account.mx_zip_code,
            )
            # verify if cclient already in facturama
            if not billing_account.paid_account.invoicing_provider_id:
                # create client in facturama
                new_client = await self.facturama_api.new_client(client=fct_client)
                if new_client.get("status") != "ok":
                    logger.warning("Error to create client in facturama")
                    logger.error(new_client["msg"])
                    return None
                # update paid account with invoicing provider id
                fct_client.Id = new_client["data"]["Id"]
                if not await self.repository.edit_alima_account(
                    billing_account.paid_account.id,
                    customer_type=billing_account.paid_account.customer_type,
                    account_name=billing_account.paid_account.account_name,
                    active_cedis=billing_account.paid_account.active_cedis,
                    invoicing_provider_id=fct_client.Id,
                ):
                    raise Exception(
                        "Error to update paid account with invoicing provider id"
                    )

        # create invoice in facturama
        internal_invoice = FacturamaInternalInvoice(
            Receiver=fct_client,
            CfdiType="I",
            NameId="1",
            ExpeditionPlace=ALIMA_EXPEDITION_PLACE,
            PaymentForm=payment_form.value,
            PaymentMethod=invoice_type.value,
            Items=item_charges,
            GlobalInformation=global_information,
        )
        try:
            internal_invoice_create = self.facturama_api.new_internal_invoice(
                invoice=internal_invoice
            )
            if internal_invoice_create.get("status") != "ok":
                raise Exception(
                    internal_invoice_create.get("msg", "Error to create invoice")
                )
        except Exception as e:
            logger.error(e)
            logger.warning("Error to create invoice in facturama")
            return None

        # create internal invoice
        try:
            b_inv_obj = BillingInvoice(
                id=uuid4(),
                paid_account_id=billing_account.paid_account.id,
                country="México",
                invoice_month=invoice_month,
                invoice_name=invoice_month,
                sat_invoice_uuid=UUID(
                    internal_invoice_create["data"].Complement.TaxStamp.Uuid
                ),
                tax_invoice_id=internal_invoice_create["data"].Id,
                invoice_number=internal_invoice_create["data"].Folio,
                result=internal_invoice_create["data"].Result,
                total=billing_charges_total.total_due,
                currency=currency,
                status=InvoiceStatusType.ACTIVE,
                payment_method=invoice_type,
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow(),
            )
            b_invoice_id = (
                await self.alima_billing_invoice_repository.add_alima_invoice(
                    billing_invoice=b_inv_obj,
                    billing_invoice_charges=billing_charges_total.charges,
                    paystatus=PayStatusType.PAID if is_paid else PayStatusType.UNPAID,
                    billing_payment_method_id=billing_account.payment_method.id,
                    transaction_id=payment_id,
                )
            )
            if not b_invoice_id:
                raise Exception("Error to create invoice in DB")
        except Exception as e:
            logger.error(e)
            logger.warning("Error to create invoice in DB")
            return None

        try:
            # fetch invoice files
            xml_file = await self.facturama_api.get_xml_internal_invoice_by_id(
                id=internal_invoice_create["data"].Id
            )
            pdf_file = await self.facturama_api.get_pdf_internal_invoice_by_id(
                id=internal_invoice_create["data"].Id
            )
            # update invoice in DB with files
            pdf_file_str = base64.b64encode(pdf_file["data"]).decode("utf-8")
            xml_file_str = base64.b64encode(xml_file["data"]).decode("utf-8")
            json_data = {"pdf": pdf_file_str, "xml": xml_file_str}
            invoice_files = json.dumps(json_data)
            b_inv_obj.invoice_files = [invoice_files]
            if not await self.alima_billing_invoice_repository.edit_alima_invoice(
                billing_invoice=b_inv_obj
            ):
                raise Exception("Could not to update invoice with files in DB")
        except Exception as e:
            logger.error(e)
            logger.warning("Error to fetch invoice files")
        return {
            "id": b_invoice_id,
            "pdf": pdf_file_str,
            "xml": xml_file_str,
            "rfc": internal_invoice.Receiver.Rfc,
        }

    async def fetch_billing_accounts(
        self, billing_period: Literal["monthly", "annual"]
    ) -> List[BillingAccount]:
        """Fetch All Billing Accounts

        Args:
            billing_period: (monthly | annual)
            current_date: datetime (in UTC)

        Returns:
            List[BillingAccount]
        """
        if billing_period == "monthly":
            return await self._fetch_monthly_billing_accounts()
        elif billing_period == "annual":
            return await self._fetch_anual_billing_accounts()

    async def get_month_invoice_folio_count(
        self, paid_account: PaidAccount, until_date: Optional[datetime] = None
    ) -> int | NoneType:
        # verify if plan has folios
        if paid_account.account_name not in self.plans_with_folios:
            logger.info("Suscription Plan has no folios activated")
            return None
        try:
            # get last invoice date
            last_invoice_date = (
                await self.alima_billing_invoice_repository.get_last_invoice_date(
                    paid_account.id
                )
            )
            # query invoices
            inv_query = """
                SELECT id FROM mx_invoice
                WHERE supplier_business_id = :supplier_business_id
                """
            core_values: Dict[Any, Any] = {
                "supplier_business_id": paid_account.customer_business_id
            }
            # query invoice complements
            inv_comp_query = """
                SELECT id FROM mx_invoice_complement
                WHERE mx_invoice_id in (SELECT id FROM mx_invoice
                WHERE supplier_business_id = :supplier_business_id)
                """

            if last_invoice_date:
                inv_query += """ and created_at > :last_invoice_date"""
                inv_comp_query += """ and created_at > :last_invoice_date"""
                core_values["last_invoice_date"] = last_invoice_date
            if until_date:
                inv_query += """ and created_at <= :until_date"""
                inv_comp_query += """ and created_at <= :until_date"""
                core_values["until_date"] = until_date

            # invoice ids
            invoice_ids = await self.alima_billing_invoice_repository.raw_query(
                inv_query,
                core_values,
            )
            if not invoice_ids:
                # if no ids -> return 0
                return 0
            # complement ids
            invoice_complement_ids = (
                await self.alima_billing_invoice_repository.raw_query(
                    inv_comp_query,
                    core_values,
                )
            )
            if not invoice_complement_ids:
                # if no complements  -> len(invoice_ids)
                return len(invoice_ids)

            # len(invoice_ids) + len(invoice_complement_ids
            return len(invoice_ids) + len(invoice_complement_ids)
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get invoice folios")
            return None

    async def get_month_reconciled_payments_count(
        self, paid_account: PaidAccount, until_date: Optional[datetime] = None
    ) -> int | NoneType:
        core_user = await self.core_user_repository.fetch_by_email("admin")
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="Error to find core user admin",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND,
            )
        # verify if plan has folios
        if paid_account.account_name not in self.plans_with_payments:
            logger.info("Suscription Plan has no payments activated")
            return None
        try:
            # get last invoice date
            last_invoice_date = (
                await self.alima_billing_invoice_repository.get_last_invoice_date(
                    paid_account.id
                )
            )
            # get last invoice date
            last_invoice_date = (
                await self.alima_billing_invoice_repository.get_last_invoice_date(
                    paid_account.id
                )
            )
            # query invoices
            inv_query = """
                SELECT id FROM payment_receipt
                WHERE id in (SELECT payment_receipt_id FROM payment_receipt_orden
                WHERE orden_id in (SELECT orden_id FROM orden_details
                WHERE supplier_unit_id in (SELECT id FROM supplier_unit
                WHERE supplier_business_id = :supplier_business_id)))
                AND created_by = :created_by
                """
            core_values: Dict[Any, Any] = {
                "supplier_business_id": paid_account.customer_business_id,
                "created_by": core_user.id,
            }

            if last_invoice_date:
                inv_query += """ and created_at > :last_invoice_date"""
                core_values["last_invoice_date"] = last_invoice_date
            if until_date:
                inv_query += """ and created_at <= :until_date"""
                core_values["until_date"] = until_date
            # invoice ids
            payments_ids = await self.alima_billing_invoice_repository.raw_query(
                inv_query,
                core_values,
            )
            if not payments_ids:
                # if no ids -> return 0
                return 0

            return len(payments_ids)
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get invoice folios")
            return None

    async def compute_total_due(
        self,
        billing_account: BillingAccount,
        date: datetime,
    ) -> BillingTotalDue:
        logger.warning("compute_total_due needs to be implemented in SubClass")
        raise NotImplementedError

    # account management

    async def create_alima_account(
        self,
        supplier_business: SupplierBusiness,
        account_name: AlimaAccountPlan,
        payment_method: PayProviderType,
        active_cedis: int,
        firebase_id: str,
        discount: Optional[AlimaAccountPlanDiscount] = None,
    ) -> SupplierAlimaAccount:
        stripe_client = StripeApi(get_app(), STRIPE_API_SECRET)
        # fetch core user
        core_user, supplier_user, supplier_user_perms = await self._fetch_curr_user(
            firebase_id
        )
        if core_user is None or core_user.id is None:
            raise GQLApiException(
                msg="Error to find user info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # verify if account exists already
        paid_account = await self.repository.fetch_alima_account(supplier_business.id)
        if paid_account:
            raise GQLApiException(
                msg="Paid Account already exists",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED.value,
            )
        current_date = datetime.now(timezone.utc)
        # create paid account
        paid_account = PaidAccount(
            id=uuid4(),  # placeholder
            customer_business_id=supplier_business.id,
            account_name=account_name.value,
            customer_type=AlimaCustomerType.SUPPLY,
            active_cedis=active_cedis,
            created_by=core_user.id,
            created_at=current_date,
            last_updated=current_date,
        )
        paid_account_id = await self.repository.new_alima_account(paid_account)
        if not paid_account_id:
            raise GQLApiException(
                msg="Error to create paid account",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        paid_account.id = paid_account_id
        # create charges & discounts
        saas_charge = Charge(
            id=uuid4(),  # placeholder
            paid_account_id=paid_account_id,
            charge_type=ChargeType.SAAS_FEE,
            charge_amount=alima_price_map.get(account_name.value, 0.0),
            currency=CurrencyType.MXN.value,
            charge_amount_type="$",
            charge_description="Servicio de Software - Operaciones",
            active=True,
            created_at=current_date,
            last_updated=current_date,
        )
        if discount:
            logger.warning("Discounts are not implemented yet")
        charge_id = await self.repository.new_charge(saas_charge)
        if not charge_id:
            raise GQLApiException(
                msg="Error to create SaaS charge",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        if account_name.value in self.plans_with_folios:
            folio_charge = Charge(
                id=uuid4(),  # placeholder
                paid_account_id=paid_account_id,
                charge_type=ChargeType.INVOICE_FOLIO,
                charge_amount=1.0,
                currency=CurrencyType.MXN.value,
                charge_amount_type="$",
                charge_description="Folios Adicionales Facturación",
                active=True,
                created_at=current_date,
                last_updated=current_date,
            )
            folio_charge_id = await self.repository.new_charge(folio_charge)
            if not folio_charge_id:
                raise GQLApiException(
                    msg="Error to create Folio charge",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
        # create stripe customer
        stripe_cust = stripe_client.create_customer(
            email=core_user.email,
            name=supplier_business.name,
            metadata={"supplier_business_id": str(supplier_business.id)},
        )
        if not stripe_cust:
            raise GQLApiException(
                msg="Error to create stripe customer",
                error_code=GQLApiErrorCodeType.STRIPE_ERROR_CREATE_USER.value,
            )
        # create payment method
        bill_pm = BillingPaymentMethod(
            id=uuid4(),  # placeholder
            paid_account_id=paid_account_id,
            payment_provider=payment_method,
            payment_provider_id=stripe_cust.id,
            payment_type=(
                PayMethodType.CARD
                if payment_method == PayProviderType.CARD_STRIPE
                else PayMethodType.TRANSFER
            ),
            active=True,
            created_by=core_user.id,
            created_at=current_date,
            last_updated=current_date,
        )
        payment_method_id = await self.repository.new_billing_payment_method(bill_pm)
        if not payment_method_id:
            raise GQLApiException(
                msg="Error to create payment method",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # finally activate supplier business
        if not await self.supplier_business_repository.edit(
            id=supplier_business.id,
            active=True,
        ):
            raise GQLApiException(
                msg="Error to activate supplier business",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        # return built supplier alima account
        return await self.fetch_supplier_alima_account_by_firebase_id(firebase_id)

    async def create_alima_account_config(
        self,
        paid_account: PaidAccount,
    ) -> bool:
        pac_exists = await self.repository.verify_paid_account_config_exists(
            paid_account.id
        )
        if pac_exists:
            logger.info("Paid Account Config already exists")
            return False
        # create paid account config
        config_data = self.generate_account_config_data(
            AlimaAccountPlan(paid_account.account_name)
        )
        return await self.repository.create_paid_account_config(
            paid_account.id, config_data
        )

    async def disable_alima_account(self, supplier_business_id: UUID) -> bool:
        # fetch paid account, busienss and connected users
        paid_account = await self.repository.fetch_alima_account(supplier_business_id)
        if not paid_account:
            # if no paid account, return False
            logger.warning("No Paid Account Found")
            return False
        sa_gql = await self._complete_business_account(supplier_business_id)
        if sa_gql is None:
            # if no billing account
            logger.warning("No Business Account Found")
            return False
        account_users = await self.supplier_user_permission_repository.fetch_supplier_user_contact_and_permission(
            """ sup.supplier_business_id = :supplier_business_id
                AND su.deleted = 'f'
            """,
            {"supplier_business_id": supplier_business_id},
        )
        # set all supplier users as deleted = true and enabled = False
        for acc_u in account_users:
            if await self.supplier_user_repository.activate_desactivate(
                acc_u["core_user_id"], False
            ):
                logger.warning(f"Error Disabling Supplier User: {acc_u['id']}")
            if not await self.supplier_user_repository.delete(
                acc_u["core_user_id"], True
            ):
                logger.warning(f"Error Deleting Supplier User: {acc_u['id']}")
        # set display_marketplace = False
        sb_acc = sa_gql.account
        if sb_acc is not None:
            sb_acc.displays_in_marketplace = False
            if not await self.supplier_business_account_repository.edit(
                supplier_business_id, sb_acc
            ):
                logger.warning("Could not set displays_in_marketplace to False")
                return False
        else:
            logger.warning("Could not find supplier business account")
            return False
        # set business.active = False
        if not await self.supplier_business_repository.edit(
            id=supplier_business_id, active=False
        ):
            logger.warning("Could not set supplier_business.active to False")
            return False
        # set ecommerce.account_active = False
        if not self.ecommerce_seller_repository:
            logger.warning("No Ecommerce seller repository instantiated")
            return False
        ecomm_seller = await self.ecommerce_seller_repository.fetch(
            id_key="supplier_business_id", id_value=supplier_business_id
        )
        if not ecomm_seller:
            logger.warning("No ecommerce seller found")
            return False
        ecomm_seller.account_active = False
        if not await self.ecommerce_seller_repository.edit(ecomm_seller):
            logger.warning("Could not update ecommerce seller")
            return False
        logger.info("Alima Account Correctly Disabled")
        return True

    async def reactivate_alima_account(self, supplier_business_id: UUID) -> bool:
        # fetch paid account, busienss and connected users
        paid_account = await self.repository.fetch_alima_account(supplier_business_id)
        if not paid_account:
            # if no paid account, return False
            return False
        sa_gql = await self._complete_business_account(supplier_business_id)
        if sa_gql is None:
            # if no billing account
            return False
        disabled_account_users = await self.supplier_user_permission_repository.fetch_supplier_user_contact_and_permission(
            """ sup.supplier_business_id = :supplier_business_id
                AND su.enabled = 'f'
            """,
            {"supplier_business_id": supplier_business_id},
        )
        # set all supplier users that are enabled = False, as deleted = False and enabled = True
        for acc_u in disabled_account_users:
            if not await self.supplier_user_repository.activate_desactivate(
                acc_u["core_user_id"], True
            ):
                logger.warning(f"Error Enabling Supplier User: {acc_u['id']}")
            if await self.supplier_user_repository.delete(acc_u["core_user_id"], False):
                logger.warning(f"Error Restoring Deleted Supplier User: {acc_u['id']}")
        # set display_marketplace = True
        sb_acc = sa_gql.account
        if sb_acc is not None:
            sb_acc.displays_in_marketplace = True
            if not await self.supplier_business_account_repository.edit(
                supplier_business_id, sb_acc
            ):
                logger.warning("Could not set displays_in_marketplace to True")
                return False
        else:
            logger.warning("Could not find supplier business account")
            return False
        # set sbusiness.active = True
        if not await self.supplier_business_repository.edit(
            id=supplier_business_id, active=True
        ):
            logger.warning("Could not set supplier_business.active to True")
            return False
        # set ecommerce.account_active = True
        if not self.ecommerce_seller_repository:
            logger.warning("No Ecommerce seller repository instantiated")
            return False
        ecomm_seller = await self.ecommerce_seller_repository.fetch(
            id_key="supplier_business_id", id_value=supplier_business_id
        )
        if not ecomm_seller:
            logger.warning("No ecommerce seller found")
            return False
        ecomm_seller.account_active = True
        if not await self.ecommerce_seller_repository.edit(ecomm_seller):
            logger.warning("Could not update ecommerce seller")
            return False
        logger.info("Alima Account Correctly Reenabled")
        return True

    async def change_alima_account_plan(
        self,
        paid_account: PaidAccount,
        charges: List[Charge],
        new_plan: AlimaAccountPlan,
    ) -> bool:
        # if current plan and new plan are the same, return False
        if paid_account.account_name == new_plan.value:
            logger.warning("Current Plan and New Plan are the same")
            return False
        # deactivate all current charges
        if not await self.repository.deactivate_charge(
            paid_account.id,
            [ChargeType.SAAS_FEE.value, ChargeType.INVOICE_FOLIO.value],
        ):
            logger.warning("Error to deactivate charges")
            return False
        current_date = datetime.now(timezone.utc)
        # create new charges
        new_charges: List[Charge] = []
        # accumulate past charges - like reports
        for ch in charges:
            # skip - saas and invoice folio
            if ch.charge_type in [
                ChargeType.SAAS_FEE.value,
                ChargeType.INVOICE_FOLIO.value,
            ]:
                continue

            new_ch = Charge(
                id=uuid4(),
                paid_account_id=paid_account.id,
                charge_type=ch.charge_type,
                charge_amount=ch.charge_amount,
                currency=ch.currency,
                charge_amount_type=ch.charge_amount_type,
                charge_description=ch.charge_description,
                active=True,
                created_at=current_date,
                last_updated=current_date,
            )
            new_charges.append(new_ch)
        # create new saas charge
        saas_charge = Charge(
            id=uuid4(),
            paid_account_id=paid_account.id,
            charge_type=ChargeType.SAAS_FEE,
            charge_amount=alima_price_map.get(new_plan.value, 0.0),
            currency=CurrencyType.MXN.value,
            charge_amount_type="$",
            charge_description="Servicio de Software - Operaciones",
            active=True,
            created_at=current_date,
            last_updated=current_date,
        )
        new_charges.append(saas_charge)
        if new_plan.value in self.plans_with_folios:
            folio_charge = Charge(
                id=uuid4(),  # placeholder
                paid_account_id=paid_account.id,
                charge_type=ChargeType.INVOICE_FOLIO,
                charge_amount=1.0,
                currency=CurrencyType.MXN.value,
                charge_amount_type="$",
                charge_description="Folios Adicionales Facturación",
                active=True,
                created_at=current_date,
                last_updated=current_date,
            )
            new_charges.append(folio_charge)
        # generate all new charges
        for ch in new_charges:
            charge_id = await self.repository.new_charge(ch)
            if not charge_id:
                logger.warning(f"Error to create new charges: {ch.charge_type.value}")
                return False
        # update paid account with new plan
        if not await self.repository.edit_alima_account(
            paid_account_id=paid_account.id,
            customer_type=paid_account.customer_type,
            active_cedis=paid_account.active_cedis,
            account_name=new_plan.value,
            invoicing_provider_id=paid_account.invoicing_provider_id,
        ):
            logger.warning("Error to update paid account with new plan")
            return False

        return True


# Sub Classes for Each one of Alima Plans


class AlimaComercialAccountHandler(AlimaAccountHandler):
    async def compute_total_due(
        self,
        billing_account: BillingAccount,
        date: datetime,  # type: ignore (safe)
    ) -> BillingTotalDue:
        """Compute total due for Alima Comercial Account
        - It only applies SaaS and Reports fees
        """
        # fetch account charges and discounts
        acc_charges = await self.repository.fetch_charges(
            billing_account.paid_account.id
        )
        acc_discounts = await self.repository.fetch_discounts_charges(
            billing_account.paid_account.id
        )
        num_units = billing_account.paid_account.active_cedis
        placeholder_billing_invoice_id = uuid4()
        # compute total due
        billing_charges, subtotal_due, total_amount_due = [], 0.0, 0.0
        for ch in acc_charges:
            discount = None
            discount = self.find_discounts(ch.id, acc_discounts)
            # vars
            chtype = ""
            chbase, chtotal_with_iva, chtotal = 0.0, 0.0, 0.0
            if ch.charge_type == ChargeType.SAAS_FEE:
                if ch.charge_description:
                    chtype = ch.charge_description
                else:
                    chtype = "Servicio de Software - Operaciones"
                chbase = num_units
                chtotal_with_iva, chtotal, chtype = self.compute_fee_charge(
                    chtype, ch, num_units, discount
                )
            elif ch.charge_type == ChargeType.REPORTS:
                chbase = 1
                chtotal_with_iva, chtotal, chtype = self.compute_reports_charge(
                    ch, discount
                )
            # format response
            bill_ch = {
                "id": uuid4(),
                "billing_invoice_id": placeholder_billing_invoice_id,
                "charge_id": ch.id,
                "charge_type": chtype,
                "charge_base_quantity": chbase,
                "charge_amount": (
                    round(chtotal_with_iva / chbase, 4)
                    if ch.charge_amount_type == "$"
                    else ch.charge_amount
                ),
                "charge_amount_type": ch.charge_amount_type,
                "total_charge": round(chtotal_with_iva, 4),
                "currency": ch.currency,
                "created_at": datetime.utcnow(),
            }
            total_amount_due += chtotal_with_iva
            subtotal_due += chtotal
            billing_charges.append(BillingInvoiceCharge(**bill_ch))
        return BillingTotalDue(
            charges=billing_charges,
            subtotal_due=round(subtotal_due, 4),
            total_due=round(total_amount_due, 4),
            tax_due=round(total_amount_due - subtotal_due, 4),
        )


class AlimaComercialAnualAccountHandler(AlimaAccountHandler):
    async def compute_total_due(
        self,
        billing_account: BillingAccount,
        date: datetime,  # type: ignore (safe)
    ) -> BillingTotalDue:
        """Compute total due for Alima Comercial Annual Account
        - It only applies SaaS and Reports fees
        """
        # fetch account charges and discounts
        acc_charges = await self.repository.fetch_charges(
            billing_account.paid_account.id
        )
        acc_discounts = await self.repository.fetch_discounts_charges(
            billing_account.paid_account.id
        )
        num_units = billing_account.paid_account.active_cedis
        placeholder_billing_invoice_id = uuid4()
        # compute total due
        billing_charges, subtotal_due, total_amount_due = [], 0.0, 0.0
        for ch in acc_charges:
            discount = None
            discount = self.find_discounts(ch.id, acc_discounts)
            # vars
            chtype = ""
            chbase, chtotal_with_iva, chtotal = 0.0, 0.0, 0.0
            if ch.charge_type == ChargeType.SAAS_FEE:
                if ch.charge_description:
                    chtype = ch.charge_description
                else:
                    chtype = "Servicio de Software - Operaciones"
                chbase = num_units
                # Annual charge base times 12
                ch.charge_amount = ch.charge_amount * 12
                chtotal_with_iva, chtotal, chtype = self.compute_fee_charge(
                    chtype, ch, num_units, discount
                )
            elif ch.charge_type == ChargeType.REPORTS:
                # Annual charge base times 12
                chbase = 1 * 12
                chtotal_with_iva, chtotal, chtype = self.compute_reports_charge(
                    ch, discount, chbase
                )
            # format response
            bill_ch = {
                "id": uuid4(),
                "billing_invoice_id": placeholder_billing_invoice_id,
                "charge_id": ch.id,
                "charge_type": chtype,
                "charge_base_quantity": chbase,
                "charge_amount": (
                    round(chtotal_with_iva / chbase, 4)
                    if ch.charge_amount_type == "$"
                    else ch.charge_amount
                ),
                "charge_amount_type": ch.charge_amount_type,
                "total_charge": round(chtotal_with_iva, 4),
                "currency": ch.currency,
                "created_at": datetime.utcnow(),
            }
            total_amount_due += chtotal_with_iva
            subtotal_due += chtotal
            billing_charges.append(BillingInvoiceCharge(**bill_ch))
        return BillingTotalDue(
            charges=billing_charges,
            subtotal_due=round(subtotal_due, 4),
            total_due=round(total_amount_due, 4),
            tax_due=round(total_amount_due - subtotal_due, 4),
        )


class AlimaProAccountHandler(AlimaAccountHandler):
    async def compute_total_due(
        self,
        billing_account: BillingAccount,
        date: datetime,
    ) -> BillingTotalDue:
        """Compute total due for Alima Pro Account
        - It applies SaaS and Reports fees
        - additional folio fees per additional folio emitted
        """
        # fetch account charges and discounts
        acc_charges = await self.repository.fetch_charges(
            billing_account.paid_account.id
        )
        acc_discounts = await self.repository.fetch_discounts_charges(
            billing_account.paid_account.id
        )
        num_units = billing_account.paid_account.active_cedis
        placeholder_billing_invoice_id = uuid4()
        folio_count = await self.get_month_invoice_folio_count(
            billing_account.paid_account, date
        )
        # compute total due
        billing_charges, subtotal_due, total_amount_due = [], 0.0, 0.0
        for ch in acc_charges:
            discount = None
            discount = self.find_discounts(ch.id, acc_discounts)
            # vars
            chtype = ""
            chbase, chtotal_with_iva, chtotal = 0.0, 0.0, 0.0
            if ch.charge_type == ChargeType.SAAS_FEE:
                if ch.charge_description:
                    chtype = ch.charge_description
                else:
                    chtype = "Servicio de Software - Operaciones"
                chbase = num_units
                chtotal_with_iva, chtotal, chtype = self.compute_fee_charge(
                    chtype, ch, num_units, discount
                )
            elif ch.charge_type == ChargeType.REPORTS:
                chbase = 1
                chtotal_with_iva, chtotal, chtype = self.compute_reports_charge(
                    ch, discount
                )
            elif ch.charge_type == ChargeType.INVOICE_FOLIO:
                # If no folios, skip
                if folio_count is None:
                    continue
                if folio_count > (included_folios_per_cedis * num_units):
                    if ch.charge_description:
                        chtype = ch.charge_description
                    else:
                        chtype = "Folios Adicionales Facturación"
                    chbase = folio_count - (included_folios_per_cedis * num_units)
                    chtotal_with_iva, chtotal, chtype = self.compute_folios_charge(
                        chbase, chtype, ch
                    )
                else:
                    continue

            elif ch.charge_type == ChargeType.PAYMENTS:

                workflow_vars = (
                    await self.integration_webhook_repo.fetch_workflow_vars(
                        billing_account.business.id
                    )
                )
                if not workflow_vars:
                    logger.warning("No workflow vars found")
                    continue
                workflow_vars_json = json.loads(workflow_vars.vars)
                stripe_api_secret = workflow_vars_json.get("stripe_api_secret", None)
                if not stripe_api_secret:
                    logger.warning("No Stripe API secret found")
                    continue
                stripe_api = StripeApi(
                    app_name=get_app(), stripe_api_secret=stripe_api_secret
                )
                # Get the current date and time
                now = datetime.now(APP_TZ)
                # Set the time to 23:59:59
                end_of_today = now.replace(hour=23, minute=59, second=59, microsecond=0)
                # Get the date one month ago
                one_month_ago = now - relativedelta(months=1)

                # Set the time to 00:00:00
                start_of_last_month = one_month_ago.replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                transfer_payments = stripe_api.get_transfer_payments(
                    start_of_last_month,
                    end_of_today,
                )
                logger.info(f"Number of transfer payments: {transfer_payments}")
                # If no folios, skip
                if transfer_payments is None or transfer_payments == 0:
                    continue
                if ch.charge_description:
                    chtype = ch.charge_description
                else:
                    chtype = "Pagos de Stripe"
                chbase = transfer_payments
                chtotal_with_iva, chtotal, chtype = self.compute_payment_charge(
                    chbase, chtype, ch
                )
            # format response
            bill_ch = {
                "id": uuid4(),
                "billing_invoice_id": placeholder_billing_invoice_id,
                "charge_id": ch.id,
                "charge_type": chtype,
                "charge_base_quantity": chbase,
                "charge_amount": (
                    round(chtotal_with_iva / chbase, 4)
                    if ch.charge_amount_type == "$"
                    else ch.charge_amount
                ),
                "charge_amount_type": ch.charge_amount_type,
                "total_charge": round(chtotal_with_iva, 4),
                "currency": ch.currency,
                "created_at": datetime.utcnow(),
            }
            total_amount_due += chtotal_with_iva
            subtotal_due += chtotal
            billing_charges.append(BillingInvoiceCharge(**bill_ch))
        return BillingTotalDue(
            charges=billing_charges,
            subtotal_due=round(subtotal_due, 4),
            total_due=round(total_amount_due, 4),
            tax_due=round(total_amount_due - subtotal_due, 4),
        )


class AlimaProAnualAccountHandler(AlimaAccountHandler):
    def _is_annual_checkout(
        self, account_created_at: datetime, checkout_date: datetime
    ) -> bool:
        # return true is month is the same as account creation and year is larger than account creation
        return (
            account_created_at.month == checkout_date.month
            and account_created_at.year < checkout_date.year
        )

    async def compute_total_due(
        self,
        billing_account: BillingAccount,
        date: datetime,
    ) -> BillingTotalDue:
        """Compute total due for Alima Pro Annual Account
        - It applies SaaS and Reports fees when annual charge
        - Additional folio fees per additional folio emitted
            - Applies for monthly checkout and annual checkout
        """
        # fetch account charges and discounts
        acc_charges = await self.repository.fetch_charges(
            billing_account.paid_account.id
        )
        acc_discounts = await self.repository.fetch_discounts_charges(
            billing_account.paid_account.id
        )
        num_units = billing_account.paid_account.active_cedis
        placeholder_billing_invoice_id = uuid4()
        folio_count = await self.get_month_invoice_folio_count(
            billing_account.paid_account, date
        )
        annual_checkout = self._is_annual_checkout(
            billing_account.paid_account.created_at, date
        )
        # compute total due
        billing_charges, subtotal_due, total_amount_due = [], 0.0, 0.0
        for ch in acc_charges:
            discount = None
            discount = self.find_discounts(ch.id, acc_discounts)
            # vars
            chtype = ""
            chbase, chtotal_with_iva, chtotal = 0.0, 0.0, 0.0
            if ch.charge_type == ChargeType.SAAS_FEE:
                # if not annual skip
                if not annual_checkout:
                    continue
                if ch.charge_description:
                    chtype = ch.charge_description
                else:
                    chtype = "Servicio de Software - Operaciones"
                chbase = num_units
                # Annual charge base times 12
                ch.charge_amount = ch.charge_amount * 12
                chtotal_with_iva, chtotal, chtype = self.compute_fee_charge(
                    chtype, ch, num_units, discount
                )
            elif ch.charge_type == ChargeType.REPORTS:
                # If not annual skip
                if not annual_checkout:
                    continue
                # Annual charge base times 12
                chbase = 1 * 12
                chtotal_with_iva, chtotal, chtype = self.compute_reports_charge(
                    ch, discount
                )
            elif ch.charge_type == ChargeType.INVOICE_FOLIO:
                # If no folios, skip
                if folio_count is None:
                    continue
                if folio_count > (included_folios_per_cedis * num_units):
                    if ch.charge_description:
                        chtype = ch.charge_description
                    else:
                        chtype = "Folios Adicionales Facturación"
                    chbase = folio_count - (included_folios_per_cedis * num_units)
                    chtotal_with_iva, chtotal, chtype = self.compute_folios_charge(
                        chbase, chtype, ch
                    )
                else:
                    continue
            # format response
            bill_ch = {
                "id": uuid4(),
                "billing_invoice_id": placeholder_billing_invoice_id,
                "charge_id": ch.id,
                "charge_type": chtype,
                "charge_base_quantity": chbase,
                "charge_amount": (
                    round(chtotal_with_iva / chbase, 4)
                    if ch.charge_amount_type == "$"
                    else ch.charge_amount
                ),
                "charge_amount_type": ch.charge_amount_type,
                "total_charge": round(chtotal_with_iva, 4),
                "currency": ch.currency,
                "created_at": datetime.utcnow(),
            }
            total_amount_due += chtotal_with_iva
            subtotal_due += chtotal
            billing_charges.append(BillingInvoiceCharge(**bill_ch))
        return BillingTotalDue(
            charges=billing_charges,
            subtotal_due=round(subtotal_due, 4),
            total_due=round(total_amount_due, 4),
            tax_due=round(total_amount_due - subtotal_due, 4),
        )


# Alima Account Handler Listener


class AlimaAccountListener(AlimaAccountListenerInterface):

    @staticmethod
    async def _create_new_ecommerce_seller(
        ecommerce_seller_handler: EcommerceSellerHandlerInterface,
        supplier_business: SupplierBusiness,
    ) -> EcommerceSeller | NoneType:
        # verify if exists
        if await ecommerce_seller_handler.fetch_ecommerce_seller(
            id_key="supplier_business_id", id_value=supplier_business.id
        ):
            logger.warning("Ecommerce Seller already exists")
            return None
        # create new ecommerce seller
        secret_key = generate_secret_key()
        ecomm_seller = EcommerceSeller(
            id=uuid4(),  # placeholder
            supplier_business_id=supplier_business.id,
            seller_name=supplier_business.name,
            secret_key=secret_key,
            account_active=True,
            created_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
        )
        ecomm_seller_w_id = await ecommerce_seller_handler.add_ecommerce_seller(
            ecomm_seller
        )
        if not ecomm_seller_w_id:
            logger.warning("Error to create new ecommerce seller")
            return None
        return ecomm_seller_w_id

    @staticmethod
    async def generate_new_business_name(
        supplier_business: SupplierBusiness,
        ecommerce_handler: EcommerceSellerHandlerInterface,
        subdomain_alima: str = "compralima.com",
    ) -> Tuple[str, str] | Tuple[None, None]:
        ecomm_proj = VercelUtils.build_project_name(supplier_business.name.strip())
        ecomm_domain = VercelUtils.build_domain_name(
            supplier_business.name.strip(), subdomain_alima
        )
        supplier_seller_val_url = await ecommerce_handler.fetch_ecommerce_seller(
            "ecommerce_url", ecomm_domain
        )
        supplier_seller_val_project = await ecommerce_handler.fetch_ecommerce_seller(
            "project_name", ecomm_proj
        )
        if not supplier_seller_val_url and not supplier_seller_val_project:
            return ecomm_proj, ecomm_domain
        alphabet = [i for i in string.ascii_lowercase]
        random.shuffle(alphabet)
        # Iterate over the alphabet
        for letter in alphabet:
            ecomm_proj = VercelUtils.build_project_name(
                supplier_business.name.strip() + "-" + letter
            )
            ecomm_domain = VercelUtils.build_domain_name(
                supplier_business.name.strip() + "-" + letter, subdomain_alima
            )
            supplier_seller_val_url = await ecommerce_handler.fetch_ecommerce_seller(
                "ecommerce_url", ecomm_domain
            )
            supplier_seller_val_project = (
                await ecommerce_handler.fetch_ecommerce_seller(
                    "project_name", ecomm_proj
                )
            )
            if not supplier_seller_val_url and not supplier_seller_val_project:
                return ecomm_proj, ecomm_domain
        return None, None

    @staticmethod
    async def _add_ecommerce(
        ecommerce_seller_handler: EcommerceSellerHandlerInterface,
        supplier_business: SupplierBusinessGQL,
        default_supplier_unit_id: UUID,
        ecommerce_seller: EcommerceSeller,
    ) -> bool:
        # generate new business name
        ecomm_proj, ecomm_domain = (
            await AlimaAccountListener.generate_new_business_name(
                supplier_business, ecommerce_seller_handler, GODADDY_DOMAIN
            )
        )
        if not ecomm_proj or not ecomm_domain:
            logger.error("Error to generate new business name")
            return False
        # 3rd p apis
        vercel_api = VercelClientApi(DEV_ENV, VERCEL_TOKEN, VERCEL_TEAM)
        go_daddy_api = GoDaddyClientApi(
            DEV_ENV, GODADDY_API_KEY, GODADDY_API_SECRET, GODADDY_DOMAIN
        )
        # build env vars
        env_vars_ph = {
            "NEXT_PUBLIC_SELLER_NAME": supplier_business.name,
            "NEXT_PUBLIC_GQLAPI_ENV": "production",
            "NEXT_PUBLIC_SELLER_ID": ecommerce_seller.secret_key,
            "NEXT_PUBLIC_SUNIT_ID": default_supplier_unit_id,
        }
        params_vars_ph = {
            "categories": "",
            "rec_prods": "",
            "styles_json": """
                {
                    "palette":{
                        "primary":"#000000","secondary":"#000000","info":"#000000","success":"#EEE3EB","warning":"#E0CABC","error":"#E32623"
                    },
                    "shape":{"borderRadius": 0,"borderRadiusSm": 2,"borderRadiusMd":4},"type":"Montserrat"
                }
            """,
            "shipping_enabled": "true",
            "shipping_rule_verified_by": "minThreshold",
            "shipping_threshold": 0,
            "shipping_cost": 0,
            "search_placeholder": "¿Qué productos necesitas?",
            "footer_msg": "",
            "footer_cta": "¡Ver Productos!",
            "seo_description": supplier_business.name,
            "seo_keywords": "ecommerce,b2b,distribuidor",
            "commerce_display": "open",
        }
        ecommerce_env_vars = NewEcommerceEnvVars(**env_vars_ph)
        ecommerce_params = EcommerceParams(**params_vars_ph)
        vercel_environment_variables: List[VercelEnvironmentVariables] = []
        # auto generated vars
        ecommerce_params.project_name = ecomm_proj
        ecommerce_params.ecommerce_url = ecomm_domain
        ecommerce_params.account_active = True
        ecommerce_params.banner_img = (
            f"alima-marketplace-PROD/supplier/profile/{supplier_business.id}_banner.png"
        )
        ecommerce_params.currency = "MXN"
        if not ecommerce_params.banner_img_href:
            ecommerce_params.banner_img_href = "/catalog/list"
        if supplier_business.account:
            ecommerce_params.footer_phone = supplier_business.account.phone_number
            ecommerce_params.footer_is_wa = True
            ecommerce_params.footer_email = supplier_business.account.email

        for key, value in ecommerce_env_vars.__dict__.items():
            if key in [
                "NEXT_PUBLIC_SELLER_NAME",
                "NEXT_PUBLIC_SELLER_ID",
                "NEXT_PUBLIC_SUNIT_ID",
                "NEXT_PUBLIC_GQLAPI_ENV",
            ]:
                vercel_environment_variables.append(
                    VercelEnvironmentVariables(
                        key=key,
                        target=["production", "preview", "development"],
                        type="encrypted",
                        value=str(value),
                        # gitBranch="main",
                    )
                )
        # verify if project in vercel already
        find_record = vercel_api.find_project(ecomm_proj)
        if find_record.status == "error" and find_record.status_code == 404:
            logger.info("Project not found, creating new project")
        if find_record.status == "ok":
            logger.error("Project already exists")
            return False

        gd_record_exists = False
        find_gd_record = go_daddy_api.find_record(ecomm_domain.split(".")[0], "CNAME")
        if find_gd_record.status == "error" and find_gd_record.status_code == 404:
            logger.info("CNAME record not found, creating new record")
        if find_gd_record.status == "ok" and find_gd_record.result:
            logger.error("CNAME record already exists")
            gd_record_exists = True

        # create new domain in godaddy
        if not gd_record_exists:
            domain_resp_gd = go_daddy_api.new_cname_record(
                ecomm_domain.split(".")[0], "cname.vercel-dns.com."
            )
            if domain_resp_gd.status == "error":
                logger.warning("ISSUES CREATING GODADDY DOMAIN!!")
                logger.error(domain_resp_gd.msg)

        # create new project in vercel
        project_resp = vercel_api.new_project(
            project_name=ecomm_proj,
            root_directory="apps/commerce-template",
            framework="nextjs",
            git_repository=VercelGitRepository(
                repo="Alima-Latam/alima-nextjs-monorepo",
                type="github",
            ),
            environment_variables=vercel_environment_variables,
        )
        if project_resp.status == "error":
            logger.error(project_resp.msg)
            return False
        # create new domain in vercel
        domain_resp = vercel_api.new_domain(ecomm_proj, ecomm_domain)
        if domain_resp.status == "error":
            logger.error(domain_resp.msg)
            return False
        project_created = vercel_api.find_project(ecomm_proj)
        if project_created.status == "error":
            logger.error(project_created.msg)
            return False
        if not project_created.result:
            logger.error("Error to create project")
            return False
        # create vercel deployment
        project_created_json = json.loads(project_created.result)
        if (
            not project_created_json["link"]
            or not project_created_json["link"]["repoId"]
        ):
            logger.error("Error to create project")
            return False
        deployment = vercel_api.new_deployment(
            project_name=ecomm_proj,
            repo_id=project_created_json["link"]["repoId"],
            github_branch="main",
            framework="nextjs",
        )
        if deployment.status == "error":
            logger.error(deployment.msg)
            return False

        # update ecommerce seller in DB
        ecommerce_seller.ecommerce_url = ecomm_domain
        ecommerce_seller.project_name = ecomm_proj
        if await ecommerce_seller_handler.edit_ecommerce_seller(
            ecommerce_seller=EcommerceSeller(
                id=ecommerce_seller.id,
                supplier_business_id=ecommerce_seller.supplier_business_id,
                seller_name=ecommerce_seller.seller_name,
                secret_key=ecommerce_seller.secret_key,
                ecommerce_url="https://" + ecommerce_seller.ecommerce_url,
                project_name=ecommerce_seller.project_name,
                banner_img=ecommerce_params.banner_img,
                banner_img_href=ecommerce_params.banner_img_href,
                categories=ecommerce_params.categories,
                rec_prods=ecommerce_params.rec_prods,
                styles_json=ecommerce_params.styles_json,
                shipping_enabled=bool(ecommerce_params.shipping_enabled),
                shipping_rule_verified_by=ecommerce_params.shipping_rule_verified_by,
                shipping_threshold=(
                    int(ecommerce_params.shipping_threshold)
                    if ecommerce_params.shipping_threshold
                    else None
                ),
                shipping_cost=(
                    int(ecommerce_params.shipping_cost)
                    if ecommerce_params.shipping_cost
                    else None
                ),
                search_placeholder=ecommerce_params.search_placeholder,
                footer_msg=ecommerce_params.footer_msg,
                footer_cta=ecommerce_params.footer_cta,
                footer_phone=ecommerce_params.footer_phone,
                footer_is_wa=bool(ecommerce_params.footer_is_wa),
                footer_email=ecommerce_params.footer_email,
                seo_description=ecommerce_params.seo_description,
                seo_keywords=ecommerce_params.seo_keywords,
                default_supplier_unit_id=default_supplier_unit_id,
                commerce_display=ecommerce_params.commerce_display,
                account_active=bool(ecommerce_params.account_active),
                currency=ecommerce_params.currency,
            ),
        ):
            logger.info("Ecommerce Seller created successfully!")

        return True

    @staticmethod
    async def on_new_alima_supply_account_created(
        alima_account_handler: AlimaAccountHandlerInterface,
        ecommerce_seller_handler: EcommerceSellerHandlerInterface,
        supplier_business: SupplierBusinessGQL,
        default_supplier_unit_id: UUID,
    ) -> bool:
        try:
            # create ecomm seller
            e_seller = await AlimaAccountListener._create_new_ecommerce_seller(
                ecommerce_seller_handler, supplier_business
            )
            if not e_seller:
                return False
            # add ecommerce
            ecom_deployed = await AlimaAccountListener._add_ecommerce(
                ecommerce_seller_handler,
                supplier_business,
                default_supplier_unit_id,
                e_seller,
            )
            return ecom_deployed
        except Exception as e:
            logger.error(str(e))
            return False
