import base64
from datetime import date, datetime
import json
import logging
from types import NoneType
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
import uuid
from gqlapi.domain.interfaces.v2.alima_account.account import (
    AlimaBillingInvoiceComplementRepositoryInterface,
    AlimaBillingInvoiceRepositoryInterface,
)
from gqlapi.domain.models.v2.alima_business import (
    BillingInvoice,
    BillingInvoiceCharge,
    BillingInvoicePaystatus,
)
from gqlapi.domain.models.v2.utils import (
    DataTypeDecoder,
    InvoiceStatusType,
    InvoiceType,
    PayStatusType,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.repository import CoreRepository
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


class AlimaBillingInvoiceRepository(
    CoreRepository, AlimaBillingInvoiceRepositoryInterface
):
    async def fetch_alima_invoices(
        self,
        paid_account_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
    ) -> List[BillingInvoice]:
        """Fetch Alima invoices

        Parameters
        ----------
        paid_account_id : UUID
        from_date : Optional[date], optional
        until_date : Optional[date], optional

        Returns
        -------
        List[BillingInvoice]
        """
        # format filters
        f_text = "paid_account_id = :paid_account_id"
        qry_dict: Dict[str, Any] = {"paid_account_id": paid_account_id}
        if from_date:
            f_text += " AND created_at >= :from_date"
            qry_dict["from_date"] = from_date
        if until_date:
            f_text += " AND created_at <= :until_date"
            qry_dict["until_date"] = until_date
        # query
        invoices = await super().find(
            core_element_name="Alima Billing Invoice",
            core_element_tablename="billing_invoice",
            core_columns="*",
            filter_values=f_text,
            values=qry_dict,
        )
        if not invoices:
            return []
        # format data type
        invoices_list = []
        for ch in invoices:
            inv_dict = dict(ch)
            inv_dict["status"] = InvoiceStatusType(
                DataTypeDecoder.get_mxinvoice_status_value(inv_dict["status"])
            )
            if "payment_method" in inv_dict and inv_dict["payment_method"]:
                inv_dict["payment_method"] = InvoiceType(inv_dict["payment_method"])
            if inv_dict["invoice_files"]:
                inv_dict["invoice_files"] = [
                    invf.decode("utf-8") for invf in inv_dict["invoice_files"]
                ]
            invoices_list.append(BillingInvoice(**inv_dict))
        return invoices_list

    async def fetch_alima_invoice_charges(
        self,
        invoice_ids: List[UUID],
    ) -> List[BillingInvoiceCharge]:
        """Fetch Alima Invoice Charges

        Parameters
        ----------
        invoice_ids : List[UUID]

        Returns
        -------
        List[BillingInvoiceCharge]
        """
        if not invoice_ids:
            return []
        # cast invoice ids to tuple
        invoice_ids_tuple = list_into_strtuple(invoice_ids)
        # query
        invoices_charges = await super().find(
            core_element_name="Alima Billing Invoice Charges",
            core_element_tablename="billing_invoice_charge",
            core_columns="*",
            filter_values=f"billing_invoice_id IN {invoice_ids_tuple}",
            values={},
        )
        if not invoices_charges:
            return []
        # format data type
        inv_charges_list = []
        for ch in invoices_charges:
            invch_dict = dict(ch)
            inv_charges_list.append(BillingInvoiceCharge(**invch_dict))
        return inv_charges_list

    async def fetch_alima_invoice_paystatus(
        self,
        invoice_ids: List[UUID],
    ) -> List[BillingInvoicePaystatus]:
        """Fetch Alima Invoice Last Paystatus

        Parameters
        ----------
        invoice_ids : List[UUID]

        Returns
        -------
        List[BillingInvoicePaystatus]
        """
        if not invoice_ids:
            return []
        invoice_ids_tuple = list_into_strtuple(invoice_ids)
        # query
        invoices_pstatus = await super().find(
            partition="""
                WITH last_billing_invoice_paystatus AS (
                    WITH binvs AS (
                        SELECT
                            *,
                            ROW_NUMBER() OVER (PARTITION BY billing_invoice_id ORDER BY created_at DESC) as row_num
                        FROM billing_invoice_paystatus
                    )
                    SELECT * FROM binvs WHERE row_num = 1
                )
                """,
            core_element_name="Alima Billing Invoice Paystatus",
            core_element_tablename="last_billing_invoice_paystatus",
            core_columns=[
                "id",
                "billing_invoice_id",
                "status",
                "created_at",
                "billing_payment_method_id",
                "transaction_id",
            ],
            filter_values=f"billing_invoice_id IN {invoice_ids_tuple}",
            values={},
        )
        if not invoices_pstatus:
            return []
        # format data type
        inv_pstatus_list = []
        for ch in invoices_pstatus:
            invps_dict = dict(ch)
            invps_dict["status"] = PayStatusType(
                DataTypeDecoder.get_orden_paystatus_value(invps_dict["status"])
            )
            inv_pstatus_list.append(BillingInvoicePaystatus(**invps_dict))
        return inv_pstatus_list

    async def fetch_next_folio(self) -> int:
        count_list = await super().find(
            core_element_name="Billing Invoice",
            core_element_tablename="billing_invoice",
            filter_values=None,
            core_columns="count(1) as count",
            values={},
        )
        if not count_list:
            return 1
        return count_list[0]["count"] + 1

    async def find(
        self, paid_account_id: UUID, date: Optional[str] = None
    ) -> List[BillingInvoice]:
        # format filters
        f_text = "paid_account_id = :paid_account_id"
        qry_dict: Dict[str, Any] = {"paid_account_id": paid_account_id}
        if date:
            f_text += " AND invoice_month = :invoice_month"
            qry_dict["invoice_month"] = date
        invoices = await super().find(
            core_element_name="Alima Billing Invoice",
            core_element_tablename="billing_invoice",
            core_columns="*",
            filter_values=f_text,
            values=qry_dict,
        )
        if not invoices:
            return []
        # format data type
        invoices_list = []
        for ch in invoices:
            inv_dict = dict(ch)
            inv_dict["status"] = InvoiceStatusType(
                DataTypeDecoder.get_mxinvoice_status_value(inv_dict["status"])
            )
            if "paymenth_method" in inv_dict and inv_dict["payment_method"]:
                inv_dict["payment_method"] = InvoiceType(inv_dict["payment_method"])
            if inv_dict["invoice_files"]:
                inv_dict["invoice_files"] = [
                    invf.decode("utf-8") for invf in inv_dict["invoice_files"]
                ]
            invoices_list.append(BillingInvoice(**inv_dict))
        return invoices_list

    async def find_by_transaction_id(
        self, transaction_id: str
    ) -> Tuple[BillingInvoice | NoneType, BillingInvoicePaystatus | NoneType]:
        # format filters
        f_text = "transaction_id = :transaction_id LIMIT 1"
        qry_dict: Dict[str, Any] = {"transaction_id": transaction_id}
        inv_pstatuses = await super().find(
            core_element_name="Alima Billing Invoice PayStatus",
            core_element_tablename="billing_invoice_paystatus",
            core_columns="*",
            filter_values=f_text,
            values=qry_dict,
        )
        if len(inv_pstatuses) == 0:
            return None, None
        # convert object
        inv_payst_dict = dict(inv_pstatuses[0])
        inv_payst_dict["status"] = PayStatusType(
            DataTypeDecoder.get_orden_paystatus_value(inv_payst_dict["status"])
        )
        inv_payst = BillingInvoicePaystatus(**inv_payst_dict)
        # fetch Billing invoice
        binv = await super().fetch(
            core_element_name="Alima Billing Invoice",
            core_element_tablename="billing_invoice",
            core_columns="*",
            id=inv_payst.billing_invoice_id,
        )
        if not binv:
            return None, None
        inv_dict = dict(binv)
        inv_dict["status"] = InvoiceStatusType(
            DataTypeDecoder.get_mxinvoice_status_value(inv_dict["status"])
        )
        if "paymenth_method" in inv_dict and inv_dict["payment_method"]:
            inv_dict["payment_method"] = InvoiceType(inv_dict["payment_method"])
        if inv_dict["invoice_files"]:
            inv_dict["invoice_files"] = [
                invf.decode("utf-8") for invf in inv_dict["invoice_files"]
            ]
        return BillingInvoice(**inv_dict), inv_payst

    async def edit(
        self, billing_invoice_id: UUID, status: Optional[InvoiceStatusType] = None
    ) -> bool:
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": billing_invoice_id}

        if status:
            core_atributes.append(" status=:status")
            core_values_view["status"] = DataTypeDecoder.get_mxinvoice_status_key(
                status.value
            )

        if len(core_atributes) == 0:
            logging.warning("Issues no data to update in sql")
            return True

        core_atributes.append(" last_updated=:last_updated")
        core_values_view["last_updated"] = datetime.utcnow()

        invoice_query = f"""UPDATE billing_invoice
                            SET {','.join(core_atributes)}
                            WHERE id= :id;
                """
        return await super().edit(
            core_element_name="billing_invoice",
            core_query=invoice_query,
            core_values=core_values_view,
        )

    async def get_last_invoice_date(self, paid_account_id: UUID) -> datetime | NoneType:
        try:
            last_invoice = await self.raw_query(
                """
                SELECT * FROM billing_invoice
                WHERE paid_account_id = :paid_account_id
                AND status = 'active'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                {"paid_account_id": paid_account_id},
            )
            if len(last_invoice) == 0:
                return None
            lid_dict = dict(last_invoice[0])
            return lid_dict["created_at"]
        except Exception as e:
            logger.error(e)
            logger.warning("Error to get last invoice date")
            return None

    async def add_alima_invoice(
        self,
        billing_invoice: BillingInvoice,
        billing_invoice_charges: List[BillingInvoiceCharge],
        paystatus: PayStatusType = PayStatusType.UNPAID,
        billing_payment_method_id: Optional[UUID] = None,
        transaction_id: Optional[str] = None,
    ) -> UUID | NoneType:
        # create billing invoice
        billing_invoice.id = uuid.uuid4()
        binv_id = await super().add(
            core_element_name="Billing Invoice",
            core_element_tablename="billing_invoice",
            core_query="""
                INSERT INTO billing_invoice (
                    id, paid_account_id, country,
                    invoice_month, invoice_name, tax_invoice_id,
                    invoice_number, total,
                    currency, status, created_at,
                    sat_invoice_uuid, payment_method
                )
                VALUES (
                    :id, :paid_account_id, :country,
                    :invoice_month, :invoice_name, :tax_invoice_id,
                    :invoice_number, :total,
                    :currency, :status, :created_at,
                    :sat_invoice_uuid, :payment_method
                )
                """,
            core_values={
                "id": billing_invoice.id,
                "paid_account_id": billing_invoice.paid_account_id,
                "country": billing_invoice.country,
                "invoice_month": billing_invoice.invoice_month,
                "invoice_name": billing_invoice.invoice_month,  # for now same as invoice_month
                "tax_invoice_id": billing_invoice.tax_invoice_id,
                "invoice_number": billing_invoice.invoice_number,
                "total": round(billing_invoice.total, 2),
                "currency": billing_invoice.currency,
                "status": DataTypeDecoder.get_mxinvoice_status_key(
                    billing_invoice.status.value
                ),
                "created_at": billing_invoice.created_at,
                "sat_invoice_uuid": billing_invoice.sat_invoice_uuid,
                "payment_method": billing_invoice.payment_method.value,
            },
        )
        if not binv_id:
            return None
        # create billing status
        status_flag = await super().add(
            core_element_name="Billing Invoice Paystatus",
            core_element_tablename="billing_invoice_paystatus",
            core_query="""
                INSERT INTO billing_invoice_paystatus (
                    id, billing_invoice_id, status, billing_payment_method_id, transaction_id
                )
                VALUES (
                    :id, :billing_invoice_id, :status, :billing_payment_method_id, :transaction_id
                )
                """,
            core_values={
                "id": uuid.uuid4(),
                "billing_invoice_id": billing_invoice.id,
                "status": DataTypeDecoder.get_orden_paystatus_key(paystatus.value),
                "billing_payment_method_id": billing_payment_method_id,
                "transaction_id": transaction_id,
            },
        )
        if not status_flag:
            logger.warning("Error to create billing invoice paystatus")
            return None
        # create billing invoice charges
        for bch in billing_invoice_charges:
            bch.billing_invoice_id = billing_invoice.id
            ch_flag = await self.add_alima_invoice_charge(bch)
            if not ch_flag:
                logger.warning("Error to create billing invoice charge")
                return None
        return billing_invoice.id

    async def edit_alima_invoice(
        self,
        billing_invoice: BillingInvoice,
        paystatus: Optional[PayStatusType] = None,
        billing_payment_method_id: Optional[UUID] = None,
        transaction_id: Optional[str] = None,
    ) -> bool:
        # update billing invoice
        qry = """
            UPDATE billing_invoice
                SET result = :result,
                    last_updated = :last_updated,
                    invoice_files = :invoice_files
                WHERE id = :id
        """
        if billing_invoice.invoice_files and len(billing_invoice.invoice_files) > 0:
            billing_invoice_files = [
                bif.encode("utf-8") for bif in billing_invoice.invoice_files
            ]
        else:
            billing_invoice_files = None
        billing_invoice.last_updated = datetime.utcnow()
        _edited = await super().edit(
            core_element_name="Billing Invoice",
            core_query=qry,
            core_values={
                "id": billing_invoice.id,
                "result": billing_invoice.result,
                "last_updated": billing_invoice.last_updated,
                "invoice_files": billing_invoice_files,
            },
        )
        if not _edited:
            return False
        # if paystatus is not None, update paystatus
        if paystatus:
            status_flag = await super().add(
                core_element_name="Billing Invoice Paystatus",
                core_element_tablename="billing_invoice_paystatus",
                core_query="""
                    INSERT INTO billing_invoice_paystatus (
                        id, billing_invoice_id, status, billing_payment_method_id, transaction_id
                    )
                    VALUES (
                        :id, :billing_invoice_id, :status, :billing_payment_method_id, :transaction_id
                    )
                    """,
                core_values={
                    "id": uuid.uuid4(),
                    "billing_invoice_id": billing_invoice.id,
                    "status": DataTypeDecoder.get_orden_paystatus_key(paystatus.value),
                    "billing_payment_method_id": billing_payment_method_id,
                    "transaction_id": transaction_id,
                },
            )
            if not status_flag:
                logger.warning("Error to create billing invoice paystatus")
                return False
        return True

    async def add_alima_invoice_charge(
        self,
        billing_invoice_charge: BillingInvoiceCharge,
    ) -> UUID | NoneType:
        bch = billing_invoice_charge
        _id = uuid.uuid4()
        _flg = await super().add(
            core_element_name="Billing Invoice Charge",
            core_element_tablename="billing_invoice_charge",
            core_query="""
                        INSERT INTO billing_invoice_charge (
                            id, billing_invoice_id, charge_id,
                            charge_type, charge_base_quantity, charge_amount,
                            charge_amount_type, total_charge, currency
                        )
                        VALUES (
                            :id, :billing_invoice_id, :charge_id,
                            :charge_type, :charge_base_quantity, :charge_amount,
                            :charge_amount_type, :total_charge, :currency
                        )
                        """,
            core_values={
                "id": _id,
                "billing_invoice_id": bch.billing_invoice_id,
                "charge_id": bch.charge_id,
                "charge_type": bch.charge_type,
                "charge_base_quantity": bch.charge_base_quantity,
                "charge_amount": bch.charge_amount,
                "charge_amount_type": bch.charge_amount_type,
                "total_charge": bch.total_charge,
                "currency": bch.currency,
            },
        )
        if not _flg:
            logger.warning("Error to create billing invoice charge")
            return None
        return _id


class AlimaBillingInvoiceComplementRepository(
    CoreRepository, AlimaBillingInvoiceComplementRepositoryInterface
):
    async def add(
        self,
        billing_invoice_id: uuid.UUID,
        tax_invoice_id: str,
        invoice_number: str,
        total: float,
        currency: str,
        status: InvoiceStatusType,
        sat_invoice_uuid: uuid.UUID,
        result: str,
        pdf_file: Any,
        xml_file: Any,
    ) -> uuid.UUID:
        """Create a new billing invoice complement.

        Parameters
        ----------
        billing_invoice_id : uuid.UUID
        country : str
        invoice_month : str
        total : float
        currency : str
        status : InvoiceStatusType

        Returns
        -------
        uuid.UUID
        """
        billing_invoice_complement_id = uuid.uuid4()
        pdf_file_str = base64.b64encode(pdf_file).decode("utf-8")
        xml_file_str = base64.b64encode(xml_file).decode("utf-8")
        json_data = {"pdf": pdf_file_str, "xml": xml_file_str}
        invoice_files = json.dumps(json_data)
        invoice_diles = invoice_files.encode("utf-8")
        await super().add(
            core_element_name="Billing Invoice Complement",
            core_element_tablename="billing_invoice_complement",
            core_query="""INSERT INTO billing_invoice_complement (
                id, billing_invoice_id,
                tax_invoice_id,
                invoice_number, total,
                currency, status, result,
                sat_invoice_uuid, invoice_files
            )
            VALUES (
                :id, :billing_invoice_id,
                :tax_invoice_id,
                :invoice_number, :total,
                :currency, :status,
                :result, :sat_invoice_uuid, :invoice_files
            )""",
            core_values={
                "id": billing_invoice_complement_id,
                "billing_invoice_id": billing_invoice_id,
                "tax_invoice_id": tax_invoice_id,  # SAT UUID - null for now
                "invoice_number": invoice_number,  # null for now
                "total": round(total, 2),
                "result": result,
                "currency": currency,
                "invoice_files": [invoice_diles],
                "status": DataTypeDecoder.get_mxinvoice_status_key(status.value),
                "sat_invoice_uuid": sat_invoice_uuid,
            },
        )
        return billing_invoice_complement_id

    # create billing invoice

    async def find(
        self,
    ) -> None:
        raise NotImplementedError

    async def fetch_next_folio(self) -> int:
        count_list = await super().find(
            core_element_name="Billing Invoice Complement",
            core_element_tablename="billing_invoice_complement",
            filter_values=None,
            core_columns="count(1) as count",
            values={},
        )
        if not count_list:
            return 1
        return count_list[0]["count"] + 1
