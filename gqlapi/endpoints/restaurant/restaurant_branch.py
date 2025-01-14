import logging
from typing import List, Optional
from uuid import UUID
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.app.permissions import (
    IsAlimaEmployeeAuthorized,
    IsAlimaRestaurantAuthorized,
    IsAuthenticated,
)
from gqlapi.repository.user.employee import EmployeeRepository

import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchError,
    RestaurantBranchResult,
    RestaurantBranchTaxResult,
    RestaurantCategories,
    RestaurantCategoryResult,
)
from gqlapi.domain.models.v2.utils import CFDIUse, RegimenSat
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.restaurant.restaurant_branch import (
    RestaurantBranchHandler,
)
from gqlapi.repository.core.category import (
    CategoryRepository,
    RestaurantBranchCategoryRepository,
)
from gqlapi.repository.restaurant.restaurant_branch import (
    RestaurantBranchRepository,
)
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessRepository,
)
from gqlapi.repository.restaurant.restaurant_user import RestaurantUserRepository


@strawberry.type
class RestaurantBranchMutation:
    # [TODO] - validate whether the user is allowed to create a branch
    @strawberry.mutation(
        name="newRestaurantBranch",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_restaurant_branch(
        self,
        info: StrawberryInfo,
        restaurant_business_id: UUID,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        category_id: UUID,
        internal_num: str = "",
    ) -> RestaurantBranchResult:  # type: ignore
        logging.info("Create new restaurant branch")
        # instantiate handler
        _handler = RestaurantBranchHandler(
            restaurant_branch_repo=RestaurantBranchRepository(info),
            branch_category_repo=RestaurantBranchCategoryRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
            core_user_repo=CoreUserRepository(info),
            rest_business_repo=RestaurantBusinessRepository(info),
            employee_repo=EmployeeRepository(info),
        )
        # call validation
        if (
            not restaurant_business_id
            or not branch_name
            or not full_address
            or not street
            or not external_num
            or not zip_code
            or not neighborhood
            or not city
            or not state
            or not country
            or not category_id
        ):
            return RestaurantBranchError(
                msg="Empty values for creating Restaurant Branch",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_restaurant_branch(
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
                fb_id,
                category_id,
            )
            return _resp
        except GQLApiException as ge:
            logging.warning(ge)
            return RestaurantBranchError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logging.warning(e)
            return RestaurantBranchError(
                msg="Error creating restaurant branch",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    # [TODO] - validate whether the user is allowed to edit a branch
    @strawberry.mutation(
        name="updateRestaurantBranch",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_restaurant_branch(
        self,
        info: StrawberryInfo,
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
    ) -> RestaurantBranchResult:  # type: ignore
        logging.info("Edit restaurant branch")
        if not restaurant_branch_id or not (
            branch_name
            or full_address
            or street
            or external_num
            or internal_num
            or zip_code
            or neighborhood
            or city
            or state
            or country
            or category_id
            or deleted
        ):
            return RestaurantBranchError(
                msg="Empty values for creating Restaurant Branch",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # [TODO] - validate whether the user is allowed to edit the requested branches
        # instantiate handler
        try:
            _handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
                category_repo=CategoryRepository(info),
            )
            # call validation
            if not restaurant_branch_id:
                return RestaurantBranchError(
                    msg="Empty values for creating Restaurant Branch",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # call handler
            return await _handler.edit_restaurant_branch(
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
                category_id,
                deleted,
            )
        except GQLApiException as ge:
            return RestaurantBranchError(msg=ge.msg, code=ge.error_code)

    # [TODO] - validate whether the user is allowed to create a branch
    @strawberry.mutation(
        name="newRestaurantBranchTaxInfo",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_restaurant_branch_tax_info(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        mx_sat_id: str,
        email: str,
        legal_name: str,
        full_address: str,
        zip_code: str,
        sat_regime: RegimenSat,
        cfdi_use: CFDIUse,
    ) -> RestaurantBranchTaxResult:  # type: ignore
        logging.info("Create new restaurant_branch tax info")
        # instantiate handler
        _handler = RestaurantBranchHandler(
            RestaurantBranchRepository(info), RestaurantBranchCategoryRepository(info)
        )
        # call validation
        if (
            not restaurant_branch_id
            or not mx_sat_id
            or not email
            or not email
            or not legal_name
            or not full_address
            or not zip_code
            or not sat_regime
            or not cfdi_use
        ):
            return RestaurantBranchError(
                msg="Empty values for creating Restaurant Branch Tax Info",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.new_restaurant_branch_tax_info(
                restaurant_branch_id,
                mx_sat_id,
                email,
                legal_name,
                full_address,
                zip_code,
                sat_regime,
                cfdi_use,
            )
            return _resp
        except GQLApiException as ge:
            return RestaurantBranchError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="updateRestaurantBranchTaxInfo",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_restaurant_branch_tax_info(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> RestaurantBranchTaxResult:  # type: ignore
        logging.info("Edit restaurant tax info")

        # instantiate handler
        try:
            # instantiate handler
            _handler = RestaurantBranchHandler(
                RestaurantBranchRepository(info),
                RestaurantBranchCategoryRepository(info),
            )
            # call validation
            if not restaurant_branch_id and not (
                mx_sat_id
                or email
                or legal_name
                or full_address
                or zip_code
                or sat_regime
                or cfdi_use
                or invoicing_provider_id
            ):
                return RestaurantBranchError(
                    msg="Empty values for creating Restaurant Branch",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # call handler
            return await _handler.edit_restaurant_branch_tax_info(
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
        except GQLApiException as ge:
            return RestaurantBranchError(msg=ge.msg, code=ge.error_code)


@strawberry.type
class RestaurantBranchQuery:
    @strawberry.field(
        name="getRestaurantBranches",
        permission_classes=[IsAuthenticated, IsAlimaEmployeeAuthorized],
    )
    async def get_restaurant_branches(
        self,
        info: StrawberryInfo,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchResult]:  # type: ignore
        """Get restaurant branches

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.

        Returns:
            List[RestaurantBranchResult]: restaurant business model list
        """
        logging.info("Get restaurant branches")
        # instantiate handler
        try:
            _handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
            )
            # call handler
            return await _handler.fetch_restaurant_branches(
                restaurant_business_id,
                restaurant_branch_id,
                branch_name,
                search,
                restaurant_category,
            )
        except GQLApiException as ge:
            logging.warning(ge)
            return [RestaurantBranchError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logging.warning(e)
            return [
                RestaurantBranchError(
                    msg="Error fetching restaurant branches",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(
        name="getRestaurantBranchesFromToken",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_restaurant_branches_from_token(
        self,
        info: StrawberryInfo,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchResult]:  # type: ignore
        """Get restaurant branches

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            restaurant_business_id (Optional[UUID], optional): restaurant business id. Defaults to None.
            restaurant_branch_id (Optional[UUID], optional): restaurant branch id. Defaults to None.
            branch_name (Optional[str], optional): branch name. Defaults to None.
            search (Optional[str], optional): search string. Defaults to None.
            restaurant_category (Optional[str], optional): restaurant category. Defaults to None.

        Returns:
            List[RestaurantBranchResult]: restaurant business model list
        """
        logging.info("Get restaurant branches")
        # instantiate handler
        try:
            _handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            # get FB id from context
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _branches = await _handler.fetch_restaurant_branches_asoc_with_user(
                fb_id,
                restaurant_business_id,
                restaurant_branch_id,
                branch_name,
                search,
                restaurant_category,
            )
            return _branches
        except GQLApiException as ge:
            logging.warning(ge)
            return [RestaurantBranchError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logging.warning(e)
            return [
                RestaurantBranchError(
                    msg="Error fetching restaurant branches",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]

    @strawberry.field(name="getRestaurantCategories")
    async def get_restaurant_categories(
        self,
        info: StrawberryInfo,
    ) -> RestaurantCategoryResult:  # type: ignore
        """Get restaurant categories

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.

        Returns:
            List[Category]: restaurant category model list
        """
        logging.info("Get restaurant categories")
        # instantiate handler
        try:
            _handler = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
                category_repo=CategoryRepository(info),
            )
            # call handler
            cats = await _handler.fetch_restaurant_categories()
            return RestaurantCategories(categories=cats)
        except GQLApiException as ge:
            return RestaurantBranchError(msg=ge.msg, code=ge.error_code)
