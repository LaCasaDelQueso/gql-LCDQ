from datetime import datetime
import logging
from types import NoneType
from typing import List, Optional, Dict, Any
from uuid import UUID
from gqlapi.domain.interfaces.v2.integrations.integrations import (
    IntegrationOrdenRepositoryInterface,
    IntegrationPartnerRepositoryInterface,
    IntegrationWebhookRepositoryInterface,
)
from gqlapi.domain.models.v2.integrations import (
    IntegrationOrden,
    IntegrationPartner,
    IntegrationWebhook,
    WorkflosVars,
    WorkflowIntegration,
)
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple


class IntegrationsOrdenRepository(CoreRepository, IntegrationOrdenRepositoryInterface):
    async def add(
        self,
        integration_orden: IntegrationOrden,
    ) -> UUID | NoneType:
        """Create IntegrationOrden

        Args:
            integration_orden: IntegrationOrden

        Returns:
            UUID: unique integration_orden id
        """
        # Contruct values
        vals = {}
        for k, v in integration_orden.__dict__.items():
            if (
                k not in ["created_at", "last_updated", "integrations_orden_id"]
                and v is not None
            ):
                vals[k] = v

        # call super method from add
        _id = await super().add(
            core_element_tablename="integrations_orden",
            core_element_name="Integration Orden",
            core_query="""INSERT INTO integrations_orden
                (id,
                integrations_partner_id,
                orden_id,
                status
                )
                    VALUES
                    (:id,
                    :integrations_partner_id,
                    :orden_id,
                    :status
                    )
                """,
            core_values=vals,
        )
        if _id and isinstance(_id, UUID):
            return _id
        return None

    async def edit(self, integration_orden: IntegrationOrden) -> bool:
        """Update integration_orden

        Args:
            integration_orden: IntegrationOrden

        Raises:
            GQLApiException: _description_

        Returns:
            bool: _description_
        """

        b_attrs = []
        b_values: Dict[str, Any] = {"id": integration_orden.id}

        if integration_orden.integrations_orden_id:
            b_attrs.append(" integrations_orden_id=:integrations_orden_id")
            b_values["integrations_orden_id"] = integration_orden.integrations_orden_id
        if integration_orden.status:
            b_attrs.append(" status=:status")
            b_values["status"] = integration_orden.status
        if integration_orden.reason:
            b_attrs.append(" reason=:reason")
            b_values["reason"] = integration_orden.reason
        if integration_orden.result:
            b_attrs.append(" result=:result")
            b_values["result"] = integration_orden.result

        if len(b_attrs) == 0:
            logging.warning("No data to update IntegrationOrden")
            return True

        b_attrs.append(" last_updated=:last_updated")
        b_values["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE integrations_orden
                            SET {','.join(b_attrs)}
                            WHERE id=:id;
                        """
        return await super().edit(
            core_element_name="integrations_orden",
            core_query=branch_query,
            core_values=b_values,
        )

    async def get_muiltiple_ordenes_ids(
        self, orden_ids: List
    ) -> List[IntegrationOrden]:
        """Get ordenes by ids

        Args:
            orden_ids: unique id list of orden

        Returns:
            UUID: unique integration_orden id
        """
        """Get Restaurant Business

        Args:
            id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: integration_partner model dict
        """
        if orden_ids:
            filter_values = f" orden_id in {list_into_strtuple(orden_ids)}"
        else:
            return []
        _data = await super().find(
            core_element_tablename="integrations_orden",
            core_element_name="integrations_orden",
            core_columns="*",
            filter_values=filter_values,
            values={},
        )
        if not _data:
            return []
        return [
            IntegrationOrden(**sql_to_domain(data, IntegrationOrden)) for data in _data
        ]


class IntegrationsPartnerRepository(
    CoreRepository, IntegrationPartnerRepositoryInterface
):
    async def get(
        self, id: Optional[UUID] = None, name: Optional[str] = None
    ) -> IntegrationPartner | NoneType:
        """Get partner

        Args:
            id: unique id of partner
            name: name of partner

        Returns:
            Object: IntegrationPartner
        """
        """

        Args:
            id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: integration_partner model dict
        """
        if id:
            search_id = id
            id_key = "id"
        elif name:
            search_id = name
            id_key = "integrator_name"
        else:
            return None
        _data = await super().fetch(
            id=search_id,
            id_key=id_key,
            core_element_tablename="integrations_partner",
            core_element_name="integrations_partner",
            core_columns="*",
        )
        if not _data:
            return None
        return IntegrationPartner(**sql_to_domain(_data, IntegrationPartner))


class IntegrationWebhookRepository(
    CoreRepository, IntegrationWebhookRepositoryInterface
):
    async def get(
        self, id: Optional[UUID] = None, source_type: Optional[str] = None
    ) -> IntegrationWebhook | NoneType:
        """Get partner

        Args:
            id: unique id of partner
            source_type: name of source_type

        Returns:
            Object: IntegrationWeebhook
        """
        """

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: IntegrationWeebhook model | NoneType
        """
        if id:
            search_id = id
            id_key = "id"
        elif source_type:
            search_id = source_type
            id_key = "source_type"
        else:
            return None
        _data = await super().fetch(
            id=search_id,
            id_key=id_key,
            core_element_tablename="integrations_webhook",
            core_element_name="integrations_webhook",
            core_columns="*",
        )
        if not _data:
            return None
        return IntegrationWebhook(**sql_to_domain(_data, IntegrationWebhook))

    async def fetch_workflow_vars(
        self, supplier_business_id: UUID
    ) -> WorkflosVars | NoneType:
        """Get workflow vars

        Args:
            supplier_business_id: unique id of supplier_business

        Returns:
            Object: WorkflosVars
        """
        """

        Args:
            supplier_business_id (UUID): unique supplier_business_id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: WorkflosVars model | NoneType
        """
        _data = await super().fetch(
            id=supplier_business_id,
            id_key="supplier_business_id",
            core_element_tablename="workflow_vars",
            core_element_name="workflow_vars",
            core_columns="*",
        )
        if not _data:
            return None
        return WorkflosVars(**sql_to_domain(_data, WorkflosVars))

    async def fetch_workflos_integration(
        self, supplier_business_id: UUID, task_type: str
    ) -> WorkflowIntegration | NoneType:
        """Get workflow integrations

        Args:
            supplier_business_id: unique id of supplier_business
            task_type: task type

        Returns:
            Object: WorkflosIntegration
        """
        """

        Args:
            supplier_business_id (UUID): unique supplier_business_id
            task_type: task type

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: WorkflosIntegration model | NoneType
        """

        _data = await super().find(
            core_element_tablename="workflow_integrations",
            core_element_name="workflow_integrations",
            core_columns="*",
            filter_values="supplier_business_id=:supplier_business_id AND task_type=:task_type",
            values={
                "supplier_business_id": supplier_business_id,
                "task_type": task_type,
            },
        )
        if not _data:
            return None
        return WorkflowIntegration(**sql_to_domain(_data[0], WorkflowIntegration))
