from datetime import date, datetime
from types import NoneType
from typing import Any, Dict, List, Optional
import uuid
from uuid import UUID
from bson import Binary
from gqlapi.domain.interfaces.v2.orden.invoice import (
    MxInvoiceComplementRepositoryInterface,
    MxInvoiceRepositoryInterface,
    MxInvoicingExecutionRepositoryInterface,
    MxSatCertificateRepositoryInterface,
)
from gqlapi.domain.models.v2.core import (
    MxInvoice,
    MxInvoiceComplement,
    MxInvoiceOrden,
    MxInvoicingExecution,
    MxSatInvoicingCertificateInfo,
)
from gqlapi.domain.models.v2.supplier import InvoicingOptions
from gqlapi.domain.models.v2.utils import (
    DataTypeDecoder,
    ExecutionStatusType,
    InvoiceConsolidation,
    InvoiceStatusType,
    InvoiceTriggerTime,
    InvoiceType,
    PayStatusType,
    RegimenSat,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.repository import CoreMongoRepository, CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger

# logger
logger = get_logger(get_app())


class MxInvoiceRepository(CoreRepository, MxInvoiceRepositoryInterface):
    async def new(
        self, mx_invoice: MxInvoice, orden_details_id: uuid.UUID
    ) -> Dict[str, Any]:
        inv_uuid = None
        try:
            # create mx invoice
            inv_uuid = uuid.uuid4()
            cvals = domain_to_dict(
                mx_invoice, skip=["created_at", "id", "status", "last_updated"]
            )
            cvals["id"] = inv_uuid
            cvals["status"] = DataTypeDecoder.get_mxinvoice_status_key(
                mx_invoice.status.value
            )
            cvals["sat_invoice_uuid"] = UUID(cvals["sat_invoice_uuid"])
            await super().new(
                core_element_name="Mx Invoice",
                core_element_tablename="mx_invoice",
                core_query="""
                    INSERT INTO mx_invoice (
                        id,
                        supplier_business_id,
                        restaurant_branch_id,
                        sat_invoice_uuid,
                        invoice_number,
                        invoice_provider_id,
                        invoice_provider,
                        pdf_file,
                        xml_file,
                        total,
                        status,
                        created_by
                    ) VALUES (
                        :id,
                        :supplier_business_id,
                        :restaurant_branch_id,
                        :sat_invoice_uuid,
                        :invoice_number,
                        :invoice_provider_id,
                        :invoice_provider,
                        :pdf_file,
                        :xml_file,
                        :total,
                        :status,
                        :created_by
                    )
                """,
                core_values=cvals,
            )
            # associate mx invoice with orden
            await self.associate(
                mx_invoice_id=inv_uuid,
                orden_details_id=orden_details_id,
                created_by=mx_invoice.created_by,
            )
            return {
                "id": inv_uuid,
                "success": True,
            }
        except Exception as e:
            logger.error(e)
            logger.warning("Error creating Mx Invoice")
            return {
                "id": inv_uuid,
                "success": False,
            }

    async def edit(
        self,
        mx_invoice_id: UUID,
        status: Optional[InvoiceStatusType] = None,
        cancel_result: Optional[str] = None,
    ) -> bool:
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": mx_invoice_id}

        if status:
            core_atributes.append(" status=:status")
            core_values_view["status"] = DataTypeDecoder.get_mxinvoice_status_key(
                status.value
            )
        if cancel_result:
            core_atributes.append(" cancel_result= :cancel_result")
            core_values_view["cancel_result"] = cancel_result

        if len(core_atributes) == 0:
            logger.warning("Issues no data to update in sql")
            return True

        core_atributes.append(" last_updated=:last_updated")
        core_values_view["last_updated"] = datetime.utcnow()

        invoice_query = f"""UPDATE mx_invoice
                            SET {','.join(core_atributes)}
                            WHERE id=:id;
                """
        return await super().edit(
            core_element_name="mx_invoice",
            core_query=invoice_query,
            core_values=core_values_view,
        )

    async def associate(
        self, mx_invoice_id: UUID, orden_details_id: UUID, created_by: UUID
    ) -> Dict[str, Any]:
        """Associate Mx Invoice with Orden Details

        Parameters
        ----------
        mx_invoice_id : UUID
        orden_details_id : UUID

        Returns
        -------
        Dict[str, Any]
        """
        await super().new(
            core_element_name="Mx Invoice Orden",
            core_element_tablename="mx_invoice_orden",
            core_query="""
                INSERT INTO mx_invoice_orden (
                    mx_invoice_id,
                    orden_details_id,
                    created_by
                ) VALUES (
                    :mx_invoice_id,
                    :orden_details_id,
                    :created_by
                )
            """,
            core_values={
                "mx_invoice_id": mx_invoice_id,
                "orden_details_id": orden_details_id,
                "created_by": created_by,
            },
        )
        return {
            "success": True,
        }

    async def add(
        self, mx_invoice: MxInvoice, orden_details_id: uuid.UUID
    ) -> Dict[str, Any]:
        inv_uuid = None
        try:
            # create mx invoice
            inv_uuid = uuid.uuid4()
            cvals = domain_to_dict(
                mx_invoice,
                skip=["created_at", "id", "status", "last_updated", "cancel_result"],
            )
            cvals["id"] = inv_uuid
            cvals["status"] = DataTypeDecoder.get_mxinvoice_status_key(
                mx_invoice.status.value
            )
            if "payment_method" in cvals and cvals["payment_method"]:
                cvals["payment_method"] = cvals["payment_method"].value
            if not isinstance(cvals["sat_invoice_uuid"], uuid.UUID):
                cvals["sat_invoice_uuid"] = UUID(cvals["sat_invoice_uuid"])
            await super().add(
                core_element_name="Mx Invoice",
                core_element_tablename="mx_invoice",
                core_query="""
                    INSERT INTO mx_invoice (
                        id,
                        supplier_business_id,
                        restaurant_branch_id,
                        sat_invoice_uuid,
                        invoice_number,
                        invoice_provider_id,
                        invoice_provider,
                        pdf_file,
                        xml_file,
                        total,
                        status,
                        created_by,
                        result,
                        payment_method
                    ) VALUES (
                        :id,
                        :supplier_business_id,
                        :restaurant_branch_id,
                        :sat_invoice_uuid,
                        :invoice_number,
                        :invoice_provider_id,
                        :invoice_provider,
                        :pdf_file,
                        :xml_file,
                        :total,
                        :status,
                        :created_by,
                        :result,
                        :payment_method
                    )
                """,
                core_values=cvals,
            )
            # associate mx invoice with orden
            await self.add_associate(
                mx_invoice_id=inv_uuid,
                orden_details_id=orden_details_id,
                created_by=mx_invoice.created_by,
            )
            await self.add_paystatus(
                mx_invoice_id=inv_uuid,
                paystatus=PayStatusType.UNPAID,
                created_by=mx_invoice.created_by,
            )
            return {
                "id": inv_uuid,
                "success": True,
            }
        except Exception as e:
            logger.error(e)
            logger.warning("Error creating Mx Invoice")
            return {
                "id": inv_uuid,
                "success": False,
            }

    async def add_consolidated(
        self, mx_invoice: MxInvoice, orden_details_ids: list[uuid.UUID]
    ) -> Dict[str, Any]:
        inv_uuid = None
        try:
            # create mx invoice
            inv_uuid = uuid.uuid4()
            cvals = domain_to_dict(
                mx_invoice,
                skip=["created_at", "id", "status", "last_updated", "cancel_result"],
            )
            cvals["id"] = inv_uuid
            cvals["status"] = DataTypeDecoder.get_mxinvoice_status_key(
                mx_invoice.status.value
            )
            if "payment_method" in cvals and cvals["payment_method"]:
                cvals["payment_method"] = cvals["payment_method"].value
            if not isinstance(cvals["sat_invoice_uuid"], uuid.UUID):
                cvals["sat_invoice_uuid"] = UUID(cvals["sat_invoice_uuid"])
            await super().add(
                core_element_name="Mx Invoice",
                core_element_tablename="mx_invoice",
                core_query="""
                    INSERT INTO mx_invoice (
                        id,
                        supplier_business_id,
                        restaurant_branch_id,
                        sat_invoice_uuid,
                        invoice_number,
                        invoice_provider_id,
                        invoice_provider,
                        pdf_file,
                        xml_file,
                        total,
                        status,
                        created_by,
                        result,
                        payment_method
                    ) VALUES (
                        :id,
                        :supplier_business_id,
                        :restaurant_branch_id,
                        :sat_invoice_uuid,
                        :invoice_number,
                        :invoice_provider_id,
                        :invoice_provider,
                        :pdf_file,
                        :xml_file,
                        :total,
                        :status,
                        :created_by,
                        :result,
                        :payment_method
                    )
                """,
                core_values=cvals,
            )
            await self.add_paystatus(
                mx_invoice_id=inv_uuid,
                paystatus=PayStatusType.UNPAID,
                created_by=mx_invoice.created_by,
            )
            for orden_details_id in orden_details_ids:
                # associate mx invoice with orden
                await self.add_associate(
                    mx_invoice_id=inv_uuid,
                    orden_details_id=orden_details_id,
                    created_by=mx_invoice.created_by,
                )

            return {
                "id": inv_uuid,
                "success": True,
            }
        except Exception as e:
            logger.error(e)
            logger.warning("Error creating Mx Invoice")
            return {
                "id": inv_uuid,
                "success": False,
            }

    async def add_associate(
        self, mx_invoice_id: UUID, orden_details_id: UUID, created_by: UUID
    ) -> Dict[str, Any]:
        """Associate Mx Invoice with Orden Details

        Parameters
        ----------
        mx_invoice_id : UUID
        orden_details_id : UUID

        Returns
        -------
        Dict[str, Any]
        """
        await super().add(
            core_element_name="Mx Invoice Orden",
            core_element_tablename="mx_invoice_orden",
            core_query="""
                INSERT INTO mx_invoice_orden (
                    mx_invoice_id,
                    orden_details_id,
                    created_by
                ) VALUES (
                    :mx_invoice_id,
                    :orden_details_id,
                    :created_by
                )
            """,
            core_values={
                "mx_invoice_id": mx_invoice_id,
                "orden_details_id": orden_details_id,
                "created_by": created_by,
            },
        )
        return {
            "success": True,
        }

    async def add_paystatus(
        self, mx_invoice_id: UUID, paystatus: PayStatusType, created_by: UUID
    ) -> Dict[str, Any]:
        """Add Mx Invoice Paystatus

        Parameters
        ----------
        mx_invoice_id : UUID
        orden_details_id : UUID

        Returns
        -------
        Dict[str, Any]
        """
        await super().add(
            core_element_name="Mx Invoice Paystatus",
            core_element_tablename="mx_invoice_paystatus",
            core_query="""
                INSERT INTO mx_invoice_paystatus (
                    mx_invoice_id,
                    status,
                    created_by
                ) VALUES (
                    :mx_invoice_id,
                    :status,
                    :created_by
                )
            """,
            core_values={
                "mx_invoice_id": mx_invoice_id,
                "status": DataTypeDecoder.get_orden_paystatus_key(paystatus.value),
                "created_by": created_by,
            },
        )
        return {
            "success": True,
        }

    async def get(self, orden_id: UUID) -> Dict[str, Any]:
        """Get Mx Invoice by Orden ID

        Parameters
        ----------
        orden_id : UUID

        Returns
        -------
        MxInvoice (dict)
        """
        _invs = await super().fetch(
            core_element_name="Mx Invoice",
            core_element_tablename="""
                mx_invoice mxi
                JOIN mx_invoice_orden mxio
                ON mxi.id = mxio.mx_invoice_id
                JOIN orden_details od
                ON od.id = mxio.orden_details_id
            """,
            core_columns="mxi.*",
            id_key="orden_id",
            id=orden_id,
        )
        if not _invs:
            return {}
        return dict(_invs)

    async def fetch_from_orden_details(self, orden_details_id: UUID) -> Dict[str, Any]:
        """Get Mx Invoice by Orden Details ID

        Parameters
        ----------
        orden_details_id : UUID

        Returns
        -------
        MxInvoice (dict)
        """
        _invs = await super().fetch(
            core_element_name="Mx Invoice",
            core_element_tablename="""
                mx_invoice mxi
                JOIN mx_invoice_orden mxio
                ON mxi.id = mxio.mx_invoice_id
                JOIN orden_details od
                ON od.id = mxio.orden_details_id
            """,
            core_columns="mxi.*",
            id_key="orden_details_id",
            id=orden_details_id,
        )
        if not _invs:
            return {}
        return dict(_invs)

    async def get_asocciated_orden(self, invoice_id: UUID) -> Dict[str, Any]:
        """Get Mx Invoice Orden by Invoice ID

        Parameters
        ----------
        invoice_id : str

        Returns
        -------
        MxInvoiceOrden (dict)
        """
        _invassoc = await super().get(
            id=invoice_id,
            core_element_name="Mx Invoice Orden",
            core_element_tablename="mx_invoice_orden",
            core_columns="*",
            id_key="mx_invoice_id",
        )
        return dict(_invassoc)

    async def find_asocciated_ordenes(self, invoice_id: UUID) -> List[MxInvoiceOrden]:
        """Get Mx Invoice Orden by Invoice ID

        Parameters
        ----------
        invoice_id : str

        Returns
        -------
        MxInvoiceOrden
        """
        _invassoc = await super().find(
            core_element_name="Mx Invoice Orden",
            core_element_tablename="mx_invoice_orden",
            core_columns="*",
            filter_values="mx_invoice_id = :invoice_id",
            values={"invoice_id": invoice_id},
        )
        if not _invassoc:
            return []
        _invassoc_list = []
        for invassoc in _invassoc:
            _invassoc_list.append(MxInvoiceOrden(**dict(invassoc)))
        return _invassoc_list

    async def get_external(self, order_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def fetch(self, mx_invoice_id: UUID) -> Dict[Any, Any]:
        """Get Mx Invoice

        Parameters
        ----------
        mx_invoice_id : uuid

        Returns
        -------
        MxInvoice (dict)
        """
        _inv = await super().fetch(
            id=mx_invoice_id,
            core_element_name="Mx Invoice",
            core_element_tablename="mx_invoice",
        )
        if _inv:
            return dict(_inv)
        return {}

    async def fetch_multiple_associated(
        self, orden_ids: List[UUID]
    ) -> List[Dict[str, Any]]:
        """Get Multiple Mx Invoices by Orden IDs

        Parameters
        ----------
        orden_ids : List[UUID]

        Returns
        -------
        List[Dict[str, Any]]
        """
        _invs = await super().find(
            partition="""
            WITH orden_details_view as (
                -- get last version of orden
                WITH last_orden_version AS (
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
                    orden_details.*
                FROM last_orden_version lov
                JOIN orden_details ON orden_details.id = lov.orden_details_id
            )
            """,
            core_element_name="Mx Invoice",
            core_element_tablename="""
                mx_invoice mxi
                JOIN mx_invoice_orden mxio
                ON mxi.id = mxio.mx_invoice_id
                JOIN orden_details_view od
                ON od.id = mxio.orden_details_id
                JOIN supplier_unit su
                ON su.id = od.supplier_unit_id
                JOIN orden o
                ON o.id = od.orden_id
            """,
            core_columns=[
                "mxi.*",
                "od.orden_id",
                "mxio.id as mx_invoice_orden_id",
                "mxio.orden_details_id",
                "mxio.created_by as mxio_created_by",
                "mxio.created_at as mxio_created_at",
                "mxio.last_updated as mxio_last_updated",
                "od.supplier_unit_id",
                "su.supplier_business_id",
                "mxi.pdf_file",
                "mxi.xml_file",
                "mxi.payment_method",
                "o.orden_number",
            ],
            filter_values=f" od.orden_id IN {list_into_strtuple(orden_ids)}",
            values={},
        )
        return [dict(_inv) for _inv in _invs]

    async def fetch_invoice_details_by_orden(
        self, orden_id: UUID
    ) -> List[Dict[Any, Any]]:
        """Get Multiple Invoice Details by Orden ID

        Parameters
        ----------
        orden_id : UUID

        Returns
        -------
        List[Dict[str, Any]]
        """
        _invs = await super().find(
            core_element_name="Mx Invoice",
            core_element_tablename="""
                orden o
                JOIN orden_details od
                ON o.id = od.orden_id
                JOIN restaurant_branch rb
                ON rb.id = od.restaurant_branch_id
                JOIN restaurant_branch_mx_invoice_info rbmii
                ON rb.id = rbmii.branch_id
                JOIN mx_invoice_orden mio
                ON mio.orden_details_id = od.id
                JOIN mx_invoice mi
                ON mi.id = mio.mx_invoice_id
                JOIN mx_invoice_paystatus mip
                ON mi.id = mip.mx_invoice_id
            """,
            core_columns=[
                "od.id",
                "od.orden_id",
                "mi.invoice_provider_id as invoice_provider_id",
                "mi.sat_invoice_uuid",
                "mip.status",
                "rbmii.mx_sat_id",
                "rbmii.legal_name",
                "mi.total",
                "mi.status",
                "mi.xml_file",
                "mi.pdf_file",
                "mi.invoice_number",
                "mi.created_at",
                "mi.created_by",
                "mio.created_at as created_at_mx_inv_ord",
                "mio.created_by as created_by_mx_inv_ord",
                "mio.last_updated",
                "od.supplier_unit_id",
                "mio.mx_invoice_id",
                "mi.cancel_result",
            ],
            filter_values=f" o.id = '{orden_id}'",
            values={},
        )
        if _invs:
            return [dict(_inv) for _inv in _invs]
        else:
            return []

    async def fetch_invoice_details_by_dates(
        self,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        receiver: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict[Any, Any]]:
        """Get Multiple Invoice Details by Dates and additional filters

        Parameters
        ----------
        supplier_unit_id : UUID
        from_date : Optional[date]
        until_date : Optional[date]
        receiver : Optional[str]
        page : Optional[int]
        page_size : Optional[int]

        Returns
        -------
        List[Dict[str, Any]]
        """
        # build query filters
        filters = [" od.supplier_unit_id = :supplier_unit_id "]
        values: Dict[str, Any] = {"supplier_unit_id": supplier_unit_id}
        if from_date:
            filters.append(" mxi.created_at >= :from_date ")
            values["from_date"] = from_date
        if until_date:
            filters.append(" mxi.created_at <= :until_date ")
            values["until_date"] = until_date
        if receiver:
            filters.append(
                """ (rb.branch_name ILIKE :receiver
                    OR rbu.name ILIKE :receiver
                    OR mxi.invoice_number ILIKE :receiver)
                """
            )
            values["receiver"] = "%" + receiver + "%"
        filters_str = " AND ".join(filters)
        filters_str += " ORDER BY mxi.created_at LIMIT :page_size OFFSET :offset "
        values["page_size"] = page_size
        values["offset"] = (page - 1) * page_size
        # query
        _invs = await super().find(
            core_element_name="Mx Invoice",
            core_element_tablename="""
                mx_invoice mxi
                JOIN mx_invoice_orden mxio
                    ON mxi.id = mxio.mx_invoice_id
                JOIN orden_details od
                    ON od.id = mxio.orden_details_id
                JOIN supplier_unit su
                    ON su.id = od.supplier_unit_id
                JOIN restaurant_branch rb
                    ON rb.id = od.restaurant_branch_id
                JOIN restaurant_business rbu
                    ON rbu.id = rb.restaurant_business_id
            """,
            core_columns=[
                "mxi.*",
                "od.orden_id",
                "mxio.id as mx_invoice_orden_id",
                "mxio.orden_details_id",
                "mxio.created_by as mxio_created_by",
                "mxio.created_at as mxio_created_at",
                "mxio.last_updated as mxio_last_updated",
                "od.supplier_unit_id",
                "su.supplier_business_id",
                "mxi.pdf_file",
                "mxi.xml_file",
            ],
            filter_values=filters_str,
            values=values,
        )
        if _invs:
            return [dict(_inv) for _inv in _invs]
        else:
            return []

    async def fetch_assocciated_by_orden(
        self, orden_details_id: UUID
    ) -> Dict[Any, Any]:
        """Get Mx Invoice Orden by Invoice ID

        Parameters
        ----------
        invoice_id : str

        Returns
        -------
        MxInvoiceOrden (dict)
        """
        _invassoc = await super().fetch(
            id=orden_details_id,
            core_element_name="Mx Invoice Orden",
            core_element_tablename="mx_invoice_orden",
            core_columns="*",
            id_key="orden_details_id",
        )
        if _invassoc:
            return dict(_invassoc)
        return {}

    async def find(self) -> List[MxInvoice]:
        invoices = await super().find(
            core_element_name="Mx Invoice",
            core_element_tablename="mx_invoice",
            filter_values=None,
            core_columns="*",
            values={},
        )
        if not invoices:
            return []
        return [MxInvoice(**sql_to_domain(r, MxInvoice)) for r in invoices]

    async def fetch_next_folio(self, supplier_business_id: UUID) -> int:
        count_list = await super().find(
            core_element_name="Mx Invoice",
            core_element_tablename="mx_invoice",
            filter_values=" supplier_business_id = :supplier_business_id ",
            core_columns="count(1) as count",
            values={
                "supplier_business_id": supplier_business_id,
            },
        )
        if not count_list:
            return 1
        return count_list[0]["count"] + 1


class MxSatCertificateRepository(
    CoreMongoRepository, MxSatCertificateRepositoryInterface
):
    async def upsert(
        self,
        sat_certificate: MxSatInvoicingCertificateInfo,
    ) -> Dict[str, Any]:
        # serialize info
        data = domain_to_dict(sat_certificate)
        data["sat_regime"] = data["sat_regime"].value
        data["supplier_unit_id"] = Binary.from_uuid(data["supplier_unit_id"])
        data["invoicing_options"] = {
            k: v if k == "automated_invoicing" else (None if not v else v.value)
            for k, v in data["invoicing_options"].__dict__.items()
        }
        if data["cer_file"]:
            data["cer_file"] = Binary(data["cer_file"].encode("utf-8"))
        if data["key_file"]:
            data["key_file"] = Binary(data["key_file"].encode("utf-8"))
        # upsert
        if await super().exists(
            core_element_collection="supplier_unit_mx_invoice_info",
            core_element_name="Supplier Unit Mx Invoice Info",
            core_query={"supplier_unit_id": data["supplier_unit_id"]},
        ):
            # update
            flag = await super().edit(
                core_element_collection="supplier_unit_mx_invoice_info",
                core_element_name="Supplier Unit Mx Invoice Info",
                core_query={"supplier_unit_id": data["supplier_unit_id"]},
                core_values={"$set": data},
            )
        else:
            flag = await super().add(
                core_element_collection="supplier_unit_mx_invoice_info",
                core_element_name="Supplier Unit Mx Invoice Info",
                core_values=data,
            )
        return data if flag else {}

    async def fetch_certificate(self, supplier_unit_id: UUID) -> Dict[str, Any]:
        _data = await super().fetch(
            core_element_name="Supplier Unit Mx Invoice Info",
            core_element_collection="supplier_unit_mx_invoice_info",
            query={
                "supplier_unit_id": Binary.from_uuid(supplier_unit_id),
            },
        )
        if not _data:
            return {}
        # format data
        _data["supplier_unit_id"] = Binary.as_uuid(_data["supplier_unit_id"])
        if _data["cer_file"]:
            _data["cer_file"] = _data["cer_file"].decode("utf-8")
        if _data["key_file"]:
            _data["key_file"] = _data["key_file"].decode("utf-8")
        _data["sat_regime"] = RegimenSat(_data["sat_regime"])
        if _data["invoicing_options"]:
            _data["invoicing_options"] = InvoicingOptions(
                automated_invoicing=_data["invoicing_options"]["automated_invoicing"],
                invoice_type=(
                    InvoiceType(_data["invoicing_options"]["invoice_type"])
                    if _data["invoicing_options"]["invoice_type"]
                    else None
                ),
                triggered_at=(
                    InvoiceTriggerTime(_data["invoicing_options"]["triggered_at"])
                    if _data["invoicing_options"]["triggered_at"]
                    else None
                ),
                consolidation=(
                    InvoiceConsolidation(_data["invoicing_options"]["consolidation"])
                    if _data["invoicing_options"]["consolidation"]
                    else None
                ),
            )
        return _data


class MxInvoicingExecutionRepository(
    CoreRepository, MxInvoicingExecutionRepositoryInterface
):
    async def add(self, mx_inv_exec: MxInvoicingExecution) -> UUID | NoneType:
        """Add Mx Invoicing Execution

        Parameters
        ----------
        mx_inv_exec : MxInvoicingExecution

        Returns
        -------
        UUID | NoneType
        """
        # create mx invoice
        cvals = domain_to_dict(mx_inv_exec)
        cvals["status"] = cvals["status"].value
        _id = await super().add(
            core_element_name="Mx Invoicing Execution",
            core_element_tablename="mx_invoicing_execution",
            core_query="""
                INSERT INTO mx_invoicing_execution (
                    id,
                    orden_details_id,
                    execution_start,
                    execution_end,
                    status,
                    result
                ) VALUES (
                    :id,
                    :orden_details_id,
                    :execution_start,
                    :execution_end,
                    :status,
                    :result
                )
            """,
            core_values=cvals,
        )
        if _id is not None:
            return cvals["id"]
        return None

    async def fetch(self, orden_details_id: UUID) -> Dict[str, Any]:
        """Fetch Mx Invoicing Execution by Orden Details ID

        Parameters
        ----------
        orden_details_id : UUID

        Returns
        -------
        Dict[str, Any]
        """
        _invexec = await super().fetch(
            id=orden_details_id,
            core_element_name="Mx Invoicing Execution",
            core_element_tablename="mx_invoicing_execution",
            core_columns="*",
            id_key="orden_details_id",
        )
        if _invexec:
            _dic_invexec = sql_to_domain(_invexec, MxInvoicingExecution)
            _dic_invexec["status"] = ExecutionStatusType(_dic_invexec["status"])
            return _dic_invexec
        return {}

    async def edit(self, mx_inv_exec: MxInvoicingExecution) -> bool:
        """Edit Mx Invoicing Execution

        Parameters
        ----------
        mx_inv_exec : MxInvoicingExecution

        Returns
        -------
        bool
        """
        # create mx invoice
        cvals = domain_to_dict(mx_inv_exec, skip=["orden_details_id"])
        cvals["status"] = cvals["status"].value
        return await super().edit(
            core_element_name="Mx Invoicing Execution",
            core_element_tablename="mx_invoicing_execution",
            core_query="""
                UPDATE mx_invoicing_execution SET
                    execution_start = :execution_start,
                    execution_end = :execution_end,
                    status = :status,
                    result = :result
                WHERE id = :id
            """,
            core_values=cvals,
        )


class MxInvoiceComplementRepository(
    CoreRepository, MxInvoiceComplementRepositoryInterface
):
    async def add(self, mx_invoice_complement: MxInvoiceComplement) -> Dict[str, Any]:
        inv_uuid = None
        try:
            # create mx invoice
            inv_uuid = uuid.uuid4()
            cvals = domain_to_dict(
                mx_invoice_complement,
                skip=["created_at", "id", "status", "last_updated"],
            )
            cvals["id"] = inv_uuid
            cvals["status"] = DataTypeDecoder.get_mxinvoice_status_key(
                mx_invoice_complement.status.value
            )
            if not isinstance(cvals["sat_invoice_uuid"], uuid.UUID):
                cvals["sat_invoice_uuid"] = UUID(cvals["sat_invoice_uuid"])
            await super().add(
                core_element_name="Mx Invoice",
                core_element_tablename="mx_invoice",
                core_query="""
                    INSERT INTO mx_invoice_complement (
                        id,
                        mx_invoice_id,
                        sat_invoice_uuid,
                        invoice_number,
                        invoice_provider_id,
                        invoice_provider,
                        pdf_file,
                        xml_file,
                        result,
                        total,
                        status,
                        created_by
                    ) VALUES (
                        :id,
                        :mx_invoice_id,
                        :sat_invoice_uuid,
                        :invoice_number,
                        :invoice_provider_id,
                        :invoice_provider,
                        :pdf_file,
                        :xml_file,
                        :result,
                        :total,
                        :status,
                        :created_by
                    )
                """,
                core_values=cvals,
            )
            return {
                "id": inv_uuid,
                "success": True,
            }
        except Exception as e:
            logger.error(e)
            logger.warning("Error creating Mx Invoice")
            return {
                "id": inv_uuid,
                "success": False,
            }

    async def fetch_next_folio(self) -> int:
        count_list = await super().find(
            core_element_name="Mx Invoice Complement",
            core_element_tablename="mx_invoice_complement",
            filter_values=None,
            core_columns="count(1) as count",
            values={},
        )
        if not count_list:
            return 1
        return count_list[0]["count"] + 1

    async def find_by_many(self, mx_invoice_complement_ids=List[UUID]) -> List[Any]:
        mxi_s = await super().find(
            core_element_name="Mx Invoice Complement",
            core_element_tablename="mx_invoice_complement",
            filter_values=f"id IN {mx_invoice_complement_ids}",
            core_columns="*",
            values={},
        )
        if not mxi_s:
            return []
        return mxi_s

    async def find_by_invoice(self, mx_invoice_id: UUID) -> List[MxInvoice]:
        mxi_s = await super().find(
            core_element_name="Mx Invoice Complement",
            core_element_tablename="mx_invoice_complement",
            filter_values="mx_invoice_id = :mx_invoice_id",
            core_columns="*",
            values={"mx_invoice_id": mx_invoice_id},
        )
        if not mxi_s:
            return []
        invoices_com = []
        for mxi in mxi_s:
            invoices_com.append(MxInvoiceComplement(**dict(mxi)))
        return invoices_com
