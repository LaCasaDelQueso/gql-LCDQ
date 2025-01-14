import datetime
import json
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from gqlapi.domain.interfaces.v2.alima_account.account import AlimaAccountRepositoryInterface
from gqlapi.domain.models.v2.alima_business import (
    BillingPaymentMethod,
    Charge,
    ChargeDiscount,
    PaidAccount,
    PaidAccountConfig,
)
from gqlapi.domain.models.v2.utils import (
    AlimaCustomerType,
    ChargeType,
    DiscountChargeType,
    PayMethodType,
    PayProviderType,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


class AlimaAccountRepository(CoreRepository, AlimaAccountRepositoryInterface):
    async def fetch_alima_account(
        self, customer_business_id: UUID
    ) -> PaidAccount | NoneType:
        """Fetch Alima Paid account

        Parameters
        ----------
        customer_business_id : UUID

        Returns
        -------
        PaidAccount | NoneType
        """
        p_acc = await super().fetch(
            id=customer_business_id,
            id_key="customer_business_id",
            core_element_name="Alima Paid Account",
            core_element_tablename="paid_account",
            core_columns="*",
        )
        if not p_acc:
            return None
        p_acc_dict = dict(p_acc)
        p_acc_dict["customer_type"] = AlimaCustomerType(p_acc_dict["customer_type"])
        return PaidAccount(**p_acc_dict)

    async def fetch_alima_account_by_id(
        self, paid_account_id: UUID
    ) -> PaidAccount | NoneType:
        p_acc = await super().fetch(
            id=paid_account_id,
            id_key="id",
            core_element_name="Alima Paid Account",
            core_element_tablename="paid_account",
            core_columns="*",
        )
        if not p_acc:
            return None
        p_acc_dict = dict(p_acc)
        p_acc_dict["customer_type"] = AlimaCustomerType(p_acc_dict["customer_type"])
        return PaidAccount(**p_acc_dict)

    async def fetch_alima_account_config(
        self, paid_account_id: UUID
    ) -> PaidAccountConfig | NoneType:
        """Fetch Alima Paid account config

        Parameters
        ----------
        customer_business_id : UUID

        Returns
        -------
        PaidAccount | NoneType
        """
        p_acc_cfg = await super().fetch(
            id=paid_account_id,
            id_key="paid_account_id",
            core_element_name="Alima Paid Account Config",
            core_element_tablename="paid_account_config",
            core_columns="*",
        )
        if not p_acc_cfg:
            return None
        p_acc_dict = dict(p_acc_cfg)
        return PaidAccountConfig(**p_acc_dict)

    async def fetch_charges(self, paid_account_id: UUID) -> List[Charge]:
        """Fetch charges

        Parameters
        ----------
        paid_account_id : UUID

        Returns
        -------
        List[Charge]
        """
        charges = await super().find(
            core_element_name="Alima Charge",
            core_element_tablename="charge",
            core_columns="*",
            filter_values="paid_account_id = :paid_account_id AND active = 't'",
            values={
                "paid_account_id": paid_account_id,
            },
        )
        if not charges:
            return []
        # format data type
        charges_dict = []
        for ch in charges:
            ch_dict = dict(ch)
            ch_dict["charge_type"] = ChargeType(ch_dict["charge_type"])
            charges_dict.append(Charge(**ch_dict))
        return charges_dict

    async def fetch_discounts_charges(
        self, paid_account_id: UUID
    ) -> List[ChargeDiscount]:
        """Fetch discount charges

        Parameters
        ----------
        paid_account_id : UUID

        Returns
        -------
        List[ChargeDiscounts]
        """
        today = datetime.datetime.today()
        discount_charges = await super().find(
            core_element_name="Alima Charge",
            core_element_tablename="charge c JOIN discount_charge cd ON c.id = cd.charge_id",
            core_columns="cd.*",
            filter_values="c.paid_account_id = :paid_account_id AND c.active = 't' AND valid_upto >= :today",
            values={"paid_account_id": paid_account_id, "today": today},
        )
        if not discount_charges:
            return []
        # format data type
        charges_dict = []
        for ch in discount_charges:
            ch_dict = dict(ch)
            ch_dict["charge_discount_type"] = DiscountChargeType(
                ch_dict["charge_discount_type"]
            )
            charges_dict.append(ChargeDiscount(**ch_dict))
        return charges_dict

    async def fetch_payment_methods(
        self, paid_account_id: UUID, only_active: bool = True
    ) -> List[BillingPaymentMethod]:
        """Fetch payment methods

        Parameters
        ----------
        paid_account_id : UUID
        only_active : bool, optional

        Returns
        -------
        List[BillingPaymentMethod]
        """
        pmethods = await super().find(
            core_element_name="Alima Billing Payment Method",
            core_element_tablename="billing_payment_method",
            core_columns="*",
            filter_values="paid_account_id = :paid_account_id"
            + (" AND active = 't'" if only_active else ""),
            values={
                "paid_account_id": paid_account_id,
            },
        )
        if not pmethods:
            return []
        # format data type
        pms_dict = []
        for pm in pmethods:
            pm_dict = dict(pm)
            pm_dict["payment_type"] = PayMethodType(pm_dict["payment_type"])
            pm_dict["payment_provider"] = PayProviderType(pm_dict["payment_provider"])
            pms_dict.append(BillingPaymentMethod(**pm_dict))
        return pms_dict

    async def new_alima_account(self, paid_account: PaidAccount) -> UUID | NoneType:
        """Alima Paid Account

        Args:
            paid_account (PaidAccount)
        Returns:
            UUID | NoneType
        """
        _id = uuid4()
        _data = domain_to_dict(paid_account, skip=["id", "created_at", "last_updated"])
        _data["id"] = _id
        _data["customer_type"] = paid_account.customer_type.value
        _flag = await super().add(
            core_element_name="Paid Account",
            core_element_tablename="paid_account",
            core_query="""
                INSERT INTO paid_account (
                    id,
                    customer_type,
                    customer_business_id,
                    account_name,
                    created_by,
                    active_cedis,
                    invoicing_provider_id
                )
                VALUES (
                    :id, :customer_type, :customer_business_id,
                    :account_name, :created_by, :active_cedis,
                    :invoicing_provider_id
                )
            """,
            core_values=_data,
        )
        if not _flag:
            return None
        return _id

    async def edit_alima_account(
        self,
        paid_account_id: UUID,
        customer_type: AlimaCustomerType,
        account_name: str,
        active_cedis: int,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        """Edit Alima Paid account

        Parameters
        ----------
        paid_account_id : UUID
        customer_type : AlimaCustomerType
        account_name : str
        active_cedis : int
        invoicing_provider_id : Optional[str], optional

        Returns
        -------
        bool
        """
        return await super().edit(
            core_element_name="Alima Paid Account",
            core_element_tablename="paid_account",
            core_query="""
                UPDATE paid_account
                SET customer_type = :customer_type,
                    account_name = :account_name,
                    active_cedis = :active_cedis,
                    invoicing_provider_id = :invoicing_provider_id
                WHERE id = :id
            """,
            core_values={
                "id": paid_account_id,
                "customer_type": customer_type.value,
                "account_name": account_name,
                "active_cedis": active_cedis,
                "invoicing_provider_id": invoicing_provider_id,
            },
        )

    async def edit_payment_method(self, payment_method: BillingPaymentMethod) -> bool:
        # create new payment method
        bpm_id = uuid4()
        pm_flag = await super().add(
            core_element_name="Alima Billing Payment Method",
            core_element_tablename="billing_payment_method",
            core_query="""
                INSERT INTO billing_payment_method (
                    id, paid_account_id, payment_type,
                    payment_provider, payment_provider_id,
                    created_by, account_number, account_name, bank_name, active)
                VALUES (:id, :paid_account_id, :payment_type,
                    :payment_provider, :payment_provider_id, :created_by,
                    :account_number, :account_name, :bank_name, :active)
                """,
            core_values={
                "id": bpm_id,
                "paid_account_id": payment_method.paid_account_id,
                "payment_type": payment_method.payment_type.value,
                "payment_provider": payment_method.payment_provider.value,
                "payment_provider_id": payment_method.payment_provider_id,
                "created_by": payment_method.created_by,
                "account_number": payment_method.account_number,
                "account_name": payment_method.account_name,
                "bank_name": payment_method.bank_name,
                "active": payment_method.active,
            },
        )
        # if payment method was not created - return False
        if not pm_flag:
            return False
        # if it was created, update the previous payment method as active = False
        return await super().edit(
            core_element_name="Alima Billing Payment Method",
            core_element_tablename="billing_payment_method",
            core_query="""
                UPDATE billing_payment_method
                SET active = 'f'
                WHERE id <> :id
                AND paid_account_id = :paid_account_id
            """,
            core_values={
                "id": bpm_id,
                "paid_account_id": payment_method.paid_account_id,
            },
        )

    async def new_charge(self, charge: Charge) -> UUID | NoneType:
        """New Charge

        Parameters
        ----------
        charge : Charge

        Returns
        -------
        UUID | NoneType
        """
        _id = uuid4()
        _data = domain_to_dict(
            charge, skip=["id", "created_at", "last_updated", "active"]
        )
        _data["id"] = _id
        _data["charge_type"] = charge.charge_type.value
        _flag = await super().add(
            core_element_name="Alima Charge",
            core_element_tablename="charge",
            core_query="""
                INSERT INTO charge (
                    id, paid_account_id, charge_type, charge_amount, charge_amount_type, currency, charge_description
                )
                VALUES (
                    :id, :paid_account_id, :charge_type, :charge_amount, :charge_amount_type, :currency, :charge_description
                )
            """,
            core_values=_data,
        )
        if not _flag:
            return None
        return _id

    async def new_discount_charge(
        self, charge_discount: ChargeDiscount
    ) -> UUID | NoneType:
        """New Charge

        Parameters
        ----------
        charge : Charge

        Returns
        -------
        UUID | NoneType
        """
        _id = uuid4()
        _data = domain_to_dict(
            charge_discount, skip=["id", "created_at", "last_updated"]
        )
        _data["id"] = _id
        _flag = await super().add(
            core_element_name="Alima Charge",
            core_element_tablename="charge",
            core_query="""
                INSERT INTO discount_charge (
                    id,
                    charge_id,
                    charge_discount_type,
                    charge_discount_amount,
                    charge_discount_amount_type,
                    charge_discount_description,
                    valid_upto
                )
                VALUES (
                    :id,
                    :charge_id,
                    :charge_discount_type,
                    :charge_discount_amount,
                    :charge_discount_amount_type,
                    :charge_discount_description,
                    :valid_upto
                )
            """,
            core_values=_data,
        )
        if not _flag:
            return None
        return _id

    async def deactivate_charge(
        self, paid_account_id: UUID, charge_type: List[str]
    ) -> bool:
        try:
            await self.db.execute(
                f"""
                UPDATE charge SET active = 'f'
                WHERE charge_type IN {list_into_strtuple(charge_type)}
                AND paid_account_id = :paid_account_id
                AND active = 't'
                """,
                {
                    "paid_account_id": paid_account_id,
                },
            )
        except Exception as e:
            logger.error(f"Error deactivating charges: {e}")
            return False
        return True

    async def new_billing_payment_method(
        self, payment_method: BillingPaymentMethod
    ) -> UUID | NoneType:
        """New Billing Payment Method

        Parameters
        ----------
        payment_method : BillingPaymentMethod

        Returns
        -------
        UUID | NoneType
        """
        _id = uuid4()
        _data = domain_to_dict(
            payment_method, skip=["id", "created_at", "last_updated"]
        )
        _data["id"] = _id
        _data["payment_type"] = payment_method.payment_type.value
        _data["payment_provider"] = payment_method.payment_provider.value
        _flag = await super().add(
            core_element_name="Alima Billing Payment Method",
            core_element_tablename="billing_payment_method",
            core_query="""
                INSERT INTO billing_payment_method (
                    id, paid_account_id, payment_type,
                    payment_provider, payment_provider_id,
                    created_by, account_number, account_name, bank_name, active
                )
                VALUES (
                    :id, :paid_account_id, :payment_type,
                    :payment_provider, :payment_provider_id, :created_by,
                    :account_number, :account_name, :bank_name, :active
                )
            """,
            core_values=_data,
        )
        if not _flag:
            return None
        return _id

    async def deactivate_billing_payment_method(self, payment_method_id: UUID) -> bool:
        try:
            await self.db.execute(
                """
                UPDATE billing_payment_method SET active = 'f'
                WHERE id = :payment_method_id
                """,
                {
                    "payment_method_id": payment_method_id,
                },
            )
        except Exception as e:
            logger.error(f"Error deactivating payment method: {e}")
            return False
        return True

    async def verify_paid_account_config_exists(self, paid_account_id: UUID) -> bool:
        """Verify Paid account config exists or not."""
        try:
            pa_confg = await self.db.fetch_one(
                """
                SELECT paid_account_id FROM paid_account_config
                WHERE paid_account_id = :paid_account_id
                """,
                {"paid_account_id": paid_account_id},
            )
            if not pa_confg:
                return False
            return True
        except Exception as e:
            logger.error(f"Error verifying paid account config: {e}")
            return False

    async def create_paid_account_config(
        self,
        paid_account_id: UUID,
        config: Dict[str, Any],
    ) -> bool:
        """Create a paid account config record.

        Parameters
        ----------
        paid_account_id : uuid.UUID
        config : Dict[str, Any]

        Returns
        -------
        uuid.UUID
        """
        # create paid account config
        try:
            await self.db.execute(
                """
                INSERT INTO paid_account_config (paid_account_id, config)
                VALUES (:paid_account_id, :config)
                """,
                {
                    "paid_account_id": paid_account_id,
                    "config": json.dumps(config),
                },
            )
            return True
        except Exception as e:
            logger.error("Error creating paid account config")
            logger.error(e)
            return False
