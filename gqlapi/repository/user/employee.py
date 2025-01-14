import logging
from types import NoneType
from typing import Dict, Any
from uuid import UUID
from bson import Binary
from gqlapi.domain.interfaces.v2.user.employee import EmployeeRepositoryInterface
from gqlapi.domain.models.v2.core import (
    PermissionDict,
    RestaurantEmployeeInfo,
    SupplierEmployeeInfo,
)
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreMongoRepository
from gqlapi.utils.domain_mapper import domain_to_dict


default_branch_perms = [
    PermissionDict(**{"key": "preordenes-all", "validation": True}),
    PermissionDict(**{"key": "preordenes-validate", "validation": True}),
    PermissionDict(**{"key": "ordenes-all", "validation": True}),
    PermissionDict(**{"key": "ordenes-history", "validation": True}),
    PermissionDict(**{"key": "suppliers-all", "validation": True}),
    PermissionDict(**{"key": "usersadmin-all", "validation": True}),
]

default_unit_perms = [
    PermissionDict(**{"key": "ordenes-all", "validation": True}),
    PermissionDict(**{"key": "invoices-all", "validation": True}),
    PermissionDict(**{"key": "clients-all", "validation": True}),
    PermissionDict(**{"key": "catalog-all", "validation": True}),
    PermissionDict(**{"key": "usersadmin-all", "validation": True}),
]


class EmployeeRepository(CoreMongoRepository, EmployeeRepositoryInterface):
    async def new_restaurant_employee(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo,
    ) -> UUID:
        """Creates new employee

        Args:
            core_element_collection: str
            employee: RestaurantEmployeeInfo

        Raises:
            GQLApiException

        Returns:
            UUID: unique core user id
        """
        # cast to dict
        employee_vals = domain_to_dict(employee)
        id = employee_vals["restaurant_user_id"]
        employee_vals["restaurant_user_id"] = Binary.from_uuid(id)
        if (
            "branch_permissions" in employee_vals
            and employee_vals["branch_permissions"]
        ):
            employee_vals["branch_permissions"] = [
                domain_to_dict(ep) for ep in employee_vals["branch_permissions"]
            ]
            for bp in employee_vals.get("branch_permissions", []):
                if bp["branch_id"]:
                    bp["branch_id"] = Binary.from_uuid(bp["branch_id"])
                    bp["permissions"] = [domain_to_dict(p) for p in bp["permissions"]]
        # call super method from new
        await super().add(
            core_element_collection=core_element_collection,
            core_element_name="Employee Info - Restaurant",
            core_values=employee_vals,
        )
        return id

    async def new_supplier_employee(
        self,
        core_element_collection: str,
        employee: SupplierEmployeeInfo,
    ) -> UUID:
        """Creates new employee

        Args:
            core_element_collection: str
            employee: SupplierEmployeeInfo

        Raises:
            GQLApiException

        Returns:
            UUID: unique core user id
        """
        # cast to dict
        employee_vals = domain_to_dict(employee)
        id = employee_vals["supplier_user_id"]
        employee_vals["supplier_user_id"] = Binary.from_uuid(id)
        if "unit_permissions" in employee_vals and employee_vals["unit_permissions"]:
            employee_vals["unit_permissions"] = [
                domain_to_dict(ep) for ep in employee_vals["unit_permissions"]
            ]
            for bp in employee_vals.get("unit_permissions", []):
                if bp["unit_id"]:
                    bp["unit_id"] = Binary.from_uuid(bp["unit_id"])
                    bp["permissions"] = [domain_to_dict(p) for p in bp["permissions"]]
        # call super method from new
        await super().add(
            core_element_collection=core_element_collection,
            core_element_name="Employee Info - Supplier",
            core_values=employee_vals,
        )
        return id

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self,
        core_element_collection: str,
        user_id_key: str,
        user_id: UUID,
    ) -> Dict[Any, Any]:
        """Get core user by id

        Args:
            user_id: UUID
            user_id_key: str
                restaurant_user_id / supplier_user_id

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """

        try:
            collection = self.db[core_element_collection]
            result = await collection.find_one({user_id_key: Binary.from_uuid(user_id)})
            if result:
                result.pop("_id")
                result[user_id_key] = Binary.as_uuid(result[user_id_key])

        except Exception as e:
            logging.error(e)
            logging.warning("Issues fetch Employee Info")
            raise GQLApiException(
                msg="Get Employee Info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        if not result:
            raise GQLApiException(
                msg="Employee Info not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        logging.debug(f"Query successfully {core_element_collection}")
        return result

    async def fetch(
        self,
        core_element_collection: str,
        user_id_key: str,
        user_id: UUID,
    ) -> Dict[Any, Any]:
        """Get core user by id

        Args:
            user_id: UUID
            user_id_key: str
                restaurant_user_id / supplier_user_id

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """

        try:
            collection = self.db[core_element_collection]
            result = await collection.find_one({user_id_key: Binary.from_uuid(user_id)})
            if result:
                result.pop("_id")
                result[user_id_key] = Binary.as_uuid(result[user_id_key])
        except Exception as e:
            logging.error(e)
            logging.warning("Issues fetch Employee Info")
            raise GQLApiException(
                msg="Get Employee Info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        logging.debug(f"Query successfully {core_element_collection}")
        return result

    async def exist(
        self,
        core_element_collection: str,
        user_id_key: str,  # Restaurant_user_id / Supplier_user_id
        user_id: UUID,
    ) -> NoneType:
        """Get core user by id

        Args:
            user_id: UUID
            user_id_key: str
                restaurant_user_id / supplier_user_id

        Raises:
            GQLApiException

        Returns:
            CoreUser
        """

        try:
            # collection = self.db[core_element_collection]
            query = {user_id_key: Binary.from_uuid(user_id)}

            await super().exist(
                core_element_collection=core_element_collection,
                core_element_name=user_id_key,
                core_query=query,
            )
        except Exception as e:
            logging.error(e)
            logging.warning("Issues fetch Employee Info")
            raise GQLApiException(
                msg="Get Employee Info",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo,
        user_id_key: str,
        user_id: UUID,
    ) -> bool:
        """Update core user by id

        Args:
            user_id: UUID
            user_id_key: str
                restaurant_user_id / supplier_user_id
            employee: RestaurantEmployeeInfo

        Raises:
            GQLApiException

        Returns:
            Bool
        """
        # create update query
        employee_vals = domain_to_dict(employee)
        query = {
            user_id_key: Binary.from_uuid(user_id),
        }

        internal_values = {}

        if employee_vals["name"]:
            internal_values["name"] = employee_vals["name"]
        if employee_vals["last_name"]:
            internal_values["last_name"] = employee_vals["last_name"]
        if employee_vals["department"]:
            internal_values["department"] = employee_vals["department"]
        if employee_vals["position"]:
            internal_values["position"] = employee_vals["position"]
        if employee_vals["phone_number"]:
            internal_values["phone_number"] = employee_vals["phone_number"]
        if employee_vals["email"]:
            internal_values["email"] = employee_vals["email"]
        if (
            "branch_permissions" in employee_vals
            and employee_vals["branch_permissions"] is not None
        ):
            internal_values["branch_permissions"] = [
                domain_to_dict(ep) for ep in employee_vals["branch_permissions"]
            ]
            for bp in internal_values.get("branch_permissions", []):
                if bp["branch_id"]:
                    bp["branch_id"] = Binary.from_uuid(bp["branch_id"])
                    bp["permissions"] = [domain_to_dict(p) for p in bp["permissions"]]

        new_values = {"$set": internal_values}

        await super().update(
            core_element_collection=core_element_collection,
            core_element_name="Employee Info",
            core_query=query,
            core_values=new_values,
        )
        return True

    async def edit(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo | SupplierEmployeeInfo,
        user_id_key: str,
        user_id: UUID,
    ) -> bool:
        """Update core user by id

        Args:
            user_id: UUID
            user_id_key: str
                restaurant_user_id / supplier_user_id
            employee: RestaurantEmployeeInfo

        Raises:
            GQLApiException

        Returns:
            Bool
        """
        # create update query
        employee_vals = domain_to_dict(employee)
        query = {
            user_id_key: Binary.from_uuid(user_id),
        }
        perms_key = (
            "branch_permissions"
            if user_id_key == "restaurant_user_id"
            else "unit_permissions"
        )
        id_key = "branch_id" if user_id_key == "restaurant_user_id" else "unit_id"
        internal_values = {}

        if employee_vals["name"]:
            internal_values["name"] = employee_vals["name"]
        if employee_vals["last_name"]:
            internal_values["last_name"] = employee_vals["last_name"]
        if employee_vals["department"]:
            internal_values["department"] = employee_vals["department"]
        if employee_vals["position"]:
            internal_values["position"] = employee_vals["position"]
        if employee_vals["phone_number"]:
            internal_values["phone_number"] = employee_vals["phone_number"]
        if employee_vals["email"]:
            internal_values["email"] = employee_vals["email"]
        if perms_key in employee_vals and employee_vals[perms_key] is not None:
            internal_values[perms_key] = [
                domain_to_dict(ep) for ep in employee_vals[perms_key]
            ]
            for bp in internal_values.get(perms_key, []):
                if bp[id_key]:
                    bp[id_key] = Binary.from_uuid(bp[id_key])
                    bp["permissions"] = [domain_to_dict(p) for p in bp["permissions"]]

        new_values = {"$set": internal_values}

        return await super().edit(
            core_element_collection=core_element_collection,
            core_element_name="Employee Info",
            core_query=query,
            core_values=new_values,
        )

    async def upsert(
        self,
        core_element_collection: str,
        employee: RestaurantEmployeeInfo | SupplierEmployeeInfo,
        user_id_key: str,
        user_id: UUID,
    ) -> bool:
        """Update or insert value in core element collection

        Parameters
        ----------
        core_element_collection : str
        employee : RestaurantEmployeeInfo | SupplierEmployeeInfo
        user_id_key : Optional[str], optional
        user_id : Optional[UUID], optional

        Returns
        -------
        bool
        """
        exists = await self.exists(
            core_element_collection=core_element_collection,
            core_element_name="Employee Info",
            core_query={user_id_key: Binary.from_uuid(user_id)},
        )

        if not exists:
            _id = None
            if user_id_key == "restaurant_user_id" and isinstance(
                employee, RestaurantEmployeeInfo
            ):
                _id = await self.new_restaurant_employee(
                    core_element_collection, employee
                )
            elif user_id_key == "supplier_user_id" and isinstance(
                employee, SupplierEmployeeInfo
            ):
                _id = await self.new_supplier_employee(
                    core_element_collection, employee
                )
            return True if _id else False
        else:
            return await self.edit(
                core_element_collection, employee, user_id_key, user_id
            )
