from datetime import datetime
# from io import BytesIO
import logging
from queue import Empty
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessComplete,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBusiness, RestaurantBusinessAccount
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from gqlapi.domain.models.v2.utils import BusinessType, RestaurantBusinessType
from gqlapi.errors import GQLApiException
from gqlapi.handlers.restaurant.restaurant_business import MockRestaurantBusinessHandler
from gqlapi.repository.restaurant.restaurant_business import (
    MockRestaurantBusinessRepository,
)


def test_post_restaurant_business_repo_with_mock_ok():
    name = "fer"
    country = "México"
    mock_repo = MockRestaurantBusinessRepository()
    rest_business = mock_repo.new(name, country)
    assert rest_business == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")


def test_post_restaurant_business_repo_type():
    name = "fer"
    country = "México"
    mock_repo = MockRestaurantBusinessRepository()
    rest_business = mock_repo.new(name, country)
    assert isinstance(rest_business, UUID)


def test_restaurant_business_repo_exception_error():
    try:
        name = "error"
        country = "México"
        mock_repo = MockRestaurantBusinessRepository()
        rest_business = mock_repo.new(name, country)
        logging.debug(rest_business)
    except GQLApiException as e:
        assert e.msg == "Get Restaurant business null" and e.error_code == 1005


def test_update_restaurant_business_repo_with_mock_ok():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    name = "fer"
    country = "México"
    active = True
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business = mock_repo.update(
        id, name, country, active
    )
    if restaurant_business:
        assert True


def test_update_restaurant_business_repo_with_mock_false():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    name = "false"
    country = "México"
    active = True
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business = mock_repo.update(
        id, name, country, active
    )
    if not restaurant_business:
        assert True


def test_update_restaurant_business_repo_error():
    try:
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        name = "Error"
        country = "México"
        active = True
        mock_repo = MockRestaurantBusinessRepository()
        restaurant_business = mock_repo.update(
            id, name, country, active
        )
        logging.debug(restaurant_business)
    except GQLApiException as e:
        assert e.msg == "Error updating restaurant business" and e.error_code == 1003


def test_get_restaurant_business_repo_with_mock_not_model():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business = mock_repo.get(id)
    if restaurant_business is not SupplierBusiness:
        assert True


def test_get_restaurant_business_repo_with_mock_ok():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business = mock_repo.get(id)
    assert restaurant_business == {
        "id": UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
        "name": "Fer",
        "country": "México",
        "active": True,
        "created_at": datetime(2023, 4, 27, 12, 11, 41, 369194),
        "last_updated": datetime(2023, 4, 27, 12, 11, 41, 369194),
    }


def test_get_restaurant_business_repo_with_mock_empty():
    try:
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a")
        mock_repo = MockRestaurantBusinessRepository()
        restaurant_business = mock_repo.get(id)
        logging.debug(restaurant_business)
    except GQLApiException as e:
        assert e.msg == "Get Restaurant Business null" and e.error_code == 1005


def test_get_restaurant_businesses_repo_with_mock_empty():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e")
    mock_repo = MockRestaurantBusinessRepository()
    name = "Fer"
    restaurants_business = mock_repo.get_restaurant_businesses(id, name)
    if restaurants_business is not Empty:
        assert True


def test_get_restaurant_businesses_repo_with_mock_ok():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e")
    mock_repo = MockRestaurantBusinessRepository()
    name = "Fer"
    restaurant_business = mock_repo.get_restaurant_businesses(id, name)
    assert restaurant_business == [
        RestaurantBusiness(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e"),
            name="Fer",
            country="México",
            active=False,
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        )
    ]


def test_get_restaurant_businesses_repo_with_mock_empty_error():
    try:
        mock_repo = MockRestaurantBusinessRepository()
        supplier_business = mock_repo.get_restaurant_businesses()
        logging.debug(supplier_business)
    except GQLApiException as e:
        assert e.msg == "Get Restaurant Business" and e.error_code == 1004


def test_create_restaurant_business_account_repo_with_mock_ok():
    restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business_account = mock_repo.create_new_restaurant_business_account(
        restaurant_business
    )
    if restaurant_business_account:
        assert True


def test_create_restaurant_business_account_repo_with_mock_false():
    restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1676")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business_account = mock_repo.create_new_restaurant_business_account(
        restaurant_business
    )
    if not restaurant_business_account:
        assert True


def test_create_restaurant_business_account_repo_error():
    try:
        restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        mock_repo = MockRestaurantBusinessRepository()
        restaurant_business_account = mock_repo.create_new_restaurant_business_account(
            restaurant_business
        )
        logging.debug(restaurant_business_account)
    except GQLApiException as e:
        assert (
            e.msg == "Error creating supplier business account legal info"
            and e.error_code == 3001
        )


def test_update_restaurant_business_account_repo_with_mock_ok():
    restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business_account = mock_repo.update_restaurant_business_account(
        restaurant_business
    )
    if restaurant_business_account:
        assert True


def test_update_restaurant_business_account_repo_with_mock_false():
    restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1676")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business_account = mock_repo.update_restaurant_business_account(
        restaurant_business
    )
    if not restaurant_business_account:
        assert True


def test_update_restaurant_business_account_repo_error():
    try:
        restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        mock_repo = MockRestaurantBusinessRepository()
        restaurant_business_account = mock_repo.update_restaurant_business_account(
            restaurant_business
        )
        logging.debug(restaurant_business_account)
    except GQLApiException as e:
        assert (
            e.msg == "Error updating restaurant business account legal info"
            and e.error_code == 3003
        )


def test_get_restaurant_business_account_repo_with_mock_ok():
    restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business_account = mock_repo.get_restaurant_business_account(
        restaurant_business
    )
    assert restaurant_business_account == RestaurantBusinessAccount(
        restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
        business_type=BusinessType.PHYSICAL_PERSON,
        # incorporation_file=BytesIO(b"dfdfa"),
        legal_rep_name="Fernando Reyes",
        legal_rep_id="RERF999999YYY",
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


def test_get_restaurant_business_account_repo_with_mock_type():
    restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1676")
    mock_repo = MockRestaurantBusinessRepository()
    restaurant_business_account = mock_repo.get_restaurant_business_account(
        restaurant_business
    )
    assert isinstance(restaurant_business_account, RestaurantBusinessAccount)


def test_get_restaurant_business_account_repo_error():
    try:
        restaurant_business = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        mock_repo = MockRestaurantBusinessRepository()
        restaurant_business_account = mock_repo.get_restaurant_business_account(
            restaurant_business
        )
        logging.debug(restaurant_business_account)
    except GQLApiException as e:
        assert (
            e.msg == "Get Restaurant business account legal infonull"
            and e.error_code == 3005
        )


def test_post_restaurant_businessa_account_handler_with_mock_ok():
    _handler = MockRestaurantBusinessHandler()
    name = "fer"
    country = "México"
    _resp = _handler.new_restaurant_business(name, country)
    assert _resp == RestaurantBusinessComplete(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
        name="Fer",
        country="México",
        active=True,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        account=RestaurantBusinessAccount(
            restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            business_type=RestaurantBusinessType.CAFE,
            # incorporation_file=BytesIO(b"dfdfa"),
            legal_rep_name="Fernando Reyes",
            legal_rep_id="RERF999999YYY",
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
        ),
    )


def test_post_restaurant_business_account_handler_with_mock_name():
    _handler = MockRestaurantBusinessHandler()
    name = "fer"
    country = "México"
    _resp = _handler.new_restaurant_business(name, country)
    assert _resp != RestaurantBusinessComplete(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
        name="name",
        country="México",
        active=True,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        account=RestaurantBusinessAccount(
            restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            business_type=RestaurantBusinessType.HOTEL,
            # incorporation_file=BytesIO(b"dfdfa"),
            legal_rep_name="Fernando Reyes",
            legal_rep_id="RERF999999YYY",
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
        ),
    )


def test_update_restaurant_businessa_account_handler_with_mock_ok():
    _handler = MockRestaurantBusinessHandler()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "fer"
    country = "México"
    _resp = _handler.edit_restaurant_business(id, name, country)
    assert _resp == RestaurantBusinessComplete(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
        name="Fer",
        country="México",
        active=True,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        account=RestaurantBusinessAccount(
            restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            business_type=RestaurantBusinessType.CAFE,
            # incorporation_file=BytesIO(b"dfdfa"),
            legal_rep_name="Fernando Reyes",
            legal_rep_id="RERF999999YYY",
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
        ),
    )


def test_update_restaurant_business_account_handler_with_mock_name():
    _handler = MockRestaurantBusinessHandler()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "fer"
    country = "México"
    _resp = _handler.edit_restaurant_business(id, name, country)
    assert _resp != RestaurantBusinessComplete(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da167a"),
        name="name",
        country="México",
        active=True,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        account=RestaurantBusinessAccount(
            restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            business_type=BusinessType.PHYSICAL_PERSON,
            # incorporation_file=BytesIO(b"dfdfa"),
            legal_rep_name="Fernando Reyes",
            legal_rep_id="RERF999999YYY",
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
        ),
    )
