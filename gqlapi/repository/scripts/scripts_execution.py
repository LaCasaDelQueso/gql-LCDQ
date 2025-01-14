import datetime
import logging
from types import NoneType
from typing import Any, Dict, Optional
from uuid import UUID
import uuid
from gqlapi.domain.interfaces.v2.scripts.scrips_execution import (
    ScriptExecutionRepositoryInterface,
)
from gqlapi.repository import CoreDataOrchestationRepository


class ScriptExecutionRepository(
    CoreDataOrchestationRepository, ScriptExecutionRepositoryInterface
):
    async def add(self, script_name: str, status: str) -> UUID | NoneType:
        """Create Script Execution

        Args:
            script_name (str): name of script
            status (str): status of script

        Raises:
            GQLApiException

        Returns:
            UUID: unique script execution id
        """

        # cast to dict
        internal_values_script = {
            "id": uuid.uuid4(),
            "script_name": script_name,
            "status": status,
        }
        # call super method from new
        _id = await super().add(
            core_element_tablename="script_execution",
            core_element_name="Script Execution",
            core_query="""INSERT INTO script_execution (id, script_name, status)
                    VALUES (:id, :script_name, :status)
                """,
            core_values=internal_values_script,
        )
        if _id and isinstance(_id, uuid.UUID):
            return _id
        return None

    async def edit(
        self,
        id: UUID,
        status: Optional[str] = None,
        script_end: Optional[datetime.datetime] = None,
        data: Optional[str] = None,
    ) -> bool:
        """Update Restaurant Business

        Args:
            id (UUID): unique script execution
            status_name (Optional[str], optional): name of script. Defaults to None.
            status_end (Optional[datetime], optional): datetime to scripd end running. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """
        str_attrs = []
        q_vals: Dict[str, Any] = {"id": id}

        if status:
            str_attrs.append(" status =:status")
            q_vals["status"] = status
        if script_end:
            q_vals["script_end"] = script_end
            str_attrs.append(" script_end=:script_end")

        if script_end:
            q_vals["data"] = data
            str_attrs.append(" data=:data")

        if len(str_attrs) == 0:
            logging.info("No values to update in Script Execution")
            return True

        core_query = f"""UPDATE script_execution
                            SET {','.join(str_attrs)}
                            WHERE id=:id;
                """
        return await super().edit(
            core_element_name="Script Execution",
            core_query=core_query,
            core_values=q_vals,
        )
