""" Script to create all Customer invoices needed on behalf of Supplier Businesses.

This script does the following:

1. Fetches all Supplier Units with active invoicing rules
2. For each Supplier Unit:
    1. Fetch all ordenes from the past 24hrs that have not been invoiced / failed invoicing
    2. For each Orden:
        1. Fetches the Restaurant Branch information from Orden UUID
        1.1. Retrieves RFC
        1.2. Retrieves Invoice Type
        2. Fetches the Supplier Business information from Orden UUID
            2.1. Retrieves Expedition Place
        3. Creates a new Customer Invoice
        4. Save into the Invoicing Execution table the result of the Invoice creation

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.alima_account.create_supplier_invoice_complement --help
"""

import asyncio
import argparse
import logging
import uuid

from gqlapi.lib.clients.clients.facturamaapi.facturama import PaymentForm
from gqlapi.domain.models.v2.utils import PayStatusType
from gqlapi.handlers.alima_account.account import AlimaAccountHandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.alima_account.billing import (
    AlimaBillingInvoiceRepository,
    AlimaBillingInvoiceComplementRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)

# from motor.motor_asyncio import AsyncIOMotorClient

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup


logger = get_logger(
    "scripts.run_daily_3rd_party_invoice", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Daily Supplier 3rd party Invoices"
    )
    parser.add_argument(
        "--business_id",
        help="Supplier_business_id",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--month",
        help="Date (YYYY-MM-DD)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--payment_form",
        help="Form of payment (01 - Cash, 03 - Transfer , 03 - Card)",
        type=str,
        choices=["01", "03", "04"],
        default=None,
        required=True,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def run_supplier_invoices_complement(
    info: InjectedStrawberryInfo,
    supplier_business_id: uuid.UUID,
    payment_form: str,
    month: str,
) -> bool:
    # initialize repos
    supplier_business_repo = SupplierBusinessRepository(info)  # type: ignore
    supplier_business_account_repo = SupplierBusinessAccountRepository(info)  # type: ignore
    paid_account_repo = AlimaAccountRepository(info)  # type: ignore
    alima_billing_repo = AlimaBillingInvoiceRepository(info)  # type: ignore
    alima_billing_comp_repo = AlimaBillingInvoiceComplementRepository(info)  # type: ignore
    core_repo = CoreUserRepository(info)  # type: ignore
    alima_acc_hdler = AlimaAccountHandler(
        alima_account_repository=paid_account_repo,
        core_user_repository=core_repo,
        supplier_business_repository=supplier_business_repo,
        supplier_business_account_repository=supplier_business_account_repo,
        supplier_user_repository=SupplierUserRepository(info),  # type: ignore
        supplier_user_permission_repository=SupplierUserPermissionRepository(info),  # type: ignore
        alima_billing_invoice_repository=alima_billing_repo,
        alima_billing_complement_repository=alima_billing_comp_repo,
    )
    # find paid account
    paid_account = await paid_account_repo.fetch_alima_account(supplier_business_id)
    if not paid_account:
        logger.error(
            f"Supplier Business {supplier_business_id} does not have a paid account"
        )
        return False
    paymethods = await paid_account_repo.fetch_payment_methods(paid_account.id)
    # find active invoice
    invoices = await alima_acc_hdler.alima_billing_invoice_repository.find(
        paid_account_id=paid_account.id,
        date=month,
    )
    if len(invoices) == 0:
        logger.error(
            f"Supplier Business {supplier_business_id} does not have an active invoice"
        )
        return False
    p_invoice = invoices[0]
    payform = PaymentForm(payment_form)
    # create payment complement
    complem_flag = await alima_acc_hdler.new_alima_invoice_complement(
        supplier_business_id=supplier_business_id,
        payment_form=payform,
        amount=p_invoice.total,
        active_invoice=p_invoice,
    )
    if complem_flag is None:
        logger.error(
            f"Supplier Business {supplier_business_id} complement could not be created"
        )
        return False
    logger.info(
        f"Supplier Business {supplier_business_id} complement for {month} created successfully"
    )
    updated_invoice_flag = (
        await alima_acc_hdler.alima_billing_invoice_repository.edit_alima_invoice(
            billing_invoice=p_invoice,
            paystatus=PayStatusType.PAID,
            billing_payment_method_id=paymethods[0].id if len(paymethods) > 0 else None,
        )
    )
    if not updated_invoice_flag:
        logger.error(
            f"Supplier Business {supplier_business_id} invoice could not be updated"
        )
        return False
    logger.info(
        f"Supplier Business {supplier_business_id} invoice for {month} updated successfully"
    )
    # update invoice as paid
    return True


async def run_supplier_invoices_complement_warapper(
    supplier_business_id: uuid.UUID,
    payment_form: str,
    month: str,
) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    # Permite conectar a la db
    _resp = await run_supplier_invoices_complement(
        _info, supplier_business_id, payment_form, month
    )
    return _resp


async def main():
    args = parse_args()
    logger.info("Started running create internal supplier invoice complement:")
    try:
        await db_startup()
        assert len(args.month.split("-")) == 2, "Invalid month format: MM-YYYY"
        assert len(args.month.split("-")[0]) == 2, "Invalid month format: MM-YYYY"
        assert len(args.month.split("-")[1]) == 4, "Invalid month format: MM-YYYY"

        fl = await run_supplier_invoices_complement_warapper(
            uuid.UUID(args.business_id),
            args.payment_form,
            args.month,
        )
        if not fl:
            logger.info(
                "Started running create internal supplier invoice complement not able to be created"
            )
            return
        logger.info(
            "Finished create internal supplier invoice complement successfully:"
        )
        await db_shutdown()
    except Exception as e:
        logger.error("Error ccreate internal supplier invoice complement")
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
