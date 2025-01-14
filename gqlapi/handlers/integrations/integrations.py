from types import NoneType
from uuid import UUID
from gqlapi.domain.interfaces.v2.integrations.integrations import (
    IntegrationPartnerHandlerInterface,
    IntegrationPartnerRepositoryInterface,
    IntegrationWebhookHandlerInterface,
    IntegrationWebhookRepositoryInterface,
)
from gqlapi.domain.models.v2.integrations import (
    IntegrationPartner,
    IntegrationWebhook,
    WorkflosVars,
    WorkflowIntegration,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger


logger = get_logger(get_app())


class IntegrationsPartnerHandler(IntegrationPartnerHandlerInterface):
    def __init__(self, repo: IntegrationPartnerRepositoryInterface):
        self.repository = repo

    async def get_by_name(
        self,
        name: str,
    ) -> IntegrationPartner | NoneType:
        return await self.repository.get(name=name)


class IntegrationsWebhookandler(IntegrationWebhookHandlerInterface):
    def __init__(self, repo: IntegrationWebhookRepositoryInterface):
        self.repository = repo

    async def get_by_source_type(
        self,
        source_type: str,
    ) -> IntegrationWebhook | NoneType:
        return await self.repository.get(source_type=source_type)

    async def get_vars(
        self,
        supplier_business_id: UUID,
    ) -> WorkflosVars | NoneType:
        return await self.repository.fetch_workflow_vars(
            supplier_business_id=supplier_business_id
        )

    async def get_workflow_integration(
        self,
        task_type: str,
        supplier_business_id: UUID,
    ) -> WorkflowIntegration | NoneType:
        return await self.repository.fetch_workflos_integration(
            task_type=task_type, supplier_business_id=supplier_business_id
        )
