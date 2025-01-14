from datetime import datetime
import json
import logging
from types import NoneType
from typing import Any, Optional, Dict, List
import uuid
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantUserGQL,
    RestaurantUserPermissionRepositoryInterface,
    RestaurantUserRepositoryInterface,
)
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.restaurant import (
    RestaurantUser,
    RestaurantUserPermission,
)
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.domain_mapper import sql_to_domain


class RestaurantUserRepository(CoreRepository, RestaurantUserRepositoryInterface):
    async def new(
        self,
        core_user_id: UUID,
        role: str,
    ) -> UUID:
        """Repo that reates new restaurant user in SQL

        Args:
            core_user_id (UUID): unique core user id
            role (str): user role in the restaurant

        Raises:
            GQLApiException

        Returns:
            UUID: unique restaurant user id
        """
        # cast to dict
        res_user_vals = {
            "id": uuid.uuid4(),
            "core_user_id": core_user_id,
            "role": role,
            "enabled": True,
            "deleted": False,
        }
        # call super method from new
        await super().new(
            core_element_tablename="restaurant_user",
            core_element_name="Restaurant User",
            validate_by="core_user_id",
            validate_against=core_user_id,
            core_query="""INSERT INTO restaurant_user (id, core_user_id, role, enabled, deleted)
                VALUES (:id, :core_user_id, :role, :enabled, :deleted)
            """,
            core_values=res_user_vals,
        )
        return res_user_vals["id"]

    async def update(
        self,
        core_id: UUID,
        role: Optional[str] = None,
    ) -> bool:
        """Repo that updates restaurant user in SQL

        Args:
            core_id (UUID): unique core user id
            role (Optional[str], optional): user role in the restaurant. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        # init vars

        restaurant_atributes = []
        restaurant_values_view: Dict[str, Any] = {"core_user_id": core_id}
        # check db connection
        if not self.db:
            raise GQLApiException(
                msg="Error creating connect SQL DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        try:
            if role:
                restaurant_values_view["role"] = role
                restaurant_atributes.append(" role= :role")

            if len(restaurant_atributes) == 0:
                raise GQLApiException(
                    msg="Issues no data to update in sql",
                    error_code=GQLApiErrorCodeType.CONNECTION_MONGO_DB_ERROR.value,
                )

            restaurant_atributes.append(" last_updated=:last_updated")
            restaurant_values_view["last_updated"] = datetime.utcnow()

            restaurant_query = f"""UPDATE restaurant_user
                                SET {','.join(restaurant_atributes)}
                                WHERE core_user_id=:core_user_id;
                    """
            # await self.db.execute(query=restaurant_query, values=restaurant_values_view)
            await super().update(
                core_element_name="Restaurant User",
                core_query=restaurant_query,
                core_values=restaurant_values_view,
            )

        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating restaurant user")
            raise GQLApiException(
                msg="Error updating restaurant user",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return True

    @deprecated("Use fetch() instead", "domain")
    async def get(self, core_user_id: UUID) -> RestaurantUserGQL:
        """Repo that gets restaurant user in SQL

        Args:
            core_user_id (UUID): unique core user id

        Raises:
            GQLApiException

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        _data = await super().get(
            id=core_user_id,
            id_key="cu.id",
            core_element_tablename="restaurant_user ru JOIN core_user cu ON ru.core_user_id = cu.id",
            core_element_name="Restaurant User",
            core_columns=["ru.*", "row_to_json(cu.*) AS user_json"],
        )
        # casts only the Restaurant User model, the user model is added from the json
        d_rest_user = dict(_data)
        rest_user = RestaurantUserGQL(**sql_to_domain(_data, RestaurantUser))
        rest_user.user = CoreUser(**json.loads(d_rest_user["user_json"]))
        # validate correct date casting
        rest_user.user.created_at = from_iso_format(
            rest_user.user.created_at  # type: ignore
        )
        rest_user.user.last_updated = from_iso_format(
            rest_user.user.last_updated  # type: ignore
        )

        return rest_user

    async def fetch(self, core_user_id: UUID) -> RestaurantUserGQL:
        """Repo that gets restaurant user in SQL

        Args:
            core_user_id (UUID): unique core user id

        Raises:
            GQLApiException

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        _data = await super().fetch(
            id=core_user_id,
            id_key="cu.id",
            core_element_tablename="restaurant_user ru JOIN core_user cu ON ru.core_user_id = cu.id",
            core_element_name="Restaurant User",
            core_columns=["ru.*", "row_to_json(cu.*) AS user_json"],
        )
        if not _data:
            raise GQLApiException(
                msg="Restaurant User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # casts only the Restaurant User model, the user model is added from the json
        d_rest_user = dict(_data)
        rest_user = RestaurantUserGQL(**sql_to_domain(_data, RestaurantUser))
        rest_user.user = CoreUser(**json.loads(d_rest_user["user_json"]))
        # validate correct date casting
        rest_user.user.created_at = from_iso_format(
            rest_user.user.created_at  # type: ignore
        )
        rest_user.user.last_updated = from_iso_format(
            rest_user.user.last_updated  # type: ignore
        )

        return rest_user

    async def delete(self, core_id: UUID, deleted: bool) -> bool:
        """Repo that deletes restaurant user in SQL

        Args:
            core_id (UUID): unique core user id
            deleted (bool): restaurant user status

        Raises:
            GQLApiException

        Returns:
            bool: the value of deleted
        """
        try:
            core_atributes = [" deleted=:deleted", " last_updated=:last_updated"]
            core_values_view: Dict[str, Any] = {
                "id": core_id,
                "deleted": deleted,
                "last_updated": datetime.utcnow(),
            }
            restaurant_query = f"""UPDATE restaurant_user
                                SET {','.join(core_atributes)}
                                WHERE core_user_id=:id;
                    """
            await self.db.execute(query=restaurant_query, values=core_values_view)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues deleting restaurant user")
            raise GQLApiException(
                msg="Error deleting restaurant user ststus",
                error_code=GQLApiErrorCodeType.DELETE_SQL_DB_ERROR.value,
            )
        return deleted

    async def activate_desactivate(self, core_id: UUID, enabled: bool) -> bool:
        """Repo that activate/desactivate restaurant user in SQL

        Args:
            core_id (UUID): unique core user id
            enabled (bool): restaurant user status

        Raises:
            GQLApiException

        Returns:
            bool: activate/desactivate status
        """
        # check db connection
        if not self.db:
            raise GQLApiException(
                msg="Error creating connect SQL DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        try:
            core_atributes = [" enabled=:enabled", " last_updated=:last_updated"]
            core_values_view: Dict[str, Any] = {
                "id": core_id,
                "enabled": enabled,
                "last_updated": datetime.utcnow(),
            }
            restaurant_query = f"""UPDATE restaurant_user
                                SET {','.join(core_atributes)}
                                WHERE core_user_id=:id;
                    """
            await self.db.execute(query=restaurant_query, values=core_values_view)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating restaurant user status")
            raise GQLApiException(
                msg="Error updating restaurant user ststus",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return enabled

    async def exist(
        self,
        restaurant_user_id: UUID,
    ) -> NoneType:
        """Validate restaurant user exists

        Args:
            restaurant_user_id (UUID): unique restaurant user id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=restaurant_user_id,
            core_columns="id",
            core_element_tablename="restaurant_user",
            id_key="id",
            core_element_name="Restaurant User",
        )

    async def get_by_id(self, restaurant_user_id: UUID) -> Dict[Any, Any]:
        """Repo that gets restaurant user in SQL

        Args:
            restaurant_user_id (UUID): unique restaurant user id

        Raises:
            GQLApiException

        Returns:
            Dict: restaurant user model dict
        """
        _data = await super().get(
            id=restaurant_user_id,
            id_key="id",
            core_element_tablename="restaurant_user",
            core_element_name="Restaurant User",
            core_columns="*",
        )

        return sql_to_domain(_data, RestaurantUser)


class RestaurantUserPermissionRepository(
    CoreRepository,
    RestaurantUserPermissionRepositoryInterface,
):
    async def new(
        self,
        restaurant_user_id: UUID,
        restaurant_business_id: UUID,
        display_orders_section: bool,
        display_suppliers_section: bool,
        display_products_section: bool,
    ) -> bool:
        """New Restauran user permissions

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_user_id (UUID): unique restaurant user id
            restaurant_business_id (UUID): unique restaurant business id
            display_orders_section (bool): permission to manaje orders section
            display_suppliers_section (bool): permission to manaje suppliers section
            display_products_section (bool): permission to manaje products section

        Raises:
            GQLApiException

        Returns:
            bool: validate creation is done
        """
        # cast to dict
        internal_values_restaurant_user_permission = {
            "id": uuid.uuid4(),
            "restaurant_user_id": restaurant_user_id,
            "display_orders_section": display_orders_section,
            "display_suppliers_section": display_suppliers_section,
            "display_products_section": display_products_section,
            "restaurant_business_id": restaurant_business_id,
        }
        # call super method from new
        await super().new(
            core_element_tablename="restaurant_user_permission",
            core_element_name="Restaurant User Permission",
            # validate_by="restaurant_user_id",
            # validate_against=restaurant_user_id,
            core_query="""INSERT INTO restaurant_user_permission
                (id,
                restaurant_user_id,
                display_orders_section, display_suppliers_section, display_products_section,
                restaurant_business_id)
                    VALUES
                    (:id,
                    :restaurant_user_id,
                    :display_orders_section, :display_suppliers_section, :display_products_section, :restaurant_business_id)
                """,
            core_values=internal_values_restaurant_user_permission,
        )
        return True

    @deprecated("Use find() instead", "gqlapi.repository")
    async def update(
        self,
        restaurant_user_id: UUID,
        display_orders_section: Optional[bool] = None,
        display_suppliers_section: Optional[bool] = None,
        display_products_section: Optional[bool] = None,
    ) -> bool:
        """Update restaurant user permissions

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            display_orders_section (bool): permission to manaje orders section
            display_suppliers_section (bool): permission to manaje suppliers section
            display_products_section (bool): permission to manaje products section

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        if not self.db:
            raise GQLApiException(
                msg="Error creating connect SQL DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )

        try:
            restaurant_user_permission_atributes = []
            restaurant_user_permission_values_view: Dict[str, Any] = {
                "restaurant_user_id": restaurant_user_id
            }
            if isinstance(display_orders_section, bool):
                restaurant_user_permission_atributes.append(
                    " display_orders_section=:display_orders_section"
                )
                restaurant_user_permission_values_view[
                    "display_orders_section"
                ] = display_orders_section
            if isinstance(display_suppliers_section, bool):
                restaurant_user_permission_atributes.append(
                    " display_suppliers_section=:display_suppliers_section"
                )
                restaurant_user_permission_values_view[
                    "display_suppliers_section"
                ] = display_suppliers_section
            if isinstance(display_products_section, bool):
                restaurant_user_permission_atributes.append(
                    " display_products_section=:display_products_section"
                )
                restaurant_user_permission_values_view[
                    "display_products_section"
                ] = display_products_section

            if len(restaurant_user_permission_atributes) == 0:
                return False

            restaurant_user_permission_atributes.append(" last_updated=:last_updated")
            restaurant_user_permission_values_view["last_updated"] = datetime.utcnow()
            core_query = f"""UPDATE restaurant_user_permission
                                SET {','.join(restaurant_user_permission_atributes)}
                                WHERE restaurant_user_id=:restaurant_user_id;
                    """
            await self.db.execute(
                query=core_query, values=restaurant_user_permission_values_view
            )

        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating restaurant user permission")
            raise GQLApiException(
                msg="Error updating restaurant user permission",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return True

    async def edit(
        self,
        restaurant_user_id: UUID,
        restaurant_business_id: Optional[UUID] = None,
        display_orders_section: Optional[bool] = None,
        display_suppliers_section: Optional[bool] = None,
        display_products_section: Optional[bool] = None,
    ) -> bool:
        """Update restaurant user permissions

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            display_orders_section (bool): permission to manaje orders section
            display_suppliers_section (bool): permission to manaje suppliers section
            display_products_section (bool): permission to manaje products section

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        restaurant_user_permission_atributes = []
        restaurant_user_permission_values_view: Dict[str, Any] = {
            "restaurant_user_id": restaurant_user_id
        }
        if isinstance(display_orders_section, bool):
            restaurant_user_permission_atributes.append(
                " display_orders_section=:display_orders_section"
            )
            restaurant_user_permission_values_view[
                "display_orders_section"
            ] = display_orders_section
        if isinstance(display_suppliers_section, bool):
            restaurant_user_permission_atributes.append(
                " display_suppliers_section=:display_suppliers_section"
            )
            restaurant_user_permission_values_view[
                "display_suppliers_section"
            ] = display_suppliers_section
        if isinstance(display_products_section, bool):
            restaurant_user_permission_atributes.append(
                " display_products_section=:display_products_section"
            )
            restaurant_user_permission_values_view[
                "display_products_section"
            ] = display_products_section
        if isinstance(restaurant_business_id, UUID):
            restaurant_user_permission_atributes.append(
                " restaurant_business_id=:restaurant_business_id"
            )
            restaurant_user_permission_values_view[
                "restaurant_business_id"
            ] = restaurant_business_id

        if len(restaurant_user_permission_atributes) == 0:
            return False

        restaurant_user_permission_atributes.append(" last_updated=:last_updated")
        restaurant_user_permission_values_view["last_updated"] = datetime.utcnow()
        core_query = f"""UPDATE restaurant_user_permission
                            SET {','.join(restaurant_user_permission_atributes)}
                            WHERE restaurant_user_id=:restaurant_user_id
                """
        return await super().edit(
            core_element_name="Restaurant User Permission",
            core_query=core_query,
            core_values=restaurant_user_permission_values_view,
        )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(self, restaurant_user_id: UUID) -> RestaurantUserPermission:
        """Get restaurant user permissions

        Args:
            restaurant_user_id (UUID): unique restaurant user id

        Raises:
            GQLApiException

        Returns:
            RestaurantUserPermission: Restaurant User Permission id
        """

        _data = await super().get(
            id=restaurant_user_id,
            id_key="restaurant_user_id",
            core_element_tablename="restaurant_user_permission",
            core_element_name="Restaurant User Permission",
            core_columns="*",
        )
        # casts only the Restaurant User model, the user model is added from the json
        rest_user_perm = RestaurantUserPermission(
            **sql_to_domain(_data, RestaurantUserPermission)
        )
        return rest_user_perm

    async def fetch(
        self, restaurant_user_id: UUID
    ) -> RestaurantUserPermission | NoneType:
        """Get restaurant user permissions

        Args:
            restaurant_user_id (UUID): unique restaurant user id

        Raises:
            GQLApiException

        Returns:
            RestaurantUserPermission: Restaurant User Permission id
        """

        _data = await super().fetch(
            id=restaurant_user_id,
            id_key="restaurant_user_id",
            core_element_tablename="restaurant_user_permission",
            core_element_name="Restaurant User Permission",
            core_columns="*",
        )
        if not _data:
            return None
        # casts only the Restaurant User model, the user model is added from the json
        rest_user_perm = RestaurantUserPermission(
            **sql_to_domain(_data, RestaurantUserPermission)
        )
        return rest_user_perm

    async def get_restaurant_user_contact_and_permission(
        self,
        filter_values: str | None,
        rest_user_info_values_view: Dict[Any, Any],
    ) -> List[Dict[str, Any]]:
        """Get restaurant user contact and permission

        Args:
            filter_values (str) : Values to build query
            rest_user_info_values_view (Dict[Any, Any]): values to query

        Raises:
            GQLApiException

        Returns:
            Sequence
        """
        _resp = await super().search(
            core_element_name="Restaurant Permission and Contact Info",
            core_element_tablename="""
                restaurant_user ru
                JOIN restaurant_user_permission rup ON ru.id = rup.restaurant_user_id
                JOIN core_user cu ON cu.id = ru.core_user_id""",
            filter_values=filter_values,
            core_columns=[
                "ru.*",
                "row_to_json(rup.*) AS permission_json",
                "row_to_json(cu.*) AS contact_json",
            ],
            values=rest_user_info_values_view,
        )
        return [dict(r) for r in _resp]
