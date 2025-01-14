""" Script to Create a Supplier Invoice given its defined charges.

This script does the following:

1. Computes the total amount due for the invoice based on the charges and arguments.
2. Creates a record in the `billing_invoice` table.
3. Creates a record in the `billing_invoice_charge` table for each charge.
4. Creates a record in the `billing_invoice_paystatus` table with status `unpaid`.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.billing.create_daily_alima_invoice_v2
"""

import asyncio
import calendar
import base64
from datetime import datetime, timedelta, timezone
import json
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from types import NoneType
from typing import Any, Dict, List, Optional
import uuid
from uuid import UUID
from gqlapi.lib.clients.clients.facturamaapi.facturama import (
    Customer,
    CustomerAddress,
    FacturamaClientApi,
    FacturamaInternalInvoice,
    GlobalInformationFacturama,
    Item,
    PaymentForm,
    PaymentFormFacturama,
    SatTaxes,
)

from databases import Database
from gqlapi.domain.models.v2.alima_business import Charge, ChargeDiscount
from gqlapi.domain.models.v2.supplier import SupplierBusinessAccount
from gqlapi.domain.models.v2.alima_business import PaidAccount
from gqlapi.config import (
    ALIMA_EXPEDITION_PLACE,
    FACT_PWD,
    FACT_USR,
    ENV as DEV_ENV,
    RETOOL_SECRET_BYPASS,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.services.mails import (
    send_new_alima_invoice_notification_v2,
    send_reports_alert,
)
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.domain.models.v2.utils import (
    ChargeType,
    DataTypeDecoder,
    InvoiceStatusType,
    InvoiceType,
    PayStatusType,
)
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.db import database as SQLDatabase, db_shutdown, db_startup
import pandas as pd
import strawberry

logger = get_logger(get_app())

# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


@strawberry.type
class BillingReport:
    paid_account_id: UUID
    supplier: Optional[str] = None
    status: str
    reason: str


async def fetch_supplier_business_info(
    db: Database, supplier_business_id: uuid.UUID
) -> Dict[str, Any]:
    """Fetch supplier business information."""
    supplier = await db.fetch_one(
        """
        WITH supplier_units AS (
            SELECT supplier_business_id, count(id) AS units
            FROM supplier_unit
            WHERE deleted <> 't'
            GROUP BY 1
        )
        SELECT id, name, active, supplier_units.units FROM supplier_business
        JOIN supplier_units ON supplier_units.supplier_business_id = supplier_business.id
        WHERE supplier_business.id = :supplier_business_id
        """,
        {"supplier_business_id": supplier_business_id},
    )
    if not supplier:
        logger.warning("Not able to retrieve supplier information")
        return {}
    if not supplier["active"]:
        logger.warning("Supplier Business is NOT ACTIVE!")
        return {}
    logger.info("Got Supplier Business info")
    return dict(supplier)


async def edit_paid_account(
    db: Database, paid_account_id: uuid.UUID, invoicing_provider_id: str
) -> bool | NoneType:
    """Edit paid account.

    Parameters
    ----------
    db : Database
    paid_Account_id : uuid.UUID
    invoicing_provider_id: str

    Returns
    -------
    bool
    """
    # verify if exists
    try:
        await db.execute(
            """
            UPDATE paid_account
            SET invoicing_provider_id = :invoicing_provider_id
            WHERE id = :paid_account_id;
            """,
            {
                "paid_account_id": paid_account_id,
                "invoicing_provider_id": invoicing_provider_id,
            },
        )
        return True
    except Exception as e:
        logger.info(e)
        return False


async def get_alima_bot(info: InjectedStrawberryInfo) -> uuid.UUID:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.get_by_email("admin")
    admin_user = tmp.id
    if not admin_user:
        raise Exception("Error getting Alima admin bot user")
    return admin_user


async def get_last_invoice_date(
    db: Database, paid_account_id: uuid.UUID
) -> datetime | None:
    last_invoice_date = await db.fetch_one(
        """
        SELECT * FROM billing_invoice
        WHERE paid_account_id = :paid_account_id and status = 'active' ORDER BY created_at DESC LIMIT 1
        """,
        {"paid_account_id": paid_account_id},
    )
    if not last_invoice_date:
        return None
    logger.info("Got Last Invoice Date")
    lid_dict = dict(last_invoice_date)
    return lid_dict["created_at"]


async def get_month_invoice_folios(
    db: Database,
    supplier_business_id: uuid.UUID,
    last_invoice_date: Optional[datetime] = None,
) -> int:
    inv_query = """
        SELECT id FROM mx_invoice
        WHERE supplier_business_id = :supplier_business_id
        """
    core_values: Dict[Any, Any] = {"supplier_business_id": supplier_business_id}
    inv_comp_query = """
        SELECT id FROM mx_invoice_complement
        WHERE mx_invoice_id in (SELECT id FROM mx_invoice
        WHERE supplier_business_id = :supplier_business_id) """

    if last_invoice_date:
        inv_query += """ and created_at > :last_invoice_date"""
        inv_comp_query += """ and created_at > :last_invoice_date"""
        core_values["last_invoice_date"] = last_invoice_date

    invoice_id = await db.fetch_all(
        inv_query,
        core_values,
    )
    if not invoice_id:
        return 0
    invoice_complements_id = await db.fetch_all(
        inv_comp_query,
        core_values,
    )
    if not invoice_complements_id:
        return len(invoice_id)

    logger.info("Got invoice folios")
    return len(invoice_id) + len(invoice_complements_id)


# ---------------------------------------------------------------------
# create functions
# ---------------------------------------------------------------------


async def create_billing_invoice(
    db: Database,
    paid_account_id: uuid.UUID,
    country: str,
    invoice_month: str,  # MONTH - YEAR (MM-YYYY)
    total: float,
    currency: str,
    status: InvoiceStatusType,
    created_at: datetime,
    sat_invoice_uuid: uuid.UUID,
    payment_method: InvoiceType,
) -> uuid.UUID:
    """Create a new billing invoice.

    Parameters
    ----------
    db : Database
    paid_account_id : uuid.UUID
    country : str
    invoice_month : str
    total : float
    currency : str
    status : InvoiceStatusType

    Returns
    -------
    uuid.UUID
    """
    # create billing invoice
    billing_invoice_id = uuid.uuid4()
    await db.execute(
        """
        INSERT INTO billing_invoice (
            id, paid_account_id, country,
            invoice_month, invoice_name, tax_invoice_id,
            invoice_number, total,
            currency, status, created_at, last_updated,
            sat_invoice_uuid, payment_method
        )
        VALUES (
            :id, :paid_account_id, :country,
            :invoice_month, :invoice_name, :tax_invoice_id,
            :invoice_number, :total,
            :currency, :status, :created_at, :last_updated,
            :sat_invoice_uuid, :payment_method
        )
        """,
        {
            "id": billing_invoice_id,
            "paid_account_id": paid_account_id,
            "country": country,
            "invoice_month": invoice_month,
            "invoice_name": invoice_month,  # for now same as invoice_month
            "tax_invoice_id": "",  # SAT UUID - null for now
            "invoice_number": "",  # null for now
            "total": round(total, 2),
            "currency": currency,
            "status": DataTypeDecoder.get_mxinvoice_status_key(status.value),
            "created_at": created_at,
            "last_updated": created_at,
            "sat_invoice_uuid": sat_invoice_uuid,
            "payment_method": payment_method.value,
        },
    )
    # create billing invoice paystatus
    await db.execute(
        """
        INSERT INTO billing_invoice_paystatus (
            id, billing_invoice_id, status, created_at
        )
        VALUES (
            :id, :billing_invoice_id, :status, :created_at
        )
        """,
        {
            "id": uuid.uuid4(),
            "billing_invoice_id": billing_invoice_id,
            "status": DataTypeDecoder.get_orden_paystatus_key(PayStatusType.PAID.value),
            "created_at": created_at,
        },
    )
    logger.info("Created Billing Invoice")
    return billing_invoice_id


async def create_billing_invoice_charges(
    db: Database,
    billing_invoice_id: uuid.UUID,
    billing_charges: List[Dict[str, Any]],
    created_at: datetime,
) -> List[uuid.UUID]:
    """Create billing invoice charges.

    Parameters
    ----------
    db : Database
    billing_invoice_id : uuid.UUID
    billing_charges : List[Dict[str, Any]]

    Returns
    -------
    List[uuid.UUID]
    """
    billing_charge_ids = []
    # create billing invoice charges
    for bch in billing_charges:
        _id = uuid.uuid4()
        await db.execute(
            """
            INSERT INTO billing_invoice_charge (
                id, billing_invoice_id, charge_id,
                charge_type, charge_base_quantity, charge_amount,
                charge_amount_type, total_charge, currency,
                created_at
            )
            VALUES (
                :id, :billing_invoice_id, :charge_id,
                :charge_type, :charge_base_quantity, :charge_amount,
                :charge_amount_type, :total_charge, :currency,
                :created_at
            )
            """,
            {
                "id": _id,
                "billing_invoice_id": billing_invoice_id,
                "charge_id": bch["charge_id"],
                "charge_type": bch["charge_type"],
                "charge_base_quantity": bch["charge_base_quantity"],
                "charge_amount": bch["charge_amount"],
                "charge_amount_type": bch["charge_amount_type"],
                "total_charge": bch["total_charge"],
                "currency": bch["currency"],
                "created_at": created_at,
            },
        )
        billing_charge_ids.append(_id)
    return billing_charge_ids


async def save_internal_invoice_info(
    db: Database,
    billing_invoice_id: uuid.UUID,
    pdf_file: Any,
    xml_file: Any,
    invoice_id: str,
    invoice_number: str,
    result: str,
) -> NoneType:
    """Create billing invoice charges.

    Parameters
    ----------
    db : Database
    billing_invoice_id : uuid.UUID
    pdf_file : str
    xml_file : str
    invoice_id : str

    Returns
    -------
    None
    """
    # create billing invoice charges
    pdf_file_str = base64.b64encode(pdf_file).decode("utf-8")
    xml_file_str = base64.b64encode(xml_file).decode("utf-8")
    json_data = {"pdf": pdf_file_str, "xml": xml_file_str}
    invoice_files = json.dumps(json_data)
    invoice_diles = invoice_files.encode("utf-8")
    await db.execute(
        """
            UPDATE billing_invoice
            SET tax_invoice_id= :invoice_id, invoice_files= :invoice_files, invoice_number= :invoice_number,
                result= :result
            WHERE id= :billing_invoice_id
            """,
        {
            "invoice_id": invoice_id,
            "invoice_files": [invoice_diles],
            "billing_invoice_id": billing_invoice_id,
            "invoice_number": invoice_number,
            "result": result,
        },
    )


# ---------------------------------------------------------------------
# logic functions
# ---------------------------------------------------------------------
def find_discounts(
    charge_id: uuid.UUID, charge_discounts: List[ChargeDiscount]
) -> List[ChargeDiscount]:
    filter_charge_discounts = []
    for cd in charge_discounts:
        if cd.charge_id == charge_id:
            filter_charge_discounts.append(cd)
    return filter_charge_discounts


def compute_total_with_discounts(
    _chtype: str, _chtotal_without_discount: float, discount: List[ChargeDiscount]
):
    _chtype = _chtype + " ("
    _chtotal = _chtotal_without_discount
    for dc in discount:
        if dc.charge_discount_amount_type == "$":
            _chtotal = _chtotal - dc.charge_discount_amount
            _chtype = _chtype + f"Descuento de ${dc.charge_discount_amount} /"
        if dc.charge_discount_amount_type == "%":
            _chtotal = _chtotal * (1 - dc.charge_discount_amount)
            _chtype = _chtype + f"Descuento de {dc.charge_discount_amount*100}% /"
    _chtype = _chtype[:-1]
    _chtype = _chtype + ")"
    return _chtotal, _chtype


def compute_fee_charge(
    _chtype: str, ch: Charge, num_units, discount: List[ChargeDiscount]
):
    _chbase = num_units
    _chtotal_without_discount = _chbase * ch.charge_amount
    # Saas fee * num units +  16% IVA
    if discount:
        _chtotal, _chtype = compute_total_with_discounts(
            _chtype, _chtotal_without_discount, discount
        )
    else:
        _chtotal = _chtotal_without_discount
    _chtotal_with_iva = _chtotal * 1.16
    return _chtype, _chtotal_with_iva


def compute_reports_charge(ch: Charge, discount: List[ChargeDiscount]):
    if ch.charge_description:
        _chtype = ch.charge_description
    else:
        _chtype = "Reporte"
    _chbase = 1
    _chtotal_without_discount = _chbase * ch.charge_amount
    if discount:
        _chtotal, _chtype = compute_total_with_discounts(
            _chtype, _chtotal_without_discount, discount
        )
    else:
        _chtotal = _chtotal_without_discount
    _chtotal_with_iva = _chtotal * 1.16
    return _chtype, _chtotal_with_iva


def compute_folios_charge(unit_price: float):
    return unit_price * 1.16


def compute_alima_comercial_total_amount_due(
    charges: List[Charge],
    discounts: List[ChargeDiscount],
    num_units: int,
    folio_count: int,
) -> Dict[str, Any]:
    """Compute the total amount due for the invoice.

    Parameters
    ----------
    charges : List[Charge]
    num_units : int
    gmv : Optional[float], optional

    Returns
    -------
    Dict[str, Any]
    """
    billing_charges = []
    total_amount_due = 0.0
    # compute total amount due
    for ch in charges:
        discount = None
        discount = find_discounts(ch.id, discounts)
        # vars
        _chtype = ""
        _chbase, _chtotal_with_iva = 0, 0.0
        if ch.charge_type == ChargeType.SAAS_FEE:
            if ch.charge_description:
                _chtype = ch.charge_description
            else:
                _chtype = "Servicio de Software - Operaciones"
            _chbase = num_units
            _chtype, _chtotal_with_iva = compute_fee_charge(
                _chtype, ch, num_units, discount
            )
        elif ch.charge_type == ChargeType.FINANCE_FEE:
            if ch.charge_description:
                _chtype = ch.charge_description
            else:
                _chtype = "Servicio de Software - Finanzas"
            _chbase = num_units
            _chtype, _chtotal_with_iva = compute_fee_charge(
                _chtype, ch, num_units, discount
            )
        elif ch.charge_type == ChargeType.REPORTS:
            _chbase = 1
            _chtype, _chtotal_with_iva = compute_reports_charge(ch, discount)
        elif ch.charge_type == ChargeType.MARKETPLACE_COMMISSION:
            continue
        elif ch.charge_type == ChargeType.INVOICE_FOLIO:
            if folio_count > (200 * num_units):
                if ch.charge_description:
                    _chtype = ch.charge_description
                else:
                    _chtype = "Folios Adicionales Facturación"
                _chbase = folio_count - (200 * num_units)
                _chtotal_with_iva = compute_folios_charge(_chbase)
            else:
                continue
        # format response
        bill_ch = {
            "charge_id": ch.id,
            "charge_type": _chtype,
            "charge_base_quantity": _chbase,
            "charge_amount": (
                round(_chtotal_with_iva / _chbase, 4)
                if ch.charge_amount_type == "$"
                else ch.charge_amount
            ),
            "charge_amount_type": ch.charge_amount_type,
            "total_charge": _chtotal_with_iva,
            "currency": ch.currency,
        }
        total_amount_due += _chtotal_with_iva
        billing_charges.append(bill_ch)
    return {
        "total": total_amount_due,
        "charges": billing_charges,
    }


def compute_anual_alima_comercial_total_amount_due(
    charges: List[Charge],
    discounts: List[ChargeDiscount],
    num_units: int,
    folio_count: int,
) -> Dict[str, Any]:
    """Compute the total amount due for the invoice.

    Parameters
    ----------
    charges : List[Charge]
    num_units : int
    gmv : Optional[float], optional

    Returns
    -------
    Dict[str, Any]
    """
    billing_charges = []
    total_amount_due = 0.0
    # compute total amount due
    for ch in charges:
        discount = None
        discount = find_discounts(ch.id, discounts)
        for _d in discount:
            if _d.charge_discount_amount_type == "$":
                _d.charge_discount_amount = _d.charge_discount_amount * 12
        # vars
        _chtype = ""
        _chbase, _chtotal_with_iva = 0, 0.0
        if ch.charge_type == ChargeType.SAAS_FEE:
            if ch.charge_description:
                _chtype = ch.charge_description
            else:
                _chtype = "Servicio de Software - Operaciones"
            _chbase = num_units
            ch.charge_amount = ch.charge_amount * 12  # Anual Charge
            _chtype, _chtotal_with_iva = compute_fee_charge(
                _chtype, ch, num_units, discount
            )
        elif ch.charge_type == ChargeType.FINANCE_FEE:
            if ch.charge_description:
                _chtype = ch.charge_description
            else:
                _chtype = "Servicio de Software - Finanzas"
            _chbase = num_units
            _chtype, _chtotal_with_iva = compute_fee_charge(
                _chtype, ch, num_units, discount
            )
        elif ch.charge_type == ChargeType.REPORTS:
            _chbase = 1 * 12  # Reports Anual Charge
            _chtype, _chtotal_with_iva = compute_reports_charge(ch, discount)
        elif ch.charge_type == ChargeType.MARKETPLACE_COMMISSION:
            continue
        elif ch.charge_type == ChargeType.INVOICE_FOLIO:
            if folio_count > (200 * num_units):
                if ch.charge_description:
                    _chtype = ch.charge_description
                else:
                    _chtype = "Folios Adicionales Facturación"
                _chbase = folio_count - (200 * num_units)
                _chtotal_with_iva = compute_folios_charge(_chbase)
            else:
                continue
        # format response
        bill_ch = {
            "charge_id": ch.id,
            "charge_type": _chtype,
            "charge_base_quantity": _chbase,
            "charge_amount": (
                round(_chtotal_with_iva / _chbase, 4)
                if ch.charge_amount_type == "$"
                else ch.charge_amount
            ),
            "charge_amount_type": ch.charge_amount_type,
            "total_charge": _chtotal_with_iva,
            "currency": ch.currency,
        }
        total_amount_due += _chtotal_with_iva
        billing_charges.append(bill_ch)
    return {
        "total": total_amount_due,
        "charges": billing_charges,
    }


def get_items_v2(total_charges: Dict[Any, Any]):
    try:
        item_list = []
        for charge in total_charges["charges"]:
            if (
                "Servicio de Software" in charge["charge_type"]
                or "Reporte" in charge["charge_type"]
            ):
                unit_code = "E48"
                sat_code = "81161501"
                Quantity = charge["charge_base_quantity"]  # type: ignore
                UnitPrice = round((charge["total_charge"] / Quantity) / (1 + 0.16), 4)  # type: ignore
            else:
                unit_code = "A9"
                sat_code = "80141600"

                Quantity = charge["charge_base_quantity"]  # type: ignore
                UnitPrice = round((charge["total_charge"] / Quantity) / (1 + 0.16), 4)  # type: ignore

            Subtotal = round(UnitPrice * Quantity, 2)  # type: ignore

            item = Item(
                ProductCode=sat_code,  # type: ignore
                Description=charge["charge_type"],  # type: ignore
                UnitCode=unit_code,  # type: ignore
                Subtotal=Subtotal,
                Quantity=Quantity,
                TaxObject="02",
                Total=round(Subtotal * 1.16, 4),  # type: ignore
                Taxes=[
                    SatTaxes(
                        Total=round(0.16 * Subtotal, 4),
                        Name="IVA",
                        Base=round(Subtotal, 4),
                        Rate=0.16,  # type: ignore
                        IsRetention=False,
                    )
                ],
                UnitPrice=UnitPrice,
            )
            item_list.append(item)
        return item_list
    except Exception as e:
        logger.error(e)
        raise GQLApiException(
            msg="Error to build sat items",
            error_code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
        )


def is_month_last_day(current_date: datetime) -> bool:
    last_day = calendar.monthrange(current_date.year, current_date.month)[1]
    return current_date.day == last_day


async def get_alima_billing_v2(
    _db: Database, current_date: datetime, is_last_day: bool
) -> List[PaidAccount]:
    """Get alima monthly billing accounts for the current date."""
    try:
        if is_last_day:
            query = """
                WITH current_bpm AS (
                    WITH unique_bpm AS (
                        SELECT bpm.paid_account_id, min(bpm.id::varchar)::uuid as id
                        FROM billing_payment_method bpm
                        WHERE bpm.active = 't'
                        GROUP BY 1
                    )
                    SELECT bpm.* from billing_payment_method bpm
                    JOIN unique_bpm USING ("id")
                    WHERE active = 't'
                )
                SELECT
                    pa.*
                FROM paid_account pa
                JOIN supplier_business sb ON sb.id = pa.customer_business_id
                JOIN current_bpm cbpm ON cbpm.paid_account_id = pa.id
                WHERE EXTRACT(DAY FROM pa.created_at) >= EXTRACT(DAY FROM CAST(:current_date AS TIMESTAMP))
                AND pa.account_name IN ('alima_comercial','alima_pro')
                AND sb.active = 'true'
                AND cbpm.payment_provider = 'spei_bbva'
        """
        else:
            query = """
                WITH current_bpm AS (
                    WITH unique_bpm AS (
                        SELECT bpm.paid_account_id, min(bpm.id::varchar)::uuid as id
                        FROM billing_payment_method bpm
                        WHERE bpm.active = 't'
                        GROUP BY 1
                    )
                    SELECT bpm.* from billing_payment_method bpm
                    JOIN unique_bpm USING ("id")
                    WHERE active = 't'
                )
                SELECT
                    pa.*
                FROM paid_account pa
                JOIN supplier_business sb ON sb.id = pa.customer_business_id
                JOIN current_bpm cbpm ON cbpm.paid_account_id = pa.id
                WHERE EXTRACT(DAY FROM pa.created_at) = EXTRACT(DAY FROM CAST(:current_date AS TIMESTAMP))
                AND pa.account_name IN ('alima_comercial','alima_pro')
                AND sb.active = 'true'
                AND cbpm.payment_provider = 'spei_bbva'
        """
        alima_billing_invoices = await _db.fetch_all(
            query, {"current_date": current_date}
        )

        if not alima_billing_invoices:
            return []
        return [PaidAccount(**dict(r)) for r in alima_billing_invoices]
    except Exception as e:
        logger.error(e)
        raise Exception("Error to get alima invoices")


async def get_alima_anual_billing_v2(
    _db: Database, current_date: datetime, is_last_day: bool
) -> List[PaidAccount]:
    try:
        if is_last_day:
            query = """
                WITH current_bpm AS (
                    WITH unique_bpm AS (
                        SELECT bpm.paid_account_id, min(bpm.id::varchar)::uuid as id
                        FROM billing_payment_method bpm
                        WHERE bpm.active = 't'
                        GROUP BY 1
                    )
                    SELECT bpm.* from billing_payment_method bpm
                    JOIN unique_bpm USING ("id")
                    WHERE active = 't'
                )
                SELECT
                    pa.*
                FROM paid_account pa
                JOIN supplier_business sb ON sb.id = pa.customer_business_id
                JOIN current_bpm cbpm ON cbpm.paid_account_id = pa.id
                WHERE EXTRACT(DAY FROM pa.created_at) >= EXTRACT(DAY FROM CAST(:current_date AS TIMESTAMP))
                AND pa.account_name IN ('alima_comercial_anual','alima_pro_anual')
                AND sb.active = 'true'
                AND cbpm.payment_provider = 'spei_bbva'
        """
        else:
            query = """
                WITH current_bpm AS (
                    WITH unique_bpm AS (
                        SELECT bpm.paid_account_id, min(bpm.id::varchar)::uuid as id
                        FROM billing_payment_method bpm
                        WHERE bpm.active = 't'
                        GROUP BY 1
                    )
                    SELECT bpm.* from billing_payment_method bpm
                    JOIN unique_bpm USING ("id")
                    WHERE active = 't'
                )
                SELECT
                    pa.*
                FROM paid_account pa
                JOIN supplier_business sb ON sb.id = pa.customer_business_id
                JOIN current_bpm cbpm ON cbpm.paid_account_id = pa.id
                WHERE EXTRACT(DAY FROM pa.created_at) = EXTRACT(DAY FROM CAST(:current_date AS TIMESTAMP))
                AND pa.account_name IN ('alima_comercial_anual','alima_comercial_anual')
                AND sb.active = 'true'
                AND cbpm.payment_provider = 'spei_bbva'
        """
        alima_billing_invoices = await _db.fetch_all(
            query, {"current_date": current_date}
        )

        if not alima_billing_invoices:
            return []
        return [PaidAccount(**dict(r)) for r in alima_billing_invoices]
    except Exception as e:
        logger.error(e)
        raise Exception("Error to get alima anual invoice' accounts")


# ---------------------------------------------------------------------
# Create supplier billing invoice
# ---------------------------------------------------------------------
async def send_create_supplier_billing_invoice_v2(
    info: InjectedStrawberryInfo, password: str
) -> bool:
    logger.info("Starting send daily alima invoice v2 ...")
    logger.info("Get_billing info...")
    _db = info.context["db"].sql
    current_date = datetime.now(timezone.utc).replace(tzinfo=None)
    if password != RETOOL_SECRET_BYPASS:
        logger.info("Access Denied")
        raise Exception("Access Denied")
    # FETCHING ONLY SPEI BBVA customers
    billings = await get_alima_billing_v2(_db, current_date, is_month_last_day(current_date))  # type: ignore
    anual_billings = await get_alima_anual_billing_v2(_db, current_date, is_month_last_day(current_date))  # type: ignore
    if not billings and not anual_billings:
        logger.info("There are no billing to invoiced")
        return True
    billing_flags = []
    if billings:
        billing_flags.append(
            await create_supplier_billing_invoice_v2(
                billings=billings, _info=info, current_date=current_date
            )
        )
    else:
        billing_flags.append(True)
    # if anual_billings:
    #     billing_flags.append(
    #         await create_supplier_anual_billing_invoice_v2(
    #             billings=anual_billings, _info=info, current_date=current_date
    #         )
    #     )
    # else:
    #     billing_flags.append(True)
    # return True - if all billing flags are True
    return all(billing_flags)


async def send_create_alima_invoice_v2_wrapper(password: str) -> bool:
    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    # Permite conectar a la db
    _resp = await send_create_supplier_billing_invoice_v2(_info, password)
    return _resp


async def create_supplier_billing_invoice_v2(
    billings: List[PaidAccount], _info: InjectedStrawberryInfo, current_date: datetime
) -> bool:
    """Create a Monthly Supplier Billing Invoice.

    Parameters
    ----------
    supplier_business_id : uuid.UUID
    invoice_month : str
    invoice_create_date : date
    gmv : Optional[float], optional

    Returns
    -------
    bool

    Raises
    ------
    Exception
    """
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    # get supplier information
    acc_repo = AlimaAccountRepository(_info)  # type: ignore
    reports: List[BillingReport] = []
    for pa in billings:
        supplier = await fetch_supplier_business_info(_db, pa.customer_business_id)
        if not supplier:
            continue
        acc_charges = await acc_repo.fetch_charges(pa.id)
        if not acc_charges:
            logger.error("No charges available for this Paid Account!")
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="No charges available for this Paid Account!",
                )
            )
            continue
        acc_discount_charges = await acc_repo.fetch_discounts_charges(pa.id)
        # calculate charges
        total_charges = None
        last_invoice_date = await get_last_invoice_date(_db, pa.id)
        now = datetime.utcnow()
        if last_invoice_date and now.strftime("%m-%Y") == last_invoice_date.strftime(
            "%m-%Y"
        ):
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="Invoice already created for this month!",
                )
            )
            continue
        folio_count = await get_month_invoice_folios(
            _db, pa.customer_business_id, last_invoice_date
        )
        if pa.account_name == "alima_comercial":
            total_charges = compute_alima_comercial_total_amount_due(
                acc_charges, acc_discount_charges, pa.active_cedis, folio_count
            )
        if pa.account_name == "alima_pro":
            total_charges = compute_alima_comercial_total_amount_due(
                acc_charges, acc_discount_charges, pa.active_cedis, folio_count
            )
        if not total_charges:
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="Error calculating charges!",
                )
            )
            continue
        if total_charges["total"] == 0.0:
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="No charges available for this Paid Account!",
                )
            )
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        supp_business_account_repo = SupplierBusinessAccountRepository(_info)  # type: ignore

        supp_bus_acc_info = await supp_business_account_repo.fetch(
            pa.customer_business_id
        )
        supp_bus_acc = SupplierBusinessAccount(**supp_bus_acc_info)  # type: ignore
        items = get_items_v2(total_charges)
        payment_method = InvoiceType.PUE.value
        global_information = None
        client = Customer(
            Email=supp_bus_acc.email,
            Address=CustomerAddress(
                ZipCode=supp_bus_acc.mx_zip_code,  # type: ignore
            ),
            Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
            Name=supp_bus_acc.legal_business_name,  # type: ignore
            CfdiUse="G03",
            FiscalRegime=supp_bus_acc.mx_sat_regimen,
            TaxZipCode=supp_bus_acc.mx_zip_code,
        )
        if client.Rfc != "XAXX010101000" and client.Rfc != "XEXX010101000":
            if not pa.invoicing_provider_id:
                new_client = await facturma_api.new_client(client=client)
                if new_client.get("status") != "ok":
                    reports.append(
                        BillingReport(
                            paid_account_id=pa.id,
                            supplier=supplier["name"],
                            status="Error",
                            reason=new_client.get("msg", "Error to create client"),
                        )
                    )
                    continue
                client.Id = new_client["data"]["Id"]
                if not await edit_paid_account(
                    db=_db,
                    paid_account_id=pa.id,
                    invoicing_provider_id=new_client["data"]["Id"],
                ):
                    reports.append(
                        BillingReport(
                            paid_account_id=pa.id,
                            supplier=supplier["name"],
                            status="Error",
                            reason="Error to add invoicing provider id",
                        )
                    )
                    continue
        else:
            issue_date = datetime.utcnow() - timedelta(hours=6)
            payment_method = "PUE"
            global_information = GlobalInformationFacturama(
                Periodicity="01",
                Months=issue_date.strftime("%m"),
                Year=issue_date.strftime("%Y"),
            )
            if client.Rfc == "XAXX010101000":
                client = Customer(
                    Email=supp_bus_acc.email,
                    Address=CustomerAddress(
                        ZipCode=supp_bus_acc.mx_zip_code,
                    ),
                    Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
                    Name="PUBLICO EN GENERAL",
                    CfdiUse="S01",
                    FiscalRegime="616",
                    TaxZipCode=ALIMA_EXPEDITION_PLACE,
                )
            # else:
            #     client = Customer(
            #         Email=supp_bus_acc.email,
            #         Address=CustomerAddress(
            #             ZipCode=supp_bus_acc.mx_zip_code,
            #         ),
            #         Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
            #         Name=supp_bus_acc.legal_business_name,  # type: ignore
            #         CfdiUse="S01",
            #         FiscalRegime="616",
            #         TaxZipCode=ALIMA_EXPEDITION_PLACE,
            #     )
        internal_invoice = FacturamaInternalInvoice(
            Receiver=client,
            CfdiType="I",
            NameId="1",
            ExpeditionPlace=ALIMA_EXPEDITION_PLACE,
            # PaymentForm="01" if payment_method else "99",
            # PaymentMethod=payment_method if payment_method else "PPD",
            PaymentForm=PaymentForm.TRANSFER.value,
            PaymentMethod=payment_method,
            Items=items,
            GlobalInformation=global_information,
        )
        internal_invoice_create = facturma_api.new_internal_invoice(
            invoice=internal_invoice
        )
        if internal_invoice_create.get("status") != "ok":
            logger.error(internal_invoice_create["msg"])
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason=internal_invoice_create.get(
                        "msg", "Error to create invoice"
                    ),
                )
            )
            continue
        print(internal_invoice_create["data"].Id)

        # fetch invoice files
        xml_file = await facturma_api.get_xml_internal_invoice_by_id(
            id=internal_invoice_create["data"].Id
        )
        pdf_file = await facturma_api.get_pdf_internal_invoice_by_id(
            id=internal_invoice_create["data"].Id
        )
        formatted_date = current_date.strftime("%m-%Y")
        # create billing invoice
        b_invoice_id = await create_billing_invoice(
            _db,
            pa.id,
            "México",
            formatted_date,
            total_charges["total"],
            "MXN",
            InvoiceStatusType.ACTIVE,
            current_date,
            uuid.UUID(internal_invoice_create["data"].Complement.TaxStamp.Uuid),
            payment_method=PaymentFormFacturama[
                internal_invoice_create["data"].PaymentMethod
            ],
        )

        # create billing invoice charges
        b_invoice_charges = await create_billing_invoice_charges(
            _db, b_invoice_id, total_charges["charges"], current_date
        )
        # insert invoice in DB
        await save_internal_invoice_info(
            db=_db,
            billing_invoice_id=b_invoice_id,
            pdf_file=pdf_file["data"],
            xml_file=xml_file["data"],
            invoice_id=internal_invoice_create["data"].Id,
            invoice_number=internal_invoice_create["data"].Folio,  # type: ignore
            result=internal_invoice_create["data"].Result,
        )
        # insert invoice in DB
        pdf_file_str = base64.b64encode(pdf_file["data"]).decode("utf-8")
        xml_file_str = base64.b64encode(xml_file["data"]).decode("utf-8")
        attcht = [
            {
                "content": pdf_file_str,
                "filename": f"Factura Alima-{formatted_date}.pdf",
                "mimetype": "application/pdf",
            },
            {
                "content": xml_file_str,
                "filename": f"Factura Alima-{formatted_date}.xml",
                "mimetype": "application/xml",
            },
        ]
        if client.Rfc != "XAXX010101000" and client.Rfc != "XEXX010101000":
            if not await send_new_alima_invoice_notification_v2(
                email_to=[supp_bus_acc.email, "pagosyfacturas@alima.la"],  # type: ignore
                name=supplier["name"],
                attchs=attcht,
            ):
                reports.append(
                    BillingReport(
                        paid_account_id=pa.id,
                        supplier=supplier["name"],
                        status="Error",
                        reason="Error sending email",
                    )
                )
        else:
            if not await send_new_alima_invoice_notification_v2(
                email_to=["pagosyfacturas@alima.la"],  # type: ignore
                name=supplier["name"],
                attchs=attcht,
            ):
                reports.append(
                    BillingReport(
                        paid_account_id=pa.id,
                        supplier=supplier["name"],
                        status="Error",
                        reason="Error sending email",
                    )
                )

        # show results
        logger.info("Finished creating Supplier Billing Invoice")
        logger.info(
            "\n".join(
                [
                    "-----",
                    f"Supplier Business ID: {pa.customer_business_id}",
                    f"Paid Account ID: {pa.id}",
                    f"Billing Invoice ID: {b_invoice_id}",
                    f"Billing Invoice Charges IDs: {b_invoice_charges}",
                    f"Billing Invoice Total: {total_charges['total']}",
                    "-----",
                ]
            )
        )
        reports.append(
            BillingReport(
                paid_account_id=pa.id,
                supplier=supplier["name"],
                status="Ok",
                reason="Mensual Invoice created successfully",
            )
        )
    if reports:
        rep_dict = []
        for r in reports:
            rep_dict.append(r.__dict__)
        df = pd.DataFrame(rep_dict)
        html_table = df.to_html(index=False)
    return True


async def create_supplier_anual_billing_invoice_v2(
    billings: List[PaidAccount], _info: InjectedStrawberryInfo, current_date: datetime
) -> bool:
    """Create a Anual Supplier Billing Invoice.

    Parameters
    ----------
    supplier_business_id : uuid.UUID
    invoice_month : str
    invoice_create_date : date
    gmv : Optional[float], optional

    Returns
    -------
    bool

    Raises
    ------
    Exception
    """
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    # get supplier information
    acc_repo = AlimaAccountRepository(_info)  # type: ignore
    reports: List[BillingReport] = []
    for pa in billings:
        supplier = await fetch_supplier_business_info(_db, pa.customer_business_id)
        if not supplier:
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    status="Error",
                    reason="No supplier information available",
                )
            )
            continue
        acc_charges = await acc_repo.fetch_charges(pa.id)
        if not acc_charges:
            logger.error("No charges available for this Paid Account!")
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="No charges available for this Paid Account!",
                )
            )
            continue
        acc_discount_charges = await acc_repo.fetch_discounts_charges(pa.id)
        # calculate charges
        total_charges = None
        last_invoice_date = await get_last_invoice_date(_db, pa.id)
        # [TODO] Check if the invoice was created for this year
        now = datetime.utcnow()
        if last_invoice_date and now.strftime("%Y") == last_invoice_date.strftime("%Y"):
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="Invoice already created for this year!",
                )
            )
            continue
        folio_count = await get_month_invoice_folios(
            _db, pa.customer_business_id, last_invoice_date
        )
        if pa.account_name == "alima_comercial_anual":
            total_charges = compute_anual_alima_comercial_total_amount_due(
                acc_charges, acc_discount_charges, pa.active_cedis, folio_count
            )
        # [TODO] - review Alima Pro Anual
        # if pa.account_name == "alima_pro":
        #     total_charges = compute_anual_alima_comercial_total_amount_due(
        #         acc_charges, acc_discount_charges, pa.active_cedis, folio_count
        #     )
        if not total_charges:
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="Error calculating charges!",
                )
            )
            continue
        if total_charges["total"] == 0.0:
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="No charges available for this Paid Account!",
                )
            )
            continue
        facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
        supp_business_account_repo = SupplierBusinessAccountRepository(_info)  # type: ignore

        supp_bus_acc_info = await supp_business_account_repo.fetch(
            pa.customer_business_id
        )
        supp_bus_acc = SupplierBusinessAccount(**supp_bus_acc_info)  # type: ignore
        items = get_items_v2(total_charges)
        if not pa.invoicing_provider_id:
            client = Customer(
                Email=supp_bus_acc.email,
                Address=CustomerAddress(
                    ZipCode=supp_bus_acc.mx_zip_code,  # type: ignore
                ),
                Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
                Name=supp_bus_acc.legal_business_name,  # type: ignore
                CfdiUse="G03",
                FiscalRegime=supp_bus_acc.mx_sat_regimen,
                TaxZipCode=supp_bus_acc.mx_zip_code,
            )

            new_client = await facturma_api.new_client(client=client)
            if new_client.get("status") != "ok":
                reports.append(
                    BillingReport(
                        paid_account_id=pa.id,
                        supplier=supplier["name"],
                        status="Error",
                        reason=new_client.get("msg", "Error to create client"),
                    )
                )
                continue
            client.Id = new_client["data"]["Id"]
            if not await edit_paid_account(
                db=_db,
                paid_account_id=pa.id,
                invoicing_provider_id=new_client["data"]["Id"],
            ):
                reports.append(
                    BillingReport(
                        paid_account_id=pa.id,
                        supplier=supplier["name"],
                        status="Error",
                        reason="Error to add invoicing provider id",
                    )
                )
                continue

        internal_invoice = FacturamaInternalInvoice(
            Receiver=Customer(
                Name=supp_bus_acc.legal_business_name,  # type: ignore
                Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
                FiscalRegime=supp_bus_acc.mx_sat_regimen,
                TaxZipCode=supp_bus_acc.mx_zip_code,  # type: ignore
                CfdiUse="S01",
            ),
            CfdiType="I",
            NameId="1",
            ExpeditionPlace=ALIMA_EXPEDITION_PLACE,
            PaymentForm="99",
            PaymentMethod="PPD",
            Items=items,
        )
        internal_invoice_create = facturma_api.new_internal_invoice(
            invoice=internal_invoice
        )
        if internal_invoice_create.get("status") != "ok":
            logger.error(internal_invoice_create["msg"])
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason=internal_invoice_create.get(
                        "msg", "Error to create invoice"
                    ),
                )
            )
            continue
        print(internal_invoice_create["data"].Id)

        # fetch invoice files
        xml_file = await facturma_api.get_xml_internal_invoice_by_id(
            id=internal_invoice_create["data"].Id
        )
        pdf_file = await facturma_api.get_pdf_internal_invoice_by_id(
            id=internal_invoice_create["data"].Id
        )
        formatted_date = current_date.strftime("%m-%Y")
        # create billing invoice
        b_invoice_id = await create_billing_invoice(
            _db,
            pa.id,
            "México",
            formatted_date,
            total_charges["total"],
            "MXN",
            InvoiceStatusType.ACTIVE,
            current_date,
            uuid.UUID(internal_invoice_create["data"].Complement.TaxStamp.Uuid),
            payment_method=PaymentFormFacturama[
                internal_invoice_create["data"].PaymentMethod
            ],
        )

        # create billing invoice charges
        b_invoice_charges = await create_billing_invoice_charges(
            _db, b_invoice_id, total_charges["charges"], current_date
        )
        # insert invoice in DB
        await save_internal_invoice_info(
            db=_db,
            billing_invoice_id=b_invoice_id,
            pdf_file=pdf_file["data"],
            xml_file=xml_file["data"],
            invoice_id=internal_invoice_create["data"].Id,
            invoice_number=internal_invoice_create["data"].Folio,  # type: ignore
            result=internal_invoice_create["data"].Result,
        )
        # insert invoice in DB
        pdf_file_str = base64.b64encode(pdf_file["data"]).decode("utf-8")
        attcht = [
            {
                "content": pdf_file_str,
                "filename": f"Factura Alima-{formatted_date}.pdf",
                "mimetype": "application/pdf",
            },
        ]
        if not await send_new_alima_invoice_notification_v2(
            email_to=[supp_bus_acc.email, "pagosyfacturas@alima.la"],  # type: ignore
            name=supplier["name"],
            attchs=attcht,
        ):
            reports.append(
                BillingReport(
                    paid_account_id=pa.id,
                    supplier=supplier["name"],
                    status="Error",
                    reason="Error sending email",
                )
            )
            continue

        # show results
        logger.info("Finished creating Supplier Billing Invoice")
        logger.info(
            "\n".join(
                [
                    "-----",
                    f"Supplier Business ID: {pa.customer_business_id}",
                    f"Paid Account ID: {pa.id}",
                    f"Billing Invoice ID: {b_invoice_id}",
                    f"Billing Invoice Charges IDs: {b_invoice_charges}",
                    f"Billing Invoice Total: {total_charges['total']}",
                    "-----",
                ]
            )
        )
        reports.append(
            BillingReport(
                paid_account_id=pa.id,
                supplier=supplier["name"],
                status="Ok",
                reason="Anual Invoice created successfully",
            )
        )
    if reports:
        rep_dict = []
        for r in reports:
            rep_dict.append(r.__dict__)
        df = pd.DataFrame(rep_dict)
        html_table = df.to_html(index=False)
    return True


async def main():
    try:
        logger.info("Started creating Daily Supplier Billing Invoice (V2)")
        await db_startup()
        password = RETOOL_SECRET_BYPASS
        fl = await send_create_alima_invoice_v2_wrapper(password)
        if fl:
            logger.info("Finished creating Daily Supplier Billing Invoice (V2)")
        await db_shutdown()
    except Exception as e:
        logger.error(e)


if __name__ == "__main__":
    asyncio.run(main())
