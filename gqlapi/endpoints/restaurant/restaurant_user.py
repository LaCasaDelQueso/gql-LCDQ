from typing import List, Optional
from uuid import UUID

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantDisplayPermissionsInput,
    RestaurantEmployeeInfoPermissionInput,
    RestaurantUserEmployeeGQLResult,
    RestaurantUserError,
    RestaurantUserPermContResult,
    RestaurantUserResult,
    RestaurantUserStatus,
    RestaurantUserStatusResult,
)
from gqlapi.domain.models.v2.core import PermissionDict, RestaurantEmployeeInfoPermission
from gqlapi.app.permissions import (
    IsAlimaEmployeeAuthorized,
    IsAlimaRestaurantAuthorized,
    IsAuthenticated,
)
from gqlapi.handlers.restaurant.restaurant_user import (
    RestaurantEmployeeHandler,
    RestaurantUserHandler,
    RestaurantUserPermissionHandler,
)
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessRepository,
)
from gqlapi.repository.restaurant.restaurant_user import (
    RestaurantUserPermissionRepository,
    RestaurantUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.repository.user.employee import EmployeeRepository
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

logger = get_logger(get_app())


@strawberry.type
class RestaurantUserQuery:
    @strawberry.field(
        name="getRestaurantUser",
        permission_classes=[IsAuthenticated, IsAlimaEmployeeAuthorized],
    )
    async def get_restaurant_user(
        self, info: StrawberryInfo, restaurant_user_id: UUID
    ) -> RestaurantUserResult:  # type: ignore
        """GraphQL Query to get restaurant user

        Args:
            info (StrawberryInfo): Info to connect to DB
            user_id (UUID): restaurant user id

        Returns:
            RestaurantUserResult: restaurant user + core user model
        """
        logger.info("Get restaurant user")
        # instantiate handler
        _handler = RestaurantUserHandler(
            core_user_repo=CoreUserRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
        )
        # get restaurant user
        _restaurant_user = await _handler.fetch_restaurant_user(restaurant_user_id)
        # return restaurant user
        return _restaurant_user

    @strawberry.field(
        name="getRestaurantUserFromToken",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_restaurant_user_from_token(
        self, info: StrawberryInfo
    ) -> RestaurantUserResult:  # type: ignore
        """GraphQL Query to get restaurant user from Session Token

        Args:
            info (StrawberryInfo): Info to connect to DB

        Returns:
            RestaurantUserResult: restaurant user + core user model
        """
        logger.info("Get restaurant_user by firebase_id")
        # instantiate handler
        _handler = RestaurantUserHandler(
            core_user_repo=CoreUserRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
        )
        # get restaurant user by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            _restaurant_user = await _handler.fetch_restaurant_user_by_firebase_id(
                fb_id
            )
            if not _restaurant_user:
                return RestaurantUserError(
                    msg="Restaurant user not found",
                    code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            return _restaurant_user
        except GQLApiException as ge:
            return RestaurantUserError(
                msg="Error fetching restaurant user", code=ge.error_code
            )
        except Exception as e:
            logger.error(e)
            return RestaurantUserError(
                msg="Error fetching restaurant user",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class RestaurantUserPermissionQuery:
    @strawberry.field(
        name="getRestaurantEmployees",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )  # [TODO] - implement alima restaurant admin access
    async def get_restaurant_user_permission_and_contact_info(
        self,
        info: StrawberryInfo,
        restaurant_business_id: UUID,
    ) -> List[RestaurantUserPermContResult]:  # type: ignore
        """GraphQL Query to get restaurant user permission and contact info

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id

        Returns:
            List[RestaurantUserPermContResult]: restaurant user permission and contact info
        """
        logger.info("get restaurant user permission and contact info")
        # instantiate handler
        try:
            _handler = RestaurantUserPermissionHandler(
                restaurant_user_perm_repo=RestaurantUserPermissionRepository(info),
                restaurant_employee_repo=EmployeeRepository(info),
            )
            # [TODO] - validate whether this User has access to retrieve this info
            # call validation
            employees = await _handler.fetch_restaurant_users_contact_and_permission_from_business(
                restaurant_business_id=restaurant_business_id
            )
            # [TODO] - filter those employees it has access to list
            return employees
        except GQLApiException as ge:
            return [RestaurantUserError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                RestaurantUserError(
                    msg="Error fetching restaurant user permission and contact info",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getRestaurantPermissionsFromToken",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_restaurant_user_permission_and_contact_info_from_token(
        self,
        info: StrawberryInfo,
    ) -> RestaurantUserPermContResult:  # type: ignore
        """GraphQL Query to get restaurant user permission and contact info by session token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            RestaurantUserPermContResult: restaurant user permission and contact info
        """
        logger.info("get restaurant user permission and contact info")
        # instantiate handler
        try:
            _handler = RestaurantUserPermissionHandler(
                restaurant_user_perm_repo=RestaurantUserPermissionRepository(info),
                restaurant_employee_repo=EmployeeRepository(info),
                core_user_repo=CoreUserRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
            )
            fb_id = info.context["request"].user.firebase_user.firebase_id
            self_employee = await _handler.fetch_restaurant_user_contact_and_permission(
                fb_id
            )
            return self_employee
        except GQLApiException as ge:
            logger.warning(ge)
            return RestaurantUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return RestaurantUserError(
                msg="Error fetching restaurant user permission and contact info",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class RestaurantUserMutation:
    @strawberry.mutation(
        name="newRestaurantUser",
    )
    async def post_new_restaurant_user(
        self,
        info: StrawberryInfo,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> RestaurantUserResult:  # type: ignore
        """GraphQL Mutation to create new restaurant user

        Args:
            info (StrawberryInfo): Info to connect to DB
            first_name (str): user first name
            last_name (str): user last name
            email (str): user contact email
            phone_number (str): user contact number
            firebase_id (str): unique restaurant user firebase id_
            role (str): user role in the restaurant

        Returns:
            RestaurantUserResult: restaurant user + core user model
        """
        logger.info("Create new restaurant_user")
        # instantiate handler
        _handler = RestaurantUserHandler(
            core_user_repo=CoreUserRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
            employee_repo=EmployeeRepository(info),
        )
        # validate inputs
        if not (first_name and last_name and email and firebase_id and phone_number):
            return RestaurantUserError(
                msg="Empty values for creating Restaurant User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.new_restaurant_user(
                first_name,
                last_name,
                email,
                phone_number,
                firebase_id,
                role,
            )
            return _resp
        except GQLApiException as ge:
            return RestaurantUserError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="updateRestaurantUser",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_restaurant_user(
        self,
        info: StrawberryInfo,
        restaurant_user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
        departament: Optional[str] = None,
        restaurant_business_id: Optional[UUID] = None,
    ) -> RestaurantUserResult:  # type: ignore
        """GraphQL Mutation to edit restaurant user

        Args:
            info (StrawberryInfo): Info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id
            core_id (UUID): unique core user id
            first_name (Optional[str], optional): user first name. Defaults to None.
            last_name (Optional[str], optional): user last name. Defaults to None.
            phone_number (Optional[str], optional): user contact number. Defaults to None.
            role (Optional[str], optional): user role in the restaurant. Defaults to None.
            department (Optional[str], optional): department to which the user belongs in the restaurant. Defaults to None.

        Returns:
            RestaurantUserResult: restaurant user + core user model
        """
        logger.info("Edit restaurant user")
        # validate inputs
        if (
            not first_name
            and not last_name
            and not phone_number
            and not role
            and not departament
            and not restaurant_business_id
        ):
            return RestaurantUserError(
                msg="Empty values for updating Restaurant User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # instantiate handler
            _handler = RestaurantUserHandler(
                core_user_repo=CoreUserRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
            )
            # call handler
            return await _handler.edit_restaurant_user(
                restaurant_user_id,
                first_name,
                last_name,
                phone_number,
                role,
            )
        except GQLApiException as ge:
            return RestaurantUserError(msg=ge.msg, code=ge.error_code)

    # @strawberry.mutation(
    #     name="changeRestaurantUserStatus",
    #     permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    # )  # [TODO] - implement alima restaurant admin access
    # async def patch_change_restaurant_user_status(
    #     self, info: StrawberryInfo, restaurant_user_id: UUID, enabled: bool
    # ) -> RestaurantUserStatusResult:  # type: ignore
    #     """GraphQL Mutation to change restaurant user status

    #     Args:
    #         info (StrawberryInfo): Info to connect to DB
    #         core_id (UUID): unique core user id
    #         enabled (bool): user status

    #     Returns:
    #         RestaurantUserResult: restaurant user + core user model
    #     """
    #     logger.info("Change restaurant user status")
    #     # instantiate handler
    #     try:
    #         _handler = RestaurantUserHandler(
    #             core_user_repo=CoreUserRepository(info),
    #             restaurant_user_repo=RestaurantUserRepository(info),
    #         )
    #         # validate inputs
    #         if not restaurant_user_id and not enabled:
    #             return RestaurantUserError(
    #                 msg="Empty values for updating Restaurant User",
    #                 code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
    #             )
    #         # call validation
    #         _enabled = await _handler.change_restaurant_user_status(
    #             restaurant_user_id, enabled
    #         )
    #         return RestaurantUserStatus(enabled=_enabled)
    #     except GQLApiException as ge:
    #         return RestaurantUserError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="deleteRestaurantUser",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )  # [TODO] - implement alima restaurant admin access
    async def patch_delete_restaurant_user(
        self,
        info: StrawberryInfo,
        restaurant_user_id: UUID,
        deleted: bool,
    ) -> RestaurantUserStatusResult:  # type: ignore
        """GraphQL Mutation to delete restaurant user

        Args:
            info (StrawberryInfo): Info to connect to DB
            core_id (UUID): unique core user id
            deleted (bool): user statu

        Returns:
            RestaurantUserResult: restaurant user + core user model
        """
        logger.info("Delete restaurant user")
        try:
            # [TODO] validate whether this user has permission to delete
            # instantiate handler
            _handler = RestaurantUserHandler(
                core_user_repo=CoreUserRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
            )
            # call handler
            _deleted = await _handler.erase_restaurant_user(restaurant_user_id, deleted)
            return RestaurantUserStatus(deleted=_deleted)
        except GQLApiException as ge:
            return RestaurantUserError(msg=ge.msg, code=ge.error_code)


@strawberry.type
class RestaurantEmployeeMutation:
    @strawberry.mutation(
        name="newRestaurantEmployee",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )  # [TODO] - implement alima restaurant admin access
    async def post_new_restaurant_employee(
        self,
        info: StrawberryInfo,
        restaurant_business_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        position: str,
        display_perms: Optional[RestaurantDisplayPermissionsInput] = None,
        department: Optional[str] = None,
        permission: Optional[List[RestaurantEmployeeInfoPermissionInput]] = None,
    ) -> RestaurantUserEmployeeGQLResult:  # type: ignore
        """Create a new restaurant employee

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id

            Resolvers: 2
            POST - Restaurant supplier creation (with catalog)
            Arguments params           name (str): employee first name
            last_name (str): employee last name
            phone_number (str): employee contact number
            email (str): employee contact email
            department (Optional[str], optional): department to which the restaurant employee belongs. Defaults to None.
            position (Optional[str], optional): employee role in restaurant. Defaults to None..

        Returns:
            RestaurantUserResult: Restaurant Employee Info model
        """
        logger.info("create restaurant employee")
        # instantiate handler
        try:
            _handler = RestaurantEmployeeHandler(
                restaurant_employee_repo=EmployeeRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
                core_user_repo=CoreUserRepository(info),
                rest_user_perm_repo=RestaurantUserPermissionRepository(info),
                firebase_api_client=info.context["db"].firebase,
                rest_branch_repo=RestaurantBranchRepository(info),
                rest_business_repo=RestaurantBusinessRepository(info),
            )
            if (
                not name
                or not last_name
                or not phone_number
                or not email
                or not phone_number
                or not restaurant_business_id
            ):
                return RestaurantUserError(
                    msg="Empty values for creating Restaurant User Employee",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # [TODO] - validate user has permission to create user
            # map input to output
            perms_out = []
            if permission:
                for p in permission:
                    if p.permissions:
                        perms_out.append(
                            RestaurantEmployeeInfoPermission(
                                branch_id=p.branch_id,
                                permissions=[
                                    PermissionDict(key=_p.key, validation=_p.validation)
                                    for _p in p.permissions
                                ],
                            )
                        )
                    else:
                        perms_out.append(
                            RestaurantEmployeeInfoPermission(
                                branch_id=p.branch_id, permissions=None
                            )
                        )
            # call validation
            return await _handler.new_restaurant_employee(
                restaurant_business_id,
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
            return RestaurantUserError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="updateRestaurantEmployee",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )  # [TODO] - implement alima restaurant admin access
    async def patch_edit_restaurant_employee(
        self,
        info: StrawberryInfo,
        restaurant_business_id: UUID,
        restaurant_user_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        display_perms: Optional[RestaurantDisplayPermissionsInput] = None,
        permission: Optional[List[RestaurantEmployeeInfoPermissionInput]] = None,
    ) -> RestaurantUserEmployeeGQLResult:  # type: ignore
        """Edit a restaurant employee

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id
            id (UUID): unique employee id
            name (Optional[str]): employee first name
            last_name (Optional[str]): employee last name
            department (Optional[str]): _department to which the restaurant employee belongs
            position (Optional[str]): employee role in restaurant.
            phone_number (Optional[str]): employee contact number
            email (Optional[str]): employee contact email

        Returns:
            RestaurantUserResult: _description_
        """
        logger.info("update restaurant employee")
        try:
            # [TODO] - validate user has permission to edit employee
            # instantiate handler
            _handler = RestaurantEmployeeHandler(
                restaurant_employee_repo=EmployeeRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
                core_user_repo=CoreUserRepository(info),
                rest_user_perm_repo=RestaurantUserPermissionRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                rest_business_repo=RestaurantBusinessRepository(info),
            )
            # map input to output
            perms_out = []
            if permission:
                for p in permission:
                    if p.permissions:
                        perms_out.append(
                            RestaurantEmployeeInfoPermission(
                                branch_id=p.branch_id,
                                permissions=[
                                    PermissionDict(key=_p.key, validation=_p.validation)
                                    for _p in p.permissions
                                ],
                            )
                        )
                    else:
                        perms_out.append(
                            RestaurantEmployeeInfoPermission(
                                branch_id=p.branch_id, permissions=None
                            )
                        )
            # call validation
            edit_rs = await _handler.edit_restaurant_employee(
                restaurant_business_id,
                restaurant_user_id,
                name,
                last_name,
                department,
                position,
                phone_number,
                display_perms.__dict__,
                perms_out,
            )
            return edit_rs
        except GQLApiException as ge:
            logger.warning(ge)
            return RestaurantUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return RestaurantUserError(
                msg="Error updating restaurant employee",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
