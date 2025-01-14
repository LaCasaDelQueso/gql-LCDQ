from typing import Any, Dict, List, Optional
from uuid import UUID
from bson import Binary

from gqlapi.domain.interfaces.v2.catalog.category import (
    CategoryRepositoryInterface,
    SupplierUnitCategoryRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import MxSatCertificateRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import (
    SupplierUnitDeliveryRepositoryInterface,
    SupplierUnitGQL,
    SupplierUnitHandlerInterface,
    SupplierUnitRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.user.employee import EmployeeRepositoryInterface
from gqlapi.domain.models.v2.core import (
    MxSatInvoicingCertificateInfo,
    PermissionDict,
    SupplierEmployeeInfo,
    SupplierEmployeeInfoPermission,
)
from gqlapi.domain.models.v2.supplier import (
    DeliveryOptions,
    SupplierUnitCategory,
    SupplierUnitDeliveryOptions,
)
from gqlapi.domain.models.v2.utils import PayMethodType, SellingOption, ServiceDay
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.repository.user.employee import default_unit_perms
from gqlapi.utils.domain_mapper import domain_to_dict


class SupplierUnitHandler(SupplierUnitHandlerInterface):
    def __init__(
        self,
        supplier_unit_repo: SupplierUnitRepositoryInterface,
        unit_category_repo: SupplierUnitCategoryRepositoryInterface,
        supplier_unit_delivery_repo: Optional[
            SupplierUnitDeliveryRepositoryInterface
        ] = None,
        category_repo: Optional[CategoryRepositoryInterface] = None,
        supplier_user_repo: Optional[SupplierUserRepositoryInterface] = None,
        supplier_user_permission_repo: Optional[
            SupplierUserPermissionRepositoryInterface
        ] = None,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        supplier_business_repo: Optional[SupplierBusinessRepositoryInterface] = None,
        employee_repo: Optional[EmployeeRepositoryInterface] = None,
        tax_info_repo: Optional[MxSatCertificateRepositoryInterface] = None,
    ):
        self.repository = supplier_unit_repo
        self.unit_category_repository = unit_category_repo
        if supplier_unit_delivery_repo:
            self.supplier_unit_delivery_repo = supplier_unit_delivery_repo
        if category_repo:
            self.category_repo = category_repo
        if supplier_user_repo:
            self.supplier_user_repo = supplier_user_repo
        if supplier_user_permission_repo:
            self.supplier_user_permission_repo = supplier_user_permission_repo
        if supplier_business_repo:
            self.supplier_business_repo = supplier_business_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if employee_repo:
            self.employee_repo = employee_repo
        if tax_info_repo:
            self.tax_info_repo = tax_info_repo

    async def _build_supplier_unit_gql(
        self,
        supplier_unit_id: UUID | Dict[Any, Any],
        unit_categ: SupplierUnitCategory | None = None,
        delivery_options: SupplierUnitDeliveryOptions | DeliveryOptions | None = None,
        tax_info: MxSatInvoicingCertificateInfo | None = None,
    ) -> SupplierUnitGQL:
        # supplier unit
        if isinstance(supplier_unit_id, UUID):
            supplier_unit = await self.repository.fetch(supplier_unit_id)
        else:
            supplier_unit = supplier_unit_id
        # supplier unit category
        if not unit_categ:
            _unit_c = await self.unit_category_repository.fetch(supplier_unit["id"])
            if _unit_c:
                supplier_unit["unit_category"] = SupplierUnitCategory(**_unit_c)
            else:
                supplier_unit["unit_category"] = None
        else:
            supplier_unit["unit_category"] = unit_categ
        # delivery options
        if not delivery_options:
            _su_deliv = await self.supplier_unit_delivery_repo.fetch(
                supplier_unit["id"]
            )
            if _su_deliv:
                supplier_unit["delivery_info"] = SupplierUnitDeliveryOptions(
                    **_su_deliv
                )
            else:
                supplier_unit["delivery_info"] = None
        else:
            if isinstance(delivery_options, SupplierUnitDeliveryOptions):
                supplier_unit["delivery_info"] = delivery_options
            else:
                supplier_unit["delivery_info"] = SupplierUnitDeliveryOptions(
                    supplier_unit_id=supplier_unit["id"],
                    **domain_to_dict(delivery_options)
                )
        # tax info
        if not tax_info:
            inv_info = await self.tax_info_repo.fetch_certificate(supplier_unit["id"])
            if inv_info:
                supplier_unit["tax_info"] = MxSatInvoicingCertificateInfo(**inv_info)
            else:
                supplier_unit["tax_info"] = None
        else:
            supplier_unit["tax_info"] = tax_info
        # with the new supplier unit id and the user id
        return SupplierUnitGQL(**supplier_unit)

    async def new_supplier_unit(
        self,
        supplier_business_id: UUID,
        unit_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        firebase_id: str,
        category_id: UUID,
        delivery_options: DeliveryOptions,
        allowed_payment_methods: List[PayMethodType],
        account_number: str
    ) -> SupplierUnitGQL:
        """Create supplier unit

        Args:
            supplier_business_id (UUID): unique supplier business id
            unit_name (str): Name of supplier unit
            full_address (str): address of unit
            street (str): street of unit
            external_num (str): external num of unit
            internal_num (str): internal num of unit
            neighborhood (str): neighborhood of unit
            city (str): city of unit
            state (str): state of unit
            country (str): country of unit
            zip_code (str): zip_code of unit
            core_user_id (UUID): unique core user id
            category_id (UUID): _unique category id
            delivery_options (DeliveryOptions): delivery options

        Returns:
            SupplierUnitGQL
        """
        if not await self.category_repo.exists(category_id):
            raise GQLApiException(
                msg="Category not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if not await self.supplier_business_repo.exists(supplier_business_id):
            raise GQLApiException(
                msg="Supplier Business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create supplier unit
        s_unit_id = await self.repository.add(
            supplier_business_id,
            unit_name,
            full_address,
            street,
            external_num,
            internal_num,
            neighborhood,
            city,
            state,
            country,
            zip_code,
            allowed_payment_methods,
            account_number
        )
        # get core user id
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create supplier unit category
        u_categ = SupplierUnitCategory(
            supplier_unit_id=s_unit_id,
            supplier_category_id=category_id,
            created_by=core_user.id,
        )
        if not await self.unit_category_repository.add(u_categ):
            raise GQLApiException(
                msg="Error creating supplier unit category",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create a supplier user record in employee directory Mongo
        supplier_user = await self.supplier_user_repo.fetch(core_user.id)
        if not supplier_user or not supplier_user["id"]:  # type: ignore
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        employee = await self.employee_repo.fetch(
            core_element_collection="supplier_employee_directory",
            user_id_key="supplier_user_id",
            user_id=supplier_user["id"],  # type: ignore
        )
        tmp_perm = []
        for _e in employee["unit_permissions"]:
            tmp_perm.append(
                SupplierEmployeeInfoPermission(
                    unit_id=Binary.as_uuid(_e["unit_id"]),
                    permissions=[PermissionDict(**_p) for _p in _e["permissions"]],
                )
            )
        tmp_perm.append(
            SupplierEmployeeInfoPermission(
                unit_id=s_unit_id,
                permissions=default_unit_perms,
            )
        )
        if not await self.employee_repo.edit(
            core_element_collection="supplier_employee_directory",
            user_id_key="supplier_user_id",
            user_id=supplier_user["id"],  # type: ignore
            employee=SupplierEmployeeInfo(
                supplier_user_id=supplier_user["id"],  # type: ignore
                name=employee["name"],
                last_name=employee["last_name"],
                department=employee["department"],
                position=employee["position"],
                phone_number=employee["phone_number"],
                unit_permissions=tmp_perm,
            ),
        ):
            raise GQLApiException(
                msg="Error updating supplier employee directory",
                error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
            )
        # add supplier delivery info
        if not await self.supplier_unit_delivery_repo.add(s_unit_id, delivery_options):
            raise GQLApiException(
                msg="Error creating supplier unit delivery options",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        # build response
        return await self._build_supplier_unit_gql(s_unit_id, u_categ, delivery_options)

    async def fetch_supplier_units(
        self,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        unit_name: Optional[str] = None,
    ) -> List[SupplierUnitGQL]:
        """Get supplier units

        Args:
            supplier_business_id (Optional[UUID], optional): unique supplier business id. Defaults to None.


        Returns:
            List[RestaurantunitGQL]
        """
        # find supplier units
        if supplier_unit_id:
            _unit = await self.repository.fetch(supplier_unit_id)
            if not _unit:
                return []
            units = [_unit]
        else:
            units = await self.repository.find(
                supplier_business_id,
                unit_name,
            )
            if not units:
                return []
        # get category info
        categs = await self.unit_category_repository.find(
            [u["id"] for u in units],
        )
        categ_idx = {c["supplier_unit_id"]: c for c in categs}
        # get delivery info
        delivs = await self.supplier_unit_delivery_repo.find(
            [u["id"] for u in units],
        )
        deliv_idx = {d["supplier_unit_id"]: d for d in delivs}

        # format response
        gqlsu = []
        for un in units:
            gqun = un.copy()
            _categ = categ_idx.get(un["id"], {})
            gqun["unit_category"] = SupplierUnitCategory(**_categ)
            _deliv = deliv_idx.get(un["id"], {})
            if _deliv:
                gqun["delivery_info"] = SupplierUnitDeliveryOptions(
                    selling_option=[
                        SellingOption(so) for so in _deliv["selling_option"]
                    ],
                    regions=[str(rg).upper() for rg in _deliv["regions"]],
                    service_hours=[ServiceDay(**rg) for rg in _deliv["service_hours"]],
                    **{
                        k: v
                        for k, v in _deliv.items()
                        if k not in ["selling_option", "regions", "service_hours"]
                    }
                )
            gqlsu.append(
                await self._build_supplier_unit_gql(
                    supplier_unit_id=gqun,
                    unit_categ=gqun["unit_category"],
                    delivery_options=gqun.get("delivery_info", None),
                    tax_info=None,
                )
            )
        return gqlsu

    async def fetch_suppliers_asoc_with_user(
        self,
        firebase_id: str,
        supplier_unit_id: Optional[UUID] = None,
    ) -> List[SupplierUnitGQL]:
        """Fetch suppliers associated with user

        Parameters
        ----------
        firebase_id : str
            firebase id of user

        Returns
        -------
        List[SupplierUnitGQL]
        """
        # get core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get supplier user & supplier user perms
        sup_user = await self.supplier_user_repo.fetch(core_user.id)
        if not sup_user or not isinstance(sup_user, dict) or not sup_user["id"]:
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_per = await self.supplier_user_permission_repo.fetch(sup_user["id"])
        if not sup_per or not isinstance(sup_per, dict) or not sup_per["id"]:
            raise GQLApiException(
                msg="Supplier User Permission not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        units = await self.fetch_supplier_units(
            supplier_business_id=sup_per["supplier_business_id"],
            supplier_unit_id=supplier_unit_id,
        )
        return units

    async def count_supplier_units(
        self,
        supplier_business_id: UUID,
    ) -> int:
        """Count supplier units that are active

        Parameters
        ----------
        supplier_business_id : UUID

        Returns
        -------
        int
        """
        return await self.repository.count(supplier_business_id, deleted=False)

    async def edit_supplier_unit(
        self,
        supplier_unit_id: UUID,
        unit_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        category_id: Optional[UUID] = None,
        deleted: Optional[bool] = None,
        delivery_options: Optional[DeliveryOptions] = None,
        allowed_payment_methods: Optional[List[PayMethodType]] = None,
        account_number: Optional[str] = None,
    ) -> SupplierUnitGQL:
        """Update supplier unit

        Args:
            supplier_unit_id (UUID): unique supplier unit id
            unit_name (str): Name of supplier unit
            full_address (str): address of unit
            street (str): street of unit
            external_num (str): external num of unit
            internal_num (str): internal num of unit
            neighborhood (str): neighborhood of unit
            city (str): city of unit
            state (str): state of unit
            country (str): country of unit
            zip_code (str): zip_code of unit
            category_id (UUID): _unique category id
            deleted (bool): deleted flag
            delivery_options (DeliveryOptions): delivery options

        Raises:
            GQLApiException

        Returns:
            SupplierUnitGQL
        """
        # verify if supplier unit exists
        if category_id:
            if not await self.category_repo.exists(category_id):
                raise GQLApiException(
                    msg="Category not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
        if not await self.repository.exists(supplier_unit_id):
            raise GQLApiException(
                msg="Supplier Unit not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # update
        if not await self.repository.edit(
            supplier_unit_id,
            unit_name,
            full_address,
            street,
            external_num,
            internal_num,
            neighborhood,
            city,
            state,
            country,
            zip_code,
            deleted,
            allowed_payment_methods,
            account_number,
        ):
            raise GQLApiException(
                msg="Error updating supplier unit",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        # update category if needed
        if category_id:
            if not await self.unit_category_repository.edit(
                supplier_unit_id, category_id
            ):
                raise GQLApiException(
                    msg="Error updating unit category",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # update delivery options if needed
        if delivery_options:
            # add supplier delivery info
            if not await self.supplier_unit_delivery_repo.edit(
                supplier_unit_id, delivery_options
            ):
                raise GQLApiException(
                    msg="Error updating supplier unit delivery options",
                    error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
                )
        # build response
        return await self._build_supplier_unit_gql(
            supplier_unit_id=supplier_unit_id,
            unit_categ=None,
            delivery_options=delivery_options,
        )
