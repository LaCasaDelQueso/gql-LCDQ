from datetime import datetime
import json
import logging
from types import NoneType
from typing import Any, List, Optional, Dict
import uuid
from uuid import UUID

from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.supplier import SupplierUser, SupplierUserPermission
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository, MongoRecord
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.domain_mapper import sql_to_domain


class SupplierUserRepository(CoreRepository, SupplierUserRepositoryInterface):
    async def add(
        self,
        core_user_id: UUID,
        role: str,
    ) -> UUID:
        """Repo that reates new supplier user in SQL

        Args:
            core_user_id (UUID): unique core user id
            role (str): user role in the supplier

        Raises:
            GQLApiException

        Returns:
            UUID: unique supplier user id
        """
        # cast to dict
        sup_user_vals = {
            "id": uuid.uuid4(),
            "core_user_id": core_user_id,
            "role": role,
            "enabled": True,
            "deleted": False,
        }
        # call super method from new
        await super().add(
            core_element_tablename="supplier_user",
            core_element_name="Supplier User",
            validate_by="core_user_id",
            validate_against=core_user_id,
            core_query="""INSERT INTO supplier_user (id, core_user_id, role, enabled, deleted)
                VALUES (:id, :core_user_id, :role, :enabled, :deleted)
            """,
            core_values=sup_user_vals,
        )
        return sup_user_vals["id"]

    async def edit(
        self,
        core_user_id: UUID,
        role: Optional[str] = None,
    ) -> bool:
        """Repo that updates supplier user in SQL

        Args:
            core_user_id (UUID): unique core user id
            role (Optional[str], optional): user role in the supplier. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        # init vars
        flag = False
        supplier_atributes = []
        supplier_values_view: Dict[str, Any] = {"core_user_id": core_user_id}
        try:
            if role:
                supplier_values_view["role"] = role
                supplier_atributes.append(" role= :role")

            if len(supplier_atributes) == 0:
                logging.warning("Issues no data to update in sql: supplier user")
                return False

            supplier_atributes.append(" last_updated=:last_updated")
            supplier_values_view["last_updated"] = datetime.utcnow()

            supplier_query = f"""UPDATE supplier_user
                                SET {','.join(supplier_atributes)}
                                WHERE core_user_id=:core_user_id;
                    """
            flag = await super().edit(
                core_element_name="Supplier User",
                core_query=supplier_query,
                core_values=supplier_values_view,
            )
        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating supplier user")
            raise GQLApiException(
                msg="Error updating supplier user",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return flag

    async def fetch(self, core_user_id: UUID) -> Dict[str, Any]:
        """Repo that gets supplier user in SQL

        Args:
            core_user_id (UUID): unique core user id

        Raises:
            GQLApiException

        Returns:
            MongoRecord: supplier user + core user model
        """
        _data = await super().fetch(
            id=core_user_id,
            id_key="cu.id",
            core_element_tablename="supplier_user su JOIN core_user cu ON su.core_user_id = cu.id",
            core_element_name="Supplier User",
            core_columns=["su.*", "row_to_json(cu.*) AS user_json"],
        )
        if not _data:
            return {}
        # casts only the Supplier User model, the user model is added from the json
        d_sup_user = dict(_data)
        sup_user = sql_to_domain(_data, SupplierUser)
        sup_user["user"] = CoreUser(**json.loads(d_sup_user["user_json"]))
        # validate correct date casting
        sup_user["user"].created_at = from_iso_format(
            sup_user["user"].created_at  # type: ignore
        )
        sup_user["user"].last_updated = from_iso_format(
            sup_user["user"].last_updated  # type: ignore
        )
        return sup_user

    async def delete(self, core_user_id: UUID, deleted: bool) -> bool:
        """Repo that deletes supplier user in SQL

        Args:
            core_user_id (UUID): unique core user id
            deleted (bool): supplier user status

        Raises:
            GQLApiException

        Returns:
            bool: the value of deleted
        """
        try:
            core_atributes = [" deleted=:deleted", " last_updated=:last_updated"]
            core_values_view: Dict[str, Any] = {
                "id": core_user_id,
                "deleted": deleted,
                "last_updated": datetime.utcnow(),
            }
            supplier_query = f"""UPDATE supplier_user
                                SET {','.join(core_atributes)}
                                WHERE core_user_id=:id;
                    """
            await self.db.execute(query=supplier_query, values=core_values_view)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues deleting supplier user")
            raise GQLApiException(
                msg="Error deleting supplier user ststus",
                error_code=GQLApiErrorCodeType.DELETE_SQL_DB_ERROR.value,
            )
        return deleted

    async def activate_desactivate(self, core_user_id: UUID, enabled: bool) -> bool:
        """Repo that activate/desactivate supplier user in SQL

        Args:
            core_user_id (UUID): unique core user id
            enabled (bool): supplier user status

        Raises:
            GQLApiException

        Returns:
            bool: activate/desactivate status
        """
        try:
            core_atributes = [" enabled=:enabled", " last_updated=:last_updated"]
            core_values_view: Dict[str, Any] = {
                "id": core_user_id,
                "enabled": enabled,
                "last_updated": datetime.utcnow(),
            }
            supplier_query = f"""UPDATE supplier_user
                                SET {','.join(core_atributes)}
                                WHERE core_user_id=:id;
                    """
            await self.db.execute(query=supplier_query, values=core_values_view)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating supplier user status")
            raise GQLApiException(
                msg="Error updating supplier user ststus",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return enabled

    async def exist(
        self,
        supplier_user_id: UUID,
    ) -> bool:
        """Validate supplier user exists

        Args:
            supplier_user_id (UUID): unique supplier user id

        Returns:
            NoneType: None
        """
        return await super().exist(
            id=supplier_user_id,
            core_columns="id",
            core_element_tablename="supplier_user",
            id_key="id",
            core_element_name="Supplier User",
        )

    async def get_by_id(self, supplier_user_id: UUID) -> MongoRecord | NoneType:
        """Repo that gets supplier user in SQL

        Args:
            supplier_user_id (UUID): unique supplier user id

        Raises:
            GQLApiException

        Returns:
            Dict: supplier user model dict | None
        """
        _data = await super().fetch(
            id=supplier_user_id,
            id_key="id",
            core_element_tablename="supplier_user",
            core_element_name="Supplier User",
            core_columns="*",
        )
        if not _data:
            return None
        return sql_to_domain(_data, SupplierUser)


class SupplierUserPermissionRepository(
    CoreRepository, SupplierUserPermissionRepositoryInterface
):
    async def fetch(self, supplier_user_id: UUID) -> Dict[Any, Any]:
        _data = await super().fetch(
            id=supplier_user_id,
            id_key="supplier_user_id",
            core_element_tablename="supplier_user_permission",
            core_element_name="Supplier User Permission",
            core_columns="*",
        )
        if not _data:
            return {}
        return sql_to_domain(_data, SupplierUserPermission)

    async def fetch_by_supplier_business(
        self, supplier_business_id: UUID
    ) -> List[Dict[Any, Any]]:
        _data = await super().find(
            core_element_tablename="supplier_user_permission",
            core_element_name="Supplier User Permission",
            core_columns="*",
            filter_values=" supplier_business_id=:supplier_business_id",
            values={"supplier_business_id": supplier_business_id},
        )
        if not _data:
            return []
        return [sql_to_domain(_d, SupplierUserPermission) for _d in _data]

    async def add(
        self,
        supplier_user_id: UUID,
        supplier_business_id: UUID,
        display_sales_section: bool,
        display_routes_section: bool,
    ) -> UUID:
        """Repo that creates new supplier user permission in SQL

        Args:
            supplier_user_id (UUID): unique supplier user id
            supplier_business_id (UUID): unique supplier business id
            display_sales_section (bool): display sales section
            display_routes_section (bool): display routes section

        Raises:
            GQLApiException

        Returns:
            UUID: unique supplier user permission id
        """
        # cast to dict
        sup_user_perm_vals = {
            "id": uuid.uuid4(),
            "supplier_user_id": supplier_user_id,
            "supplier_business_id": supplier_business_id,
            "display_sales_section": display_sales_section,
            "display_routes_section": display_routes_section,
        }
        # call super method from new
        await super().add(
            core_element_tablename="supplier_user_permission",
            core_element_name="Supplier User Permission",
            validate_by="id",
            validate_against=supplier_user_id,
            core_query="""
                INSERT INTO supplier_user_permission (
                    id, supplier_user_id, supplier_business_id, display_sales_section, display_routes_section
                )
                VALUES (
                    :id, :supplier_user_id, :supplier_business_id, :display_sales_section, :display_routes_section
                )
            """,
            core_values=sup_user_perm_vals,
        )
        return sup_user_perm_vals["id"]

    async def fetch_supplier_user_contact_and_permission(
        self,
        filter_str: str | None,
        filter_values: Dict[Any, Any],
    ) -> List[Dict[str, Any]]:
        """Get supplier user contact and permission

        Args:
            filter_str (str) : Values to build query
            filter_values (Dict[Any, Any]): values to query

        Raises:
            GQLApiException

        Returns:
            Sequence
        """
        _resp = await super().find(
            core_element_name="Supplier Permission and Contact Info",
            core_element_tablename="""
                supplier_user su
                JOIN supplier_user_permission sup ON su.id = sup.supplier_user_id
                JOIN core_user cu ON cu.id = su.core_user_id""",
            filter_values=filter_str,
            core_columns=[
                "su.*",
                "row_to_json(sup.*) AS permission_json",
                "row_to_json(cu.*) AS contact_json",
            ],
            values=filter_values,
        )
        return [dict(r) for r in _resp]

    async def edit(
        self,
        supplier_user_id: UUID,
        supplier_business_id: UUID,
        display_sales_section: bool,
        display_routes_section: bool,
    ) -> bool:
        """Repo that creates new supplier user permission in SQL

        Args:
            supplier_user_id (UUID): unique supplier user id
            supplier_business_id (UUID): unique supplier business id
            display_sales_section (bool): display sales section
            display_routes_section (bool): display routes section

        Raises:
            GQLApiException

        Returns:
            UUID: unique supplier user permission id
        """
        # cast to dict
        sup_user_perm_vals = {
            "supplier_user_id": supplier_user_id,
            "supplier_business_id": supplier_business_id,
            "display_sales_section": display_sales_section,
            "display_routes_section": display_routes_section,
        }
        # call super method from new
        return await super().edit(
            core_element_tablename="supplier_user_permission",
            core_element_name="Supplier User Permission",
            core_query="""
                UPDATE supplier_user_permission
                SET
                    supplier_business_id=:supplier_business_id,
                    display_sales_section=:display_sales_section,
                    display_routes_section=:display_routes_section
                WHERE
                    supplier_user_id=:supplier_user_id
            """,
            core_values=sup_user_perm_vals,
        )
