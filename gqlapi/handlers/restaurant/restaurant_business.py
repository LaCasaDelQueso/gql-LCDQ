import logging
from typing import Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountInput,
    RestaurantBusinessAccountRepositoryInterface,
    RestaurantBusinessAdminGQL,
    RestaurantBusinessGQL,
    RestaurantBusinessHandlerInterface,
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantUserPermissionRepositoryInterface,
    RestaurantUserRepositoryInterface,
)

from gqlapi.domain.models.v2.restaurant import (
    RestaurantBusinessAccount,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.utils.domain_mapper import domain_inp_to_out
from gqlapi.utils.helpers import serialize_encoded_file


class RestaurantBusinessHandler(RestaurantBusinessHandlerInterface):
    def __init__(
        self,
        restaurant_business_repo: RestaurantBusinessRepositoryInterface,
        restaurant_business_account_repo: RestaurantBusinessAccountRepositoryInterface,
        restaurant_permission_repo: Optional[
            RestaurantUserPermissionRepositoryInterface
        ] = None,
        restaurant_user_repo: Optional[RestaurantUserRepositoryInterface] = None,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
    ):
        self.repository = restaurant_business_repo
        self.account_repository = restaurant_business_account_repo
        if restaurant_permission_repo:
            self.restaurant_permission = restaurant_permission_repo
        if restaurant_user_repo:
            self.restaurant_user_repo = restaurant_user_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo

    async def new_restaurant_business(
        self,
        name: str,
        country: str,
        firebase_id: str,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessAdminGQL:
        """Create Restaurant Business

        Args:
            info (StrawberryInfo): info to connect to DB
            name (str): name of restaurant business
            country (str): country where the restaurant resides
            restaurant_user_id (UUID): unique restaurant user id,
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
            RestaurantBusinessAdminGQL: Restaurant bussines +
              restaurant business account + restaurant user permissions model
            }
        """
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        rest_user = await self.restaurant_user_repo.get(core_user.id)
        # create supplier business
        restaurant_business_id = await self.repository.new(name, country)
        # build response
        restaurant_business = {}
        restaurant_business = await self.repository.get(restaurant_business_id)
        # create permissions as admin
        if await self.restaurant_permission.new(
            rest_user.id, restaurant_business_id, True, True, True
        ):
            restaurant_business["permission"] = await self.restaurant_permission.get(
                rest_user.id
            )
        # create mongo business account
        account_dict = {}
        if account_input:
            account_dict = domain_inp_to_out(account_input, RestaurantBusinessAccount)
        account_dict["restaurant_business_id"] = restaurant_business_id
        restaurant_business_account = RestaurantBusinessAccount(**account_dict)
        if await self.account_repository.new(
            restaurant_business_id, restaurant_business_account
        ):
            restaurant_business["account"] = await self.account_repository.get(
                restaurant_business_id
            )

        return RestaurantBusinessAdminGQL(**restaurant_business)

    async def new_ecommerce_restaurant_business(
        self,
        name: str,
        country: str,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessAdminGQL:
        """Create Restaurant Business for ecommerc user

        Args:
            info (StrawberryInfo): info to connect to DB
            name (str): name of restaurant business
            country (str): country where the restaurant resides
            restaurant_user_id (UUID): unique restaurant user id,
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
            RestaurantBusinessAdminGQL: Restaurant bussines +
              restaurant business account + restaurant user permissions model
            }
        """
        core_user = await self.core_user_repo.fetch_by_email("admin")
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # create supplier business
        restaurant_business_id = await self.repository.add(name, country)
        if not restaurant_business_id:
            raise GQLApiException(
                msg="Error creating restaurant business",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # build response
        restaurant_business = {}
        restaurant_business = await self.repository.fetch(restaurant_business_id)
        if not restaurant_business:
            raise GQLApiException(
                msg="Error fetching restaurant business",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        # create mongo business account
        account_dict = {}
        if account_input:
            account_dict = domain_inp_to_out(account_input, RestaurantBusinessAccount)
        account_dict["restaurant_business_id"] = restaurant_business_id
        restaurant_business_account = RestaurantBusinessAccount(**account_dict)
        if await self.account_repository.add(restaurant_business_account):
            restaurant_business["account"] = await self.account_repository.fetch(
                restaurant_business_id
            )
        return RestaurantBusinessAdminGQL(**restaurant_business)

    async def edit_restaurant_business(
        self,
        restaurant_business_id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessGQL:  # type: ignore
        """Edit Restaurant Business

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.
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
            RestaurantBusinessAdminGQL: Restaurant bussines +
              restaurant business account + restaurant user permissions model
            }
        """
        # validate inputs fk
        await self.account_repository.exist(
            "restaurant_business_id", restaurant_business_id
        )
        await self.repository.exist(restaurant_business_id)
        # update
        account_dict = {}
        if account_input:
            account_dict = domain_inp_to_out(account_input, RestaurantBusinessAccount)
            if account_dict.get("legal_rep_id", None):
                account_dict["legal_rep_id"] = await serialize_encoded_file(
                    account_dict["legal_rep_id"]
                )
            if account_dict.get("incorporation_file", None):
                account_dict["incorporation_file"] = await serialize_encoded_file(
                    account_dict["incorporation_file"]
                )
            if account_dict.get("mx_sat_csf", None):
                account_dict["mx_sat_csf"] = await serialize_encoded_file(
                    account_dict["mx_sat_csf"]
                )
        account_dict["restaurant_business_id"] = restaurant_business_id
        restaurant_business_account = RestaurantBusinessAccount(**account_dict)
        restaurant_business = {}
        # update restaurant business
        if await self.repository.update(
            restaurant_business_id,
            name,
            country,
            active,
        ):
            # return object
            restaurant_business = await self.repository.get(restaurant_business_id)
        # update restaurant business account
        if await self.account_repository.update(
            restaurant_business_id, restaurant_business_account
        ):
            restaurant_business["account"] = await self.account_repository.get(
                restaurant_business_id
            )
        return RestaurantBusinessGQL(**restaurant_business)

    async def fetch_restaurant_business(
        self,
        id: UUID,
    ) -> RestaurantBusinessGQL:  # type: ignore
        """Get Restaurant Businesses

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            id (UUID): unique restaurant business id

        Returns:
            RestaurantBusiness: restaurant business GQL Model
        """
        r_bus = await self.repository.fetch(id)
        if not r_bus:
            raise GQLApiException(
                msg="Restaurant business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        r_bus["account"] = await self.account_repository.fetch(id)
        return RestaurantBusinessGQL(**r_bus)

    async def fetch_restaurant_business_by_firebase_id(
        self,
        firebase_id: str,
    ) -> RestaurantBusinessAdminGQL:  # type: ignore
        """Get Restaurant Business from Firebase id associated to restaurant user

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            firebase_id (str): Firebase ID

        Returns:
            RestaurantBusiness: restaurant business model
        """
        try:
            core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
            if not core_user.id:
                raise GQLApiException(
                    msg="User not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            res_user = await self.restaurant_user_repo.get(core_user.id)
            if not res_user.id:
                raise GQLApiException(
                    msg="Restaurant user not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            # get permissions to validate association
            perms = await self.restaurant_permission.get(res_user.id)
            if perms.restaurant_business_id is None:
                raise GQLApiException(
                    msg="Restaurant business not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            # fetch restaurant business
            rest_bus_dict = await self.repository.get(perms.restaurant_business_id)
            # add account info
            rest_bus_dict["account"] = await self.account_repository.get(
                rest_bus_dict["id"]
            )
            return RestaurantBusinessAdminGQL(**rest_bus_dict)
        except GQLApiException as ge:
            raise ge
        except Exception as e:
            logging.error(e)
            raise GQLApiException(
                msg="Error fetching restaurant user",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )

    async def delete_restaurant_business_account(
        self,
        restaurant_business_id: UUID,
    ) -> bool:
        try:
            if await self.account_repository.delete(
                restaurant_business_id=restaurant_business_id
            ):
                return True
            else:
                return False
        except GQLApiException as ge:
            raise ge
