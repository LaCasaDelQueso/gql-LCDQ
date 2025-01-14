from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    SupplierRestaurantsRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import SupplierRestaurantRelation
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


class SupplierRestaurantsRepository(
    CoreRepository, SupplierRestaurantsRepositoryInterface
):
    async def add(
        self, supplier_restaurant_relation: SupplierRestaurantRelation
    ) -> UUID | NoneType:
        """Add a new SupplierRestaurantRelation

        Parameters
        ----------
        supplier_restaurant_relation : SupplierRestaurantRelation

        Returns
        -------
        UUID | NoneType
        """
        ser_dict = domain_to_dict(
            supplier_restaurant_relation, skip=["created_at", "last_updated"]
        )
        _id = await super().add(
            core_element_name="Supplier Restaurant Relation",
            core_element_tablename="supplier_restaurant_relation",
            core_query="""
                INSERT INTO supplier_restaurant_relation (
                    id,
                    supplier_unit_id,
                    restaurant_branch_id,
                    approved,
                    priority,
                    rating,
                    review,
                    created_by
                ) VALUES (
                    :id,
                    :supplier_unit_id,
                    :restaurant_branch_id,
                    :approved,
                    :priority,
                    :rating,
                    :review,
                    :created_by
                )
            """,
            core_values=ser_dict,
        )
        if _id and isinstance(_id, UUID):
            return _id
        return None

    async def edit(
        self, supplier_restaurant_relation: SupplierRestaurantRelation
    ) -> bool:
        """

        Parameters
        ----------
        supplier_restaurant_relation : SupplierRestaurantRelation

        Returns
        -------
        bool
        """
        ser_dict = domain_to_dict(
            supplier_restaurant_relation, skip=["id", "created_at", "last_updated"]
        )
        qry = "UPDATE supplier_restaurant_relation SET "
        q_vals = {}
        for key, val in ser_dict.items():
            if val is not None:
                qry += f"{key} = :{key}, "
                q_vals[key] = val
        if len(q_vals) == 0:
            logger.warning("No values to update")
            return True
        # add last updated
        qry += "last_updated = now() "
        qry += "WHERE id = :id"
        q_vals["id"] = supplier_restaurant_relation.id
        # call super method
        return await super().edit(
            core_element_name="Supplier Restaurant Relation",
            core_element_tablename="supplier_restaurant_relation",
            core_query=qry,
            core_values=q_vals,
        )

    async def fetch(
        self,
        supplier_restaurant_relation_id: UUID,
    ) -> Dict[str, Any]:
        """Fetch Supplier Restaurant Relation by ID

        Parameters
        ----------
        supplier_restaurant_relation_id : UUID

        Returns
        -------
        Dict[str, Any]
        """
        res = await super().fetch(
            core_element_name="Supplier Restaurant Relation",
            core_element_tablename="supplier_restaurant_relation",
            core_columns="*",
            id_key="id",
            id=supplier_restaurant_relation_id,
        )
        if not res:
            return {}
        return sql_to_domain(res, SupplierRestaurantRelation)

    async def reasign(
        self,
        restaurant_branch_id: UUID,
        supplier_unit_id: UUID,
        set_supplier_unit_id: UUID,
    ):
        query = """UPDATE supplier_restaurant_relation SET supplier_unit_id= :set_supplier_unit_id
            WHERE
            supplier_unit_id= :supplier_unit_id AND
            restaurant_branch_id= :restaurant_branch_id"""
        await super().execute(
            query=query,
            core_element_name="Restaurant Supplier Relation",
            values={
                "restaurant_branch_id": restaurant_branch_id,
                "supplier_unit_id": supplier_unit_id,
                "set_supplier_unit_id": set_supplier_unit_id,
            },
        )

    async def exists(self, restaurant_branch_id, supplier_unit_id) -> bool:
        val = await super().find(
            core_element_name="supplier_restaurant_relation",
            core_element_tablename="Supplier Restaurant Relation",
            values={
                "restaurant_branch_id": restaurant_branch_id,
                "supplier_unit_id": supplier_unit_id,
            },
            core_columns="id",
            filter_values="",
        )
        if val:
            return True
        return False

    async def search_supplier_business_restaurant(
        self,
        supplier_business_id: UUID,
        restaurant_branch_name: Optional[str] = None,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> List[SupplierRestaurantRelation]:
        """Search for a restaurant branch with the same name
            that has related supplier_restaurant_relation within
            the same supplier business

        Parameters
        ----------
        supplier_business_id : UUID
        restaurant_branch_name : str
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierRestaurantRelation]
        """
        qry = """
            SELECT
                srr.*
            FROM supplier_restaurant_relation srr
            LEFT JOIN supplier_unit su ON su.id = srr.supplier_unit_id
            LEFT JOIN restaurant_branch rb ON rb.id = srr.restaurant_branch_id
            WHERE
                su.supplier_business_id = :supplier_business_id
        """
        if restaurant_branch_name:
            qry += """
            AND
                rb.branch_name = :branch_name
            """
            _val = {
                "supplier_business_id": supplier_business_id,
                "branch_name": restaurant_branch_name,
            }
        elif restaurant_branch_id:
            qry += """
            AND
                rb.id = :restaurant_branch_id
            """
            _val = {
                "supplier_business_id": supplier_business_id,
                "restaurant_branch_id": restaurant_branch_id,
            }
        else:
            return []
        res = await super().raw_query(
            qry,
            _val,
        )
        if not res:
            return []
        return [SupplierRestaurantRelation(**dict(row)) for row in res]

    async def fetch_by_restaurant_branch(
        self,
        restaurant_branch_id: UUID,
    ) -> SupplierRestaurantRelation | NoneType:
        res = await super().fetch(
            core_element_name="Supplier Restaurant Relation",
            core_element_tablename="supplier_restaurant_relation",
            core_columns="*",
            id_key="restaurant_branch_id",
            id=restaurant_branch_id,
        )
        if not res:
            return None
        return SupplierRestaurantRelation(
            **sql_to_domain(res, SupplierRestaurantRelation)
        )

    async def fetch_clients_to_export(
        self,
        supplier_business_id: UUID,
    ) -> List[Dict[Any, Any]]:
        """Get products by supplier business

        Parameters
        ----------
        supplier_business_id : UUID

        Returns
        -------
        List[Dict[str, Any]]
        """
        values: Dict[str, Any] = {}
        # query
        _clients = await super().find(
            core_element_name="Products",
            partition=f"""with sup_bus as (
                SELECT
                sb.*
                FROM supplier_business sb
                WHERE sb.id = '{supplier_business_id}'
            )
            """,
            core_element_tablename="""
                supplier_unit su
                JOIN sup_bus ON sup_bus.id = su.supplier_business_id
                JOIN supplier_restaurant_relation srr ON srr.supplier_unit_id = su.id
                JOIN restaurant_branch rb ON rb.id = srr.restaurant_branch_id
                LEFT JOIN restaurant_branch_mx_invoice_info rbmxi ON rbmxi.branch_id = rb.id
                LEFT JOIN supplier_restaurant_relation_mx_invoice_options srrmio
                    ON srrmio.supplier_restaurant_relation_id = srr.id
            """,
            core_columns=[
                "rb.restaurant_business_id",
                """rb.branch_name "Nombre del Negocio" """,
                """'' "Nombre Contacto" """,
                """'' "Correo electrónico" """,
                """'' "Teléfono" """,
                """su.unit_name "Cedis Asignado" """,
                """rb.street "Calle" """,
                """rb.external_num "Numero Ext" """,
                """rb.internal_num "Número Int" """,
                """rb.zip_code "Código Postal" """,
                """rb.neighborhood "Colonia" """,
                """rb.city "Municipio o Alcaldía" """,
                """rb.state "Estado" """,
                """rb.country "Pais" """,
                """rbmxi.sat_regime "Régimen Fiscal" """,
                """rbmxi.legal_name "Nombre o Razón Social" """,
                """rbmxi.full_address "Dirección Fiscal" """,
                """rbmxi.cfdi_use "Uso CFDI" """,
                """rbmxi.zip_code "CP Facturación" """,
                """rbmxi.email "Email Facturación" """,
                """srrmio.invoice_type "Tipo de Factura" """,
                """(
                CASE WHEN srrmio.triggered_at = 'deactivated' THEN 'Desactivada'
                    WHEN srrmio.triggered_at = 'at_delivery' THEN 'Al Marcar Entregado'
                    WHEN srrmio.triggered_at = 'at_purchase' THEN 'Al Confirmar'
                    ELSE srrmio.triggered_at
                END
            ) "Facturación Automática" """,
            ],
            filter_values=" rb.deleted <> 't' ORDER BY 1",
            values=values,
        )
        if _clients:
            return [dict(_prod) for _prod in _clients]
        else:
            return []
