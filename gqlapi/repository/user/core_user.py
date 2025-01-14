from abc import ABC
from datetime import datetime
from typing import Any, Dict, List, Type
import uuid
from uuid import UUID
from types import NoneType

from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple


# create Repository interface
class CoreUserRepositoryInterface(ABC):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        user: CoreUser,
    ) -> UUID:
        """Creates new core user

        Args:
            user: CoreUser

        Raises:
            GQLApiException

        Returns:
            UUID: unique core user id
        """
        raise NotImplementedError

    async def add(
        self,
        user: CoreUser,
    ) -> UUID | NoneType:
        """Creates new core user

        Args:
            user: CoreUser

        Raises:
            GQLApiException

        Returns:
            UUID: unique core user id | None
        """
        raise NotImplementedError

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        user_id: UUID,
    ) -> CoreUser:
        """Get core user by id

        Args:
            user_id: UUID

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        raise NotImplementedError

    async def fetch(
        self,
        user_id: UUID,
    ) -> CoreUser | NoneType:
        """Get core user by id

        Args:
            user_id: UUID

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        raise NotImplementedError

    @deprecated("Use fetch_by_firebase_id() instead", "gqlapi.repository")
    async def get_by_firebase_id(
        self,
        firebase_id: str,
    ) -> CoreUser:
        """Get core user by firebase id

        Args:
            firebase_id: str
            Firebase id (uid)

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        raise NotImplementedError

    async def fetch_by_firebase_id(
        self,
        firebase_id: str,
    ) -> CoreUser | NoneType:
        """Get core user by firebase id

        Args:
            firebase_id: str
            Firebase id (uid)

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        raise NotImplementedError

    async def get_by_email(
        self,
        email: str,
    ) -> CoreUser:
        """Get core user by email

        Args:
            email: str
                Email

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        raise NotImplementedError

    async def fetch_by_email(
        self,
        email: str,
    ) -> CoreUser | None:
        """Get core user by email

        Args:
            email: str
                Email

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        raise NotImplementedError

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        user_id: UUID,
        first_name: str | NoneType = None,
        last_name: str | NoneType = None,
        email: str | NoneType = None,
        phone_number: str | NoneType = None,
        firebase_id: str | NoneType = None,
    ) -> bool:
        """Update core user by id

        Args:
            user_id: UUID
            first_name: str
            last_name: str
            email: str
            phone_number: str
            firebase_id: str

        Raises:
            GQLApiException

        Returns:
            Bool
        """
        raise NotImplementedError

    async def edit(
        self,
        user_id: UUID,
        first_name: str | NoneType = None,
        last_name: str | NoneType = None,
        email: str | NoneType = None,
        phone_number: str | NoneType = None,
        firebase_id: str | NoneType = None,
    ) -> bool:
        """Update core user by id

        Args:
            user_id: UUID
            first_name: str
            last_name: str
            email: str
            phone_number: str
            firebase_id: str

        Raises:
            GQLApiException

        Returns:
            Bool
        """
        raise NotImplementedError

    async def exist(
        self,
        core_user_id: UUID,
    ) -> NoneType:
        raise NotImplementedError

    async def fetch_from_many(
        self,
        core_user_ids: List[UUID],
    ) -> List[CoreUser]:
        raise NotImplementedError


class CoreUserRepository(CoreRepository, CoreUserRepositoryInterface):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        user: CoreUser,
    ) -> UUID:
        return await self.add(user)

    async def add(
        self,
        user: CoreUser,
    ) -> UUID:
        """Creates new core user

        Args:
            user: CoreUser

        Raises:
            GQLApiException

        Returns:
            UUID: unique core user id
        """
        # cast to dict
        core_user_vals = domain_to_dict(user, skip=["created_at", "last_updated"])
        core_user_vals["id"] = uuid.uuid4()
        # call super method from new
        await super().add(
            core_element_tablename="core_user",
            core_element_name="Core User",
            validate_by="email",
            validate_against=user.email,
            core_query="""INSERT INTO core_user (id, first_name, last_name, email, phone_number, firebase_id)
                    VALUES (:id, :first_name, :last_name, :email, :phone_number, :firebase_id)
                """,
            core_values=core_user_vals,
        )
        return core_user_vals["id"]

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        user_id: UUID,
    ) -> CoreUser:
        """Get core user by id

        Args:
            user_id: UUID

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        c_user = await super().get(
            id=user_id,
            core_element_tablename="core_user",
            core_element_name="Core User",
            core_columns="*",
        )
        return CoreUser(**sql_to_domain(c_user, CoreUser))

    async def fetch(
        self,
        core_user_id: UUID,
    ) -> CoreUser | NoneType:
        """Get core user by id

        Args:
            user_id: UUID

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        c_user = await super().fetch(
            id=core_user_id,
            core_element_tablename="core_user",
            core_element_name="Core User",
            core_columns="*",
        )
        if not c_user:
            return None
        return CoreUser(**sql_to_domain(c_user, CoreUser))

    @deprecated("Use fetch_by_firebase_id() instead", "gqlapi.repository")
    async def get_by_firebase_id(
        self,
        firebase_id: str,
    ) -> CoreUser:
        """Get core user by firebase id

        Args:
            firebase_id: str
            Firebase id (uid)

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        c_user = await super().get(
            id=firebase_id,
            id_key="firebase_id",
            core_element_tablename="core_user",
            core_element_name="Core User",
            core_columns="*",
        )
        return CoreUser(**sql_to_domain(c_user, CoreUser))

    async def fetch_by_firebase_id(
        self,
        firebase_id: str,
    ) -> CoreUser | NoneType:
        """Get core user by firebase id

        Args:
            firebase_id: str
            Firebase id (uid)

        Raises:
            GQLApiException

        Returns:
            CoreUser | NoneType
        """
        c_user = await super().fetch(
            id=firebase_id,
            id_key="firebase_id",
            core_element_tablename="core_user",
            core_element_name="Core User",
            core_columns="*",
        )
        if not c_user:
            return None
        return CoreUser(**sql_to_domain(c_user, CoreUser))

    async def get_by_email(
        self,
        email: str,
    ) -> CoreUser:
        """Get core user by email

        Args:
            email: str
                Email

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        c_user = await super().get(
            id=email,
            id_key="email",
            core_element_tablename="core_user",
            core_element_name="Core User",
            core_columns="*",
        )
        return CoreUser(**sql_to_domain(c_user, CoreUser))

    async def fetch_by_email(
        self,
        email: str,
    ) -> CoreUser | None:
        """Get core user by email

        Args:
            email: str
                Email

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """
        c_user = await super().fetch(
            id=email,
            id_key="email",
            core_element_tablename="core_user",
            core_element_name="Core User",
            core_columns="*",
        )
        if not c_user:
            return None
        return CoreUser(**sql_to_domain(c_user, CoreUser))

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        user_id: UUID,
        first_name: str | NoneType = None,
        last_name: str | NoneType = None,
        email: str | NoneType = None,
        phone_number: str | NoneType = None,
        firebase_id: str | NoneType = None,
    ) -> bool:
        """Update core user by id

        Args:
            user_id: UUID
            first_name: str
            last_name: str
            email: str
            phone_number: str
            firebase_id: str

        Raises:
            GQLApiException

        Returns:
            Bool
        """
        # create update query
        core_query = "UPDATE core_user SET "
        core_values = {}
        if first_name:
            core_query += "first_name = :first_name, "
            core_values["first_name"] = first_name
        if last_name:
            core_query += "last_name = :last_name, "
            core_values["last_name"] = last_name
        if email:
            core_query += "email = :email, "
            core_values["email"] = email
        if phone_number:
            core_query += "phone_number = :phone_number, "
            core_values["phone_number"] = phone_number
        if firebase_id:
            core_query += "firebase_id = :firebase_id, "
            core_values["firebase_id"] = firebase_id
        core_query += "last_updated = :last_updated WHERE id = :id"
        core_values["last_updated"] = datetime.utcnow()
        core_values["id"] = user_id
        # call super method from update
        await super().update(
            core_element_name="Core User",
            core_query=core_query,
            core_values=core_values,
        )
        return True

    async def edit(
        self,
        user_id: UUID,
        first_name: str | NoneType = None,
        last_name: str | NoneType = None,
        email: str | NoneType = None,
        phone_number: str | NoneType = None,
        firebase_id: str | NoneType = None,
    ) -> bool:
        """Update core user by id

        Args:
            user_id: UUID
            first_name: str
            last_name: str
            email: str
            phone_number: str
            firebase_id: str

        Raises:
            GQLApiException

        Returns:
            Bool
        """
        # create update query
        core_query = "UPDATE core_user SET "
        core_values = {}
        for k, v in locals().items():
            if k in ["first_name", "last_name", "email" "phone_number", "firebase_id"]:
                if v:
                    core_query += f"{k} = :{k}, "
                    core_values[k] = v
        # set up last updated
        core_query += "last_updated = :last_updated WHERE id = :id"
        core_values["last_updated"] = datetime.utcnow()
        core_values["id"] = user_id
        # call super method from update
        return await super().edit(
            core_element_name="Core User",
            core_query=core_query,
            core_values=core_values,
        )

    async def exist(
        self,
        core_user_id: UUID,
    ) -> NoneType:
        await super().exist(
            id=core_user_id,
            core_columns="id",
            core_element_tablename="core_user",
            id_key="id",
            core_element_name="Core User",
        )

    async def find_many(
        self,
        cols: List[str],
        filter_values: List[Dict[str, str]],
        tablename: str = "supplier_product",
        filter_type: str = "AND",
        cast_type: Type = CoreUser,
    ) -> List[Dict[str, Any]]:
        """Search Core user by multiple filter values

        Parameters
        ----------
        cols : List[str]
        filter_values : List[Dict[str, Any]]
        tablename : str, optional (default: "core_user")

        Returns
        -------
        List[Dict[str, Any]]
        """
        # format query
        qry = tablename
        if filter_values:
            _filt = " WHERE "
            for filter_value in filter_values:
                if len(_filt) > 7:  # 7 is len(" WHERE ")
                    _filt += f" {filter_type} "
                _filt += f"{filter_value['column']} {filter_value['operator']} {filter_value['value']}"
            qry += _filt
        users = await super().find(
            core_element_name="Core User",
            core_element_tablename=qry,
            core_columns=cols,
            values={},
        )
        return [sql_to_domain(core_user, cast_type) for core_user in users]

    async def fetch_from_many(
        self,
        core_user_ids: List[UUID],
    ) -> List[CoreUser]:
        """Fetch Core User

        Args:
            core user_ids (List[UUID]): core user ids

        Returns:
            List[Core User]: list of Core User objects
        """
        db_core_users = await self.find_many(
            cols=["*"],
            filter_values=[
                {
                    "column": "id",
                    "operator": "in",
                    "value": list_into_strtuple(core_user_ids),
                }
            ],
            tablename="core_user",
            cast_type=CoreUser,
        )
        if not db_core_users:
            return []
        return [
            CoreUser(**sql_to_domain(core_user, CoreUser))
            for core_user in db_core_users
        ]
