from types import NoneType
from typing import List, Optional
from uuid import UUID, uuid4
from gqlapi.domain.interfaces.v2.integrations.integrations import (
    IntegrationOrdenRepositoryInterface,
)
from gqlapi.domain.models.v2.integrations import IntegrationOrden
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.integrations.integrations.scorpion import ScorpionHandlerInterface
from gqlapi.lib.logger.logger.basic_logger import get_logger


logger = get_logger(get_app())


class ScorpionHandler(ScorpionHandlerInterface):
    def __init__(self, integrations_orden_repo: IntegrationOrdenRepositoryInterface):
        self.integrations_orden_repo = integrations_orden_repo

    async def new_orden(
        self, integrations_partner_id: UUID, orden_id: UUID, status: str
    ) -> UUID | NoneType:
        io = await self.integrations_orden_repo.add(
            integration_orden=IntegrationOrden(
                id=uuid4(),
                integrations_partner_id=integrations_partner_id,
                orden_id=orden_id,
                status=status,
            )
        )
        return io

    async def edit_orden(
        self,
        id: UUID,
        integrations_partner_id: UUID,
        orden_id: UUID,
        status: str,
        integrations_orden_id: Optional[str] = None,
        reason: Optional[str] = None,
        result: Optional[str] = None,
    ) -> UUID | NoneType:
        io = await self.integrations_orden_repo.edit(
            integration_orden=IntegrationOrden(
                id=id,
                integrations_partner_id=integrations_partner_id,
                orden_id=orden_id,
                status=status,
                integrations_orden_id=integrations_orden_id,
                reason=reason,
                result=result,
            )
        )
        return io

    async def get_by_multiple_ordenes(self, orden_ids: List) -> List[IntegrationOrden]:
        return await self.integrations_orden_repo.get_muiltiple_ordenes_ids(
            orden_ids=orden_ids
        )
