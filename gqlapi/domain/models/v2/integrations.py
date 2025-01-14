from abc import ABC
from uuid import UUID
from typing import Optional
from datetime import datetime

from strawberry import type as strawberry_type


@strawberry_type
class IntegrationOrden(ABC):
    id: UUID
    integrations_partner_id: UUID
    orden_id: UUID
    integrations_orden_id: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    reason: Optional[str] = None
    result: Optional[str] = None

    def new(self, *args) -> "IntegrationOrden":
        raise NotImplementedError

    def get(self, id: UUID) -> "IntegrationOrden":
        raise NotImplementedError


@strawberry_type
class IntegrationPartner(ABC):
    id: UUID
    integrator_name: UUID
    description: Optional[str] = None
    business_id: UUID
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    def new(self, *args) -> "IntegrationPartner":
        raise NotImplementedError

    def get(self, id: UUID) -> "IntegrationPartner":
        raise NotImplementedError


@strawberry_type
class WorkflosVars(ABC):
    id: UUID
    supplier_business_id: UUID
    vars: str
    created_at: Optional[datetime] = None

    def new(self, *args) -> "WorkflosVars":
        raise NotImplementedError

    def get(self, id: UUID) -> "WorkflosVars":
        raise NotImplementedError


@strawberry_type
class IntegrationWebhook(ABC):
    id: UUID
    url: str
    source_type: str
    created_at: Optional[datetime] = None

    def new(self, *args) -> "IntegrationWebhook":
        raise NotImplementedError

    def get(self, id: UUID) -> "IntegrationWebhook":
        raise NotImplementedError


@strawberry_type
class WorkflowIntegration(ABC):
    id: UUID
    supplier_business_id: UUID
    script_task: str
    task_type: str
    customer_type: str
    created_at: Optional[datetime] = None

    def new(self, *args) -> "WorkflowIntegration":
        raise NotImplementedError

    def get(self, id: UUID) -> "WorkflowIntegration":
        raise NotImplementedError
