from datetime import datetime
from typing import Optional
from uuid import UUID

from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountInput,
    RestaurantBusinessGQL,
    RestaurantBusinessHandlerInterface,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBusiness, RestaurantBusinessAccount
from gqlapi.domain.models.v2.utils import RestaurantBusinessType


class MockRestaurantBusinessHandler(RestaurantBusinessHandlerInterface):
    def new_restaurant_business(
        self,
        name: str,
        country: str,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessGQL:
        """_summary_

        Args:
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
            RestaurantBusinessComplete: Restaurant bussines + restaurant business account model
            }
        """
        restaurant_business = {
            "id": UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
            "name": "Fer",
            "country": "México",
            "active": True,
            "created_at": datetime(2023, 4, 27, 12, 11, 41, 369194),
            "last_updated": datetime(2023, 4, 27, 12, 11, 41, 369194),
        }

        restaurant_business["account"] = RestaurantBusinessAccount(
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
        return RestaurantBusinessGQL(**restaurant_business)

    def edit_restaurant_business(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
        account_input: Optional[RestaurantBusinessAccountInput] = None,
    ) -> RestaurantBusinessGQL:  # type: ignore
        """_summary_

        Args:
            id (UUID): unique restaurant business id
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
            RestaurantBusinessComplete: Restaurant bussines + restaurant business account model
        """
        # update

        restaurant_business = {
            "id": UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
            "name": "Fer",
            "country": "México",
            "active": True,
            "created_at": datetime(2023, 4, 27, 12, 11, 41, 369194),
            "last_updated": datetime(2023, 4, 27, 12, 11, 41, 369194),
        }

        restaurant_business["account"] = RestaurantBusinessAccount(
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
        return RestaurantBusinessGQL(**restaurant_business)

    def fetch_restaurant_business(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> RestaurantBusiness:
        """_summary_

        Args:
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.

        Returns:
            List[RestaurantBusiness]: restaurant business model list
        """

        return RestaurantBusiness(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e"),
            name="Fer",
            country="México",
            active=False,
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        )
