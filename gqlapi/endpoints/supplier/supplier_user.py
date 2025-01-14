from typing import List, Optional
from uuid import UUID
import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.models.v2.core import PermissionDict, SupplierEmployeeInfoPermission
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierDisplayPermissionsInput,
    SupplierEmployeeInfoPermissionInput,
    SupplierUserEmployeeGQLResult,
    SupplierUserError,
    SupplierUserResult,
    SupplierUserStatus,
    SupplierUserStatusResult,
)
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.app.permissions import (
    IsAlimaSupplyAuthorized,
    IsAuthenticated,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.handlers.supplier.supplier_user import (
    SupplierEmployeeHandler,
    SupplierUserHandler,
    SupplierUserPermissionHandler,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.employee import EmployeeRepository
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

logger = get_logger(get_app())


@strawberry.type
class SupplierUserQuery:
    @strawberry.field(
        name="getSupplierUserFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_user_from_token(
        self, info: StrawberryInfo
    ) -> SupplierUserResult:  # type: ignore
        """GraphQL Query to get supplier user from Session Token

        Args:
            info (StrawberryInfo): Info to connect to DB

        Returns:
            SupplierUserResult: supplier user + core user model
        """
        logger.info("Get supplier by firebase_id")
        # instantiate handler
        _handler = SupplierUserHandler(
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            employee_repo=EmployeeRepository(info),
        )
        # get supplier user by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            _sup_user = await _handler.fetch_supplier_user_by_firebase_id(fb_id)
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(
                msg="Error fetching supplier user", code=ge.error_code
            )
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error fetching supplier user",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
        # return supplier user
        return _sup_user


@strawberry.type
class SupplierUserPermissionQuery:
    @strawberry.field(
        name="getSupplierEmployees",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )  # [TODO] - implement alima restaurant admin access
    async def get_supplier_employees(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
    ) -> List[SupplierUserEmployeeGQLResult]:  # type: ignore
        """GraphQL Query to get supplier employees permission and contact info

        Args:
            info (StrawberryInfo): info to connect to DB
            supplier_business_id (UUID): unique supplier business id

        Returns:
            List[SupplierUserEmployeeGQLResult]
        """
        logger.info("get supplier employees permission and contact info")
        # instantiate handler
        try:
            _handler = SupplierUserPermissionHandler(
                supplier_user_perm_repo=SupplierUserPermissionRepository(info),
                supplier_employee_repo=EmployeeRepository(info),
            )
            # [TODO] - validate whether this User has access to retrieve this info
            # call validation
            employees = await _handler.fetch_supplier_users_contact_and_permission_from_business(
                supplier_business_id=supplier_business_id
            )
            # [TODO] - filter those employees it has access to list
            return employees
        except GQLApiException as ge:
            return [SupplierUserError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                SupplierUserError(
                    msg="Error fetching restaurant user permission and contact info",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getSupplierPermissionsFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_user_permission_from_token(
        self,
        info: StrawberryInfo,
    ) -> SupplierUserEmployeeGQLResult:  # type: ignore
        """GraphQL Query to get supplier user permission
            and contact info by session token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            SupplierUserEmployeeGQLResult: supplier user permission and contact info
        """
        logger.info("get supplier user permission and contact info")
        # instantiate handler
        try:
            _handler = SupplierUserPermissionHandler(
                supplier_user_perm_repo=SupplierUserPermissionRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_employee_repo=EmployeeRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            fb_id = info.context["request"].user.firebase_user.firebase_id
            self_employee = await _handler.fetch_supplier_user_contact_and_permission(
                fb_id
            )
            return self_employee
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error fetching supplier user permission and contact info",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class SupplierUserMutation:
    @strawberry.mutation(
        name="newSupplierUser",
    )
    async def post_new_supplier_user(
        self,
        info: StrawberryInfo,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> SupplierUserResult:  # type: ignore
        """GraphQL Mutation to create new supplier user

        Args:
            info (StrawberryInfo): Info to connect to DB
            first_name (str): user first name
            last_name (str): user last name
            email (str): user contact email
            phone_number (str): user contact number
            firebase_id (str): unique supplier user firebase id_
            role (str): user role in the supplier

        Returns:
            SupplierUserResult: supplier user + core user model
        """
        logger.info("Create new supplier user")
        # instantiate handler
        _handler = SupplierUserHandler(
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            employee_repo=EmployeeRepository(info),
        )
        # validate inputs
        if not (first_name and last_name and email and firebase_id and phone_number):
            return SupplierUserError(
                msg="Empty values for creating Supplier User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.new_supplier_user(
                first_name,
                last_name,
                email,
                phone_number,
                firebase_id,
                role,
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error creating supplier user",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="updateSupplierUser",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_supplier_user(
        self,
        info: StrawberryInfo,
        supplier_user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
        departament: Optional[str] = None,
        supplier_business_id: Optional[UUID] = None,
    ) -> SupplierUserResult:  # type: ignore
        """GraphQL Mutation to edit supplier user

        Args:
            info (StrawberryInfo): Info to connect to DB
            supplier_business_id (UUID): unique supplier business id
            core_id (UUID): unique core user id
            first_name (Optional[str], optional): user first name. Defaults to None.
            last_name (Optional[str], optional): user last name. Defaults to None.
            phone_number (Optional[str], optional): user contact number. Defaults to None.
            role (Optional[str], optional): user role in the supplier. Defaults to None.
            department (Optional[str], optional): department to which the user belongs in the supplier. Defaults to None.

        Returns:
            SupplierUserResult: supplier user + core user model
        """
        logger.info("Edit supplier user")
        # validate inputs
        if (
            not first_name
            and not last_name
            and not phone_number
            and not role
            and not departament
            and not supplier_business_id
        ):
            return SupplierUserError(
                msg="Empty values for updating Supplier User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # instantiate handler
            _handler = SupplierUserHandler(
                core_user_repo=CoreUserRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
            )
            # call handler
            return await _handler.edit_supplier_user(
                supplier_user_id,
                first_name,
                last_name,
                phone_number,
                role,
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error updating supplier user",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="deleteSupplierUser",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )  # [TODO] - implement alima supplier admin access
    async def patch_delete_supplier_user(
        self,
        info: StrawberryInfo,
        supplier_user_id: UUID,
        deleted: bool,
    ) -> SupplierUserStatusResult:  # type: ignore
        """GraphQL Mutation to delete supplier user

        Args:
            info (StrawberryInfo): Info to connect to DB
            supplier_user_id (UUID): unique supplier user id
            deleted (bool): user statu

        Returns:
            SupplierUserStatusResult
        """
        logger.info("Delete supplier user")
        try:
            # [TODO] validate whether this user has permission to delete
            # instantiate handler
            _handler = SupplierUserHandler(
                core_user_repo=CoreUserRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
            )
            # call handler
            _deleted = await _handler.erase_supplier_user(supplier_user_id, deleted)
            return SupplierUserStatus(deleted=_deleted)
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error deleting supplier user",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class SupplierEmployeeMutation:
    @strawberry.mutation(
        name="newSupplierEmployee",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )  # [TODO] - implement alima supplier admin access
    async def post_new_supplier_employee(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        position: str,
        display_perms: Optional[SupplierDisplayPermissionsInput] = None,
        department: Optional[str] = None,
        permission: Optional[List[SupplierEmployeeInfoPermissionInput]] = None,
    ) -> SupplierUserEmployeeGQLResult:  # type: ignore
        """Create a new supplier employee

        Args:
            info (StrawberryInfo): info to connect to DB
            supplier_business_id (UUID): unique supplier business id
        Returns:
            RestaurantUserResult: Restaurant Employee Info model
        """
        logger.info("create supplier employee")
        # instantiate handler
        try:
            _handler = SupplierEmployeeHandler(
                supplier_employee_repo=EmployeeRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                core_user_repo=CoreUserRepository(info),
                sup_user_perm_repo=SupplierUserPermissionRepository(info),
                firebase_api_client=info.context["db"].firebase,
                sup_unit_repo=SupplierUnitRepository(info),
                sup_business_repo=SupplierBusinessRepository(info),
            )
            if (
                not name
                or not last_name
                or not phone_number
                or not email
                or not phone_number
                or not supplier_business_id
            ):
                return SupplierUserError(
                    msg="Empty values for creating Supplier User Employee",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # [TODO] - validate user has permission to create user
            # map input to output
            perms_out = []
            if permission:
                for p in permission:
                    if p.permissions:
                        perms_out.append(
                            SupplierEmployeeInfoPermission(
                                unit_id=p.unit_id,
                                permissions=[
                                    PermissionDict(key=_p.key, validation=_p.validation)
                                    for _p in p.permissions
                                ],
                            )
                        )
                    else:
                        perms_out.append(
                            SupplierEmployeeInfoPermission(
                                unit_id=p.unit_id, permissions=None
                            )
                        )
            # call validation
            return await _handler.new_supplier_employee(
                supplier_business_id,
                name,
                last_name,
                phone_number,
                email,
                position,
                display_perms.__dict__,
                department,
                perms_out,
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error creating supplier employee",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="updateSupplierEmployee",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )  # [TODO] - implement alima supplier admin access
    async def patch_edit_supplier_employee(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        supplier_user_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        display_perms: Optional[SupplierDisplayPermissionsInput] = None,
        permission: Optional[List[SupplierEmployeeInfoPermissionInput]] = None,
    ) -> SupplierUserEmployeeGQLResult:  # type: ignore
        """Edit a supplier employee

        Args:
            info (StrawberryInfo): info to connect to DB
            supplier_business_id (UUID): unique supplier business id
            supplier_user_id (UUID): unique employee id
            name (Optional[str]): employee first name
            last_name (Optional[str]): employee last name
            department (Optional[str]): _department to which the restaurant employee belongs
            position (Optional[str]): employee role in restaurant.
            phone_number (Optional[str]): employee contact number
            email (Optional[str]): employee contact email

        Returns:
            SupplierUserEmployeeGQLResult: Restaurant Employee Info model
        """
        logger.info("update supplier employee")
        try:
            # [TODO] - validate user has permission to edit employee
            # instantiate handler
            _handler = SupplierEmployeeHandler(
                supplier_employee_repo=EmployeeRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                core_user_repo=CoreUserRepository(info),
                sup_user_perm_repo=SupplierUserPermissionRepository(info),
                firebase_api_client=info.context["db"].firebase,
                sup_unit_repo=SupplierUnitRepository(info),
                sup_business_repo=SupplierBusinessRepository(info),
            )
            # map input to output
            perms_out = []
            if permission:
                for p in permission:
                    if p.permissions:
                        perms_out.append(
                            SupplierEmployeeInfoPermission(
                                unit_id=p.unit_id,
                                permissions=[
                                    PermissionDict(key=_p.key, validation=_p.validation)
                                    for _p in p.permissions
                                ],
                            )
                        )
                    else:
                        perms_out.append(
                            SupplierEmployeeInfoPermission(
                                unit_id=p.unit_id, permissions=None
                            )
                        )
            # call validation
            edit_rs = await _handler.edit_supplier_employee(
                supplier_business_id=supplier_business_id,
                supplier_user_id=supplier_user_id,
                name=name,
                last_name=last_name,
                department=department,
                position=position,
                phone_number=phone_number,
                display_perms=display_perms.__dict__,
                permission=perms_out,
            )
            return edit_rs
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUserError(
                msg="Error updating supplier employee",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
