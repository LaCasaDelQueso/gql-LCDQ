import logging
from queue import Empty
from gqlapi.domain.models.v2.utils import NotificationChannelType
from gqlapi.errors import GQLApiException
from uuid import UUID
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from .mock.handler import MockSupplierBusinessHandler
from .mock.repository import MockSupplierBusinessRepository


def test_post_supplier_business_handler_with_mock_ok():
    _handler = MockSupplierBusinessHandler()
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    _resp = _handler.new_supplier_business(name, country, notification_preference)
    assert _resp == SupplierBusiness(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="fer",
        country="México",
        active=True,
        notification_preference=NotificationChannelType.EMAIL,
    )


def test_post_supplier_business_handler_with_mock_active():
    _handler = MockSupplierBusinessHandler()
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    _resp = _handler.new_supplier_business(name, country, notification_preference)
    assert _resp != SupplierBusiness(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="fer",
        country="México",
        active=False,
        notification_preference=NotificationChannelType.EMAIL,
    )


def test_post_supplier_business_repo_with_mock_ok():
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    mock_repo = MockSupplierBusinessRepository()
    supplier_business = mock_repo.new(
        name, country, notification_preference
    )
    assert supplier_business == SupplierBusiness(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="fer",
        country="México",
        active=True,
        notification_preference=NotificationChannelType.EMAIL,
    )


def test_post_supplier_business_repo_error_notification_preference_value():
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    mock_repo = MockSupplierBusinessRepository()
    supplier_business = mock_repo.new(
        name, country, notification_preference
    )
    assert supplier_business != SupplierBusiness(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="fer",
        country="México",
        active=False,
        notification_preference=NotificationChannelType.SMS,
    )


def test_supplier_business_repo_exception_error():
    try:
        name = "error"
        country = "México"
        notification_preference = NotificationChannelType.EMAIL
        mock_repo = MockSupplierBusinessRepository()
        supplier_business = mock_repo.new(
            name, country, notification_preference
        )
        logging.debug(supplier_business)
    except GQLApiException as e:
        assert (
            e.msg == "Error creating supplier business" and e.error_code.value == 1001
        )


def test_update_supplier_business_handler_with_mock_ok():
    _handler = MockSupplierBusinessHandler()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    _resp = _handler.edit_supplier_business(id, name, country, notification_preference)
    assert _resp == SupplierBusiness(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="fercho",
        country="México",
        active=True,
        notification_preference=NotificationChannelType.EMAIL,
    )


def test_update_supplier_business_handler_with_mock_active():
    _handler = MockSupplierBusinessHandler()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    _resp = _handler.edit_supplier_business(id, name, country, notification_preference)
    assert _resp != SupplierBusiness(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="fer",
        country="México",
        active=False,
        notification_preference=NotificationChannelType.EMAIL,
    )


def test_update_supplier_business_repo_with_mock_ok():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    name = "fer"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    mock_repo = MockSupplierBusinessRepository()
    supplier_business = mock_repo.update(
        id, name, country, notification_preference
    )
    if supplier_business:
        assert True


def test_update_supplier_business_repo_with_mock_error():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    name = "false"
    country = "México"
    notification_preference = NotificationChannelType.EMAIL
    mock_repo = MockSupplierBusinessRepository()
    supplier_business = mock_repo.update(
        id, name, country, notification_preference
    )
    if not supplier_business:
        assert True


def test_update_supplier_business_repo_error():
    try:
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        name = "error"
        country = "México"
        notification_preference = NotificationChannelType.EMAIL
        mock_repo = MockSupplierBusinessRepository()
        supplier_business = mock_repo.update(
            id, name, country, notification_preference
        )
        logging.debug(supplier_business)
    except GQLApiException as e:
        assert (
            e.msg == "Error updating supplier business" and e.error_code.value == 1003
        )


def test_get_supplier_business_repo_with_mock_ok():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    mock_repo = MockSupplierBusinessRepository()
    supplier_business = mock_repo.get(id)
    if supplier_business is not Empty:
        assert True


def test_get_supplier_business_repo_with_mock_error():
    try:
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e")
        mock_repo = MockSupplierBusinessRepository()
        supplier_business = mock_repo.get(id)
        logging.debug(supplier_business)
    except GQLApiException as e:
        assert (
            e.msg == "Get Supplier business account null" and e.error_code.value == 1005
        )


def test_get_supplier_business_repo_with_mock_empty():
    try:
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        mock_repo = MockSupplierBusinessRepository()
        supplier_business = mock_repo.get(id)
        logging.debug(supplier_business)
    except GQLApiException as e:
        assert e.msg == "Get Supplier business null" and e.error_code.value == 1004


# def test_post_supplier_business_account_handler_with_mock_ok():
#     supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#     legal_rep_name = "Fernando"
#     legal_rep_id = "123456789"
#     legal_address = "Calle San Mateo"
#     mock_repo = MockSupplierBusinessAccountRepository()
#     supplier_business_account = mock_repo.upload_new_supplier_business_account(
#         supplier_business_id, legal_rep_name, legal_rep_id, legal_address
#     )
#     assert supplier_business_account == SupplierBusinessAccount(
#         supplier_business_id=UUID("d95db285-a30c-4281-bcb6-fb83c2c16367"),
#         business_type=None,
#         incorporation_file=None,
#         legal_rep_name="Fercnando",
#         legal_rep_id="123456789",
#         legal_address="Calle San Mateo",
#         phone_number=None,
#         email=None,
#         website=None,
#         mx_sat_regimen=None,
#         mx_sat_rfc=None,
#         mx_sat_csf=None,
#         displays_in_marketplace=None,
#         created_at=None,
#         last_updated=None,
#     )


# def test_post_supplier_business_account_handler_error_notification_preference_value():
#     supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#     legal_rep_name = "Fercnando"
#     legal_rep_id = "123456789"
#     legal_address = "Calle San Mateo"
#     mock_repo = MockSupplierBusinessAccountRepository()
#     supplier_business_account = mock_repo.upload_new_supplier_business_account(
#         supplier_business_id,
#         legal_rep_name,
#         legal_rep_id,
#         legal_address,
#     )
#     assert supplier_business_account != SupplierBusinessAccount(
#         supplier_business_id=UUID("d95db285-a30c-4281-bcb6-fb83c2c16367"),
#         business_type=None,
#         incorporation_file=None,
#         legal_rep_name="Error",
#         legal_rep_id="123456789",
#         legal_address="Calle San Mateo",
#         phone_number=None,
#         email=None,
#         website=None,
#         mx_sat_regimen=None,
#         mx_sat_rfc=None,
#         mx_sat_csf=None,
#         default_commercial_conditions=None,
#         displays_in_marketplace=None,
#         employee_directory=None
#         created_at=None,
#         last_updated=None,
#     )


# def test_supplier_business_account_exception_error():
#     try:
#         supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#         legal_rep_name = "Error"
#         legal_rep_id = "123456789"
#         legal_address = "Calle San Mateo"
#         mock_repo = MockSupplierBusinessAccountRepository()
#         supplier_business_account = mock_repo.upload_new_supplier_business_account(
#             supplier_business_id, legal_rep_name, legal_rep_id, legal_address
#         )
#         print(supplier_business_account)
#     except GQLApiException as e:
#         assert (
#             e.msg == "Error creating supplier business account" and e.error_code == 1001
#         )


# def test_update_supplier_business_account_handler_with_mock_ok():
#     supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#     legal_rep_name = "Fernando"
#     legal_rep_id = "123456789"
#     legal_address = "Calle San Mateo"
#     business_type = BusinessType.MORAL_PERSON
#     incorporation_file = None
#     phone_number = "554440000"
#     email = "fer@alima.la"
#     website = "fer.com"
#     mx_sat_regimen = "Regimen"
#     mx_sat_rfc = "ERFSDSDGSGSDG"
#     mx_sat_csf = BytesIO(b"dfdfa")
#     # default_commercial_conditions: Optional[SupplierBusinessMongoCommercialConditions] = None
#     displays_in_marketplace = False
#     # employee_directory: Optional[List[EmployeeInfo]]
#     mock_repo = MockSupplierBusinessAccountRepository()
#     supplier_business_account = mock_repo.update_supplier_business_account(
#         supplier_business_id,
#         legal_rep_name,
#         legal_rep_id,
#         legal_address,
#         business_type,
#         incorporation_file,
#         phone_number,
#         email,
#         website,
#         mx_sat_regimen,
#         mx_sat_rfc,
#         mx_sat_csf,
#         # default_commercial_conditions
#         displays_in_marketplace,
#         # employee_directory
#     )
#     if supplier_business_account:
#         assert True


# def test_update_supplier_business_account_handler_with_mock_error():
#     supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#     legal_rep_name = None
#     legal_rep_id = None
#     legal_address = None
#     business_type = None
#     incorporation_file = None
#     phone_number = None
#     email = None
#     website = None
#     mx_sat_regimen = None
#     mx_sat_rfc = None
#     mx_sat_csf = None
#     # default_commercial_conditions: Optional[SupplierBusinessMongoCommercialConditions] = None
#     displays_in_marketplace = None
#     # employee_directory: Optional[List[EmployeeInfo]]
#     mock_repo = MockSupplierBusinessAccountRepository()
#     supplier_business_account = mock_repo.update_supplier_business_account(
#         supplier_business_id,
#         legal_rep_name,
#         legal_rep_id,
#         legal_address,
#         business_type,
#         incorporation_file,
#         phone_number,
#         email,
#         website,
#         mx_sat_regimen,
#         mx_sat_rfc,
#         mx_sat_csf,
#         # default_commercial_conditions
#         displays_in_marketplace,
#         # employee_directory
#     )
#     if not supplier_business_account:
#         assert True


# def test_update_supplier_business_account_handler_error():
#     try:
#         supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#         legal_rep_name = "Error"
#         legal_rep_id = "123456789"
#         legal_address = "Calle San Mateo"
#         business_type = BusinessType.MORAL_PERSON
#         incorporation_file = None
#         phone_number = "554440000"
#         email = "fer@alima.la"
#         website = "fer.com"
#         mx_sat_regimen = "Regimen"
#         mx_sat_rfc = "ERFSDSDGSGSDG"
#         mx_sat_csf = None
#         # default_commercial_conditions: Optional[SupplierBusinessMongoCommercialConditions] = None
#         displays_in_marketplace = False
#         # employee_directory: Optional[List[EmployeeInfo]]
#         mock_repo = MockSupplierBusinessAccountRepository()
#         supplier_business_account = mock_repo.update_supplier_business_account(
#             supplier_business_id,
#             legal_rep_name,
#             legal_rep_id,
#             legal_address,
#             business_type,
#             incorporation_file,
#             phone_number,
#             email,
#             website,
#             mx_sat_regimen,
#             mx_sat_rfc,
#             mx_sat_csf,
#             # default_commercial_conditions
#             displays_in_marketplace,
#             # employee_directory
#         )
#         logging.debug(supplier_business_account)
#     except GQLApiException as e:
#         assert (
#             e.msg == "Error updating supplier business account legal info"
#             and e.error_code.value == 3003
#         )


# def test_get_supplier_business_account_handler_with_mock_ok():
#     supplier_business_id = UUID("d95db285-a30c-4281-bcb6-fb83c2c16367")
#     mock_repo = MockSupplierBusinessAccountRepository()
#     supplier_business_account = mock_repo.get_supplier_business_account(
#         supplier_business_id
#     )
#     if supplier_business_account is not Empty:
#         assert True


# def test_get_supplier_business_account_handler_with_mock_error():
#     try:
#         supplier_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e")
#         mock_repo = MockSupplierBusinessAccountRepository()
#         supplier_business_account = mock_repo.get_supplier_business_account(
#             supplier_business_id
#         )
#         logging.debug(supplier_business_account)
#     except GQLApiException as e:
#         assert (
#             e.msg == "Get Supplier business account null" and e.error_code.value == 3005
#         )


# def test_get_supplier_business_account_handler_with_mock_empty():
#     try:
#         supplier_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
#         mock_repo = MockSupplierBusinessAccountRepository()
#         supplier_business_account = mock_repo.get_supplier_business_account(
#             supplier_business_id
#         )
#         logging.debug(supplier_business_account)
#     except GQLApiException as e:
#         assert e.msg == "Get Supplier business account" and e.error_code.value == 3004
