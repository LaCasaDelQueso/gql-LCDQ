import logging
from bson import Binary
from gqlapi.domain.interfaces.v2.catalog.category import (
    CategoryRepositoryInterface,
    RestaurantBranchCategoryRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchGQL,
    RestaurantBranchHandlerInterface,
    RestaurantBranchInvoicingOptionsRepositoryInterface,
    RestaurantBranchRepositoryInterface,
)
from typing import Optional, List
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    SupplierRestaurantsHandlerInterface,
    SupplierRestaurantsRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.user.employee import EmployeeRepositoryInterface
from gqlapi.domain.models.v2.core import (
    Category,
    PermissionDict,
    RestaurantEmployeeInfo,
    RestaurantEmployeeInfoPermission,
)
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranch,
    RestaurantBranchCategory,
    RestaurantBranchMxInvoiceInfo,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierRestaurantRelationMxInvoicingOptions,
    SupplierUnit,
    SupplierUser,
    SupplierUserPermission,
)
from gqlapi.domain.models.v2.utils import (
    CFDIUse,
    CategoryType,
    InvoiceConsolidation,
    InvoiceTriggerTime,
    InvoiceType,
    RegimenSat,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.repository.user.employee import default_branch_perms


class RestaurantBranchHandler(RestaurantBranchHandlerInterface):
    def __init__(
        self,
        restaurant_branch_repo: RestaurantBranchRepositoryInterface,
        branch_category_repo: RestaurantBranchCategoryRepositoryInterface,
        category_repo: Optional[CategoryRepositoryInterface] = None,
        restaurant_user_repo: Optional[RestaurantUserRepositoryInterface] = None,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        rest_business_repo: Optional[RestaurantBusinessRepositoryInterface] = None,
        employee_repo: Optional[EmployeeRepositoryInterface] = None,
        invoicing_options_repo: Optional[
            RestaurantBranchInvoicingOptionsRepositoryInterface
        ] = None,
        supplier_restaurants_repo: Optional[
            SupplierRestaurantsRepositoryInterface
        ] = None,
        supplier_unit_repo: Optional[SupplierUnitRepositoryInterface] = None,
        supplier_user_repo: Optional[SupplierUserRepositoryInterface] = None,
        supplier_user_permission_repo: Optional[
            SupplierUserPermissionRepositoryInterface
        ] = None,
        supplier_restaurant_handler: Optional[
            SupplierRestaurantsHandlerInterface
        ] = None,
    ):
        self.repository = restaurant_branch_repo
        self.branch_category_repository = branch_category_repo
        if category_repo:
            self.category_repo = category_repo
        if restaurant_user_repo:
            self.restaurant_user_repo = restaurant_user_repo
        if rest_business_repo:
            self.rest_business_repo = rest_business_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if employee_repo:
            self.employee_repo = employee_repo
        if invoicing_options_repo:
            self.invoicing_options_repo = invoicing_options_repo
        if supplier_restaurants_repo:
            self.supplier_restaurants_repo = supplier_restaurants_repo
        if supplier_unit_repo:
            self.supplier_unit_repo = supplier_unit_repo
        if supplier_user_repo:
            self.supplier_user_repo = supplier_user_repo
        if supplier_user_permission_repo:
            self.supplier_user_permission_repo = supplier_user_permission_repo
        if supplier_restaurant_handler:
            self.supplier_restaurant_handler = supplier_restaurant_handler

    async def new_restaurant_branch(
        self,
        restaurant_business_id: UUID,
        branch_name: str,
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
    ) -> RestaurantBranchGQL:  # type: ignore
        """Create restaurant branch

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch
            core_user_id (UUID): unique core user id
            category_id (UUID): _unique category id

        Returns:
            RestaurantBranchGQL
        """
        await self.category_repo.exist(category_id)
        await self.rest_business_repo.exist(restaurant_business_id)
        # create restaurant branch
        restaurant_branch_id = await self.repository.new(
            restaurant_business_id,
            branch_name,
            full_address,
            street,
            external_num,
            internal_num,
            neighborhood,
            city,
            state,
            country,
            zip_code,
        )
        restaurant_branch = await self.repository.get(restaurant_branch_id)
        # get core user id
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create restaurant branch category
        if await self.branch_category_repository.new(
            branch_category=RestaurantBranchCategory(
                restaurant_branch_id=restaurant_branch_id,
                restaurant_category_id=category_id,
                created_by=core_user.id,
            )
        ):
            restaurant_branch["branch_category"] = (
                await self.branch_category_repository.get(restaurant_branch_id)
            )

        # create a restaurant branch user record in employee directory Mongo
        resto_user = await self.restaurant_user_repo.get(core_user.id)
        if not resto_user:
            raise GQLApiException(
                msg="Restaurant User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        employee = await self.employee_repo.get(
            core_element_collection="restaurant_employee_directory",
            user_id_key="restaurant_user_id",
            user_id=resto_user.id,
        )
        tmp_perm = []
        for _e in employee["branch_permissions"]:
            tmp_perm.append(
                RestaurantEmployeeInfoPermission(
                    branch_id=Binary.as_uuid(_e["branch_id"]),
                    permissions=[PermissionDict(**_p) for _p in _e["permissions"]],
                )
            )
        tmp_perm.append(
            RestaurantEmployeeInfoPermission(
                branch_id=restaurant_branch_id,
                permissions=default_branch_perms,
            )
        )
        await self.employee_repo.update(
            core_element_collection="restaurant_employee_directory",
            user_id_key="restaurant_user_id",
            user_id=resto_user.id,
            employee=RestaurantEmployeeInfo(
                restaurant_user_id=resto_user.id,
                name=employee["name"],
                last_name=employee["last_name"],
                department=employee["department"],
                position=employee["position"],
                phone_number=employee["phone_number"],
                branch_permissions=tmp_perm,
            ),
        )
        # with the new restaurant branch id and the user id
        return RestaurantBranchGQL(**restaurant_branch)

    async def new_ecommerce_restaurant_address(
        self,
        restaurant_business_id: UUID,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        category_id: Optional[UUID] = None,
    ) -> RestaurantBranchGQL:  # type: ignore
        """Create ecommerce restaurant address

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch
            core_user_id (UUID): unique core user id
            category_id (UUID): _unique category id

        Returns:
            RestaurantBranchGQL
        """
        # create restaurant branch
        restaurant_branch_id = await self.repository.new(
            restaurant_business_id,
            branch_name,
            full_address,
            street,
            external_num,
            internal_num,
            neighborhood,
            city,
            state,
            country,
            zip_code,
        )
        restaurant_branch = await self.repository.get(restaurant_branch_id)
        # get default ecom user
        core_user = await self.core_user_repo.fetch_by_email("admin")
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create restaurant branch category
        optional_categ = None
        try:
            searched_categs = await self.category_repo.get_categories(
                search="Otro",
                category_type=CategoryType.RESTAURANT,
            )
            if len(searched_categs) > 0:
                optional_categ = searched_categs[0]
        except GQLApiException as ge:
            logging.warning(ge)
        if category_id or optional_categ is not None:
            cat_id = category_id if category_id else optional_categ.id  # type: ignore (safe)
            if await self.branch_category_repository.new(
                branch_category=RestaurantBranchCategory(
                    restaurant_branch_id=restaurant_branch_id,
                    restaurant_category_id=cat_id,
                    created_by=core_user.id,
                )
            ):
                restaurant_branch["branch_category"] = (
                    await self.branch_category_repository.get(restaurant_branch_id)
                )
        # with the new restaurant branch id and the user id
        return RestaurantBranchGQL(**restaurant_branch)

    async def edit_restaurant_branch(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
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
    ) -> RestaurantBranchGQL:  # type: ignore
        """Update restaurant branch

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch
            category_id (UUID): _unique category id

        Raises:
            GQLApiException

        Returns:
            RestaurantBranchGQL
        """
        if category_id:
            await self.category_repo.exist(category_id)
        await self.repository.exist(restaurant_branch_id)
        # update
        if not await self.repository.update(
            restaurant_branch_id,
            branch_name,
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
        ):
            raise GQLApiException(
                msg="Error updating restaurant branch",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        restaurant_branch = await self.repository.get(restaurant_branch_id)
        if category_id:
            if not await self.branch_category_repository.update(
                restaurant_branch_id, category_id
            ):
                raise GQLApiException(
                    msg="Error updating branch category",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        restaurant_branch["branch_category"] = (
            await self.branch_category_repository.get(restaurant_branch_id)
        )
        return RestaurantBranchGQL(**restaurant_branch)

    async def edit_ecommerce_restaurant_branch(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
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
    ) -> RestaurantBranchGQL:  # type: ignore
        """Update ecommerce restaurant branch

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch
            category_id (UUID): _unique category id

        Raises:
            GQLApiException

        Returns:
            RestaurantBranchGQL
        """
        # update
        if not await self.repository.edit(
            restaurant_branch_id,
            branch_name,
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
        ):
            raise GQLApiException(
                msg="Error updating restaurant branch",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        restaurant_branch = await self.repository.fetch(restaurant_branch_id)
        if category_id:
            if not await self.branch_category_repository.edit(
                restaurant_branch_id, category_id
            ):
                raise GQLApiException(
                    msg="Error updating branch category",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        restaurant_branch["branch_category"] = (
            await self.branch_category_repository.get(restaurant_branch_id)
        )
        return RestaurantBranchGQL(**restaurant_branch)

    async def new_restaurant_branch_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: str,
        email: str,
        legal_name: str,
        full_address: str,
        zip_code: str,
        sat_regime: RegimenSat,
        cfdi_use: CFDIUse,
    ) -> RestaurantBranchMxInvoiceInfo:  # type: ignore
        """Create restaurant branch tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            mx_sat_id (str): unique alphanumeric key
            email (str):  email to contact the branch
            legal_name (str): Legal NAme of branch
            full_address (str): address of branch
            zip_code (str): code of branch zone
            sat_regime (RegimenSat): code of Sat Regime
            cfdi_use (CFDIUse): code od cfdi use

        Returns:
            RestaurantBranchMxInvoiceInfo
        """
        # review is restaurant branch exists
        await self.repository.exist(restaurant_branch_id)
        if await self.repository.new_tax_info(
            restaurant_branch_id,
            mx_sat_id,
            email,
            legal_name,
            full_address,
            zip_code,
            sat_regime,
            cfdi_use,
        ):
            branch_tax_info = await self.repository.get_tax_info(restaurant_branch_id)
            return RestaurantBranchMxInvoiceInfo(**branch_tax_info)

    async def edit_restaurant_branch_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> RestaurantBranchMxInvoiceInfo:  # type: ignore
        """Update restaurant branch tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            mx_sat_id (str): unique alphanumeric key
            email (str):  email to contact the branch
            legal_name (str): Legal NAme of branch
            full_address (str): address of branch
            zip_code (str): code of branch zone
            sat_regime (RegimenSat): code of Sat Regime
            cfdi_use (CFDIUse): code od cfdi use
            invoicing_provider_id (str): _description_

        Returns:
            RestaurantBranchMxInvoiceInfo
        """
        # verify if restaurant branch exists
        if not await self.repository.exists(restaurant_branch_id):
            raise GQLApiException(
                msg="Branch not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # verify if restaurant branch tax info exists
        branch_tax_info = {}
        try:
            branch_tax_info = await self.repository.get_tax_info(restaurant_branch_id)
        except GQLApiException as ge:
            if ge.error_code != GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
                logging.warning(ge)
            else:
                raise ge
        # if exists update, else create
        if branch_tax_info:
            await self.repository.update_tax_info(
                restaurant_branch_id,
                mx_sat_id,
                email,
                legal_name,
                full_address,
                zip_code,
                sat_regime,
                cfdi_use,
                invoicing_provider_id,
            )
        else:
            if (
                mx_sat_id is not None
                and email is not None
                and legal_name is not None
                and full_address is not None
                and zip_code is not None
                and sat_regime is not None
                and cfdi_use is not None
            ):
                await self.repository.new_tax_info(
                    restaurant_branch_id,
                    mx_sat_id,
                    email,
                    legal_name,
                    full_address,
                    zip_code,
                    sat_regime,
                    cfdi_use,
                )
            else:
                raise GQLApiException(
                    msg="Cannot Insert Branch Tax Info, missing info.",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        branch_tax_info = await self.repository.get_tax_info(restaurant_branch_id)
        return RestaurantBranchMxInvoiceInfo(**branch_tax_info)

    async def fetch_restaurant_branches(
        self,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchGQL]:  # type: ignore
        """Get restaurant branches

        Args:
            restaurant_business_id (Optional[UUID], optional): unique restaurant business id. Defaults to None.
            branch_name (Optional[str], optional): Name of branch. Defaults to None.
            search (Optional[str], optional): code to query filter. Defaults to None.
            restaurant_category (Optional[str], optional): restaurant category. Defaults to None.

        Returns:
            List[RestaurantBranchGQL]
        """
        return await self.repository.get_restaurant_branches(
            restaurant_business_id,
            restaurant_branch_id,
            branch_name,
            search,
            restaurant_category,
        )

    async def fetch_restaurant_branches_asoc_with_user(
        self,
        firebase_id: str,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchGQL]:
        """Fetch restaurant branches associated with user

        Parameters
        ----------
        firebase_id : str
            _description_
        restaurant_business_id : Optional[UUID], optional
            _description_, by default None
        restaurant_branch_id : Optional[UUID], optional
            _description_, by default None
        branch_name : Optional[str], optional
            _description_, by default None
        search : Optional[str], optional
            _description_, by default None
        restaurant_category : Optional[str], optional
            _description_, by default None

        Returns
        -------
        List[RestaurantBranchGQL]
        """
        # get core user
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        branches = await self.fetch_restaurant_branches(
            restaurant_business_id,
            restaurant_branch_id,
            branch_name,
            search,
            restaurant_category,
        )
        for i, br in enumerate(branches):
            try:
                inv_info = await self.repository.get_tax_info(br.id)
                if inv_info:
                    _tax_info = RestaurantBranchMxInvoiceInfo(**inv_info)
                    branches[i].tax_info = _tax_info
            except GQLApiException as ge:
                if ge.error_code != GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
                    logging.warning(ge)
                    raise ge
            except Exception as e:
                logging.error(e)
        # [TODO] - fetch branches associated with user
        # [TODO] - filter branches from the response that are not associated with user
        return branches

    async def fetch_restaurant_categories(self) -> List[Category]:
        """Get all categories for Restaurants

        Returns
        -------
        List[Category]
            List of Categories for Restaurants
        """
        return await self.category_repo.get_all([CategoryType.RESTAURANT])

    async def edit_restaurant_branch_invoicing_options(
        self,
        firebase_id: str,
        restaurant_branch_id: UUID,
        automated_invoicing: bool,
        invoice_type: InvoiceType,
        triggered_at: Optional[InvoiceTriggerTime] = None,
        consolidation: Optional[InvoiceConsolidation] = None,
    ):
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="User not found",
            )
        # if core_user.id:
        supp_user = await self.supplier_user_repo.fetch(core_user.id)  # type: ignore
        if not supp_user:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="Supplier User not found",
            )
        supp_user.pop("user", None)
        supp_user_obj = SupplierUser(**supp_user)

        supp_user_perm = await self.supplier_user_permission_repo.fetch(
            supp_user_obj.id
        )
        if not supp_user_perm:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="Supplier User not found",
            )
        supp_user_perm_obj = SupplierUserPermission(**supp_user_perm)

        if not await self.repository.exists(restaurant_branch_id):
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg=f"Branch with id {restaurant_branch_id} not found",
            )

        restaurant_branch = await self.repository.fetch(restaurant_branch_id)
        if not restaurant_branch:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg=f"Branch with id {restaurant_branch_id} not found",
            )
        restaurant_branch_obj = RestaurantBranch(**restaurant_branch)

        actual_supplier_restaurant_relations = await self.supplier_restaurant_handler.search_supplier_business_restaurant(
            supp_user_perm_obj.supplier_business_id, restaurant_branch_obj.branch_name  # type: ignore
        )
        if not actual_supplier_restaurant_relations:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="Supplier Restaurant Relation not found",
            )

        spr = None
        supplier_unit = await self.supplier_unit_repo.fetch(
            actual_supplier_restaurant_relations[0].supplier_unit_id
        )
        if not supplier_unit:
            raise GQLApiException(
                msg="Does Not Found Supplier Unit.",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED,
            )
        supp_unit_obj = SupplierUnit(**supplier_unit)

        spr = await self.supplier_restaurants_repo.search_supplier_business_restaurant(
            supplier_business_id=supp_unit_obj.supplier_business_id,
            restaurant_branch_id=restaurant_branch_id,
        )
        if not spr:
            raise GQLApiException(
                msg="Does Not Found Supplier RestauranT Relation.",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED,
            )
        if spr and len(spr) > 1:
            raise GQLApiException(
                msg="This branch has more that 2 relations.",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED,
            )

        restaurant_branch_invoicing_options = await self.invoicing_options_repo.fetch(
            spr[0].id
        )

        if restaurant_branch_invoicing_options:
            await self.invoicing_options_repo.edit(
                supplier_restaurant_relation_id=spr[0].id,
                automated_invoicing=automated_invoicing,
                invoice_type=invoice_type,
                triggered_at=triggered_at,
                consolidation=consolidation,
            )

        else:
            if (
                restaurant_branch_id
                and triggered_at
                and invoice_type
                and isinstance(automated_invoicing, bool)
            ):
                await self.invoicing_options_repo.add(
                    branch_invoicing_options=SupplierRestaurantRelationMxInvoicingOptions(
                        supplier_restaurant_relation_id=spr[0].id,
                        automated_invoicing=automated_invoicing,
                        triggered_at=triggered_at,
                        consolidation=consolidation,
                        invoice_type=invoice_type,
                    )
                )
            else:
                raise GQLApiException(
                    msg="Cannot Insert Branch Invoicing Options Info, missing info.",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )

        restaurant_branch_invoicing_options = await self.invoicing_options_repo.fetch(
            spr[0].id
        )
        if restaurant_branch_invoicing_options:
            return restaurant_branch_invoicing_options
