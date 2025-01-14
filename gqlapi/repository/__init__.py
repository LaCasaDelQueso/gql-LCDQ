import logging
from types import NoneType
from typing import Any, Dict, List, Sequence, Optional, Tuple
from uuid import UUID
from bson import Binary

from strawberry.types import Info as StrawberryInfo
from databases.interfaces import Record as SQLRecord

from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.domain.interfaces.v2.user.core_user import CoreRepositoryInterface
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from pymongo.results import DeleteResult, UpdateResult

from motor.motor_asyncio import AsyncIOMotorClient

# Types
MongoRecord = Dict[str, Any]


class CoreRepository(CoreRepositoryInterface):
    def __init__(self, info: StrawberryInfo) -> None:
        try:
            _db = info.context["db"].sql
        except Exception as e:
            logging.error(e)
            logging.warning("Issues connect SQL DB")
            raise GQLApiException(
                msg="Error creating connect SQL DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        self.db = _db

    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        core_element_tablename: str,
        core_element_name: str,
        core_query: str,
        core_values: Dict[str, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[Any] = None,
    ) -> UUID | bool:
        """Creates new core element

        Args:
            core_element: CoreElement
                Element to be created
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against

        Raises:
            GQLApiException

        Returns:
            UUID: unique core element id
        """
        # validate if user is already existing
        if validate_by and validate_against:
            try:
                query = f"""SELECT id FROM {core_element_tablename} WHERE {validate_by}=:validator """
                _exists = await self.db.fetch_one(
                    query=query, values={"validator": validate_against}
                )
            except Exception as e:
                logging.error(e)
                logging.warning(f"Issues fetch {core_element_name}")
                raise GQLApiException(
                    msg=f"Get {core_element_name}",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
                )
            if _exists:
                raise GQLApiException(
                    msg=f"{core_element_name} with this validator ({validate_by}) already exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        # create new core user
        await self._query(
            query=core_query, values=core_values, core_element_name=core_element_name
        )
        if "id" in core_values:
            id = core_values["id"]
            logging.debug(f"Create new {core_element_name} with id = {id}")
            return core_values["id"]
        else:
            logging.debug(f"Create new {core_element_name}")
            return True

    async def add(
        self,
        core_element_tablename: str,
        core_element_name: str,
        core_query: str,
        core_values: Dict[str, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[Any] = None,
    ) -> UUID | Tuple[Any] | NoneType:
        """Creates new core element

        Args:
            core_element: CoreElement
                Element to be created
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against

        Raises:
            GQLApiException

        Returns:
        UUID | Tuple[Any] | NoneType:
            unique core element id or none when not valid
        """
        # validate if user is already existing
        if validate_by and validate_against:
            try:
                query = f"""SELECT {validate_by} FROM {core_element_tablename} WHERE {validate_by}=:validator """
                _exists = await self.db.fetch_one(
                    query=query, values={"validator": validate_against}
                )
            except Exception as e:
                logging.error(e)
                logging.warning(f"Issues fetch {core_element_name}")
                raise GQLApiException(
                    msg=f"Get {core_element_name}",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
                )
            if _exists:
                logging.warning(
                    f"{core_element_name} with this validator ({validate_by}) already exists"
                )
                return None
        # create new core user
        await self._query(
            query=core_query, values=core_values, core_element_name=core_element_name
        )
        # return id or tuple of elements
        if "id" in core_values:
            id = core_values["id"]
            logging.debug(f"Create new {core_element_name} with id = {id}")
            return core_values["id"]  # UUID
        else:
            return tuple(core_values.values())  # type: ignore (safe) Tuple[Any]

    async def _query(self, query: str, values: Dict[str, Any], core_element_name: str):
        # check db connection
        if not self.db:
            raise GQLApiException(
                msg="Error creating connect SQL DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        try:
            await self.db.execute(query=query, values=values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues executing query: {core_element_name}")
            raise GQLApiException(
                msg=f"Error creating {core_element_name}",
                error_code=GQLApiErrorCodeType.EXECUTE_SQL_DB_ERROR.value,
            )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        id: UUID | str,
        core_element_name: str,
        core_element_tablename: str,
        id_key: str = "id",
        core_columns: List[str] | str = "*",
    ) -> Sequence:
        """Get core element by id

        Args:
            id: UUID
                Id of the core element
            core_element: Type[Any]
                Core element to be returned
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_columns: List[str] | str = "*"
                Columns to be returned
            id_key: str = "id"
                Column field to query from
        Raises:
            GQLApiException

        Returns:
            Sequence
        """
        # get core user
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = (
                f"""SELECT {cols} FROM {core_element_tablename} WHERE {id_key}=:id """
            )
            core_el = await self.db.fetch_one(query=query, values={"id": id})
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if not core_el:
            raise GQLApiException(
                msg=f"{core_element_name} not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        logging.debug(f"Query successfully - {core_element_name} with id({id})")
        return core_el

    async def fetch(
        self,
        id: UUID | str,
        core_element_name: str,
        core_element_tablename: str,
        id_key: str = "id",
        core_columns: List[str] | str = "*",
    ) -> SQLRecord | NoneType:
        """Get core element by id

        Args:
            id: UUID
                Id of the core element
            core_element: Type[Any]
                Core element to be returned
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_columns: List[str] | str = "*"
                Columns to be returned
            id_key: str = "id"
                Column field to query from
        Raises:
            GQLApiException

        Returns:
            SQLRecord | NoneType
        """
        # get core element
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = f"""SELECT {cols} FROM {core_element_tablename} WHERE {id_key}=:validator """
            core_el = await self.db.fetch_one(query=query, values={"validator": id})
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        logging.debug(f"Query successfully - {core_element_name} with {id_key} ({id})")
        return core_el

    @deprecated("Use fetch_filter() instead", "gqlapi.repository")
    async def get_filter(
        self,
        partition_key: str,
        order_key: str,
        order_filter: str,
        values: Dict[Any, Any],
        core_element_name: str,
        core_element_tablename: str,
        core_columns: List[str] | str = "*",
        filter_values: Optional[str] = None,
    ) -> Sequence:
        """Get core element by id

        Args:
            id: UUID
                Id of the core element
            core_element: Type[Any]
                Core element to be returned
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_columns: List[str] | str = "*"
                Columns to be returned
            id_key: str = "id"
                Column field to query from
        Raises:
            GQLApiException

        Returns:
            Sequence
        """
        # get core user
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = f"""WITH rcos AS
            ( SELECT {cols}, ROW_NUMBER() OVER (PARTITION BY {partition_key} ORDER BY {order_key} {order_filter}) row_num
            FROM {core_element_tablename}) SELECT * FROM rcos WHERE row_num = 1 and {filter_values}"""
            query = query[:-3]
            core_el = await self.db.fetch_one(query=query, values=values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if not core_el:
            raise GQLApiException(
                msg=f"{core_element_name} not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        logging.debug(f"Query successfully - {core_element_name})")
        return core_el

    async def fetch_filter(
        self,
        partition_key: str,
        order_key: str,
        order_filter: str,
        values: Dict[Any, Any],
        core_element_name: str,
        core_element_tablename: str,
        core_columns: List[str] | str = "*",
        filter_values: Optional[str] = None,
    ) -> SQLRecord | NoneType:
        """Get core element by id

        Args:
            id: UUID
                Id of the core element
            core_element: Type[Any]
                Core element to be returned
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_columns: List[str] | str = "*"
                Columns to be returned
            id_key: str = "id"
                Column field to query from
        Raises:
            GQLApiException

        Returns:
            SQLRecord | NoneType
        """
        # get core element
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = f"""WITH rcos AS
            ( SELECT {cols}, ROW_NUMBER() OVER (PARTITION BY {partition_key} ORDER BY {order_key} {order_filter}) row_num
            FROM {core_element_tablename}) SELECT * FROM rcos WHERE row_num = 1 and {filter_values}"""
            query = query[:-3]
            core_el = await self.db.fetch_one(query=query, values=values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        logging.debug(f"Query successfully - {core_element_name})")
        return core_el

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        core_element_name: str,
        core_query: str,
        core_values: Dict[str, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[Any] = None,
        core_element_tablename: Optional[str] = None,
    ) -> None:
        """Update core element by id

        Args:
            core_element_name (str):
                Name of the core element
            core_query (str):
                Query to result_
            core_values (Dict[str, Any]:
                Values to query
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_element_tablename (Optional[str], optional):
                Corresponding table name in SQL DB

        Raises:
            GQLApiException
        """
        if validate_by and validate_against and core_element_tablename:
            try:
                query = f"""SELECT * FROM {core_element_tablename} WHERE {validate_by}=:validator """
                _exists = await self.db.fetch_one(
                    query=query, values={"validator": validate_against}
                )
            except Exception as e:
                logging.error(e)
                logging.warning(f"Issues fetch {core_element_name}")
                raise GQLApiException(
                    msg=f"Get {core_element_name}",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
                )
            if _exists:
                raise GQLApiException(
                    msg=f"{core_element_name} with this validator ({validate_by}) already exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        # update core user
        await self._query(
            query=core_query, values=core_values, core_element_name=core_element_name
        )
        logging.debug(f"Update {core_element_name}")

    async def edit(
        self,
        core_element_name: str,
        core_query: str,
        core_values: Dict[str, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[Any] = None,
        core_element_tablename: Optional[str] = None,
    ) -> bool:
        """Update core element by id

        Args:
            core_element_name (str):
                Name of the core element
            core_query (str):
                Query to result_
            core_values (Dict[str, Any]:
                Values to query
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_element_tablename (Optional[str], optional):
                Corresponding table name in SQL DB

        Returns:
            bool: True if updated

        Raises:
            GQLApiException
        """
        # [TODO] - review what cases this validation applies, else remove
        if validate_by and validate_against and core_element_tablename:
            try:
                query = f"""SELECT * FROM {core_element_tablename} WHERE {validate_by}=:validator """
                _exists = await self.db.fetch_one(
                    query=query, values={"validator": validate_against}
                )
            except Exception as e:
                logging.error(e)
                logging.warning(f"Issues fetch {core_element_name}")
                raise GQLApiException(
                    msg=f"Get {core_element_name}",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
                )
            if _exists:
                logging.warning("Record already exists")
                return False
        # update core user
        try:
            await self._query(
                query=core_query,
                values=core_values,
                core_element_name=core_element_name,
            )
        except GQLApiException as ge:
            logging.warning(f"Not able to update {core_element_name}: {ge.msg}")
            return False
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues executing query: {core_element_name}")
            raise GQLApiException(
                msg=f"Error updating {core_element_name}",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        logging.debug(f"Update {core_element_name}")
        return True

    @deprecated("Use find() instead", "gqlapi.repository")
    async def search(
        self,
        values: Dict[Any, Any],
        core_element_name: str,
        core_element_tablename: str,
        core_columns: List[str] | str = "*",
        filter_values: Optional[str] = None,
        partition: Optional[str] = "",
    ) -> Sequence:
        """Search many documents

        Args:
            values (Dict[Any, Any]):
                Values to query
            core_element_name (str):
                Name of the core element
            core_element_tablename (Optional[str], optional):
                Corresponding table name in SQL DB
            core_columns (List[str] | str, optional):
                Columns to fetch.
            filter_values (Optional[str], optional):
                Values to query

        Raises:
            GQLApiException

        Returns:
            Sequence
        """
        # get core user
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = f"""{partition} SELECT {cols} FROM {core_element_tablename}"""
            if filter_values:
                query += f""" WHERE {filter_values}"""
            core_el = await self.db.fetch_all(query=query, values=values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if not core_el:
            raise GQLApiException(
                msg=f"{core_element_name} not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        logging.debug(f"Query successfully - {core_element_name}")
        return core_el

    async def find(
        self,
        values: Dict[Any, Any],
        core_element_name: str,
        core_element_tablename: str,
        core_columns: List[str] | str = "*",
        filter_values: Optional[str] = None,
        partition: Optional[str] = "",
    ) -> List[SQLRecord]:
        """Search many core elements

        Args:
            values (Dict[Any, Any]):
                Values to query
            core_element_name (str):
                Name of the core element
            core_element_tablename (Optional[str], optional):
                Corresponding table name in SQL DB
            core_columns (List[str] | str, optional):
                Columns to fetch.
            filter_values (Optional[str], optional):
                Values to query

        Returns:
            List[SQLRecord]: List of core elements

        Raises:
            GQLApiException
        """
        # get core element
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = f"""{partition} SELECT {cols} FROM {core_element_tablename}"""
            if filter_values:
                query += f""" WHERE {filter_values}"""
            core_el = await self.db.fetch_all(query=query, values=values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        logging.debug(f"Search successfully - {core_element_name}")
        return core_el

    @deprecated("Use exists() instead", "gqlapi.repository")
    async def exist(
        self,
        id: Any,
        core_element_name: str,
        core_element_tablename: str,
        id_key: str = "id",
        core_columns: List[str] | str = "*",
    ) -> None:
        """Validate document exists

        Args:
            id (UUID): unique id
            core_element_name (str):
                Name of the core element
            core_element_tablename (Optional[str], optional):
                Corresponding table name in SQL DB
            id_key (str, optional):
                key to query id
            core_columns (List[str] | str, optional):
                Columns to fetch. Defaults to "*".

        Raises:
            GQLApiException
        """
        # get core user
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = (
                f"""SELECT {cols} FROM {core_element_tablename} WHERE {id_key}=:id """
            )
            core_el = await self.db.fetch_one(query=query, values={"id": id})
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if not core_el:
            raise GQLApiException(
                msg=f"{core_element_name} not found with validator {id}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        logging.debug(f"{core_element_name} exist with validator {id}")

    async def exists(
        self,
        id: Any,
        core_element_name: str,
        core_element_tablename: str,
        id_key: str = "id",
        core_columns: List[str] | str = "id",
    ) -> bool:
        """Validate core element exists

        Args:
            id (UUID): unique id
            core_element_name (str):
                Name of the core element
            core_element_tablename (Optional[str], optional):
                Corresponding table name in SQL DB
            id_key (str, optional):
                key to query id
            core_columns (List[str] | str, optional):
                Columns to fetch. Defaults to "*".

        Returns:
            bool: True if exists

        Raises:
            GQLApiException
        """
        # get core element
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = (
                f"""SELECT {cols} FROM {core_element_tablename} WHERE {id_key}=:id """
            )
            core_el = await self.db.fetch_one(query=query, values={"id": id})
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        return False if not core_el else True

    @deprecated("Use exists() instead", "gqlapi.repository")
    async def exists_relation(
        self,
        values: Dict[Any, Any],
        core_element_name: str,
        core_element_tablename: str,
        core_columns: List[str] | str = "*",
        filter_values: Optional[str] = None,
    ):
        """Get core element by id

        Args:
            Values Dict: UUID
                Values to query
            filter_values (Dict[str, Any]:
                Values to build query
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            core_columns: List[str] | str = "*"
                Columns to be returned
        Raises:
            GQLApiException

        Returns:
            Sequence
        """
        # get core user
        try:
            cols = (
                ", ".join(core_columns)
                if isinstance(core_columns, list)
                else core_columns
            )
            query = f"""SELECT {cols} FROM {core_element_tablename}"""
            if filter_values:
                query += f""" WHERE {filter_values}"""
            core_el = await self.db.fetch_all(query=query, values=values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if core_el:
            raise GQLApiException(
                msg=f"{core_element_name} exists",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        logging.debug(f"Validate - {core_element_name}")

    async def bulk(self, query: str, query_vars: List[Dict[Any, Any]]) -> NoneType:
        """Execute bulk transaction

        Parameters
        ----------
        query : str
        query_vars : List[Dict[Any, Any]]

        Returns
        -------
        NoneType

        Raises
        ------
        GQLApiException
        """
        records_list_template = ",".join(["%s"] * len(query_vars))
        insert_query = query.format(records_list_template)
        try:
            self.db.execute(insert_query, query_vars)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues executing bulk query")
            raise GQLApiException(
                msg="Error executing bulk query",
                error_code=GQLApiErrorCodeType.EXECUTE_SQL_DB_ERROR.value,
            )

    async def execute(self, query: str, values: Dict[str, Any], core_element_name: str):
        return await self._query(
            query=query, values=values, core_element_name=core_element_name
        )

    async def raw_query(
        self, query: str, vals: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        """Execute raw query -> fetch_all

        Parameters
        ----------
        query : str
        vals : Dict[str, Any]

        Returns
        -------
        List[Dict[str, Any]]
            _description_

        Raises
        ------
        GQLApiException
        """
        try:
            res = await self.db.fetch_all(query=query, values=vals)
        except Exception as e:
            logging.error(e)
            logging.warning("Issues executing raw query")
            raise GQLApiException(
                msg="Error executing raw query",
                error_code=GQLApiErrorCodeType.EXECUTE_SQL_DB_ERROR.value,
            )
        return res


class CoreDataOrchestationRepository(CoreRepository):
    def __init__(self, sql_db) -> None:  # type: ignore
        self.db = sql_db


class CoreMongoRepository(CoreRepositoryInterface):
    def __init__(self, info: StrawberryInfo) -> None:  # type: ignore
        try:
            _db = info.context["db"].mongo
        except Exception as e:
            logging.error(e)
            logging.warning("Issues connect MONGO DB")
            raise GQLApiException(
                msg="Error creating connect MONGO DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        self.db = _db

    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_values: Dict[str, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[UUID] = None,
    ) -> bool:
        """Creates new core element

        Args:
            core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query

        Raises:
            GQLApiException

        Returns:
            UUID: unique core element id
        """
        # validate if user is already existing
        try:
            collection = self.db[core_element_collection]
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues connect {core_element_collection}")
            raise GQLApiException(
                msg=f"Connect {core_element_collection}",
                error_code=GQLApiErrorCodeType.CONNECTION_MONGO_DB_ERROR.value,
            )
        if validate_by and validate_against:
            try:
                validation = await collection.find(
                    {validate_by: Binary.from_uuid(validate_against)}  # type: ignore
                ).to_list(length=1)
            except Exception as e:
                logging.error(e)
                logging.warning(f"Issues fetch {core_element_name}")
                raise GQLApiException(
                    msg=f"Get {core_element_name}",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
                )
            if len(validation) != 0:
                raise GQLApiException(
                    msg=f"{core_element_name} with this validator ({validate_by}) already exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        # create new core user
        await collection.insert_one(core_values)
        logging.debug(f"Create new {core_element_name}")
        return True

    async def add(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_values: Dict[str, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[UUID] = None,
    ) -> UUID | Tuple[Any] | NoneType:
        """Creates new core element

        Args:
            core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query

        Raises:
            GQLApiException

        Returns:
            Tuple[Any] | UUID: unique core element id
        """
        # validate if user is already existing
        try:
            collection = self.db[core_element_collection]
            if validate_by and validate_against:
                validation = await collection.find(
                    {validate_by: Binary.from_uuid(validate_against)}  # type: ignore
                ).to_list(length=1)
                if len(validation) != 0:
                    logging.warning(
                        f"{core_element_name} with this validator ({validate_by}) already exists"
                    )
                    return None
            # create new core user
            await collection.insert_one(core_values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        logging.debug(f"Create new {core_element_name}")
        if validate_by and validate_against:
            return validate_against
        return tuple(core_values.values())  # type: ignore (safe)

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self, core_element_name: str, core_element_collection: str, query: Any
    ) -> Dict[Any, Any]:
        """Get core element by id

        Args:
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            query: Any
                To filter result
        Raises:
            GQLApiException

        Returns:
            MongoRecord
        """
        # get core user
        try:
            collection = self.db[core_element_collection]
            result = await collection.find_one(query)
            if "restaurant_business_id" in result:
                result["restaurant_business_id"] = Binary.as_uuid(
                    result["restaurant_business_id"]
                )
            if "supplier_business_id" in result:
                result["supplier_business_id"] = Binary.as_uuid(
                    result["supplier_business_id"]
                )
            result.pop("_id")
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if not result:
            raise GQLApiException(
                msg=f"{core_element_name} not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        logging.debug(f"Query successfully - {core_element_name}")
        return result

    async def fetch(
        self, core_element_name: str, core_element_collection: str, query: Any
    ) -> MongoRecord:
        """Get core element by id

        Args:
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            query: Any
                To filter result
        Raises:
            GQLApiException

        Returns:
            MongoRecord
        """
        # get core element
        try:
            collection = self.db[core_element_collection]
            result = await collection.find_one(query)
            if result:
                result.pop("_id")
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )
        if not result:
            logging.warning(f"{core_element_name} not found")
            return {}
        logging.debug(f"Query successfully - {core_element_name}")
        return result

    async def fetch_many(
        self, core_element_name: str, core_element_collection: str, query: Any
    ) -> List[Dict[Any, Any]]:
        """Get core element by id

        Args:
            core_element_name: str
                Name of the core element
            core_element_tablename: str
                Corresponding table name in SQL DB
            query: Any
                To filter result
        Raises:
            GQLApiException

        Returns:
            MongoRecord
        """
        # get core element
        try:
            collection = self.db[core_element_collection]
            result = collection.find(query)
            documents = []
            if result:
                async for r in result:
                    r.pop("_id")
                    documents.append(r)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )
        if not documents:
            logging.warning(f"{core_element_name} not found")
            return []
        logging.debug(f"Query successfully - {core_element_name}")
        return documents

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
        core_values: Dict[Any, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[UUID] = None,
    ) -> None:
        """Update core element

        core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query
            core_query: Any
                Query to result

        Raises:
            GQLApiException
        """
        # update core user
        try:
            collection = self.db[core_element_collection]
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues connect {core_element_collection}")
            raise GQLApiException(
                msg=f"Connect {core_element_collection}",
                error_code=GQLApiErrorCodeType.CONNECTION_MONGO_DB_ERROR.value,
            )
        if validate_by and validate_against:
            try:
                validation = await collection.find(
                    {validate_by: Binary.from_uuid(validate_against)}  # type: ignore
                ).to_list(length=1)
            except Exception as e:
                logging.error(e)
                logging.warning(f"Issues fetch {core_element_name}")
                raise GQLApiException(
                    msg=f"Get {core_element_name}",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
                )
            if len(validation) == 0:
                raise GQLApiException(
                    msg=f"{core_element_name} with this validator ({validate_by}) don't exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        try:
            await collection.update_one(core_query, core_values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues updating new {core_element_name}")
            raise GQLApiException(
                msg=f"Error creating {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        logging.info(f"Update {core_element_name}")

    async def edit(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
        core_values: Dict[Any, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[UUID] = None,
    ) -> bool:
        """Update core element

        core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query
            core_query: Any
                Query to result

        Returns:
            bool: True if updated

        Raises:
            GQLApiException
        """
        # update core user
        try:
            collection = self.db[core_element_collection]
            if validate_by and validate_against:
                validation = await collection.find(
                    {validate_by: Binary.from_uuid(validate_against)}  # type: ignore
                ).to_list(length=1)
                if len(validation) == 0:
                    logging.warning(
                        f"{core_element_name} with this validator ({validate_by}) don't exists"
                    )
                    return False
            await collection.update_one(core_query, core_values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues edit {core_element_name}")
            raise GQLApiException(
                msg=f"Issues editing {core_element_name}",
                error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
            )
        logging.info(f"Update {core_element_name}")
        return True

    async def update_one(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
        core_values: Dict[Any, Any],
        validate_by: Optional[str] = None,
        validate_against: Optional[UUID] = None,
    ) -> UpdateResult | NoneType:
        """Update core element

        core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query
            core_query: Any
                Query to result

        Returns:
            bool: True if updated

        Raises:
            GQLApiException
        """
        # update core user
        try:
            collection = self.db[core_element_collection]
            if validate_by and validate_against:
                validation = await collection.find(
                    {validate_by: Binary.from_uuid(validate_against)}  # type: ignore
                ).to_list(length=1)
                if len(validation) == 0:
                    logging.warning(
                        f"{core_element_name} with this validator ({validate_by}) don't exists"
                    )
                    return None
            updated_info = await collection.update_one(core_query, core_values)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues edit {core_element_name}")
            raise GQLApiException(
                msg=f"Issues editing {core_element_name}",
                error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
            )
        logging.info(f"Update {core_element_name}")
        return updated_info

    @deprecated("Use exists() instead", "gqlapi.repository")
    async def exist(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
    ) -> None:
        """Validate core existing

        Args:
            core_element_collection (str):
                Corresponding table name in MONGO DB
            core_element_name (str):
                Name of the core element
            core_query (Dict[Any, Any]):
                Query to result

        Raises:
            GQLApiException
        """
        # [TODO] - modify this. Response cannot be an exception, It should be in the case of an error.
        # update core user
        try:
            collection = self.db[core_element_collection]
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues connect {core_element_collection}")
            raise GQLApiException(
                msg=f"Connect {core_element_collection}",
                error_code=GQLApiErrorCodeType.CONNECTION_MONGO_DB_ERROR.value,
            )

        try:
            result = await collection.find_one(core_query)
            if result:
                raise GQLApiException(
                    msg=f"{core_element_name} already exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues updating new {core_element_name}")
            raise GQLApiException(
                msg=f"Error creating {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        logging.debug(f"{core_element_name} validation")

    async def exists(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
    ) -> bool:
        """Validate core existing

        Args:
            core_element_collection (str):
                Corresponding table name in MONGO DB
            core_element_name (str):
                Name of the core element
            core_query (Dict[Any, Any]):
                Query to result

        Returns:
            bool: True if exists

        Raises:
            GQLApiException
        """
        # verify core element
        result = None
        try:
            collection = self.db[core_element_collection]
            result = await collection.find_one(core_query)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues updating new {core_element_name}")
            raise GQLApiException(
                msg=f"Error creating {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        logging.debug(f"{core_element_name} validation")
        return True if result else False

    @deprecated("Use find() instead", "gqlapi.repository")
    async def search(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
    ) -> List:
        """Serch core element by id

        Args:
            core_element_collection (str):
                Corresponding table name in MONGO DB
            core_element_name (str):
                Name of the core element
            core_query (Dict[Any, Any]):
                Query to result
        Raises:
            GQLApiException

        Returns:
            List: data
        """
        # get core user
        try:
            collection = self.db[core_element_collection]
            result = collection.find(core_query)
            my_data_as_list = await result.to_list(length=1000000)
            # [TODO] - change this outside of the repository, this is not the right place
            for r in my_data_as_list:
                if "branch_id" in r and r["branch_id"]:
                    r["branch_id"] = Binary.as_uuid(r["branch_id"])
                if "restaurant_user_id" in r:
                    r["restaurant_user_id"] = Binary.as_uuid(r["restaurant_user_id"])
                r.pop("_id")
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )
        if not result:
            raise GQLApiException(
                msg=f"{core_element_name} not found",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_EMPTY_RECORD.value,
            )
        logging.debug(f"Query successfully - {core_element_name}")
        return my_data_as_list

    async def find(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
        max_length: int = 1000000,
    ) -> List[MongoRecord]:
        """Serch core element by id

        Args:
            core_element_collection (str):
                Corresponding table name in MONGO DB
            core_element_name (str):
                Name of the core element
            core_query (Dict[Any, Any]):
                Query to result
        Raises:
            GQLApiException

        Returns:
            List[MongoRecord]
        """
        # get core user
        try:
            collection = self.db[core_element_collection]
            result = collection.find(core_query)
            result_data = await result.to_list(length=max_length)
            for r in result_data:
                r.pop("_id")
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues fetch {core_element_name}")
            raise GQLApiException(
                msg=f"Get {core_element_name}",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )
        logging.debug(f"Query successfully - {core_element_name}")
        return result_data

    async def execute(self, *args):
        logging.warning("Not implemented")
        raise NotImplementedError

    async def upsert_list_element(
        self,
        core_element_collection: str,
        core_element_name: str,
        document_key: str,
        document_id: Any,
        element_key: str,
        element_id: Any,
        list_name: str,
        data: Dict[Any, Any],
    ) -> bool:
        try:
            collection = self.db[core_element_collection]

            if isinstance(document_id, UUID):
                document_id = Binary.from_uuid(document_id)
            if isinstance(element_id, UUID):
                element_id = Binary.from_uuid(element_id)
            query = {
                document_key: document_id,
                list_name + "." + element_key: element_id,
            }
            result_exists = await self.find(
                core_element_collection=core_element_collection,
                core_element_name=core_element_name,
                core_query=query,
            )
            if result_exists:
                filter = {
                    document_key: document_id,
                    list_name + "." + element_key: element_id,
                }

                # Update the element in the list
                data_set = {}
                for key, value in data.items():
                    data_set.update({list_name + ".$[elem]." + key: value})
                update = {"$set": data_set}
                array_filters = [
                    {"elem." + element_key: filter[list_name + "." + element_key]}
                ]
                collection.update_one(filter, update, array_filters=array_filters)
            else:
                filter = {document_key: document_id}
                new_values = {element_key: element_id}
                for key, value in data.items():
                    new_values.update({key: value})
                update = {
                    "$push": {
                        list_name: {
                            "$each": [new_values],
                            "$position": 0,
                        }
                    }
                }

                result = collection.update_one(filter, update)

                print(result)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues upsert {core_element_name}")
            raise GQLApiException(
                msg=f"Upsert {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        return True

    async def delete(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[str, Any],
    ) -> bool | NoneType:
        """Creates new core element

        Args:
            core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query

        Raises:
            GQLApiException

        Returns:
            Tuple[Any] | UUID: unique core element id
        """
        # validate if user is already existing
        try:
            collection = self.db[core_element_collection]

            # create new core user
            await collection.delete_one(core_query)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues delete {core_element_name}")
            raise GQLApiException(
                msg=f"Delete {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        logging.debug(f"Create new {core_element_name}")

        return True

    async def delete_many(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[str, Any],
    ) -> DeleteResult:
        """Creates new core element

        Args:
            core_element_collection: str
                Corresponding table name in MONGO DB
            core_element_name: str
                Name of the core element
            validate_by: str
                Column name to validate against
            validate_against: Any
                Value to validate against
            core_values: Dict[str, Any]
                Values to Query

        Raises:
            GQLApiException

        Returns:
            Tuple[Any] | UUID: unique core element id
        """
        # validate if user is already existing
        try:
            collection = self.db[core_element_collection]

            # create new core user
            resp = await collection.delete_many(core_query)
        except Exception as e:
            logging.error(e)
            logging.warning(f"Issues delete {core_element_name}")
            raise GQLApiException(
                msg=f"Delete {core_element_name}",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        logging.debug(f"Create new {core_element_name}")

        return resp

    async def raw_query(
        self, collection: str, query: Dict[str, Any], **kwargs
    ) -> List[MongoRecord]:
        """Raw Mongo Query

        Args:
            collection (str)
            query (Dict[str, Any])

        Returns:
            List[MongoRecord]
        """
        try:
            result = self.db[collection].find(query)
            documents = []
            async for r in result:
                r.pop("_id")
                documents.append(r)
            return documents
        except Exception as e:
            logging.error(e)
            logging.warning("Issues executing raw query")
            raise GQLApiException(
                msg="Error executing raw query",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
            )


class CoreMongoBypassRepository(CoreMongoRepository):
    def __init__(self, mongo_db: AsyncIOMotorClient) -> None:  # type: ignore
        self.db = mongo_db
