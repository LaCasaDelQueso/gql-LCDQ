""" Script to Create a Supplier Invoice given its defined charges.

This script does the following:

1. Computes the total amount due for the invoice based on the charges and arguments.
2. Creates a record in the `billing_invoice` table.
3. Creates a record in the `billing_invoice_charge` table for each charge.
4. Creates a record in the `billing_invoice_paystatus` table with status `unpaid`.

Usage:
    cd projects/gqlapi/
    python -m gqlapi.scripts.alima_account.create_supplier_invoice --help
"""

import asyncio
import argparse
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import json
import logging
from types import NoneType
from typing import Any, Dict, List, Optional
import uuid
from gqlapi.lib.clients.clients.facturamaapi.facturama import (
    Customer,
    CustomerAddress,
    FacturamaClientApi,
    FacturamaInternalInvoice,
    GlobalInformationFacturama,
    Item,
    PaymentFormFacturama,
    SatTaxes,
)

from databases import Database
from gqlapi.domain.models.v2.alima_business import Charge, ChargeDiscount
from gqlapi.domain.models.v2.supplier import SupplierBusinessAccount
from gqlapi.domain.models.v2.alima_business import PaidAccount
from gqlapi.config import ALIMA_EXPEDITION_PLACE, FACT_PWD, FACT_USR, ENV as DEV_ENV
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.services.mails import send_new_alima_invoice_notification
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository

from gqlapi.lib.environ.environ.environ import Environment, get_env
from gqlapi.scripts.billing.create_daily_alima_invoice_v2 import (
    compute_alima_comercial_total_amount_due,
    compute_fee_charge,
    compute_reports_charge,
    edit_paid_account,
    find_discounts,
    get_items_v2,
    get_last_invoice_date,
    get_month_invoice_folios,
)
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.lib.logger.logger.basic_logger import get_logger
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


logger = get_logger(
    "scripts.create_supplier_invoice", logging.INFO, Environment(get_env())
)


# arg parser
def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Create new Supplier Billing Invoice")
    parser.add_argument(
        "--supplier_business_id",
        help="Supplier Business ID (UUID)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--invoice-month",
        help="Invoice Month (MM-YYYY)",
        type=str,
        default=None,
        required=True,
    )
    parser.add_argument(
        "--gmv",
        help="GMV in MXN",
        type=float,
        default=None,
        required=False,
    )
    return parser.parse_args()


# ---------------------------------------------------------------------
# Fetch info functions
# ---------------------------------------------------------------------


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
        logging.warning("Not able to retrieve supplier information")
        return {}
    if not supplier["active"]:
        logging.warning("Supplier Business is NOT ACTIVE!")
        return {}
    logging.info("Got Supplier Business info")
    return dict(supplier)


async def get_paid_account(
    db: Database,
    supplier_business_id: uuid.UUID,
) -> Dict[Any, Any] | NoneType:
    """Get a new paid account.

    Parameters
    ----------
    db : Database
    supplier_business_id : uuid.UUID

    Returns
    -------
    uuid.UUID
    """
    # verify if exists
    _id = await db.fetch_one(
        """
        SELECT * FROM paid_account
        WHERE customer_business_id = :customer_business_id
        """,
        {"customer_business_id": supplier_business_id},
    )

    return dict(_id) if _id else None


async def get_alima_bot(info: InjectedStrawberryInfo) -> uuid.UUID:
    core_repo = CoreUserRepository(info=info)  # type: ignore
    tmp = await core_repo.get_by_email("admin")
    admin_user = tmp.id
    if not admin_user:
        raise Exception("Error getting Alima admin bot user")
    return admin_user


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
            "status": DataTypeDecoder.get_orden_paystatus_key(
                PayStatusType.UNPAID.value
            ),
            "created_at": created_at,
        },
    )
    logging.info("Created Billing Invoice")
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


async def get_month_orders(
    db: Database, supplier_business_id: uuid.UUID, month: int
) -> List[Dict[Any, Any]]:
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
    # create billing invoice charges

    orders_list = []
    orders = await db.fetch_all(
        """
            WITH orden_details_view as (
            -- get last status from orden
            WITH last_orden_status AS (
                WITH rcos AS (
                    SELECT
                        orden_id,
                        status,
                        ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
                    FROM orden_status
            )
                SELECT * FROM rcos WHERE row_num = 1
            ),
            -- get last version of orden
            last_orden_version AS (
                WITH last_upd AS (
                    SELECT
                        orden_id,
                        id as orden_details_id,
                        ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
                    FROM orden_details
                )
                SELECT * FROM last_upd WHERE row_num = 1
            )
            SELECT
                orden_details.*,
                los.status
            FROM last_orden_version lov
            JOIN last_orden_status los ON los.orden_id = lov.orden_id
            JOIN orden_details ON orden_details.id = lov.orden_details_id
    )
    select
        orden_id,
        delivery_date,
        delivery_time,
        rbu.name as "restaurant_business",
        rb.branch_name as "restaurant_branch",
        rbu.active as "resto_from_marketplace",
        su.unit_name as "supplier",
        status,
        total as subtotal,
        version,
        (orden_details_view.created_at - interval '6 hours') created_at
    from orden_details_view
    join restaurant_branch rb on rb.id = orden_details_view.restaurant_branch_id
    join restaurant_business rbu on rbu.id = rb.restaurant_business_id
    join supplier_unit su on su.id = orden_details_view.supplier_unit_id
    join supplier_business sb on sb.id = su.supplier_business_id
    where true
    AND EXTRACT(MONTH FROM delivery_date) = :month
    and sb.id = :supplier_business_id and sb.active = 'true'
    and status != 'canceled'
    order by created_at desc
            """,
        {
            "supplier_business_id": supplier_business_id,
            "month": int(month),
        },
    )
    if orders:
        for order in orders:
            orders_list.append(dict(order))
    return orders_list


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


def compute_standard_amount_due(
    charges: List[Charge],
    discounts: List[ChargeDiscount],
    num_units: int,
    orders: int,
    gmv: Optional[float] = None,
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
        if ch.charge_type == ChargeType.SAAS_FEE:
            if orders >= 30:
                _chtype = "Servicio de Software"
                _chbase = num_units
                _chtype, _chtotal_with_iva = compute_fee_charge(
                    _chtype, ch, num_units, discount
                )
            else:
                continue
        if ch.charge_type == ChargeType.FINANCE_FEE:
            if orders >= 30:
                _chtype = "Servicio de Software - Finanzas"
                _chbase = num_units
                _chtype, _chtotal_with_iva = compute_fee_charge(
                    _chtype, ch, num_units, discount
                )
            else:
                continue
        if ch.charge_type == ChargeType.REPORTS:
            _chbase = 1
            _chtype, _chtotal_with_iva = compute_reports_charge(ch, discount)
        if ch.charge_type == ChargeType.MARKETPLACE_COMMISSION:
            # marketplace fee
            if gmv is None:
                continue
            _chtype = "Comisión de Marketplace"
            _chbase = gmv
            # Mkt take rate * GMV  +  16% IVA
            _chtotal_with_iva = _chbase * ch.charge_amount * 1.16
        if ch.charge_type == ChargeType.INVOICE_FOLIO:
            continue
        # format response
        bill_ch = {
            "charge_id": ch.id,
            "charge_type": _chtype,  # type: ignore
            "charge_base_quantity": _chbase,  # type: ignore
            "charge_amount": ch.charge_amount,
            "charge_amount_type": ch.charge_amount_type,
            "total_charge": _chtotal_with_iva,  # type: ignore
            "currency": ch.currency,
        }
        total_amount_due += _chtotal_with_iva  # type: ignore
        billing_charges.append(bill_ch)
    return {
        "total": total_amount_due,
        "charges": billing_charges,
    }


def get_items(total_charges: Dict[Any, Any]):
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

                Quantity = 1  # type: ignore
                UnitPrice = round(charge["total_charge"] / (1 + 0.16), 4)  # type: ignore

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
        logging.error(e)
        raise GQLApiException(
            msg="Error to build sat items",
            error_code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
        )


def get_commission(charges: List[Charge]):
    try:
        for charge in charges:
            if charge.charge_type == ChargeType.MARKETPLACE_COMMISSION:
                return float(charge.charge_amount)
        return 0
    except Exception as e:
        logging.error(e)
        raise GQLApiException(
            msg="Error to get commission",
            error_code=GQLApiErrorCodeType.FACTURAMA_ERROR_BUILD.value,
        )


def get_commission_column(row: pd.Series, commision: float):
    if row["resto_from_marketplace"] == 1:
        return commision
    else:
        return 0


def get_orders_xls_file(orders: List[Dict[Any, Any]], commision: float):
    df = pd.DataFrame(orders)
    if not df.empty:
        # Create the new column based on the "validation" column
        df["porcentaje_comision"] = df.apply(
            lambda row: get_commission_column(row, commision=commision), axis=1
        )
        # df["porcentaje_comision"] = commision
        df["commision"] = df["porcentaje_comision"] * df["subtotal"]
        total_sum = df["commision"].sum()
        total_orders = df["resto_from_marketplace"].value_counts().get(True, 0)  # type: ignore
        # Create a new row with the total sum
        total_row = pd.Series(
            {
                "restaurant_branch": "Ordenes de Marketplace",
                "resto_from_marketplace": total_orders,
                "porcentaje_comision": "TOTAL",
                "commision": total_sum,
            }
        )
        # Append the new row to the DataFrame
        df = pd.concat([df, total_row.to_frame().T], ignore_index=False)

    with pd.ExcelWriter("output_variable.xlsx", engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False)
    with open("output_variable.xlsx", "rb") as file:
        xls_file = base64.b64encode(file.read()).decode()
    return xls_file


# ---------------------------------------------------------------------
# Create supplier billing invoice
# ---------------------------------------------------------------------


async def create_supplier_billing_invoice(
    supplier_business_id: uuid.UUID,
    invoice_month: str,
    invoice_create_date: datetime,
    month: int,
    gmv: Optional[float] = None,
) -> bool:
    """Create a Supplier Billing Invoice.

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

    _info = InjectedStrawberryInfo(SQLDatabase, MongoDatabase)
    await db_startup()
    _db = _info.context["db"].sql
    _mongo = _info.context["db"].mongo
    if not _db or _mongo is None:
        raise Exception("Error initializing database")
    # get supplier information
    supplier = await fetch_supplier_business_info(_db, supplier_business_id)
    if not supplier:
        return False
    # create paid account
    paid_account_obj = await get_paid_account(_db, supplier_business_id)

    if not paid_account_obj:
        raise Exception("Paid Account is not available!")
    else:
        paid_account = PaidAccount(**paid_account_obj)
    # get charges
    acc_repo = AlimaAccountRepository(_info)  # type: ignore
    acc_charges = await acc_repo.fetch_charges(paid_account.id)
    if not acc_charges:
        raise Exception("No charges available for this Paid Account!")
    acc_discount_charges = await acc_repo.fetch_discounts_charges(paid_account.id)
    # if paid_account.account_name =="standard":

    xls_file_attcht = None
    total_charges = {}
    items = None
    # compute total amount due & billing charges
    if paid_account.account_name == "standard":
        orders = await get_month_orders(_db, supplier_business_id, month)
        if orders:
            commision = get_commission(acc_charges)
            xls_file = get_orders_xls_file(orders=orders, commision=commision)
            xls_file_attcht = {
                "content": xls_file,
                "filename": "Ordenes",
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        total_charges = compute_standard_amount_due(
            acc_charges, acc_discount_charges, supplier["units"], len(orders), gmv
        )
        items = get_items(total_charges)
    if paid_account.account_name == "alima_comercial":
        last_invoice_date = await get_last_invoice_date(_db, paid_account.id)
        folio_count = await get_month_invoice_folios(
            _db, paid_account.customer_business_id, last_invoice_date
        )
        total_charges = compute_alima_comercial_total_amount_due(
            acc_charges, acc_discount_charges, supplier["units"], folio_count
        )
        items = get_items_v2(total_charges)
    if paid_account.account_name == "alima_pro":
        last_invoice_date = await get_last_invoice_date(_db, paid_account.id)
        folio_count = await get_month_invoice_folios(
            _db, paid_account.customer_business_id, last_invoice_date
        )
        total_charges = compute_alima_comercial_total_amount_due(
            acc_charges, acc_discount_charges, supplier["units"], folio_count
        )
        items = get_items_v2(total_charges)
    if total_charges["total"] == 0.0:
        raise Exception("No charges available for this Paid Account!")
    facturma_api = FacturamaClientApi(usr=FACT_USR, pasw=FACT_PWD, env=DEV_ENV)
    supp_business_account_repo = SupplierBusinessAccountRepository(_info)  # type: ignore

    supp_bus_acc_info = await supp_business_account_repo.fetch(supplier_business_id)
    supp_bus_acc = SupplierBusinessAccount(**supp_bus_acc_info)  # type: ignore
    if not items:
        raise Exception("No Items Found!")
    client = Customer(
        Email=supp_bus_acc.email,
        Address=CustomerAddress(
            ZipCode=supp_bus_acc.mx_zip_code,
        ),
        Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
        Name=supp_bus_acc.legal_business_name,  # type: ignore
        CfdiUse="G03",
        FiscalRegime=supp_bus_acc.mx_sat_regimen,
        TaxZipCode=supp_bus_acc.mx_zip_code,
    )
    payment_method = None
    global_information = None
    if client.Rfc != "XAXX010101000" and client.Rfc != "XEXX010101000":
        if not paid_account.invoicing_provider_id:
            new_client = await facturma_api.new_client(client=client)
            if new_client.get("status") != "ok":
                raise GQLApiException(
                    msg=new_client.get("msg", "Error to create client"),
                    error_code=GQLApiErrorCodeType.FACTURAMA_NEW_CUSTOMER_ERROR.value,
                )
            client.Id = new_client["data"]["Id"]
            if not await edit_paid_account(
                db=_db,
                paid_account_id=paid_account.id,
                invoicing_provider_id=new_client["data"]["Id"],
            ):
                raise GQLApiException(
                    msg="Error to add invoicing provider id",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
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
        else:
            client = Customer(
                Email=supp_bus_acc.email,
                Address=CustomerAddress(
                    ZipCode=supp_bus_acc.mx_zip_code,
                ),
                Rfc=supp_bus_acc.mx_sat_rfc,  # type: ignore
                Name=supp_bus_acc.legal_business_name,  # type: ignore
                CfdiUse="S01",
                FiscalRegime="616",
                TaxZipCode=ALIMA_EXPEDITION_PLACE,
            )

    internal_invoice = FacturamaInternalInvoice(
        Receiver=client,
        CfdiType="I",
        NameId="1",
        ExpeditionPlace=ALIMA_EXPEDITION_PLACE,
        PaymentForm="01" if payment_method else "99",
        PaymentMethod=payment_method if payment_method else "PPD",
        Items=items,
        GlobalInformation=global_information,
    )
    internal_invoice_create = facturma_api.new_internal_invoice(
        invoice=internal_invoice
    )
    if internal_invoice_create.get("status") != "ok":
        logging.error(internal_invoice_create["msg"])
        raise GQLApiException(
            msg=internal_invoice_create.get("msg", "Error to create invoice"),
            error_code=GQLApiErrorCodeType.FACTURAMA_FETCH_ERROR.value,
        )
    print(internal_invoice_create["data"].Id)

    # fetch invoice files
    xml_file = await facturma_api.get_xml_internal_invoice_by_id(
        id=internal_invoice_create["data"].Id
    )
    pdf_file = await facturma_api.get_pdf_internal_invoice_by_id(
        id=internal_invoice_create["data"].Id
    )
    # create billing invoice
    b_invoice_id = await create_billing_invoice(
        _db,
        paid_account.id,
        "México",
        invoice_month,
        total_charges["total"],
        "MXN",
        InvoiceStatusType.ACTIVE,
        invoice_create_date,
        uuid.UUID(internal_invoice_create["data"].Complement.TaxStamp.Uuid),
        payment_method=PaymentFormFacturama[
            internal_invoice_create["data"].PaymentMethod
        ],
    )

    # create billing invoice charges
    b_invoice_charges = await create_billing_invoice_charges(
        _db, b_invoice_id, total_charges["charges"], invoice_create_date
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
            "filename": f"Factura Alima-{month}-{datetime.utcnow().year}.pdf",
            "mimetype": "application/pdf",
        },
    ]
    if xls_file_attcht and paid_account.account_name == "standard":
        attcht.append(xls_file_attcht)
    if client.Rfc != "XAXX010101000" and client.Rfc != "XEXX010101000":
        if not await send_new_alima_invoice_notification(
            email_to=[supp_bus_acc.email, "pagosyfacturas@alima.la"],  # type: ignore
            name=supplier["name"],  # type: ignore
            month=str(month) + f"-{datetime.utcnow().year}",
            attchs=attcht,
        ):
            raise Exception("Error to send email")
    else:
        if not await send_new_alima_invoice_notification(
            email_to=["pagosyfacturas@alima.la"],  # type: ignore
            name=supplier["name"],  # type: ignore
            month=str(month) + f"-{datetime.utcnow().year}",
            attchs=attcht,
        ):
            raise Exception("Error to send email")

    # show results
    logging.info("Finished creating Supplier Billing Invoice")
    logging.info(
        "\n".join(
            [
                "-----",
                f"Supplier Business ID: {supplier_business_id}",
                f"Paid Account ID: {paid_account.id}",
                f"Billing Invoice ID: {b_invoice_id}",
                f"Billing Invoice Charges IDs: {b_invoice_charges}",
                f"Billing Invoice Total: {total_charges['total']}",
                "-----",
            ]
        )
    )
    await db_shutdown()
    return True


async def main():
    args = parse_args()
    logging.info(
        f"Started creating Supplier Billing Invoice: {args.supplier_business_id} - {args.invoice_month}"
    )
    try:
        _month, _year = args.invoice_month.split("-")
        _invoice_create_date = datetime(int(_year), int(_month), 1) + relativedelta(
            months=1
        )
    except Exception as e:
        logging.error(
            f"Error parsing Invoice Month: {args.supplier_business_id} - {args.invoice_month}"
        )
        logging.error(e)
        return
    try:
        fl = await create_supplier_billing_invoice(
            uuid.UUID(args.supplier_business_id),
            args.invoice_month,
            _invoice_create_date,
            _month,
            args.gmv,
        )
        if not fl:
            logging.info(
                f"Supplier Invoice for ({args.supplier_business_id}) not able to be created"
            )
            return
        logging.info(
            f"Finished creating SupplierBilling Invoice successfully: {args.supplier_business_id} - {args.invoice_month}"
        )
    except Exception as e:
        logging.error(
            f"Error creating Supplier Billing Invoice: {args.supplier_business_id}"
        )
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
