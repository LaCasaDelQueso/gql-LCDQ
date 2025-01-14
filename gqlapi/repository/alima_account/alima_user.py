from types import NoneType
from typing import Any, Dict
from uuid import UUID

from gqlapi.domain.interfaces.v2.alima_admin.user import AlimaUserRepositoryInterface
from gqlapi.domain.models.v2.alima_business import AlimaUser
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain


class AlimaUserRepository(CoreRepository, AlimaUserRepositoryInterface):
    async def new(
        self,
        alima_user: AlimaUser,
    ) -> UUID:
        """Create New Alima User

        Args:
            alima_user (AlimaUser): AlimaUser object

        Returns:
            UUID: unique AlimaUser id
        """
        # cast to dict
        core_vals = domain_to_dict(alima_user, skip=["created_at", "updated_at"])
        # call super method from new

        await super().new(
            core_element_tablename="alima_user",
            core_element_name="Alima User",
            # validate_by="id",
            # validate_against=core_user_vals["id"],
            core_query="""INSERT INTO alima_user
                (id,
                core_user_id,
                role,
                enabled,
                deleted
                )
                    VALUES
                    (:id,
                    :core_user_id,
                    :role,
                    :enabled,
                    :deleted)
                """,
            core_values=core_vals,
        )
        return core_vals["id"]

    async def get(
        self,
        alima_user_id: UUID,
    ) -> Dict[Any, Any]:
        """Get Alima User

        Args:
            alima_user_id (UUID): unique alima user id

        Returns:
            Dict: Alima User Model
        """
        alima_user = await super().get(
            id=alima_user_id,
            core_element_tablename="alima_user",
            core_element_name="Alima User",
            core_columns="*",
        )
        return sql_to_domain(alima_user, AlimaUser)

    async def update(self) -> bool:
        """_summary_

        Returns:
            bool: Validate update id done
        """
        return True

    async def exist(
        self,
        alima_user_id: UUID,
    ) -> NoneType:
        """Validate category exists

        Args:
            category_id (UUID): unique category id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=alima_user_id,
            core_columns="id",
            core_element_tablename="alima_user",
            id_key="id",
            core_element_name="Alima User",
        )
