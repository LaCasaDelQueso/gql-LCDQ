import logging
from typing import List, Optional
from uuid import UUID

# from io import BytesIO, StringIO

import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountDeleteGQLResult,
    RestaurantBusinessAccountInput,
    RestaurantBusinessAdminGQLResult,
    RestaurantBusinessError,
    RestaurantBusinessGQLResult,
    RestaurantBusinessResult,
)
from gqlapi.app.permissions import (
    IsAlimaEmployeeAuthorized,
    IsAlimaRestaurantAuthorized,
    IsAuthenticated,
)
from gqlapi.handlers.restaurant.restaurant_business import RestaurantBusinessHandler
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.restaurant.restaurant_user import (
    RestaurantUserPermissionRepository,
    RestaurantUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


@strawberry.type
class RestaurantBusinessMutation:
    @strawberry.mutation(
        name="newRestaurantBusiness",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_restaurant_business(
        self,
        info: StrawberryInfo,
        name: str,
        country: str,
        account: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessAdminGQLResult:  # type: ignore
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB
            name (str): name of restaurant business
            country (str): country where the restaurant resides
            account_input (Optional[RestaurantBusinessAccountInput], optional): {
                legal_business_name: Optional[str] = None
                incorporation_file (Optional[Upload], optional): documents filed with a government body to
                    legally document the creation of a corporation.
                legal_rep_name (Optional[str], optional): acts as the “legal face” of the company and is the
                    signatory for all company operational activities
                legal_rep_id (Optional[str], optional): id of rep name (CURP in mx)
                legal_address (Optional[str], optional): the place where your company registered legally
                phone_number (Optional[str]), optional): number to contact the restaurant
                email (Optional[str], optional): email to contact the restaurant
                website: (Optional[str], optional): restaurant website
                mx_sat_regimen: (Optional[str], optional): set of laws governing an activity within a region (mx)
                mx_sat_rfc: (Optional[str], optional): unique alphanumeric key
                mx_sat_csf: (Optional[Upload], optional): document that allows you to know your status as a
                    taxpayer before the Tax Administration Service (SAT)
                }
            . Defaults to None.

        Returns:
            RestaurantBusinessResult: Restaurant bussines + restaurant business account model
        """
        logging.info("Create new restaurant_business")
        # instantiate handler
        _handler = RestaurantBusinessHandler(
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            restaurant_permission_repo=RestaurantUserPermissionRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # validate inputs
        if not name or not country:
            return RestaurantBusinessError(
                msg="Empty values for creating Restaurant User",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # call validation
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            _resp = await _handler.new_restaurant_business(
                name, country, fb_id, account
            )
            return _resp
        except GQLApiException as ge:
            return RestaurantBusinessError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="updateRestaurantBusiness",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_restaurant_business(
        self,
        info: StrawberryInfo,
        restaurant_business_id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
        account: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessGQLResult:  # type: ignore
        """Edit restaurant business

        Args:
            info (StrawberryInfo): info to connect to DB
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides. Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None.
            account_input (Optional[RestaurantBusinessAccountInput], optional): {
                legal_business_name: Optional[str] = None
                incorporation_file (Optional[Upload], optional): documents filed with a government body to
                    legally document the creation of a corporation.
                legal_rep_name (Optional[str], optional): acts as the “legal face” of the company and is the
                    signatory for all company operational activities
                legal_rep_id (Optional[str], optional): id of rep name (CURP in mx)
                legal_address (Optional[str], optional): the place where your company registered legally
                phone_number (Optional[str]), optional): number to contact the restaurant
                email (Optional[str], optional): email to contact the restaurant
                website: (Optional[str], optional): restaurant website
                mx_sat_regimen: (Optional[str], optional): set of laws governing an activity within a region (mx)
                mx_sat_rfc: (Optional[str], optional): unique alphanumeric key
                mx_sat_csf: (Optional[Upload], optional): document that allows you to know your status as a
                    taxpayer before the Tax Administration Service (SAT)
                }
                . Defaults to None.

        Returns:
            RestaurantBusinessResult: _description_
        """
        logging.info("Edit restaurant business")
        # instantiate handler
        try:
            _handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            # validate inputs
            if not restaurant_business_id or not (
                name or country or isinstance(active, bool) or account
            ):
                return RestaurantBusinessError(
                    msg="Empty values for updating Restaurant Business",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # call validation
            upd_res_bus = await _handler.edit_restaurant_business(
                restaurant_business_id, name, country, active, account
            )
            return upd_res_bus
        except GQLApiException as ge:
            return RestaurantBusinessError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="deleteRestaurantBusinessAccount",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def delete_restaurant_business_account(
        self,
        info: StrawberryInfo,
        restaurant_business_id: UUID,
    ) -> RestaurantBusinessAccountDeleteGQLResult:  # type: ignore
        logging.info("Delete restaurant business account")
        # instantiate handler
        try:
            # _handler = RestaurantBusinessHandler(
            #     restaurant_business_repo=RestaurantBusinessRepository(info),
            #     restaurant_business_account_repo=RestaurantBusinessAccountRepository(
            #         info
            #     ),
            # )
            # [TODO] verify if this user is the same as the restaurant business
            # fb_id = info.context["request"].user.firebase_user.firebase_id
            # validate inputs
            # if not restaurant_business_id:
            #     return RestaurantBusinessError(
            #         msg="Empty values for updating Restaurant Business",
            #         code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            #     )
            # # call validation
            # del_res_bus = await _handler.delete_restaurant_business_account(
            #     restaurant_business_id
            # )
            # return RestaurantBusinessAccountDeleteGQL(delete=del_res_bus)
            raise GQLApiException(
                msg="Not implemented",
                error_code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
        except GQLApiException as ge:
            return RestaurantBusinessError(msg=ge.msg, code=ge.error_code)


@strawberry.type
class RestaurantBusinessQuery:
    @strawberry.field(
        name="getRestaurantBusinesses",
        permission_classes=[IsAuthenticated, IsAlimaEmployeeAuthorized],
    )
    async def get_restaurant_businesses(
        self,
        info: StrawberryInfo,
        id: Optional[UUID] = None,
    ) -> List[RestaurantBusinessResult]:  # type: ignore
        """Get restaurant businesses

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            id (UUID): unique restaurant business id. Defaults to None.
            name (str): name of restaurant business. Defaults to None.
            country (str): country where the restaurant resides. Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None.

        Returns:
            List[RestaurantBusinessResult]: restaurant business model list
        """
        logging.info("Get restaurant businesses")
        # instantiate handler
        try:
            if not id:
                raise GQLApiException(
                    msg="Empty values for fetching Restaurant Business",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            _handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
            )
            # call handler
            return [await _handler.fetch_restaurant_business(id)]
        except GQLApiException as ge:
            return [RestaurantBusinessError(msg=ge.msg, code=ge.error_code)]

    @strawberry.field(
        name="getRestaurantBusinessFromToken",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_restaurant_business_from_token(
        self, info: StrawberryInfo
    ) -> RestaurantBusinessAdminGQLResult:  # type: ignore
        """Get restaurant business from token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            RestaurantBusinessAdminGQLResult: restaurant business model
        """
        logging.info("Get restaurant business from token")
        # instantiate handler
        _handler = RestaurantBusinessHandler(
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            restaurant_user_repo=RestaurantUserRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_permission_repo=RestaurantUserPermissionRepository(info),
        )
        # get restaurant user by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _rest_bus = await _handler.fetch_restaurant_business_by_firebase_id(fb_id)
        except GQLApiException as ge:
            return RestaurantBusinessError(msg=ge.msg, code=ge.error_code)
        # return restaurant business
        return _rest_bus
