# Repository Interfaces
from abc import ABC, abstractmethod
from types import NoneType
from typing import List, Optional
from uuid import UUID

from gqlapi.domain.models.v2.integrations import (
    IntegrationOrden,
    IntegrationPartner,
    IntegrationWebhook,
    WorkflosVars,
    WorkflowIntegration,
)


class IntegrationPartnerHandlerInterface(ABC):
    @abstractmethod
    async def get_by_name(self, name: str) -> IntegrationPartner | NoneType:
        raise NotImplementedError


class IntegrationPartnerRepositoryInterface(ABC):
    @abstractmethod
    async def get(
        self, id: Optional[UUID] = None, name: Optional[str] = None
    ) -> IntegrationPartner | NoneType:
        raise NotImplementedError


class IntegrationWebhookHandlerInterface(ABC):
    @abstractmethod
    async def get_by_source_type(
        self, source_type: str
    ) -> IntegrationWebhook | NoneType:
        raise NotImplementedError

    async def get_vars(
        self,
        supplier_business_id: UUID,
    ) -> WorkflosVars | NoneType:
        raise NotImplementedError

    async def get_workflow_integration(
        self,
        task_type: str,
        supplier_business_id: UUID,
    ) -> WorkflowIntegration | NoneType:
        raise NotImplementedError


class IntegrationOrdenRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        integration_orden: IntegrationOrden,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        integration_orden: IntegrationOrden,
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def get_muiltiple_ordenes_ids(
        self, orden_ids: List
    ) -> List[IntegrationOrden]:
        raise NotImplementedError


class IntegrationWebhookRepositoryInterface(ABC):
    @abstractmethod
    async def get(
        self, id: Optional[UUID] = None, source_type: Optional[str] = None
    ) -> IntegrationWebhook | NoneType:
        raise NotImplementedError

    async def fetch_workflow_vars(
        self,
        supplier_business_id: UUID,
    ) -> WorkflosVars | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def fetch_workflos_integration(
        self, task_type: str, supplier_business_id: UUID
    ) -> WorkflowIntegration | NoneType:
        raise NotImplementedError
