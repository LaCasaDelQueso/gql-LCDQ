import json
from types import NoneType
from typing import Any, Dict, Optional, List
from uuid import UUID
import secrets
import string
from bson import Binary
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantEmployeeHandlerInterface,
    RestaurantUserEmployeeGQL,
    RestaurantUserGQL,
    RestaurantUserHandlerInterface,
    RestaurantUserPermCont,
    RestaurantUserPermissionHandlerInterface,
    RestaurantUserPermissionRepositoryInterface,
    RestaurantUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.user.employee import EmployeeRepositoryInterface
from gqlapi.domain.models.v2.core import (
    CoreUser,
    PermissionDict,
    RestaurantEmployeeInfo,
    RestaurantEmployeeInfoPermission,
)
from gqlapi.lib.clients.clients.firebaseapi.firebase_auth import FirebaseAuthApi
from gqlapi.domain.models.v2.restaurant import RestaurantUserPermission
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.notifications import (
    send_employee_welcome_msg,
    send_new_resto_user_welcome_msg,
)


logger = get_logger(get_app())


class RestaurantUserHandler(RestaurantUserHandlerInterface):
    def __init__(
        self,
        core_user_repo: CoreUserRepositoryInterface,
        restaurant_user_repo: RestaurantUserRepositoryInterface,
        employee_repo: Optional[EmployeeRepositoryInterface] = None,
    ):
        self.core_user_repository = core_user_repo
        self.repository = restaurant_user_repo
        if employee_repo:
            self.employee_repo = employee_repo

    async def new_restaurant_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> RestaurantUserGQL:
        """Creates a new core user and then a restaurant user

        Args:
            first_name (str): user first name
            last_name (str): user last name
            email (str): user contact email
            phone_number (str): user contact number
            firebase_id (str): unique restaurant user firebase id_
            role (str): user role in the restaurant

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        # create core user
        core_id = await self.core_user_repository.new(
            CoreUser(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                firebase_id=firebase_id,
            )
        )
        # create restaurant user
        rest_user_id = await self.repository.new(core_id, role)

        # new restaurant employee in mongo
        await self.employee_repo.new_restaurant_employee(
            core_element_collection="restaurant_employee_directory",
            employee=RestaurantEmployeeInfo(
                restaurant_user_id=rest_user_id,
                name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                department="Admin",
                position="Admin",
                branch_permissions=[],
            ),
        )

        logger.info(f"Restaurant user is been created: ({rest_user_id})")
        rest_user = await self.repository.get(core_id)
        # notify new user
        try:
            # new user welcome email
            await send_new_resto_user_welcome_msg(
                subject="Bienvenido a Alima",
                to_email={"name": f"{first_name} {last_name}", "email": email},
            )
        except Exception as e:
            logger.warning("Error sending email to new user")
            logger.error(e)
        return rest_user

    async def edit_restaurant_user(
        self,
        restaurant_user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
    ) -> RestaurantUserGQL:
        """Updates first the core user and then the restaurant user

        Args:
            core_id (UUID): unique core user id
            first_name (Optional[str], optional): user first name. Defaults to None.
            last_name (Optional[str], optional): user last name. Defaults to None.
            phone_number (Optional[str], optional): user contact number. Defaults to None.
            role (Optional[str], optional): user role in the restaurant. Defaults to None.

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        await self.repository.exists(restaurant_user_id)
        # update core user
        restaurant_user = await self.repository.get_by_id(restaurant_user_id)
        if first_name or last_name or phone_number:
            if not await self.core_user_repository.update(
                restaurant_user.get("id"),  # type: ignore
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
            ):
                raise GQLApiException(
                    msg="Error updating core user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # update restaurant user
        if role:
            if not await self.repository.update(restaurant_user["core_user_id"], role):
                raise GQLApiException(
                    msg="Error updating restaurant user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        try:
            _res_user = await self.repository.get(restaurant_user["core_user_id"])
            return _res_user
        except Exception as e:
            logger.error(e)
        raise GQLApiException(
            msg="Error updating restaurant user",
            error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
        )

    async def change_restaurant_user_status(
        self, restaurant_user_id: UUID, enabled: bool
    ) -> bool:
        """Changes the status of a restaurant user

        Args:
            info (StrawberryInfo): Info to connect to DB
            core_id (UUID): unique core user id
            enabled (bool): user status

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        # validate fk
        await self.repository.exists(restaurant_user_id)
        # update core user
        restaurant_user = await self.repository.get_by_id(restaurant_user_id)
        # update status
        if isinstance(
            await self.repository.activate_desactivate(
                restaurant_user["core_user_id"], enabled
            ),
            bool,
        ):
            return enabled
        else:
            raise GQLApiException(
                msg="Error updating restaurant user",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )

    async def erase_restaurant_user(
        self, restaurant_user_id: UUID, deleted: bool
    ) -> bool:
        """Erases a restaurant user

        Args:
            info (StrawberryInfo): Info to connect to DB
            core_id (UUID): unique core user id
            deleted (bool): user status

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        # update core user
        restaurant_user = await self.repository.get_by_id(restaurant_user_id)
        # update deleted status
        _del_resp = await self.repository.delete(
            restaurant_user["core_user_id"], deleted
        )
        return _del_resp

    async def fetch_restaurant_user(
        self, restaurant_user_id: UUID
    ) -> RestaurantUserGQL:
        """Fetches a restaurant user

        Parameters
        ----------
        core_user_id : UUID
            unique core user id

        Returns
        -------
        RestaurantUserGQL
        """
        # validate fk
        await self.repository.exists(restaurant_user_id)
        try:
            restaurant_user = await self.repository.get_by_id(restaurant_user_id)
            _res_user = await self.repository.get(restaurant_user["core_user_id"])
            return _res_user
        except Exception as e:
            logger.error(e)
            raise GQLApiException(
                msg="Error fetching restaurant user",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )

    async def fetch_restaurant_user_by_firebase_id(
        self, firebase_id: str
    ) -> RestaurantUserGQL | NoneType:
        """Fetch restaurant User from firebase id

        Parameters
        ----------
        firebase_id : str
            Firebase ID (uid)

        Returns
        -------
        RestaurantUserGQL

        Raises
        ------
        GQLApiException
        """
        try:
            core_user = await self.core_user_repository.get_by_firebase_id(firebase_id)
            if not core_user.id:
                return None
        except Exception as e:
            logger.error(e)
            raise GQLApiException(
                msg="Error fetching core user",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        _res_user = await self.repository.fetch(core_user.id)
        if not _res_user:
            return None
        return _res_user


class RestaurantUserPermissionHandler(RestaurantUserPermissionHandlerInterface):
    def __init__(
        self,
        restaurant_user_perm_repo: RestaurantUserPermissionRepositoryInterface,
        restaurant_employee_repo: EmployeeRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        restaurant_user_repo: Optional[RestaurantUserRepositoryInterface] = None,
    ):
        self.repository = restaurant_user_perm_repo
        self.rest_employee_repo = restaurant_employee_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if restaurant_user_repo:
            self.rest_user_repo = restaurant_user_repo

    def _format_restaurant_user_permission(
        self, rest_usr: Dict[str, Any], emp_hmap: Optional[Dict[str, Any]] = None
    ) -> RestaurantUserPermCont:
        """Generate RestaurantUserPermCont object from dict

        Parameters
        ----------
        rest_usr : Dict[str, Any]
        emp_hmap : Dict[str, Any]

        Returns
        -------
        RestaurantUserPermCont
        """
        rest_usr["contact_info_user"] = CoreUser(**json.loads(rest_usr["contact_json"]))
        rest_usr["permission"] = RestaurantUserPermission(
            **json.loads(rest_usr["permission_json"])
        )
        # use hash map to get employee
        if emp_hmap:
            rest_usr["employee"] = emp_hmap.get(rest_usr["id"])
        else:
            rest_usr["employee"] = None
        if rest_usr["permission"].created_at:
            rest_usr["permission"].created_at = from_iso_format(
                rest_usr["permission"].created_at  # type: ignore
            )
        if rest_usr["permission"].last_updated:
            rest_usr["permission"].last_updated = from_iso_format(
                rest_usr["permission"].last_updated  # type: ignore
            )
        if rest_usr["contact_info_user"].created_at:
            rest_usr["contact_info_user"].created_at = from_iso_format(
                rest_usr["contact_info_user"].created_at  # type: ignore
            )
        if rest_usr["contact_info_user"].last_updated:
            rest_usr["contact_info_user"].last_updated = from_iso_format(
                rest_usr["contact_info_user"].last_updated  # type: ignore
            )
        del rest_usr["permission_json"]
        del rest_usr["contact_json"]
        return RestaurantUserPermCont(**rest_usr)

    def _build_employee_hashmap(
        self, employees: List[Dict[str, Any]]
    ) -> Dict[str, RestaurantEmployeeInfo]:
        emp_hmap = {}
        for em in employees:
            if em["branch_permissions"] is not None:
                if (
                    isinstance(em["branch_permissions"], list)
                    and len(em["branch_permissions"]) == 0
                ):
                    em["branch_permissions"] = None
                else:
                    em["branch_permissions"] = [
                        RestaurantEmployeeInfoPermission(
                            branch_id=Binary.as_uuid(bp["branch_id"]),
                            permissions=[
                                PermissionDict(**_p) for _p in bp["permissions"]
                            ],
                        )
                        for bp in em["branch_permissions"]
                    ]
            emp_hmap[em["restaurant_user_id"]] = RestaurantEmployeeInfo(**em)
        return emp_hmap

    async def fetch_restaurant_users_contact_and_permission_from_business(
        self,
        restaurant_business_id: UUID,
    ) -> List[RestaurantUserPermCont]:
        """Get restaurant user contact with permission

        Args:
            restaurant_business_id (Optional[UUID], optional): unique restaurant business id. Defaults to None.

        Returns:
            List[RestaurantUserPermCont]
        """
        # fetch all restaurant users permission
        rest_usrs = await self.repository.get_restaurant_user_contact_and_permission(
            " rup.restaurant_business_id = :res_bus_id",
            {"res_bus_id": restaurant_business_id},
        )
        # fetch all employees from mongo employee directory
        employees = await self.rest_employee_repo.search(
            core_element_collection="restaurant_employee_directory",
            core_element_name="Restaurant Employee Directory",
            core_query={
                "restaurant_user_id": {
                    "$in": [Binary.from_uuid(ru["id"]) for ru in rest_usrs]
                }
            },
        )
        # create hash map with employees
        emp_hmap = self._build_employee_hashmap(employees)

        # format values
        restaurant_branch_dir = []
        for r in rest_usrs:
            rest_user_info = self._format_restaurant_user_permission(r.copy(), emp_hmap)
            restaurant_branch_dir.append(rest_user_info)
        return restaurant_branch_dir

    async def fetch_restaurant_user_contact_and_permission(
        self,
        firebase_id: str,
    ) -> RestaurantUserPermCont:
        """Get restaurant user contact with permission

        Parameters
        ----------
            firebase_id: str

        Returns
        -------
            List[RestaurantUserPermCont]
        """
        # fetch restaurant user
        core_usr = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_usr.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        rest_usr = await self.rest_user_repo.get(core_usr.id)
        if not rest_usr.id:
            raise GQLApiException(
                msg="Restaurant User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        # fetch restaurant user permission
        rest_usr_perm = (
            await self.repository.get_restaurant_user_contact_and_permission(
                " ru.id = :rest_user_id",
                {"rest_user_id": rest_usr.id},
            )
        )
        if not rest_usr_perm:
            raise GQLApiException(
                msg="Restaurant User Permission not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch all employees from mongo employee directory
        employee_res = await self.rest_employee_repo.search(
            core_element_collection="restaurant_employee_directory",
            core_element_name="Restaurant Employee Directory",
            core_query={"restaurant_user_id": {"$in": [Binary.from_uuid(rest_usr.id)]}},
        )
        # create hash map with employees - or set None
        emp_hmap = None
        if employee_res:
            employee = employee_res[0]
            emp_hmap = self._build_employee_hashmap([employee])

        # format values
        rest_user_info = self._format_restaurant_user_permission(
            rest_usr_perm[0].copy(), emp_hmap
        )
        return rest_user_info


class RestaurantEmployeeHandler(RestaurantEmployeeHandlerInterface):
    def __init__(
        self,
        restaurant_employee_repo: EmployeeRepositoryInterface,
        restaurant_user_repo: RestaurantUserRepositoryInterface,
        core_user_repo: CoreUserRepositoryInterface,
        rest_user_perm_repo: RestaurantUserPermissionRepositoryInterface,
        firebase_api_client: Optional[FirebaseAuthApi] = None,
        rest_branch_repo: Optional[RestaurantBranchRepositoryInterface] = None,
        rest_business_repo: Optional[RestaurantBusinessRepositoryInterface] = None,
    ):
        self.repository = restaurant_employee_repo
        self.rest_user_repo = restaurant_user_repo
        self.core_user_repo = core_user_repo
        self.rest_user_perm = rest_user_perm_repo
        if firebase_api_client:
            self.firebase = firebase_api_client
        if rest_branch_repo:
            self.rest_branch_repo = rest_branch_repo
        if rest_business_repo:
            self.rest_business_repo = rest_business_repo

    async def new_restaurant_employee(
        self,
        restaurant_business_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        position: str,
        display_perms: Dict[str, bool],
        department: Optional[str] = None,
        permission: Optional[List[RestaurantEmployeeInfoPermission]] = None,
    ) -> RestaurantUserEmployeeGQL:
        """Create restaurant employee

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            name (str): employee first name
            last_name (str): employee last name
            phone_number (str): employee contact number
            email (str): employee contact email
            department (Optional[str], optional): department to which the restaurant employee belongs. Defaults to None.
            position (Optional[str], optional): employee role in restaurant. Defaults to None.
            display_perms (Dict[str, bool]): permissions to manage restaurant sections
            permission (Optional[List[RestaurantEmployeeInfoPermission]], optional): permissions to branch level.
                Defaults to None.

        Returns:
            RestaurantUserEmployeeGQL: RestaurantUserEmployeeGQL model
        """
        # branch level permissions validation
        if permission:
            for p in permission:
                await self.rest_branch_repo.exists(p.branch_id)
        # validate  business existance
        rest_business = await self.rest_business_repo.get(restaurant_business_id)

        # generate random password : 10 random
        alphabet = string.ascii_letters + string.digits + string.punctuation
        pwd_length = 10
        pwd: str = ""
        for i in range(pwd_length):
            pwd += "".join(secrets.choice(alphabet))
        # create firebase user and update display name
        fb_dict = self.firebase.signup_with_email(email, pwd)
        if "localId" not in fb_dict:
            raise GQLApiException(
                msg="Error creating firebase user",
                error_code=GQLApiErrorCodeType.INSERT_FIREBASE_DB_ERROR.value,
            )
        self.firebase.update_profile(
            fb_dict["idToken"], **{"displayName": f"{name} {last_name}"}
        )
        # create core user
        core_id = await self.core_user_repo.new(
            CoreUser(
                first_name=name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                firebase_id=fb_dict["localId"],
            )
        )
        # create restaurant user
        rest_user_id = await self.rest_user_repo.new(core_id, position)

        logger.info(f"Restaurant user is been created: ({rest_user_id})")
        rest_user_employee = {}
        rest_user_employee["restaurant_user"] = await self.rest_user_repo.get(core_id)

        if await self.rest_user_perm.new(
            rest_user_id,
            restaurant_business_id,
            display_perms.get("display_orders_section", False),
            display_perms.get("display_suppliers_section", False),
            display_perms.get("display_products_section", False),
        ):
            # return object
            rest_user_employee["permission"] = await self.rest_user_perm.get(
                rest_user_id
            )

        # insert all branch permissions or just one record without branch
        await self.repository.new_restaurant_employee(
            core_element_collection="restaurant_employee_directory",
            employee=RestaurantEmployeeInfo(
                restaurant_user_id=rest_user_id,
                name=name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                department=department,
                position=position,
                branch_permissions=permission,
            ),
        )

        # return object
        rest_user_employee["employee"] = await self.repository.get(
            core_element_collection="restaurant_employee_directory",
            user_id_key="restaurant_user_id",
            user_id=rest_user_id,
        )
        if isinstance(rest_user_employee["employee"]["branch_permissions"], Dict):
            rest_user_employee["employee"]["branch_permissions"] = (
                RestaurantEmployeeInfoPermission(
                    **rest_user_employee["employee"]["branch_permissions"]
                )
            )
        rest_user_employee["employee"] = RestaurantEmployeeInfo(
            **rest_user_employee["employee"]
        )
        # send notification email to new employee
        try:
            # new employee welcome email
            await send_employee_welcome_msg(
                subject=f"Bienvenido a Alima - {rest_business.get('name', '')}",
                to_email={"name": f"{name} {last_name}", "email": email},
                business_name=rest_business.get("name", ""),
                tmp_pswd=pwd,
            )
        except Exception as e:
            logger.warning("Error sending email to new employee")
            logger.error(e)

        return RestaurantUserEmployeeGQL(**rest_user_employee)

    async def edit_restaurant_employee(
        self,
        restaurant_business_id: UUID,
        restaurant_user_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        display_perms: Optional[Dict[str, bool]] = None,
        permission: Optional[List[RestaurantEmployeeInfoPermission]] = None,
    ) -> RestaurantUserEmployeeGQL:  # type: ignore
        """Edit_restaurant_employee

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
            display_perms (Optional[Dict[str, bool]]): permissions to manage restaurant sections
            permissions (EmployeeInfoPermissionInput): permissions to branch level
            core_user_id (UUID): Unique core user id

        Returns:
            RestaurantUserEmployeeGQL
        """
        # validate fk
        await self.rest_business_repo.exist(restaurant_business_id)
        # await self.rest_branch_repo.exists(branch_id)
        await self.rest_user_repo.exist(restaurant_user_id)
        restaurant_user = await self.rest_user_repo.get_by_id(restaurant_user_id)
        if (
            not restaurant_user
            or not isinstance(restaurant_user, dict)
            or not restaurant_user.get("id")
        ):
            raise GQLApiException(
                msg="Restaurant user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create
        rest_user_employee = {}
        rest_user_employee["restaurant_user"] = RestaurantUserGQL(**restaurant_user)
        if display_perms:
            upd_tmp: Dict[str, Any] = {
                "restaurant_user_id": rest_user_employee["restaurant_user"].id,
                "restaurant_business_id": restaurant_business_id,
            }
            if "display_orders_section" in display_perms:
                upd_tmp["display_orders_section"] = display_perms[
                    "display_orders_section"
                ]
            if "display_suppliers_section" in display_perms:
                upd_tmp["display_suppliers_section"] = display_perms[
                    "display_suppliers_section"
                ]
            if "display_products_section" in display_perms:
                upd_tmp["display_products_section"] = display_perms[
                    "display_products_section"
                ]
            if not await self.rest_user_perm.edit(
                **upd_tmp,
            ):
                raise GQLApiException(
                    msg="Error updating restaurant user permission",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )

        if name or last_name or department or position or phone_number or permission:
            if not await self.repository.upsert(
                core_element_collection="restaurant_employee_directory",
                user_id_key="restaurant_user_id",
                user_id=rest_user_employee["restaurant_user"].id,
                employee=RestaurantEmployeeInfo(
                    restaurant_user_id=rest_user_employee["restaurant_user"].id,
                    name=name,
                    last_name=last_name,
                    department=department,
                    position=position,
                    phone_number=phone_number,
                    branch_permissions=permission,
                ),
            ):
                raise GQLApiException(
                    msg="Error updating employee",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        if position:
            if not await self.rest_user_repo.update(
                rest_user_employee["restaurant_user"].id, position
            ):
                raise GQLApiException(
                    msg="Error updating restaurant user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )

        if name or last_name or phone_number:
            if not await self.core_user_repo.update(
                restaurant_user["core_user_id"],
                first_name=name,
                last_name=last_name,
                phone_number=phone_number,
            ):
                raise GQLApiException(
                    msg="Error updating core user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
            # [TODO] - update firebase user profile

        # return object
        rest_user_employee["employee"] = await self.repository.get(
            core_element_collection="restaurant_employee_directory",
            user_id_key="restaurant_user_id",
            user_id=rest_user_employee["restaurant_user"].id,
        )
        if isinstance(rest_user_employee["employee"]["branch_permissions"], Dict):
            rest_user_employee["employee"]["branch_permissions"] = (
                RestaurantEmployeeInfoPermission(
                    **rest_user_employee["employee"]["branch_permissions"]
                )
            )
        rest_user_employee["employee"] = RestaurantEmployeeInfo(
            **rest_user_employee["employee"]
        )

        rest_user_employee["permission"] = await self.rest_user_perm.get(
            rest_user_employee["restaurant_user"].id
        )

        return RestaurantUserEmployeeGQL(**rest_user_employee)
