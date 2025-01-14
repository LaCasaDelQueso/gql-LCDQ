""" Script to Create a validated Supplier Alima Account.

This script does the following:

1. Created a record in `paid_account` table.
2. Creates all defined charges for the account in the `charge` table.
3. Creates established pay methods for the account in the `billing_payment_method` table.
4. Updates the `supplier_business` table with the `active` field set to `True`.

Usage:
    cd projects/gqlapi/
    # python -m gqlapi.scripts.alima_account.create_supplier_alima_account --help
        WARNING TO DETERMINATE VALUES OF PRICES AND DISCOUNTS TIMES, UPDATE MAP
"""

import asyncio
import argparse
import logging
from typing import Any, Dict, List, Optional
import uuid
import datetime
from gqlapi.lib.clients.clients.stripeapi.stripe_api import StripeApi
from dateutil.relativedelta import relativedelta
from databases import Database
from gqlapi.config import STRIPE_API_SECRET
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

# from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.scripts.alima_account.create_supplier_alima_config_account import (
    create_alima_account_config,
)
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.models.v2.utils import (
    AlimaCustomerType,
    ChargeType,
    DiscountChargeType,
    PayMethodType,
    PayProviderType,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.create_supplier_alima_account", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Create new Supplier Alima Account.")
    parser.add_argument(
        "--supplier_business_id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--account-name",
        help="Account Name. Options: (standard, enterprise)",
        type=str,
        choices=["alima_comercial", "alima_pro", "standard"],
        default=None,
        required=True,
    )
    parser.add_argument(
        "--payment-method",
        help="Payment Method. Options: (transfer_bbva, transfer_stripe, card)",
        type=str,
        choices=["transfer_bbva", "transfer_stripe", "card"],
        default=None,
        required=True,
    )
    parser.add_argument(
        "--active-cedis",
        help="Active CEDIS",
        type=int,
        default=1,
        required=True,
    )
    parser.add_argument(
        "--marketplace-commission",
        help="Marketplace Commision in percentage without IVA",
        type=float,
        default=None,
        required=False,
    )
    parser.add_argument(
        "--discounts",
        nargs="+",
        choices=["saas_temporal", "finance_temporal", "saas_yearly"],
        help="Select one or more discounts modes",
    )

    _args = parser.parse_args()
    # return args
    return _args


saas_prices_map = {
    # "create_supplier_account": create_alima_account,
    "standard": 400,
    "alima_comercial": 1200,  # 900, 1200
    "alima_pro": 1750,  # 1375, 1750
}

saas_discount_map = {
    "standard": 100,
    "alima_comercial": 100,
    "alima_pro": 125,
}

discount_month_map = {"saas_temporal": 1, "finance_temporal": 1, "saas_yearly": 12}

finance_prices_map = {
    # "create_supplier_account": create_alima_account,
    "standard": 400,
    "alima_comercial": 450,
    "alima_pro": 450,
}

finance_discount_map = {
    "standard": 100,
    "alima_comercial": 100,
    "alima_pro": 125,
}

desactivate_charge_type = ["saas", "finance", "marketplace_commission", "invoice_folio"]

# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


async def fetch_supplier_business_info(
    db: Database, supplier_business_id: uuid.UUID
) -> Dict[str, Any]:
    """Fetch supplier business information."""
    supplier = await db.fetch_one(
        """
        SELECT id, name, active FROM supplier_business
        WHERE id = :supplier_business_id
        """,
        {"supplier_business_id": supplier_business_id},
    )
    if not supplier:
        logging.warning("Not able to retrieve supplier information")
        return {}
    # fetch first core user associated to supplier business
    core_user = await db.fetch_one(
        """
        SELECT CU.id as core_user_id, CU.email
        FROM core_user CU
        JOIN supplier_user SU ON SU.core_user_id = CU.id
        JOIN supplier_user_permission SUP ON SUP.supplier_user_id = SU.id
        WHERE SUP.supplier_business_id = :supplier_business_id
        ORDER BY CU.created_at ASC
        LIMIT 1
        """,
        {"supplier_business_id": supplier_business_id},
    )
    if not core_user:
        logging.warning("Not able to retrieve supplier user information")
        return {}
    logging.info("Got Supplier Business info")
    sup_dict = dict(supplier)
    for k, v in dict(core_user).items():
        sup_dict[k] = v
    return sup_dict


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def create_paid_account(
    db: Database,
    supplier_business_id: uuid.UUID,
    account_name: str,
    created_by: uuid.UUID,
    active_cedis: int = 1,
) -> uuid.UUID:
    """Create a new paid account.

    Parameters
    ----------
    db : Database
    supplier_business_id : uuid.UUID
    account_name : str
    created_by : uuid.UUID
    active_cedis : int

    Returns
    -------
    uuid.UUID
    """
    # verify if exists
    exists = await db.fetch_one(
        """
        SELECT id FROM paid_account
        WHERE customer_business_id = :customer_business_id
        """,
        {"customer_business_id": supplier_business_id},
    )
    if exists:
        raise Exception("Paid account already exists")
    # create paid account
    paid_account_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO paid_account (id, customer_type, customer_business_id, account_name, created_by, active_cedis)
        VALUES (:id, :customer_type, :customer_business_id, :account_name, :created_by, :active_cedis)
        """,
        {
            "id": paid_account_id,
            "customer_type": AlimaCustomerType.SUPPLY.value,
            "customer_business_id": supplier_business_id,
            "account_name": account_name,
            "created_by": created_by,
            "active_cedis": active_cedis,
        },
    )
    logging.info("Created Paid Account")
    return paid_account_id


async def create_new_charge(
    db: Database,
    paid_account_id: uuid.UUID,
    charge_type: ChargeType,
    charge_amount: float,
    charge_amount_type: str,  # "$" or "%"
    charge_description: str,
) -> uuid.UUID:
    """Create a new charge.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    charge_type : ChargeType
    charge_amount : float
    charge_amount_type : str
    charge_description: str

    Returns
    -------
    uuid.UUID
    """
    # create charge
    charge_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO charge (id, paid_account_id, charge_type, charge_amount, charge_amount_type, currency, charge_description)
        VALUES (:id, :paid_account_id, :charge_type, :charge_amount, :charge_amount_type, :currency, :charge_description)
        """,
        {
            "id": charge_id,
            "paid_account_id": paid_account_id,
            "charge_type": charge_type.value,
            "charge_amount": (
                charge_amount if charge_amount_type == "$" else charge_amount / 100
            ),
            "charge_amount_type": charge_amount_type,
            "currency": "MXN",
            "charge_description": charge_description,
        },
    )
    logging.info(f"Created Charge: {charge_type.value}")
    return charge_id


async def create_new_discount_charge(
    db: Database,
    charge_id: uuid.UUID,
    charge_discount_type: DiscountChargeType,
    charge_discount_amount: float,
    charge_discount_amount_type: str,  # "$" or "%"
    valid_upto: datetime.datetime,
    charge_discount_description: str,
) -> uuid.UUID:
    """Create a new charge.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    charge_type : ChargeType
    charge_amount : float
    charge_amount_type : str
    charge_discount_description: str

    Returns
    -------
    uuid.UUID
    """
    # create charge
    id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO discount_charge (id,
            charge_id,
            charge_discount_type,
            charge_discount_amount,
            charge_discount_amount_type,
            charge_discount_description,
            valid_upto)
        VALUES (:id,
            :charge_id,
            :charge_discount_type,
            :charge_discount_amount,
            :charge_discount_amount_type,
            :charge_discount_description,
            :valid_upto)
        """,
        {
            "id": id,
            "charge_id": charge_id,
            "charge_discount_type": charge_discount_type.value,
            "charge_discount_amount": (
                charge_discount_amount
                if charge_discount_amount_type == "$"
                else charge_discount_amount / 100
            ),
            "charge_discount_amount_type": charge_discount_amount_type,
            "valid_upto": valid_upto,
            "charge_discount_description": charge_discount_description,
        },
    )
    logging.info(f"Created Charge: {charge_discount_type.value}")
    return id


async def create_billing_payment_method(
    db: Database,
    paid_account_id: uuid.UUID,
    payment_type: PayMethodType,
    payment_provider: PayProviderType,
    created_by: uuid.UUID,
    payment_provider_id: str = "",
    account_number: str = "",
    account_name: str = "",
    bank_name: str = "",
) -> uuid.UUID:
    """Create a new billing payment method.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    payment_type : PayMethodType
    payment_provider : PayProviderType
    payment_provider_id : str
    created_by : uuid.UUID

    Returns
    -------
    uuid.UUID
    """
    # create billing payment method
    billing_payment_method_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO billing_payment_method (
            id, paid_account_id, payment_type,
            payment_provider, payment_provider_id,
            created_by, account_number, account_name, bank_name, active)
        VALUES (:id, :paid_account_id, :payment_type,
            :payment_provider, :payment_provider_id, :created_by,
            :account_number, :account_name, :bank_name, :active)
        """,
        {
            "id": billing_payment_method_id,
            "paid_account_id": paid_account_id,
            "payment_type": payment_type.value,
            "payment_provider": payment_provider.value,
            "payment_provider_id": payment_provider_id,
            "created_by": created_by,
            "account_number": account_number,
            "account_name": account_name,
            "bank_name": bank_name,
            "active": True,
        },
    )
    logging.info(f"Created Billing Payment Method: {payment_type.value}")
    return billing_payment_method_id


async def get_alima_bot(info: InjectedStrawberryInfo) -> uuid.UUID:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.fetch_by_email("admin")
    if not tmp or not tmp.id:
        raise Exception("Error getting Alima admin bot user")
    admin_user = tmp.id
    return admin_user


async def desactive_charges(
    db: Database, paid_account_id: uuid.UUID, charge_type: List[str]
) -> bool:
    try:
        await db.execute(
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
        logging.info(f"Desactivate charges of: {paid_account_id}")
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------
# update functions
# ---------------------------------------------------------------------


async def update_supplier_business(
    db: Database,
    supplier_business_id: uuid.UUID,
    active: bool,
) -> bool:
    """Update supplier business.

    Parameters
    ----------
    db : Database
    supplier_business_id : uuid.UUID
    active : bool

    Returns
    -------
    bool
    """
    # update supplier business
    await db.execute(
        """
        UPDATE supplier_business
        SET active = :active
        WHERE id = :supplier_business_id
        """,
        {
            "supplier_business_id": supplier_business_id,
            "active": active,
        },
    )
    logging.info("Updated Supplier Business")
    return True


async def update_paid_account(
    db: Database,
    paid_account_id: uuid.UUID,
    account_type: str,
    active_cedis: int = 1,
) -> bool:
    """Update paid account.

    Parameters
    ----------
    db : Database
    paid account : uuid.UUID
    account_type : str

    Returns
    -------
    bool
    """
    # update supplier business
    await db.execute(
        """
        UPDATE paid_account
        SET account_name = :account_type,
            active_cedis = :active_cedis
        WHERE id = :paid_account_id
        """,
        {
            "paid_account_id": paid_account_id,
            "account_type": account_type,
            "active_cedis": active_cedis,
        },
    )
    logging.info("Updated Paid Account")
    return True


# ---------------------------------------------------------------------
# Create alima account
# ---------------------------------------------------------------------


async def create_alima_account(
    supplier_business_id: uuid.UUID,
    account_name: str,
    payment_method: str,
    marketplace_commission: Optional[float] = None,
    discounts: Optional[List[str]] = [],
    active_cedis: Optional[int] = 1,
) -> bool:
    """Create a new Supplier Alima Account.

    Parameters
    ----------
    supplier_business_id : uuid.UUID
    account_name : str
    payment_method : str - transfer_bbva, transfer_stripe, card
    saas_price : float
    marketplace_commission : Optional[float], optional

    Returns
    -------
    bool

    Raises
    ------
    Exception
    """
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    alima_bot = await get_alima_bot(_info)

    _handler = AlimaAccountHandler(
        AlimaAccountRepository(_info),  # type: ignore
        CoreUserRepository(_info),  # type: ignore
        SupplierBusinessRepository(_info),  # type: ignore
        SupplierBusinessAccountRepository(_info),  # type: ignore
        SupplierUserRepository(_info),  # type: ignore
        SupplierUserPermissionRepository(_info),  # type: ignore
    )
    _stripe_api = StripeApi("scripts.create_supplier_alima_account", STRIPE_API_SECRET)

    paid_account = await _handler.repository.fetch_alima_account(supplier_business_id)
    supplier = await fetch_supplier_business_info(_db, supplier_business_id)
    if not paid_account or not supplier:
        # create paid account
        paid_account_id = await create_paid_account(
            _db, supplier_business_id, account_name, alima_bot, active_cedis or 1
        )
        edit_mode = False
    else:
        paid_account_id = paid_account.id
        await update_paid_account(
            db=_db,
            paid_account_id=paid_account_id,
            account_type=account_name,
            active_cedis=active_cedis or 1,
        )
        # Update account_name
        await desactive_charges(_db, paid_account_id, desactivate_charge_type)
        edit_mode = True
    current_date = datetime.datetime.utcnow()
    # create SaaS Charge
    saas_id = await create_new_charge(
        _db,
        paid_account_id,
        ChargeType.SAAS_FEE,
        saas_prices_map[account_name],
        "$",
        "Servicio de Software - Operaciones",
    )

    if discounts:
        if "saas_yearly" in discounts:
            await create_new_discount_charge(
                db=_db,
                charge_id=saas_id,
                charge_discount_type=DiscountChargeType.SAAS_YEARLY,
                charge_discount_amount=saas_discount_map[
                    account_name
                ],  # [TODO] - change discountt map to %
                charge_discount_amount_type="%",
                valid_upto=datetime.datetime(
                    current_date.year, current_date.month, current_date.day
                )
                + relativedelta(
                    month=discount_month_map[DiscountChargeType.SAAS_YEARLY.value]
                ),
                charge_discount_description="Descuento Anual de Software",
            )
        elif "saas_temporal" in discounts:
            await create_new_discount_charge(
                db=_db,
                charge_id=saas_id,
                charge_discount_type=DiscountChargeType.SAAS_TEMPORAL,
                charge_discount_amount=saas_discount_map[account_name],
                charge_discount_amount_type="$",
                valid_upto=current_date
                + relativedelta(
                    months=discount_month_map[DiscountChargeType.SAAS_TEMPORAL.value]
                ),
                charge_discount_description="Descuento Servicio de Software",
            )

    if account_name == "alima_pro":
        # Invoice commission
        await create_new_charge(
            _db,
            paid_account_id,
            ChargeType.INVOICE_FOLIO,
            1,
            "$",
            "Folios Adicionales Facturación",
        )

    # if commission is passed create Marketplace Commission Charge
    mktplace_id = None
    if marketplace_commission:
        mktplace_id = await create_new_charge(
            _db,
            paid_account_id,
            ChargeType.MARKETPLACE_COMMISSION,
            marketplace_commission,
            "%",
            "Comisión de Marketplace",
        )
    # when creating new account
    paym_id = None
    if not edit_mode:
        if payment_method == "transfer_bbva":
            # add payment method of transfer
            # [TODO] - add account number and bank name
            paym_id = await create_billing_payment_method(
                _db,
                paid_account_id,
                PayMethodType.TRANSFER,
                PayProviderType.TRANSFER_BBVA,
                alima_bot,
                account_number="012180001182328575",
                account_name="SERVICIOS DE DISTRIBUCION DE PERECEDEROS NEUTRO",
                bank_name="BBVA",
            )
        elif payment_method == "transfer_stripe":
            # add payment method of transfer
            print("[TODO]: Not implemented yet")
            # create stripe customer
            # stripe_cust = _stripe_api.create_customer(
            #     email=supplier["email"],
            #     name=supplier["name"],
            #     metadata={"supplier_business_id": str(supplier_business_id)},
            # )
            # if not stripe_cust:
            #     raise Exception("Error creating Stripe Customer")
            # compute total due to pay in next invoice
            # add payment spei intent
            # with response of spei info, create payment method
        elif payment_method == "card":
            # add payment method of card
            # create stripe customer
            stripe_cust = _stripe_api.create_customer(
                email=supplier["email"],
                name=supplier["name"],
                metadata={"supplier_business_id": str(supplier_business_id)},
            )
            if not stripe_cust:
                raise Exception("Error creating Stripe Customer")
            # with custoemer info create payment method
            paym_id = await create_billing_payment_method(
                _db,
                paid_account_id,
                PayMethodType.CARD,
                PayProviderType.CARD_STRIPE,
                alima_bot,
                payment_provider_id=stripe_cust["id"],
            )
        if not paym_id:
            raise Exception("Error creating Payment Method")
        # update supplier business to active
        await update_supplier_business(
            _db,
            supplier_business_id,
            True,
        )
    # show results
    logging.info("Finished creating Supplier Alima Account")
    logging.info(
        "\n".join(
            [
                "-----",
                f"Supplier Business ID: {supplier_business_id}",
                f"Paid Account ID: {paid_account_id}",
                f"Saas Charge ID: {saas_id}",
                f"Marketplace Commission Charge ID: {mktplace_id}",
                f"Payment Method ID: {paym_id}",
                "-----",
            ]
        )
    )
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(
        f"Started creating Supplier Alima Account: {args.supplier_business_id}"
    )
    try:
        fl = await create_alima_account(
            uuid.UUID(args.supplier_business_id),
            args.account_name,
            args.payment_method,
            args.marketplace_commission,
            args.discounts,
            args.active_cedis,
        )
        if not fl:
            logging.info(
                f"Supplier Business with id ({args.supplier_business_id}) not able to be created"
            )
            return
        # create config
        if not await create_alima_account_config(
            uuid.UUID(args.supplier_business_id),
        ):
            logging.warning(
                f"Paid account config not created for Supplier Business with id ({args.supplier_business_id})"
            )
            return False
        logging.info(
            f"Finished creating Alima account successfully: {args.supplier_business_id}"
        )
    except Exception as e:
        logging.error(
            f"Error creating Supplier Alima account: {args.supplier_business_id}"
        )
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
