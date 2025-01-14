import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from bson import Binary

from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.clients.clients.firebaseapi.firebase_auth import FirebaseAuthApi
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierEmployeeHandlerInterface,
    SupplierUserEmployeeGQL,
    SupplierUserGQL,
    SupplierUserHandlerInterface,
    SupplierUserPermissionHandlerInterface,
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.user.employee import EmployeeRepositoryInterface
from gqlapi.domain.models.v2.core import (
    CoreUser,
    PermissionDict,
    SupplierEmployeeInfo,
    SupplierEmployeeInfoPermission,
)
from gqlapi.domain.models.v2.supplier import SupplierUser, SupplierUserPermission
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.domain_mapper import sql_to_domain
from gqlapi.utils.helpers import generate_random_password
from gqlapi.utils.notifications import send_employee_welcome_msg

logger = get_logger(get_app())


class SupplierUserHandler(SupplierUserHandlerInterface):
    def __init__(
        self,
        core_user_repo: CoreUserRepositoryInterface,
        supplier_user_repo: SupplierUserRepositoryInterface,
        employee_repo: Optional[EmployeeRepositoryInterface] = None,
    ):
        self.repository = supplier_user_repo
        self.core_user_repository = core_user_repo
        if employee_repo:
            self.employee_repo = employee_repo

    async def new_supplier_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> SupplierUserGQL:
        """Creates a new core user and then a supplier user

        Args:
            first_name (str): user first name
            last_name (str): user last name
            email (str): user contact email
            phone_number (str): user contact number
            firebase_id (str): unique supplier user firebase id_
            role (str): user role in the supplier

        Returns:
            SupplierUserGQL: supplier user + core user model
        """
        # create core user
        core_id = await self.core_user_repository.add(
            CoreUser(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                firebase_id=firebase_id,
            )
        )
        if not core_id:
            raise GQLApiException(
                msg="Error creating core user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create supplier user
        sup_user_id = await self.repository.add(core_id, role)
        if not sup_user_id:
            raise GQLApiException(
                msg="Error creating supplier user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

        # new supplier employee in mongo
        await self.employee_repo.new_supplier_employee(
            core_element_collection="supplier_employee_directory",
            employee=SupplierEmployeeInfo(
                supplier_user_id=sup_user_id,
                name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                department="Admin",
                position="Admin",
                unit_permissions=[],
            ),
        )

        logger.info(f"Supplier user is been created: ({sup_user_id})")
        sup_user = await self.repository.fetch(core_id)
        # format model
        if isinstance(sup_user, dict):
            return SupplierUserGQL(**sup_user)
        return SupplierUserGQL(**sql_to_domain(sup_user, SupplierUserGQL))  # type: ignore

    async def fetch_supplier_user_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierUserGQL:
        """Fetch supplier User from firebase id

        Parameters
        ----------
        firebase_id : str
            Firebase ID (uid)

        Returns
        -------
        SupplierUserGQL

        Raises
        ------
        GQLApiException
        """
        try:
            core_user = await self.core_user_repository.fetch_by_firebase_id(
                firebase_id
            )
            if not core_user or not core_user.id:
                raise GQLApiException(
                    msg="User not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            sup_user = await self.repository.fetch(core_user.id)
            # format model
            if isinstance(sup_user, dict):
                return SupplierUserGQL(**sup_user)
            return SupplierUserGQL(**sql_to_domain(sup_user, SupplierUserGQL))  # type: ignore
        except GQLApiException as ge:
            raise ge
        except Exception as e:
            logger.error(e)
            raise GQLApiException(
                msg="Error fetching supplier user",
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    async def edit_supplier_user(
        self,
        supplier_user_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
    ) -> SupplierUserGQL:
        """Updates first the core user and then the supplier user

        Args:
            core_id (UUID): unique core user id
            first_name (Optional[str], optional): user first name. Defaults to None.
            last_name (Optional[str], optional): user last name. Defaults to None.
            phone_number (Optional[str], optional): user contact number. Defaults to None.
            role (Optional[str], optional): user role in the supplier. Defaults to None.

        Returns:
            SupplierUserGQL: supplier user + core user model
        """
        # verify if exists
        supplier_user_dict = await self.repository.get_by_id(supplier_user_id)
        if not supplier_user_dict:
            raise GQLApiException(
                msg="Supplier user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_user = SupplierUser(**dict(supplier_user_dict))
        # update core user
        if first_name or last_name or phone_number:
            if not await self.core_user_repository.edit(
                supplier_user.id,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
            ):
                raise GQLApiException(
                    msg="Error updating core user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # update supplier user
        if role:
            if not await self.repository.edit(supplier_user.core_user_id, role):
                raise GQLApiException(
                    msg="Error updating supplier user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # fetch response
        _sup_user = await self.repository.fetch(supplier_user.core_user_id)
        return SupplierUserGQL(
            **sql_to_domain(_sup_user, SupplierUserGQL)  # type: ignore
        )

    async def erase_supplier_user(self, supplier_user_id: UUID, deleted: bool) -> bool:
        """Erases a supplier user

        Args:
            info (StrawberryInfo): Info to connect to DB
            core_id (UUID): unique core user id
            deleted (bool): user status

        Returns:
            SupplierUserGQL: supplier user + core user model
        """
        # update core user
        supplier_user = await self.repository.get_by_id(supplier_user_id)
        if (
            not supplier_user
            or not isinstance(supplier_user, dict)
            or not supplier_user["id"]
        ):
            raise GQLApiException(
                msg="Supplier user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # update deleted status
        _del_resp = await self.repository.delete(supplier_user["core_user_id"], deleted)
        return _del_resp

    # async def change_supplier_user_status(
    #     self, supplier_user_id: UUID, enabled: bool
    # ) -> bool:
    #     """Changes the status of a supplier user

    #     Args:
    #         info (StrawberryInfo): Info to connect to DB
    #         core_id (UUID): unique core user id
    #         enabled (bool): user status

    #     Returns:
    #         SupplierUserGQL: supplier user + core user model
    #     """
    #     # validate fk
    #     await self.repository.exists(supplier_user_id)
    #     # update core user
    #     supplier_user = await self.repository.get_by_id(supplier_user_id)
    #     # update status
    #     if isinstance(
    #         await self.repository.activate_desactivate(
    #             supplier_user["core_user_id"], enabled
    #         ),
    #         bool,
    #     ):
    #         return enabled
    #     else:
    #         raise GQLApiException(
    #             msg="Error updating supplier user",
    #             error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
    #         )

    # async def fetch_supplier_user(
    #     self, supplier_user_id: UUID
    # ) -> SupplierUserGQL:
    #     """Fetches a supplier user

    #     Parameters
    #     ----------
    #     core_user_id : UUID
    #         unique core user id

    #     Returns
    #     -------
    #     SupplierUserGQL
    #     """
    #     # validate fk
    #     await self.repository.exists(supplier_user_id)
    #     try:
    #         supplier_user = await self.repository.get_by_id(supplier_user_id)
    #         _sup_user = await self.repository.get(supplier_user["core_user_id"])
    #         return _sup_user
    #     except Exception as e:
    #         logger.error(e)
    #         raise GQLApiException(
    #             msg="Error fetching supplier user",
    #             error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
    #         )


class SupplierUserPermissionHandler(SupplierUserPermissionHandlerInterface):
    def __init__(
        self,
        supplier_user_perm_repo: SupplierUserPermissionRepositoryInterface,
        supplier_employee_repo: Optional[EmployeeRepositoryInterface] = None,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        supplier_user_repo: Optional[SupplierUserRepositoryInterface] = None,
    ):
        self.repository = supplier_user_perm_repo
        if supplier_employee_repo:
            self.sup_employee_repo = supplier_employee_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if supplier_user_repo:
            self.sup_user_repo = supplier_user_repo

    async def fetch_supplier_user_permission(
        self, firebase_id: str
    ) -> SupplierUserPermission:
        # get core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_user = await self.sup_user_repo.fetch(core_user_id=core_user.id)
        if (
            not supplier_user
            or not isinstance(supplier_user, dict)
            or not supplier_user["id"]
        ):
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supp_user_perm = await self.repository.fetch(
            supplier_user_id=supplier_user["id"]
        )
        return SupplierUserPermission(**supp_user_perm)

    async def fetch_supplier_user_contact_and_permission(
        self, firebase_id: str
    ) -> SupplierUserEmployeeGQL:
        """Fetch supplier user contact with permission

        Parameters
        ----------
        firebase_id : str

        Returns
        -------
        SupplierUserEmployeeGQL

        Raises
        ------
        GQLApiException
        """
        # get core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_user = await self.sup_user_repo.fetch(core_user_id=core_user.id)
        if (
            not supplier_user
            or not isinstance(supplier_user, dict)
            or not supplier_user["id"]
        ):
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supp_user_perm = (
            await self.repository.fetch_supplier_user_contact_and_permission(
                " su.id = :sup_user_id",
                {"sup_user_id": supplier_user["id"]},
            )
        )
        if not supp_user_perm:
            raise GQLApiException(
                msg="Supplier User Permission not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch all employees from mongo employee directory
        employee_sup = await self.sup_employee_repo.find(
            core_element_collection="supplier_employee_directory",
            core_element_name="Supplier Employee Directory",
            core_query={
                "supplier_user_id": {"$in": [Binary.from_uuid(supplier_user["id"])]}
            },
        )
        # create hash map with employees - or set None
        emp_hmap = None
        if employee_sup:
            emp_hmap = self._build_employee_hashmap(employee_sup[:1])

        # format values
        sup_user_info = self._format_supplier_user_permission(
            supplier_user, supp_user_perm[0].copy(), emp_hmap
        )
        return sup_user_info

    def _format_supplier_user_permission(
        self,
        sup_usr: Dict[str, Any],
        sup_user_perm: Dict[str, Any],
        emp_hmap: Optional[Dict[str, Any]] = None,
    ) -> SupplierUserEmployeeGQL:
        """Generate SupplierUserEmployeeGQL object from dict

        Parameters
        ----------
        sup_usr : Dict[str, Any]
        emp_hmap : Dict[str, Any]

        Returns
        -------
        SupplierUserPermCont
        """
        # build supplier user
        sup_usr["user"] = CoreUser(**json.loads(sup_user_perm["contact_json"]))
        # build permission
        perm = SupplierUserPermission(**json.loads(sup_user_perm["permission_json"]))
        # use hash map to get employee
        employee = None
        if emp_hmap:
            employee = emp_hmap.get(sup_usr["id"])
        if perm.created_at:
            perm.created_at = from_iso_format(perm.created_at)  # type: ignore
        if perm.last_updated:
            perm.last_updated = from_iso_format(perm.last_updated)  # type: ignore
        if sup_usr["user"].created_at:
            sup_usr["user"].created_at = from_iso_format(
                sup_usr["user"].created_at  # type: ignore
            )
        if sup_usr["user"].last_updated:
            sup_usr["user"].last_updated = from_iso_format(
                sup_usr["user"].last_updated  # type: ignore
            )
        return SupplierUserEmployeeGQL(
            supplier_user=SupplierUserGQL(**sup_usr),
            permission=perm,
            employee=employee,
        )

    def _build_employee_hashmap(
        self, employees: List[Dict[str, Any]]
    ) -> Dict[str, SupplierEmployeeInfo]:
        emp_hmap = {}
        for emp in employees:
            em = emp.copy()
            em["supplier_user_id"] = (
                em["supplier_user_id"]
                if isinstance(em["supplier_user_id"], UUID)
                else Binary.as_uuid(em["supplier_user_id"])
            )
            sup_user_id = em["supplier_user_id"]
            if em["unit_permissions"] is not None:
                if (
                    isinstance(em["unit_permissions"], list)
                    and len(em["unit_permissions"]) == 0
                ):
                    em["unit_permissions"] = None
                else:
                    em["unit_permissions"] = [
                        SupplierEmployeeInfoPermission(
                            unit_id=Binary.as_uuid(sp["unit_id"]),
                            permissions=[
                                PermissionDict(**_p) for _p in sp["permissions"]
                            ],
                        )
                        for sp in em["unit_permissions"]
                    ]
            emp_hmap[sup_user_id] = SupplierEmployeeInfo(**em)
        return emp_hmap

    async def fetch_supplier_users_contact_and_permission_from_business(
        self,
        supplier_business_id: UUID,
    ) -> List[SupplierUserEmployeeGQL]:
        """Get supplier user contact with permission

        Args:
            supplier_business_id (Optional[UUID], optional): unique supplier business id. Defaults to None.

        Returns:
            List[SupplierUserEmployeeGQL]
        """
        # fetch all supplier users permission
        sup_usrs = await self.repository.fetch_supplier_user_contact_and_permission(
            " sup.supplier_business_id = :sup_bus_id",
            {"sup_bus_id": supplier_business_id},
        )
        # fetch all employees from mongo employee directory
        employees = await self.sup_employee_repo.find(
            core_element_collection="supplier_employee_directory",
            core_element_name="Supplier Employee Directory",
            core_query={
                "supplier_user_id": {
                    "$in": [Binary.from_uuid(ru["id"]) for ru in sup_usrs]
                }
            },
        )
        # create hash map with employees
        emp_hmap = self._build_employee_hashmap(employees)

        # format values
        supplier_unit_list = []
        for r in sup_usrs:
            s_usr = {
                k: v
                for k, v in r.items()
                if k not in ["contact_json", "permission_json"]
            }
            sup_user_info = self._format_supplier_user_permission(
                s_usr, r.copy(), emp_hmap
            )
            supplier_unit_list.append(sup_user_info)
        return supplier_unit_list


class SupplierEmployeeHandler(SupplierEmployeeHandlerInterface):
    def __init__(
        self,
        supplier_employee_repo: EmployeeRepositoryInterface,
        supplier_user_repo: SupplierUserRepositoryInterface,
        core_user_repo: CoreUserRepositoryInterface,
        sup_user_perm_repo: SupplierUserPermissionRepositoryInterface,
        firebase_api_client: Optional[FirebaseAuthApi] = None,
        sup_unit_repo: Optional[SupplierUnitRepositoryInterface] = None,
        sup_business_repo: Optional[SupplierBusinessRepositoryInterface] = None,
    ):
        self.repository = supplier_employee_repo
        self.sup_user_repo = supplier_user_repo
        self.core_user_repo = core_user_repo
        self.sup_user_perm = sup_user_perm_repo
        if firebase_api_client:
            self.firebase = firebase_api_client
        if sup_unit_repo:
            self.sup_unit_repo = sup_unit_repo
        if sup_business_repo:
            self.sup_business_repo = sup_business_repo

    async def new_supplier_employee(
        self,
        supplier_business_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        position: str,
        display_perms: Dict[str, bool],
        department: Optional[str] = None,
        permission: Optional[List[SupplierEmployeeInfoPermission]] = None,
    ) -> SupplierUserEmployeeGQL:
        """Create supplier employee

        Args:
            supplier_business_id (UUID): unique supplier business id
            name (str): employee first name
            last_name (str): employee last name
            phone_number (str): employee contact number
            email (str): employee contact email
            department (Optional[str], optional): department to which the supplier employee belongs. Defaults to None.
            position (Optional[str], optional): employee role in supplier. Defaults to None.
            display_perms (Dict[str, bool]): permissions to manage supplier sections
            permission (Optional[List[SupplierEmployeeInfoPermission]], optional): permissions to branch level.
                Defaults to None.

        Returns:
            SupplierUserEmployeeGQL: SupplierUserEmployeeGQL model
        """
        # unit level permissions validation
        if permission:
            for p in permission:
                if not await self.sup_unit_repo.exists(p.unit_id):
                    raise GQLApiException(
                        msg="Unit not found",
                        error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                    )
        # validate  business existance
        sup_business = await self.sup_business_repo.fetch(supplier_business_id)
        if not sup_business or not sup_business.get("id"):
            raise GQLApiException(
                msg="Supplier business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # generate random password : 10 random
        pwd = generate_random_password(pwd_length=10)
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
        core_user = CoreUser(
            first_name=name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            firebase_id=fb_dict["localId"],
        )
        core_id = await self.core_user_repo.add(core_user)
        if not core_id:
            raise GQLApiException(
                msg="Error creating core user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        core_user.id = core_id
        # create supplier user
        sup_user_id = await self.sup_user_repo.add(core_id, position)
        if not sup_user_id:
            raise GQLApiException(
                msg="Error creating supplier user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        logger.info(f"Supplier user is been created: ({sup_user_id})")
        sup_user_employee = {}
        sup_user_employee["supplier_user"] = SupplierUserGQL(
            **await self.sup_user_repo.fetch(core_id)  # type: ignore
        )

        if not await self.sup_user_perm.add(
            sup_user_id,
            supplier_business_id,
            display_perms.get("display_sales_section", False),
            display_perms.get("display_routes_section", False),
        ):
            raise GQLApiException(
                msg="Error creating supplier user permission",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        sup_user_employee["permission"] = SupplierUserPermission(
            **await self.sup_user_perm.fetch(sup_user_id)
        )

        # insert all branch permissions or just one record without branch
        sup_employee = SupplierEmployeeInfo(
            supplier_user_id=sup_user_id,
            name=name,
            last_name=last_name,
            phone_number=phone_number,
            email=email,
            department=department,
            position=position,
            unit_permissions=permission,
        )
        await self.repository.new_supplier_employee(
            core_element_collection="supplier_employee_directory",
            employee=sup_employee,
        )
        sup_user_employee["employee"] = sup_employee
        # send notification email to new employee
        try:
            # new employee welcome email
            await send_employee_welcome_msg(
                subject=f"Bienvenido a Alima - {sup_business.get('name', '')}",
                to_email={"name": f"{name} {last_name}", "email": email},
                business_name=sup_business.get("name", ""),
                tmp_pswd=pwd,
                template="welcome_supplier_employee.html",
            )
        except Exception as e:
            logger.warning("Error sending email to new employee")
            logger.error(e)
        # return object
        return SupplierUserEmployeeGQL(**sup_user_employee)

    async def edit_supplier_employee(
        self,
        supplier_business_id: UUID,
        supplier_user_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        display_perms: Optional[Dict[str, bool]] = None,
        permission: Optional[List[SupplierEmployeeInfoPermission]] = None,
    ) -> SupplierUserEmployeeGQL:  # type: ignore
        """Edit_supplier_employee

        Args:
            info (StrawberryInfo): info to connect to DB
            supplier_business_id (UUID): unique supplier business id
            id (UUID): unique employee id
            name (Optional[str]): employee first name
            last_name (Optional[str]): employee last name
            department (Optional[str]): _department to which the supplier employee belongs
            position (Optional[str]): employee role in supplier.
            phone_number (Optional[str]): employee contact number
            email (Optional[str]): employee contact email
            display_perms (Optional[Dict[str, bool]]): permissions to manage supplier sections
            permissions (EmployeeInfoPermissionInput): permissions to branch level
            core_user_id (UUID): Unique core user id

        Returns:
            SupplierUserEmployeeGQL
        """
        # validate fk
        if not await self.sup_business_repo.exists(supplier_business_id):
            raise GQLApiException(
                msg="Supplier business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if position:
            if not await self.sup_user_repo.edit(supplier_user_id, position):
                raise GQLApiException(
                    msg="Error updating supplier user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        supplier_user = await self.sup_user_repo.get_by_id(
            supplier_user_id=supplier_user_id
        )
        if (
            not supplier_user
            or not isinstance(supplier_user, dict)
            or not supplier_user.get("id")
        ):
            raise GQLApiException(
                msg="Supplier user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create
        sup_user_employee = {}
        sup_user_employee["supplier_user"] = SupplierUserGQL(**supplier_user)
        if display_perms:
            upd_tmp: Dict[str, Any] = {
                "supplier_user_id": sup_user_employee["supplier_user"].id,
                "supplier_business_id": supplier_business_id,
            }
            if "display_sales_section" in display_perms:
                upd_tmp["display_sales_section"] = display_perms[
                    "display_sales_section"
                ]
            if "display_routes_section" in display_perms:
                upd_tmp["display_routes_section"] = display_perms[
                    "display_routes_section"
                ]
            if not await self.sup_user_perm.edit(
                **upd_tmp,
            ):
                raise GQLApiException(
                    msg="Error updating supplier user permission",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # get permission
        sup_user_employee["permission"] = SupplierUserPermission(
            **await self.sup_user_perm.fetch(sup_user_employee["supplier_user"].id)
        )

        if name or last_name or department or position or phone_number or permission:
            if not await self.repository.upsert(
                core_element_collection="supplier_employee_directory",
                user_id_key="supplier_user_id",
                user_id=supplier_user["id"],
                employee=SupplierEmployeeInfo(
                    supplier_user_id=supplier_user["id"],
                    name=name,
                    last_name=last_name,
                    department=department,
                    position=position,
                    phone_number=phone_number,
                    unit_permissions=permission,
                ),
            ):
                raise GQLApiException(
                    msg="Error updating employee",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )

        if name or last_name or phone_number:
            if not await self.core_user_repo.edit(
                supplier_user["core_user_id"],
                first_name=name,
                last_name=last_name,
                phone_number=phone_number,
            ):
                raise GQLApiException(
                    msg="Error updating core user",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
            # [TODO] - update firebase user profile
        core_user = await self.core_user_repo.fetch(supplier_user["core_user_id"])
        sup_user_employee["supplier_user"].user = core_user

        # return object
        sup_user_employee["employee"] = await self.repository.fetch(
            core_element_collection="supplier_employee_directory",
            user_id_key="supplier_user_id",
            user_id=sup_user_employee["supplier_user"].id,
        )
        if isinstance(sup_user_employee["employee"]["unit_permissions"], Dict):
            sup_user_employee["employee"]["unit_permissions"] = (
                SupplierEmployeeInfoPermission(
                    **sup_user_employee["employee"]["unit_permissions"]
                )
            )
        sup_user_employee["employee"] = SupplierEmployeeInfo(
            **sup_user_employee["employee"]
        )

        return SupplierUserEmployeeGQL(**sup_user_employee)
