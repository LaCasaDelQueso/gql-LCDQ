import base64
from datetime import date, datetime
from types import NoneType
from typing import Any, Dict, List, Optional, Sequence
from uuid import UUID
from gqlapi.domain.interfaces.v2.orden.orden import (
    MxInvoiceComplementGQL,
    OrdenDetailsRepositoryInterface,
    OrdenPaymentStatusRepositoryInterface,
    OrdenRepositoryInterface,
    OrdenStatusRepositoryInterface,
    PaymentReceiptGQL,
    PaymentReceiptOrdenGQL,
)
from gqlapi.domain.models.v2.core import (
    Orden,
    OrdenDetails,
    OrdenPayStatus,
    OrdenStatus,
    PaymentReceipt,
    PaymentReceiptOrden,
)
from gqlapi.domain.models.v2.utils import (
    DataTypeDecoder,
    OrdenSourceType,
    OrdenType,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple


# logger
logger = get_logger(get_app())


class OrdenRepository(CoreRepository, OrdenRepositoryInterface):
    async def new(
        self,
        orden: Orden,
    ) -> UUID:
        """Create New Orden

        Args:
            orden (Orden): Orden object

        Returns:
            UUID: unique orden id
        """
        # cast to dict
        core_vals = domain_to_dict(orden, skip=["created_at", "last_updated"])
        core_vals["orden_type"] = core_vals["orden_type"].value
        if core_vals["source_type"]:
            core_vals["source_type"] = core_vals["source_type"].value
        else:
            core_vals["source_type"] = OrdenSourceType.AUTOMATION.value
        # call super method from new

        await super().new(
            core_element_tablename="orden",
            core_element_name="Orden",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden
                (id,
                orden_type,
                source_type,
                created_by
                )
                    VALUES
                    (:id,
                    :orden_type,
                    :source_type,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    async def add(
        self,
        orden: Orden,
    ) -> NoneType | UUID:
        """Create New Orden

        Args:
            orden (Orden): Orden object

        Returns:
            UUID: unique orden id
        """
        # cast to dict
        core_vals = domain_to_dict(orden, skip=["created_at", "last_updated"])
        core_vals["orden_type"] = core_vals["orden_type"].value
        if core_vals["source_type"]:
            core_vals["source_type"] = core_vals["source_type"].value
        else:
            core_vals["source_type"] = OrdenSourceType.AUTOMATION.value
        # call super method from new

        validation = await super().add(
            core_element_tablename="orden",
            core_element_name="Orden",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden
                (id,
                orden_type,
                orden_number,
                source_type,
                created_by
                )
                    VALUES
                    (:id,
                    :orden_type,
                    :orden_number,
                    :source_type,
                    :created_by)
                """,
            core_values=core_vals,
        )
        if not validation:
            return None
        return core_vals["id"]

    async def get(
        self,
        orden_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Model dict
        """
        orden = await super().get(
            id=orden_id,
            core_element_tablename="orden",
            core_element_name="Orden",
            core_columns="*",
        )
        return sql_to_domain(orden, Orden)

    async def fetch(
        self,
        orden_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Model dict
        """
        orden = await super().fetch(
            id=orden_id,
            core_element_tablename="orden",
            core_element_name="Orden",
            core_columns="*",
        )
        if orden:
            return sql_to_domain(orden, Orden)
        return {}

    async def update(self, orden_id: UUID, orden_type: OrdenType) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        core_atributes = []
        core_values_view: Dict[str, Any] = {"id": orden_id}

        if orden_type:
            core_atributes.append(" orden_type=:orden_type")
            core_values_view["orden_type"] = orden_type.value

        if len(core_atributes) == 0:
            raise GQLApiException(
                msg="Issues no data to update in sql",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )

        branch_query = f"""UPDATE orden
                            SET {','.join(core_atributes)}
                            WHERE id=:id;
                """
        await super().update(
            core_element_name="Orden",
            core_query=branch_query,
            core_values=core_values_view,
        )
        return True

    async def exist(
        self,
        orden_id: UUID,
    ) -> NoneType:
        """Validate orden exists

        Args:
            orden_id (UUID): unique orden id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=orden_id,
            core_columns="id",
            core_element_tablename="orden",
            id_key="id",
            core_element_name="Orden",
        )

    async def validation(
        self,
        orden_id: UUID,
    ) -> bool:
        """Validate orden exists

        Args:
            orden_id (UUID): unique orden id

        Returns:
            NoneType: None
        """
        return await super().exists(
            id=orden_id,
            core_columns="id",
            core_element_tablename="orden",
            id_key="id",
            core_element_name="Orden",
        )

    async def get_orders(
        self, filter_values: str | None, info_values_view: Dict[Any, Any]
    ) -> Sequence:  # type: ignore
        _resp = await super().search(
            core_element_name="Ordenes",
            partition="""WITH
            status_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) status_row_num
                FROM orden_status),
            paystatus_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) paystatus_row_num
                FROM orden_paystatus),
            details_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY version DESC) details_row_num
                FROM orden_details)""",
            core_element_tablename="""
            orden ord
            JOIN status_cos sc ON ord.id = sc.orden_id
            JOIN paystatus_cos pc ON ord.id = pc.orden_id
            JOIN details_cos dc ON ord.id = dc.orden_id
            """,
            filter_values=filter_values,
            core_columns=[
                "ord.*",
                "row_to_json(sc.*) AS status_json",
                "row_to_json(pc.*) AS paystatus_json",
                "row_to_json(dc.*) AS details_json",
            ],
            values=info_values_view,
        )
        return _resp

    async def find_orders(
        self, filter_values: str | None, info_values_view: Dict[Any, Any]
    ) -> Sequence:  # type: ignore
        _resp = await super().find(
            core_element_name="Ordenes",
            partition="""WITH
            status_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) status_row_num
                FROM orden_status),
            paystatus_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) paystatus_row_num
                FROM orden_paystatus),
            details_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY version DESC) details_row_num
                FROM orden_details)""",
            core_element_tablename="""
            orden ord
            JOIN status_cos sc ON ord.id = sc.orden_id
            JOIN paystatus_cos pc ON ord.id = pc.orden_id
            JOIN details_cos dc ON ord.id = dc.orden_id
            """,
            filter_values=filter_values,
            core_columns=[
                "ord.*",
                "row_to_json(sc.*) AS status_json",
                "row_to_json(pc.*) AS paystatus_json",
                "row_to_json(dc.*) AS details_json",
            ],
            values=info_values_view,
        )
        return _resp

    async def count_by_supplier_business(self, supplier_business_id: UUID) -> int:
        """Validate orden exists

        Args:
            orden_id (UUID): unique orden id

        Returns:
            NoneType: None
        """
        _resp = await super().find(
            core_element_name="Ordenes",
            partition="""WITH
            details_cos AS
                ( SELECT *, ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY version DESC) details_row_num
                FROM orden_details)""",
            core_element_tablename="""
            orden ord
            JOIN details_cos dc ON ord.id = dc.orden_id
            JOIN supplier_unit su ON dc.supplier_unit_id = su.id
            """,
            filter_values="su.supplier_business_id = :supplier_business_id",
            core_columns=[
                "DISTINCT(ord.id)",
            ],
            values={"supplier_business_id": supplier_business_id},
        )
        if _resp:
            return len(_resp)
        return 0

    async def get_by_created_at_range(
        self, supplier_business_id: UUID, from_date: datetime, until_date: datetime
    ) -> List[Dict[Any, Any]]:
        """Get Orden by Dates and additional filters

        Parameters
        ----------
        supplier_unit_id : UUID
        from_date : Optional[date]
        until_date : Optional[date]
        comments : Optional[str]
        page : Optional[int]
        page_size : Optional[int]

        Returns
        -------
        List[Dict[str, Any]]
        """
        # build query filters
        filters = [" su.supplier_business_id = :supplier_business_id "]
        values: Dict[str, Any] = {"supplier_business_id": supplier_business_id}
        if from_date:
            filters.append(" ord.created_at >= :from_date ")
            values["from_date"] = from_date
        if until_date:
            filters.append(" ord.created_at <= :until_date ")
            values["until_date"] = until_date
        filters_str = " AND ".join(filters)
        # query
        _payds = await super().find(
            partition="""WITH last_orden_details AS (
                WITH last_upd AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
                    FROM orden_details
                )
                SELECT * FROM last_upd WHERE row_num = 1
            )
            """,
            core_element_name="Ordenes",
            core_element_tablename="""
                orden ord
                JOIN last_orden_details od
                    ON od.orden_id = ord.id
                JOIN supplier_unit su
                    ON od.supplier_unit_id = su.id
            """,
            core_columns=[
                "ord.*",
                "od.id",
            ],
            filter_values=filters_str,
            values=values,
        )
        if not _payds:
            return []
        return [dict(p) for p in _payds]


class OrdenStatusRepository(CoreRepository, OrdenStatusRepositoryInterface):
    async def new(
        self,
        orden_status: OrdenStatus,
    ) -> bool:
        """Create New Orden Status

        Args:
            orden_status (OrdenStatus): OrdenStatus object

        Returns:
            bool, validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(orden_status, skip=["created_at"])
        core_vals["status"] = DataTypeDecoder.get_orden_status_key(
            core_vals["status"].value
        )
        # call super method from new

        await super().new(
            core_element_tablename="orden_status",
            core_element_name="Orden Status",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden_status
                (id,
                orden_id,
                status,
                created_by
                )
                    VALUES
                    (:id,
                    :orden_id,
                    :status,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return True

    async def add(
        self,
        orden_status: OrdenStatus,
    ) -> UUID | NoneType:
        """Create New Orden Status

        Args:
            orden_status (OrdenStatus): OrdenStatus object

        Returns:
            bool, validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(orden_status, skip=["created_at"])
        core_vals["status"] = DataTypeDecoder.get_orden_status_key(
            core_vals["status"].value
        )
        # call super method from new

        _id = await super().add(
            core_element_tablename="orden_status",
            core_element_name="Orden Status",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden_status
                (id,
                orden_id,
                status,
                created_by
                )
                    VALUES
                    (:id,
                    :orden_id,
                    :status,
                    :created_by)
                """,
            core_values=core_vals,
        )
        if _id and isinstance(_id, UUID):
            return _id
        return None

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        orden_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden Status

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        order_status = await super().get(
            id=orden_id,
            id_key="orden_id",
            core_element_tablename="orden_status",
            core_element_name="Orden Status",
            core_columns="*",
        )
        return sql_to_domain(order_status, OrdenStatus)

    async def fetch(
        self,
        orden_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden Status

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        order_status = await super().fetch(
            id=orden_id,
            id_key="orden_id",
            core_element_tablename="orden_status",
            core_element_name="Orden Status",
            core_columns="*",
        )
        if order_status:
            return sql_to_domain(order_status, OrdenStatus)
        return {}

    @deprecated("Use fetch_last() instead", "gqlapi.repository")
    async def get_last(self, orden_id: UUID) -> Dict[Any, Any]:
        """Get Last Orden Status

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values)

        order_status = await super().get_filter(
            core_element_tablename="orden_status",
            core_element_name="Orden Status",
            core_columns="*",
            partition_key="orden_id",
            order_key="created_at",
            order_filter="DESC",
            values=orden_status_values_view,
            filter_values=filter_values,
        )
        return sql_to_domain(order_status, OrdenStatus)

    async def fetch_last(self, orden_id: UUID) -> Dict[Any, Any]:
        """Get Last Orden Status

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values)

        order_status = await super().fetch_filter(
            core_element_tablename="orden_status",
            core_element_name="Orden Status",
            core_columns="*",
            partition_key="orden_id",
            order_key="created_at",
            order_filter="DESC",
            values=orden_status_values_view,
            filter_values=filter_values,
        )
        if order_status:
            return sql_to_domain(order_status, OrdenStatus)
        return {}

    async def update(self) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        return True

    async def exist(
        self,
        orden_id: UUID,
    ) -> NoneType:
        """Validate orden status exists

        Args:
            orden_id (UUID): unique orden id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=orden_id,
            core_columns="orden_id",
            core_element_tablename="orden_status",
            id_key="orden_id",
            core_element_name="Orden Status",
        )

    async def search(
        self,
        orden_id: UUID,
    ) -> List[OrdenStatus]:
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        ord_stats = await super().search(
            core_element_name="Orden Status",
            core_element_tablename="orden_status",
            filter_values=filter_values,
            core_columns="*",
            values=orden_status_values_view,
        )

        return [OrdenStatus(**sql_to_domain(r, OrdenStatus)) for r in ord_stats]


class OrdenPaymentStatusRepository(
    CoreRepository, OrdenPaymentStatusRepositoryInterface
):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        orden_paystatus: OrdenPayStatus,
    ) -> bool:
        """Create New Orden Paystatus

        Args:
            orden_paystatus (OrdenPaystatus): OrdenOaystatus object

        Returns:
            bool, validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(orden_paystatus, skip=["created_at"])
        if core_vals["status"]:
            core_vals["status"] = DataTypeDecoder.get_orden_paystatus_key(
                core_vals["status"].value
            )
        # call super method from new

        await super().new(
            core_element_tablename="orden_paystatus",
            core_element_name="Orden Paystatus",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden_paystatus
                (id,
                orden_id,
                status,
                created_by
                )
                    VALUES
                    (:id,
                    :orden_id,
                    :status,
                    :created_by)
                """,
            core_values=core_vals,
        )
        return True

    async def add(
        self,
        orden_paystatus: OrdenPayStatus,
    ) -> bool:
        """Create New Orden Paystatus

        Args:
            orden_paystatus (OrdenPaystatus): OrdenOaystatus object

        Returns:
            bool, validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(orden_paystatus, skip=["created_at"])
        if core_vals["status"]:
            core_vals["status"] = DataTypeDecoder.get_orden_paystatus_key(
                core_vals["status"].value
            )
        # call super method from new

        validation = await super().add(
            core_element_tablename="orden_paystatus",
            core_element_name="Orden Paystatus",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden_paystatus
                (id,
                orden_id,
                status,
                created_by
                )
                    VALUES
                    (:id,
                    :orden_id,
                    :status,
                    :created_by)
                """,
            core_values=core_vals,
        )
        if not validation:
            return False
        return True

    async def get(
        self,
        orden_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden Paystatus

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Paystatus Model
        """
        order_paystatus = await super().get(
            id=orden_id,
            id_key="orden_id",
            core_element_tablename="orden_paystatus",
            core_element_name="Orden Paystatus",
            core_columns="*",
        )
        return sql_to_domain(order_paystatus, OrdenPayStatus)

    async def update(self) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        return True

    async def exist(
        self,
        orden_id: UUID,
    ) -> NoneType:
        """Validate orden paystatus exists

        Args:
            orden_id (UUID): unique orden id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=orden_id,
            core_columns="orden_id",
            core_element_tablename="orden_paystatus",
            id_key="orden_id",
            core_element_name="Orden Paytatus",
        )

    @deprecated("Use find() instead", "gqlapi.repository")
    async def search(
        self,
        orden_id: UUID,
    ) -> List[OrdenPayStatus]:
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        ord_stats = await super().search(
            core_element_name="Orden Pay Status",
            core_element_tablename="orden_paystatus",
            filter_values=filter_values,
            core_columns="*",
            values=orden_status_values_view,
        )

        return [OrdenPayStatus(**sql_to_domain(r, OrdenPayStatus)) for r in ord_stats]

    async def get_last(self, orden_id: UUID) -> Dict[Any, Any]:
        """Get Last Orden PayStatus

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values)

        order_status = await super().get_filter(
            core_element_tablename="orden_paystatus",
            core_element_name="Orden Pay Status",
            core_columns="*",
            partition_key="orden_id",
            order_key="created_at",
            order_filter="DESC",
            values=orden_status_values_view,
            filter_values=filter_values,
        )
        return sql_to_domain(order_status, OrdenPayStatus)

    async def find(
        self,
        orden_id: UUID,
    ) -> List[OrdenPayStatus]:
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        ord_stats = await super().find(
            core_element_name="Orden PayStatus",
            core_element_tablename="orden_paystatus",
            filter_values=filter_values,
            core_columns="*",
            values=orden_status_values_view,
        )

        return [OrdenPayStatus(**sql_to_domain(r, OrdenPayStatus)) for r in ord_stats]

    async def find_payment_receipts(
        self,
        orden_id: UUID,
    ) -> List[PaymentReceiptGQL]:
        # find payment receipt ordenes
        pro_s = await super().find(
            core_element_name="Payment Receipt Orden",
            core_element_tablename="payment_receipt_orden",
            filter_values="orden_id=:orden_id AND deleted = 'f'",
            core_columns="*",
            values={"orden_id": orden_id},
        )
        if not pro_s:
            return []
        # from payment receipt ordenes get payment receipts
        pr_s = await super().find(
            core_element_name="Payment Receipt",
            core_element_tablename="payment_receipt",
            filter_values=f"id IN {list_into_strtuple([p['payment_receipt_id'] for p in pro_s])}",
            core_columns="*",
            values={},
        )
        if not pr_s:
            return []
        mx_invoice_complement_ids = []
        for p in pro_s:
            if p["mx_invoice_complement_id"] is not None:
                mx_invoice_complement_ids.append(p["mx_invoice_complement_id"])
        if len(mx_invoice_complement_ids) == 0:
            mxi_s = []
        else:
            mxi_s = await super().find(
                core_element_name="Mx Invoice Complement",
                core_element_tablename="mx_invoice_complement",
                filter_values=f"id IN {list_into_strtuple(mx_invoice_complement_ids)}",
                core_columns="*",
                values={},
            )

        # format payment receipts
        pay_receipts = []
        for pr in pr_s:
            _dict_pr = dict(pr)
            pt_tmp = PaymentReceiptGQL(**_dict_pr)
            pt_tmp.ordenes = []
            for pro in pro_s:
                if pro["payment_receipt_id"] == pr["id"]:
                    _pro = PaymentReceiptOrdenGQL(**dict(pro))
                    for mxi in mxi_s:
                        if pro["mx_invoice_complement_id"] == mxi["id"]:
                            _pro.payment_complement = MxInvoiceComplementGQL(
                                id=mxi["id"],
                                sat_invoice_uuid=mxi["sat_invoice_uuid"],
                                total=mxi["total"],
                                pdf_file=(
                                    base64.b64encode(mxi["pdf_file"]).decode("utf-8")
                                    if isinstance(mxi["pdf_file"], bytes)
                                    else None
                                ),
                                xml_file=(
                                    base64.b64encode(mxi["xml_file"]).decode("utf-8")
                                    if isinstance(mxi["xml_file"], bytes)
                                    else None
                                ),
                            )
                    pt_tmp.ordenes.append(_pro)

            pay_receipts.append(pt_tmp)
        return pay_receipts

    async def fetch_payment_receipt(
        self, payment_receipt_id: UUID
    ) -> PaymentReceipt | NoneType:
        pr_s = await super().fetch(
            core_element_name="Payment Receipt",
            core_element_tablename="payment_receipt",
            id=payment_receipt_id,
        )
        if not pr_s:
            return None
        return PaymentReceipt(**dict(pr_s))

    async def add_payment_receipt(self, receipt: PaymentReceipt) -> bool:
        _vals = domain_to_dict(receipt, skip=["created_at", "last_updated"])
        _check = await super().add(
            core_element_tablename="payment_receipt",
            core_element_name="Payment Receipt",
            core_query="""INSERT INTO payment_receipt
                (
                    id,
                    payment_value,
                    evidence_file,
                    comments,
                    created_by,
                    payment_day
                )
                VALUES (
                    :id,
                    :payment_value,
                    :evidence_file,
                    :comments,
                    :created_by,
                    :payment_day
                )
                """,
            core_values=_vals,
        )
        return True if _check else False

    async def add_payment_receipt_association(
        self,
        receipt_orden: PaymentReceiptOrden,
    ) -> bool:
        if receipt_orden.mx_invoice_complement_id:
            _vals = domain_to_dict(receipt_orden, skip=["created_at"])
            query = """INSERT INTO payment_receipt_orden
                (
                    id,
                    orden_id,
                    payment_receipt_id,
                    mx_invoice_complement_id,
                    deleted,
                    created_by
                )
                VALUES
                    (:id,
                    :orden_id,
                    :payment_receipt_id,
                    :mx_invoice_complement_id
                    :deleted,
                    :created_by)
                """
        else:
            _vals = domain_to_dict(
                receipt_orden, skip=["created_at", "mx_invoice_complement_id"]
            )
            query = """INSERT INTO payment_receipt_orden
                (
                    id,
                    orden_id,
                    payment_receipt_id,
                    deleted,
                    created_by
                )
                VALUES
                    (:id,
                    :orden_id,
                    :payment_receipt_id,
                    :deleted,
                    :created_by)
                """
        _check = await super().add(
            core_element_tablename="payment_receipt_orden",
            core_element_name="Payment Receipt Orden",
            core_query=query,
            core_values=_vals,
        )
        return True if _check else False

    async def edit_payment_receipt(self, receipt: PaymentReceipt) -> bool:
        _vals = domain_to_dict(
            receipt, skip=["created_by", "created_at", "last_updated"]
        )
        _vals["last_updated"] = datetime.utcnow()
        return await super().edit(
            core_element_tablename="payment_receipt",
            core_element_name="Payment Receipt",
            core_query="""UPDATE payment_receipt
                SET
                    payment_value = :payment_value,
                    evidence_file = :evidence_file,
                    comments = :comments,
                    last_updated = :last_updated,
                    payment_day= :payment_day
                WHERE id = :id
                """,
            core_values=_vals,
        )

    async def _delete_payment_receipt_orden(
        self,
        payment_receipt_orden_id: UUID,
    ) -> bool:
        return await super().edit(
            core_element_tablename="payment_receipt_orden",
            core_element_name="Payment Receipt Orden",
            core_query="""UPDATE payment_receipt_orden
                SET
                    deleted = 't'
                WHERE id = :id
                """,
            core_values={"id": payment_receipt_orden_id},
        )

    async def edit_payment_receipt_association(
        self,
        receipt_ordens: List[PaymentReceiptOrden],
    ) -> bool:
        # get all the payment receipt orden ids from current payment receipt
        _ids = await super().find(
            core_element_name="Payment Receipt Orden",
            core_element_tablename="payment_receipt_orden",
            filter_values="payment_receipt_id = :payment_receipt_id AND deleted = 'f'",
            core_columns="id",
            values={"payment_receipt_id": receipt_ordens[0].payment_receipt_id},
        )
        # set the payment receipt orden as deleted
        for _id in _ids:
            if not await self._delete_payment_receipt_orden(_id["id"]):
                logger.warning(f"Payment Receipt Orden not able to be deleted: ({_id})")
                return False
        # create new payment receipt ordenes
        for r in receipt_ordens:
            if not await self.add_payment_receipt_association(r):
                logger.warning(
                    f"Payment Receipt Orden not able to be created: ({r.id})"
                )
                return False
        return True

    async def add_payment_complement_receipt_association(
        self,
        payment_receipt_orden_id: UUID,
        mx_invoice_complement_id: UUID,
    ) -> bool:
        return await super().edit(
            core_element_tablename="payment_receipt_orden",
            core_element_name="Payment Receipt Orden",
            core_query="""UPDATE payment_receipt_orden
                SET
                    mx_invoice_complement_id = :mx_invoice_complement_id
                WHERE id = :id
                """,
            core_values={
                "id": payment_receipt_orden_id,
                "mx_invoice_complement_id": mx_invoice_complement_id,
            },
        )

    async def find_payment_receipts_by_dates(
        self,
        supplier_unit_id: UUID,
        from_date: Optional[date] = None,
        until_date: Optional[date] = None,
        comments: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> List[Dict[Any, Any]]:
        """Get Multiple Payment Details by Dates and additional filters

        Parameters
        ----------
        supplier_unit_id : UUID
        from_date : Optional[date]
        until_date : Optional[date]
        comments : Optional[str]
        page : Optional[int]
        page_size : Optional[int]

        Returns
        -------
        List[Dict[str, Any]]
        """
        # build query filters
        filters = [" od.supplier_unit_id = :supplier_unit_id ", " pro.deleted = 'f' "]
        values: Dict[str, Any] = {"supplier_unit_id": supplier_unit_id}
        if from_date:
            filters.append(" pr.created_at >= :from_date ")
            values["from_date"] = from_date
        if until_date:
            filters.append(" pr.created_at <= :until_date ")
            values["until_date"] = until_date
        if comments:
            filters.append(
                " pr.comments ILIKE :comments or TO_CHAR(pr.payment_day, 'YYYY-MM-DD') ILIKE :comments"
            )
            values["comments"] = "%" + comments + "%"
        filters_str = " AND ".join(filters)
        filters_str += " ORDER BY pr.created_at LIMIT :page_size OFFSET :offset "
        values["page_size"] = page_size
        values["offset"] = (page - 1) * page_size
        # query
        _payds = await super().find(
            partition="""WITH last_orden_details AS (
                WITH last_upd AS (
                    SELECT
                        *,
                        ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
                    FROM orden_details
                )
                SELECT * FROM last_upd WHERE row_num = 1
            )
            """,
            core_element_name="Payment Receipt",
            core_element_tablename="""
                payment_receipt pr
                JOIN payment_receipt_orden pro
                    ON pr.id = pro.payment_receipt_id
                JOIN last_orden_details od
                    ON od.orden_id = pro.orden_id
            """,
            core_columns=[
                "pr.*",
                "od.orden_id",
                "pro.id as pro_id",
                "od.id as orden_details_id",
                "pro.deleted as pro_deleted",
                "pro.created_by as pro_created_by",
                "pro.created_at as pro_created_at",
                "pro.mx_invoice_complement_id as mx_invoice_complement_id",
            ],
            filter_values=filters_str,
            values=values,
        )
        if not _payds:
            return []
        return [dict(p) for p in _payds]


class OrdenDetailsRepository(CoreRepository, OrdenDetailsRepositoryInterface):
    async def new(
        self,
        orden_details: OrdenDetails,
    ) -> bool:
        """Create New Orden Details

        Args:
            orden_details (OrdenDetails): OrdenDetails object

        Returns:
            bool, validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(orden_details, skip=["created_at"])
        if core_vals["payment_method"]:
            core_vals["payment_method"] = core_vals["payment_method"].value
        if core_vals["delivery_time"]:
            core_vals["delivery_time"] = (core_vals["delivery_time"]).__str__()
        if core_vals["delivery_date"]:
            core_vals["delivery_date"] = core_vals["delivery_date"]
        if core_vals["delivery_type"]:
            core_vals["delivery_type"] = core_vals["delivery_type"].value
        # call super method from new

        await super().new(
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden_details
                (id,
                orden_id,
                version,
                restaurant_branch_id,
                supplier_unit_id,
                cart_id,
                delivery_date,
                delivery_time,
                delivery_type,
                subtotal_without_tax,
                tax,
                subtotal,
                discount,
                discount_code,
                cashback,
                cashback_transation_id,
                shipping_cost,
                packaging_cost,
                service_fee,
                total,
                comments,
                payment_method,
                created_by,
                approved_by
                )
                    VALUES
                    (:id,
                    :orden_id,
                    :version,
                    :restaurant_branch_id,
                    :supplier_unit_id,
                    :cart_id,
                    :delivery_date,
                    :delivery_time,
                    :delivery_type,
                    :subtotal_without_tax,
                    :tax,
                    :subtotal,
                    :discount,
                    :discount_code,
                    :cashback,
                    :cashback_transation_id,
                    :shipping_cost,
                    :packaging_cost,
                    :service_fee,
                    :total,
                    :comments,
                    :payment_method,
                    :created_by,
                    :approved_by)
                    """,
            core_values=core_vals,
        )

        return core_vals["id"]

    async def add(
        self,
        orden_details: OrdenDetails,
    ) -> NoneType | UUID:
        """Create New Orden Details

        Args:
            orden_details (OrdenDetails): OrdenDetails object

        Returns:
            bool, validate create is done
        """
        # cast to dict
        core_vals = domain_to_dict(orden_details, skip=["created_at"])
        if core_vals["payment_method"]:
            core_vals["payment_method"] = core_vals["payment_method"].value
        if core_vals["delivery_time"]:
            core_vals["delivery_time"] = (core_vals["delivery_time"]).__str__()
        if core_vals["delivery_date"]:
            core_vals["delivery_date"] = core_vals["delivery_date"]
        if core_vals["delivery_type"]:
            core_vals["delivery_type"] = core_vals["delivery_type"].value
        # call super method from new

        validation = await super().add(
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO orden_details
                (id,
                orden_id,
                version,
                restaurant_branch_id,
                supplier_unit_id,
                cart_id,
                delivery_date,
                delivery_time,
                delivery_type,
                subtotal_without_tax,
                tax,
                subtotal,
                discount,
                discount_code,
                cashback,
                cashback_transation_id,
                shipping_cost,
                packaging_cost,
                service_fee,
                total,
                comments,
                payment_method,
                created_by,
                approved_by
                )
                    VALUES
                    (:id,
                    :orden_id,
                    :version,
                    :restaurant_branch_id,
                    :supplier_unit_id,
                    :cart_id,
                    :delivery_date,
                    :delivery_time,
                    :delivery_type,
                    :subtotal_without_tax,
                    :tax,
                    :subtotal,
                    :discount,
                    :discount_code,
                    :cashback,
                    :cashback_transation_id,
                    :shipping_cost,
                    :packaging_cost,
                    :service_fee,
                    :total,
                    :comments,
                    :payment_method,
                    :created_by,
                    :approved_by)
                    """,
            core_values=core_vals,
        )
        if not validation:
            return None
        return core_vals["id"]

    async def get(
        self,
        orden_details_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden Details

        Args:
            orden_details_id (UUID): unique orden details id

        Returns:
            Dict: Orden Details Model
        """
        order_details = await super().get(
            id=orden_details_id,
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
            core_columns="*",
        )
        return sql_to_domain(order_details, OrdenDetails)

    async def fetch(
        self,
        orden_details_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Orden Details

        Args:
            orden_details_id (UUID): unique orden details id

        Returns:
            Dict: Orden Details Model
        """
        order_details = await super().fetch(
            id=orden_details_id,
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
            core_columns="*",
        )
        if order_details:
            return sql_to_domain(order_details, OrdenDetails)
        else:
            return {}

    async def get_last(self, orden_id: UUID) -> Dict[Any, Any]:
        """Get Last Orden Details

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values)

        order_status = await super().get_filter(
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
            core_columns="*",
            partition_key="orden_id",
            order_key="version",
            order_filter="DESC",
            values=orden_status_values_view,
            filter_values=filter_values,
        )
        return sql_to_domain(order_status, OrdenDetails)

    async def fetch_last(self, orden_id: UUID) -> Dict[Any, Any]:
        """Get Last Orden Details

        Args:
            orden_id (UUID): unique orden id

        Returns:
            Dict: Orden Status Model
        """
        orden_status_atributes = []
        orden_status_values_view = {}
        if orden_id:
            orden_status_atributes.append(" orden_id=:orden_id and")
            orden_status_values_view["orden_id"] = orden_id

        if len(orden_status_atributes) == 0:
            filter_values = None
        else:
            filter_values = ",".join(orden_status_atributes).split()
            filter_values = " ".join(filter_values)

        order_details = await super().fetch_filter(
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
            core_columns="*",
            partition_key="orden_id",
            order_key="version",
            order_filter="DESC",
            values=orden_status_values_view,
            filter_values=filter_values,
        )
        if order_details:
            return sql_to_domain(order_details, OrdenDetails)
        else:
            return {}

    async def update(self) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        return True

    async def exist(
        self,
        orden_details_id: UUID,
    ) -> NoneType:
        """Validate orden details exists

        Args:
            orden_details_id (UUID): unique orden details id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=orden_details_id,
            core_columns="id",
            core_element_tablename="orden_details",
            core_element_name="Orden Details",
        )
