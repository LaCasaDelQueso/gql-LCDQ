from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantUserGQL,
    RestaurantUserPermissionRepositoryInterface,
    RestaurantUserRepositoryInterface,
)
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBusiness,
    RestaurantBusinessAccount,
    RestaurantUserPermission,
)
from gqlapi.domain.models.v2.utils import RestaurantBusinessType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


class MockRestaurantUserRepository(RestaurantUserRepositoryInterface):
    def new(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        firebase_id: str,
        role: str,
    ) -> UUID:
        """_summary_

        Args:
            first_name (str): user first name
            last_name (str): user last name
            email (str): user contact email
            phone_number (str): user contact number
            firebase_id (str): unique restaurant user firebase id_
            role (str): user role in the restaurant

        Raises:
            GQLApiException

        Returns:
            UUID: unique restaurant user id
        """

        core_user_id = uuid.uuid4()
        if email == "fer@alima.la":
            pass
        else:
            raise GQLApiException(
                msg="Error to build restauratn user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

        return core_user_id

    def update_restaurant_user(
        self,
        core_id: UUID,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
    ) -> bool:
        """_summary_

        Args:
            core_id (UUID): unique core user id
            first_name (Optional[str], optional): user first name. Defaults to None.
            last_name (Optional[str], optional): user last name. Defaults to None.
            phone_number (Optional[str], optional): user contact number. Defaults to None.
            role (Optional[str], optional): user role in the restaurant. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        if first_name == "error":
            raise GQLApiException(
                msg="Error updating restaurant user",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        if first_name == "false":
            return False
        return True

    def get(self, core_user_id: UUID) -> RestaurantUserGQL:  # type: ignore
        """_summary_

        Args:
            info (StrawberryInfo): Info to connect to DB
            core_user_id (UUID): unique core user id

        Raises:
            GQLApiException

        Returns:
            RestaurantUserGQL: restaurant user + core user model
        """
        if core_user_id != UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"):
            raise GQLApiException(
                msg="Get Restaurant User",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        internal_values = {
            "id": UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
            "user_id": UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
            "role": "jefe",
            "enabled": True,
            "deleted": True,
            "created_at": datetime(2023, 4, 27, 12, 11, 41, 369194),
            "last_updated": datetime(2023, 4, 27, 12, 11, 41, 369194),
        }
        tree_user_sql_values: Dict[Any, Any] = {}
        tree_user_sql_values = internal_values
        tree_user_sql_values["user"] = CoreUser(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
            first_name="Fer,",
            last_name="reyes",
            email="fer@alima.la",
            phone_number="1234567890",
            firebase_id="123",
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        )
        return RestaurantUserGQL(**tree_user_sql_values)

    def delete(self, core_id: UUID, deleted: bool) -> bool:
        """_summary_

        Args:
            core_id (UUID): unique core user id
            deleted (bool): restaurant user status

        Raises:
            GQLApiException

        Returns:
            bool: validate delete is done
        """

        if core_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"):
            raise GQLApiException(
                msg="Error updating restaurant user",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        if core_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673"):
            return False
        return True

    def activate_desactivate(self, core_id: UUID, enabled: bool) -> bool:
        """_summary_

        Args:
            core_id (UUID): unique core user id
            enabled (bool): restaurant user status

        Raises:
            GQLApiException

        Returns:
            bool: validate activate/desactivate is done
        """
        # [TODO] - implement method
        if core_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"):
            raise GQLApiException(
                msg="Error updating restaurant user",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        if core_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673"):
            return False
        return True

    def create_restaurant_user_employee(
        self,
        restaurant_business_id: UUID,
        core_user_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        department: Optional[str] = None,
        position: Optional[str] = None,
    ) -> bool:
        """_summary_

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            core_user_id (UUID): unique user id
            name (str): employee first name
            last_name (str): employee last name
            phone_number (str): employee contact number
            email (str): employee contact email
            department (Optional[str], optional): department to which the restaurant employee belongs. Defaults to None.
            position (Optional[str], optional): employee role in restaurant. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate creation is done
        """
        # [TODO] - implement method
        if name == "false":
            return False
        if name == "error":
            raise GQLApiException(
                msg="Error creating restaurant employee info",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        return True

    def update_restaurant_user_employee(
        self,
        restaurant_business_id: UUID,
        core_id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
    ) -> bool:
        """Update restaurant user employee

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            core_user_id (UUID): unique user id
            name (Optional[str], optional): employee first name. Defaults to None.
            last_name (Optional[str], optional): employee last name. Defaults to None.
            department (Optional[str], optional): department to which the restaurant employee belongs. Defaults to None.
            position (Optional[str], optional): employee role in restaurant. Defaults to None.
            phone_number (Optional[str], optional): employee contact number. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        # [TODO] - implement method
        if not (name and last_name and department and position and phone_number):
            raise GQLApiException(
                msg="Error updating restaurant employee",
                error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
            )
        return False


class MockRestaurantUserPermissionRepository(
    RestaurantUserPermissionRepositoryInterface
):
    def new(
        self,
        restaurant_user_id: UUID,
        restaurant_business_id: UUID,
        display_orders_section: bool,
        display_suppliers_section: bool,
        display_products_section: bool,
    ) -> bool:
        """_summary_

        Args:
            restaurant_user_id (UUID): unique restaurant user id
            restaurant_business_id (UUID): unique restaurant business id
            display_orders_section (bool): permission to manaje orders section
            display_suppliers_section (bool): permission to manaje suppliers section
            display_products_section (bool): permission to manaje products section

        Raises:
            GQLApiException

        Returns:
            bool: validate creation is done
        """

        if restaurant_user_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            return False
        if restaurant_user_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673"):
            raise GQLApiException(
                msg="Error creating restaurant user permission",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        return True

    def update(
        self,
        restaurant_user_id: UUID,
        display_orders_section: bool,
        display_suppliers_section: bool,
        display_products_section: bool,
    ) -> bool:
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id
            display_orders_section (bool): permission to manaje orders section
            display_suppliers_section (bool): permission to manaje suppliers section
            display_products_section (bool): permission to manaje products section

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        if restaurant_user_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            return False
        if restaurant_user_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673"):
            raise GQLApiException(
                msg="Error updating restaurant user permission",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return True

    def get(self, restaurant_user_id: UUID) -> RestaurantUserPermission:
        """_summary_

        Args:
            restaurant_user_id (UUID): unique restaurant user id

        Raises:
            GQLApiException

        Returns:
            RestaurantUserPermission: Restaurant User Permission id
        """

        if restaurant_user_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            raise GQLApiException(
                msg="Get Restaurant User Permission",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        return RestaurantUserPermission(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            restaurant_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            display_orders_section=False,
            display_suppliers_section=False,
            display_products_section=False,
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        )

    def get_restaurant_user_contact_and_permission(
        self, restaurant_business_id: UUID
    ) -> List[RestaurantUserPermission]:
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB
            restaurant_business_id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            List[RestaurantUserPermission]: {
                core_user_id (UUID): unique user id
                restaurant_business_id (UUID): unique restaurant business id
                display_orders_section (bool): permission to manaje orders section
                display_suppliers_section (bool): permission to manaje suppliers section
                display_products_section (bool): permission to manaje products section
                email (str): user contact email
                phone_number (str): user contact number
            } list
        """
        if restaurant_business_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            raise GQLApiException(
                msg="Get Restaurant User Permission",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        return [
            RestaurantUserPermission(
                id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
                restaurant_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
                restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
                # core_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
                display_orders_section=False,
                display_suppliers_section=False,
                display_products_section=False,
                # email="Fercho@alima.la",
                # phone_number="0987654321",
                created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
                last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
            )
        ]


class MockRestaurantBusinessRepository(RestaurantBusinessRepositoryInterface):
    def new(self, name: str, country: str) -> UUID:
        """_summary_

        Args:
            name (str): name of restaurant business
            country (str): country where the restaurant resides

        Raises:
            GQLApiException

        Returns:
            UUID: unique restaurant business id
        """
        # Sumary

        if name == "error":
            logging.warning("Issues fetch restaurant business (empty)")
            raise GQLApiException(
                msg="Get Restaurant business null",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        return UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")

    def update(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """_summary_

        Args:
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """
        if name == "false":
            return False
        if name == "Error":
            raise GQLApiException(
                msg="Error updating restaurant business",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return True

    def get(self, id: UUID) -> Dict[Any, Any]:  # type: ignore
        """_summary_

        Args:
            id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: restaurant business model dict
        """

        if id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"):
            logging.warning("Issues fetch restaurant business (empty)")
            raise GQLApiException(
                msg="Get Restaurant Business null",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        return {
            "id": UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
            "name": "Fer",
            "country": "México",
            "active": True,
            "created_at": datetime(2023, 4, 27, 12, 11, 41, 369194),
            "last_updated": datetime(2023, 4, 27, 12, 11, 41, 369194),
        }

    def get_restaurant_businesses(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> List[RestaurantBusiness]:
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            List[RestaurantBusiness]: restaurant business model list
        """

        if not (id and name):
            raise GQLApiException(
                msg="Get Restaurant Business",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR.value,
            )
        return [
            RestaurantBusiness(
                id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e"),
                name="Fer",
                country="México",
                active=False,
                created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
                last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
            )
        ]

    def create_new_restaurant_business_account(
        self,
        restaurant_business_id: UUID,
        account: Optional[RestaurantBusinessAccount] = None,
    ) -> bool:
        """_summary_

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            account (Optional[RestaurantBusinessAccount], optional): Restaurant business account model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the creation is done
        """
        if restaurant_business_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            raise GQLApiException(
                msg="Error creating supplier business account legal info",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        if restaurant_business_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1676"):
            return False

        return True

    def update_restaurant_business_account(
        self,
        restaurant_business_id: UUID,
        account: Optional[RestaurantBusinessAccount] = None,
    ) -> bool:
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            restaurant_business_id (UUID): unique restaurant business id
            account (Optional[RestaurantBusinessAccount], optional): Restaurant business account model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """
        if restaurant_business_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            raise GQLApiException(
                msg="Error updating restaurant business account legal info",
                error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
            )
        if restaurant_business_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1676"):
            return False

        return True

    def get_restaurant_business_account(
        self, restaurant_business_id: UUID
    ) -> RestaurantBusinessAccount:  # type: ignore
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.
            restaurant_business_id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            RestaurantBusinessAccount: Restaurant business account model.
        """
        if restaurant_business_id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
            raise GQLApiException(
                msg="Get Restaurant business account legal infonull",
                error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_EMPTY_RECORD.value,
            )

        return RestaurantBusinessAccount(
            restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            business_type=RestaurantBusinessType.CAFE,
            # incorporation_file=BytesIO(b"dfdfa"),
            legal_rep_name="Fernando Reyes",
            # legal_rep_id="RERF999999YYY",
            legal_address="Yunque8",
            phone_number="1122223333",
            email="Fernando@alima.la",
            website="alima.la",
            mx_sat_regimen="sat",
            mx_sat_rfc="SarRFC",
            # mx_sat_csf=BytesIO(b"dfdfa"),
            # employee_directory: Optional[List[RestaurantEmployeeInfo]]
            # Branch details
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        )
