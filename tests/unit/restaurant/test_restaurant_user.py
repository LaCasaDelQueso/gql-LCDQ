from datetime import datetime
import logging
from uuid import UUID
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantUserGQL,
    # RestaurantUserPermCont,
)
from gqlapi.domain.models.v2.core import CoreUser, RestaurantEmployeeInfo
from gqlapi.domain.models.v2.restaurant import RestaurantUserPermission
from gqlapi.errors import GQLApiException
from gqlapi.repository.restaurant.restaurant_user import (
    MockRestaurantEmployeeRepository,
    MockRestaurantUserPermissionRepository,
    MockRestaurantUserRepository,
)
from pyparsing import Empty


def test_post_restaurant_user_repo_with_mock_ok():
    mock_repo = MockRestaurantUserRepository()
    first_name = "fer"
    last_name = "reyes"
    email = "fer@alima.la"
    phone_number = "5544440000"
    firebase_id = "firebaseid"
    role = "jefe"
    _resp = mock_repo.new(
        first_name, last_name, email, phone_number, firebase_id, role
    )
    assert isinstance(_resp, UUID)


def test_post_restaurant_user_repo_with_mock_type():
    mock_repo = MockRestaurantUserRepository()
    first_name = "fer"
    last_name = "reyes"
    email = "fer@alima.la"
    phone_number = "5544440000"
    firebase_id = "firebaseid"
    role = "jefe"
    _resp = mock_repo.new(
        first_name, last_name, email, phone_number, firebase_id, role
    )
    assert not isinstance(_resp, str)


def test_post_restaurant_user_repo_with_mock_error():
    try:
        mock_repo = MockRestaurantUserRepository()
        first_name = "fer"
        last_name = "reyes"
        email = "fer@neutro.la"
        phone_number = "5544440000"
        firebase_id = "firebaseid"
        role = "jefe"
        _resp = mock_repo.new(
            first_name, last_name, email, phone_number, firebase_id, role
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Error to build restauratn user" and e.error_code == 1001


def test_update_restaurant_user_repo_with_mock_ok():
    mock_repo = MockRestaurantUserRepository()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    first_name = "fer"
    last_name = "reyes"
    phone_number = "5544440000"
    role = "jefe"
    _resp = mock_repo.update_restaurant_user(
        id, first_name, last_name, phone_number, role
    )
    if _resp:
        assert True


def test_update_restaurant_user_repo_with_mock_false():
    mock_repo = MockRestaurantUserRepository()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    first_name = "false"
    last_name = "reyes"
    phone_number = "5544440000"
    role = "jefe"
    _resp = mock_repo.update_restaurant_user(
        id, first_name, last_name, phone_number, role
    )
    if not _resp:
        assert True


def test_update_restaurant_user_repo_with_mock_error():
    try:
        mock_repo = MockRestaurantUserRepository()
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        first_name = "error"
        last_name = "reyes"
        phone_number = "5544440000"
        role = "jefe"
        _resp = mock_repo.update_restaurant_user(
            id, first_name, last_name, phone_number, role
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Error updating restaurant user" and e.error_code == 1003


def test_get_restaurant_user_repo_with_mock_not_empty():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    mock_repo = MockRestaurantUserRepository()
    supplier_business = mock_repo.get(id)
    if supplier_business is not Empty:
        assert True


def test_get_restaurant_user_repo_with_mock_ok():
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    mock_repo = MockRestaurantUserRepository()
    supplier_business = mock_repo.get(id)
    assert supplier_business == RestaurantUserGQL(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        core_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        role="jefe",
        enabled=True,
        deleted=True,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        user=CoreUser(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
            first_name="Fer,",
            last_name="reyes",
            email="fer@alima.la",
            phone_number="1234567890",
            firebase_id="123",
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        ),
    )


def test_get_restaurant_user_repo_with_mock_empty():
    try:
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673")
        mock_repo = MockRestaurantUserRepository()
        supplier_business = mock_repo.get(id)
        logging.debug(supplier_business)
    except GQLApiException as e:
        assert e.msg == "Get Restaurant User" and e.error_code == 1004


def test_delete_restaurant_user_repo_with_mock_ok():
    mock_repo = MockRestaurantUserRepository()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    _resp = mock_repo.delete(id, True)
    if _resp:
        assert True


def test_delete_restaurant_user_repo_with_mock_false():
    mock_repo = MockRestaurantUserRepository()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673")
    _resp = mock_repo.delete(id, True)
    if not _resp:
        assert True


def test_delete_restaurant_user_repo_with_mock_error():
    try:
        mock_repo = MockRestaurantUserRepository()
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        _resp = mock_repo.delete(id, True)
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Error updating restaurant user" and e.error_code == 1003


def test_activate_restaurant_user_repo_with_mock_ok():
    mock_repo = MockRestaurantUserRepository()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    _resp = mock_repo.activate_desactivate(id, True)
    if _resp:
        assert True


def test_activate_restaurant_user_repo_with_mock_false():
    mock_repo = MockRestaurantUserRepository()
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673")
    _resp = mock_repo.activate_desactivate(id, True)
    if not _resp:
        assert True


def test_activate_restaurant_user_repo_with_mock_error():
    try:
        mock_repo = MockRestaurantUserRepository()
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        _resp = mock_repo.activate_desactivate(id, True)
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Error updating restaurant user" and e.error_code == 1003


def test_create_restaurant_user_employee_repo_with_mock_ok():
    mock_repo = MockRestaurantUserRepository()
    core_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "Fer"
    last_name = "Reyes"
    phone_number = "1234123455"
    email = "Fercho@alima.la"
    _resp = mock_repo.create_restaurant_user_employee(
        restaurant_business_id, core_user_id, name, last_name, phone_number, email
    )
    if _resp:
        assert True


def test_create_restaurant_user_employee_repo_with_mock_false():
    mock_repo = MockRestaurantUserRepository()
    core_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "false"
    last_name = "Reyes"
    phone_number = "1234123455"
    email = "Fercho@alima.la"
    _resp = mock_repo.create_restaurant_user_employee(
        restaurant_business_id, core_user_id, name, last_name, phone_number, email
    )
    if not _resp:
        assert True


def test_create_restaurant_user_employee_with_mock_error():
    try:
        mock_repo = MockRestaurantUserRepository()
        core_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        name = "error"
        last_name = "Reyes"
        phone_number = "1234123455"
        email = "Fercho@alima.la"
        _resp = mock_repo.create_restaurant_user_employee(
            restaurant_business_id, core_user_id, name, last_name, phone_number, email
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert (
            e.msg == "Error creating restaurant employee info" and e.error_code == 3001
        )


def test_update_restaurant_user_employee_repo_with_mock_ok():
    mock_repo = MockRestaurantUserRepository()
    core_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "Fer"
    last_name = "Reyes"
    department = "Tech"
    phone_number = "1234123455"
    role = "Jefe"
    _resp = mock_repo.update_restaurant_user_employee(
        restaurant_business_id,
        core_user_id,
        name,
        last_name,
        department,
        role,
        phone_number,
    )
    if _resp:
        assert True


def test_update_restaurant_user_employee_repo_with_mock_false():
    mock_repo = MockRestaurantUserRepository()
    core_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "false"
    last_name = "Reyes"
    department = "Tech"
    phone_number = "1234123455"
    role = "Jefe"
    _resp = mock_repo.update_restaurant_user_employee(
        restaurant_business_id,
        core_user_id,
        name,
        last_name,
        department,
        role,
        phone_number,
    )
    if not _resp:
        assert True


def test_update_restaurant_user_employee_with_mock_error():
    try:
        mock_repo = MockRestaurantUserRepository()
        core_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        _resp = mock_repo.update_restaurant_user_employee(
            restaurant_business_id, core_user_id
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Error updating restaurant employee" and e.error_code == 3003


def test_create_restaurant_user_perm_repo_with_mock_ok():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    display_orders_section = False
    display_suppliers_section = False
    display_products_section = False

    _resp = mock_repo.new(
        restaurant_user_id,
        restaurant_business_id,
        display_orders_section,
        display_suppliers_section,
        display_products_section,
    )
    if _resp:
        assert True


def test_create_restaurant_user_perm_repo_with_mock_false():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    display_orders_section = False
    display_suppliers_section = False
    display_products_section = False

    _resp = mock_repo.new(
        restaurant_user_id,
        restaurant_business_id,
        display_orders_section,
        display_suppliers_section,
        display_products_section,
    )
    if not _resp:
        assert True


def test_create_restaurant_user_perm_with_mock_error():
    try:
        mock_repo = MockRestaurantUserPermissionRepository()
        restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673")
        restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        display_orders_section = False
        display_suppliers_section = False
        display_products_section = False

        _resp = mock_repo.new(
            restaurant_user_id,
            restaurant_business_id,
            display_orders_section,
            display_suppliers_section,
            display_products_section,
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert (
            e.msg == "Error creating restaurant user permission"
            and e.error_code == 1001
        )


def test_update_restaurant_user_perm_repo_with_mock_ok():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    display_orders_section = False
    display_suppliers_section = False
    display_products_section = False

    _resp = mock_repo.update(
        restaurant_user_id,
        display_orders_section,
        display_suppliers_section,
        display_products_section,
    )
    if _resp:
        assert True


def test_update_restaurant_user_perm_repo_with_mock_false():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    display_orders_section = False
    display_suppliers_section = False
    display_products_section = False

    _resp = mock_repo.update(
        restaurant_user_id,
        display_orders_section,
        display_suppliers_section,
        display_products_section,
    )
    if not _resp:
        assert True


def test_update_restaurant_user_perm_with_mock_error():
    try:
        mock_repo = MockRestaurantUserPermissionRepository()
        restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1673")
        display_orders_section = False
        display_suppliers_section = False
        display_products_section = False

        _resp = mock_repo.update(
            restaurant_user_id,
            display_orders_section,
            display_suppliers_section,
            display_products_section,
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert (
            e.msg == "Error updating restaurant user permission"
            and e.error_code == 1003
        )


def test_get_restaurant_user_perm_repo_with_mock_ok():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    _resp = mock_repo.get(restaurant_user_id)
    assert _resp == RestaurantUserPermission(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
        restaurant_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
        display_orders_section=False,
        display_suppliers_section=False,
        display_products_section=False,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
    )


def test_get_restaurant_user_perm_repo_with_mock_type():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    _resp = mock_repo.get(restaurant_user_id)
    assert _resp != RestaurantUserPermission(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
        restaurant_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
        display_orders_section=True,
        display_suppliers_section=True,
        display_products_section=True,
        created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
        last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
    )


def test_get_restaurant_user_perm_repo_with_mock_error():
    try:
        mock_repo = MockRestaurantUserPermissionRepository()
        restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        _resp = mock_repo.get(restaurant_user_id)
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Get Restaurant User Permission" and e.error_code == 1004


def test_get_restaurant_user_perm_and_contact_repo_with_mock_ok():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    _resp = mock_repo.get_restaurant_user_contact_and_pemission(
        restaurant_business_id)
    assert _resp == [
        RestaurantUserPermission(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            restaurant_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            # core_user_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            display_orders_section=False,
            display_suppliers_section=False,
            display_products_section=False,
            # restaurant_business_id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"),
            # email="Fercho@alima.la",
            # phone_number="0987654321",
            created_at=datetime(2023, 4, 27, 12, 11, 41, 369194),
            last_updated=datetime(2023, 4, 27, 12, 11, 41, 369194),
        )
    ]


def test_get_restaurant_user_perm_and_contact_repo_with_mock_type():
    mock_repo = MockRestaurantUserPermissionRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    _resp = mock_repo.get_restaurant_user_contact_and_pemission(
        restaurant_business_id)
    assert isinstance(_resp, list)


def test_get_restaurant_user_perm_repo_and_contact_with_mock_error():
    try:
        mock_repo = MockRestaurantUserPermissionRepository()
        restaurant_user_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        _resp = mock_repo.get(restaurant_user_id)
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Get Restaurant User Permission" and e.error_code == 1004


def test_create_restaurant_employee_repo_with_mock_ok():
    mock_repo = MockRestaurantEmployeeRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "Fer"
    last_name = "Reyes"
    phone_number = "1234123455"
    email = "Fercho@alima.la"
    department = "Tech"
    position = "Jefe"
    _resp = mock_repo.create_new_restaurant_employee(
        restaurant_business_id,
        name,
        last_name,
        phone_number,
        email,
        department,
        position,
    )
    if _resp == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675"):
        assert True


def test_create_restaurant_employee_repo_with_mock_type():
    mock_repo = MockRestaurantEmployeeRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "Fer"
    last_name = "Reyes"
    phone_number = "1234123455"
    email = "Fercho@alima.la"
    department = "Tech"
    position = "Jefe"
    _resp = mock_repo.create_new_restaurant_employee(
        restaurant_business_id,
        name,
        last_name,
        phone_number,
        email,
        department,
        position,
    )
    assert isinstance(_resp, UUID)


def test_create_restaurant_employee_with_mock_error():
    try:
        mock_repo = MockRestaurantEmployeeRepository()
        restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        name = "Erros"
        last_name = "Reyes"
        phone_number = "1234123455"
        email = "Fercho@alima.la"
        department = "Tech"
        position = "Jefe"
        _resp = mock_repo.create_new_restaurant_employee(
            restaurant_business_id,
            name,
            last_name,
            phone_number,
            email,
            department,
            position,
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert (
            e.msg == "Error creating restaurant employee info" and e.error_code == 3001
        )


def test_update_restaurant_employee_repo_with_mock_ok():
    mock_repo = MockRestaurantEmployeeRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "Fer"
    last_name = "Reyes"
    phone_number = "1234123455"
    email = "Fercho@alima.la"
    department = "Tech"
    position = "Jefe"
    _resp = mock_repo.update_restaurant_employee(
        restaurant_business_id,
        id,
        name,
        last_name,
        phone_number,
        email,
        department,
        position,
    )
    if _resp:
        assert True


def test_update_restaurant_employee_repo_with_mock_false():
    mock_repo = MockRestaurantEmployeeRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
    name = "false"
    last_name = "Reyes"
    phone_number = "1234123455"
    email = "Fercho@alima.la"
    department = "Tech"
    position = "Jefe"
    _resp = mock_repo.update_restaurant_employee(
        restaurant_business_id,
        id,
        name,
        last_name,
        phone_number,
        email,
        department,
        position,
    )
    if not _resp:
        assert True


def test_update_restaurant_employee_with_mock_error():
    try:
        mock_repo = MockRestaurantEmployeeRepository()
        restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        name = "Error"
        last_name = "Reyes"
        phone_number = "1234123455"
        email = "Fercho@alima.la"
        department = "Tech"
        position = "Jefe"
        _resp = mock_repo.update_restaurant_employee(
            restaurant_business_id,
            id,
            name,
            last_name,
            phone_number,
            email,
            department,
            position,
        )
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Error updating restaurant employee" and e.error_code == 3003


def test_get_restaurant_employee_repo_with_mock_ok():
    mock_repo = MockRestaurantEmployeeRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    _resp = mock_repo.get_restaurant_employee(restaurant_business_id, id)
    assert _resp == RestaurantEmployeeInfo(
        id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
        name="Fer",
        last_name="Reyes",
        department="Tech",
        position="Jefe",
        phone_number="1234567800",
        email="fer@alima.la",
    )


def test_get_restaurant_employee_repo_with_mock_type():
    mock_repo = MockRestaurantEmployeeRepository()
    restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
    _resp = mock_repo.get_restaurant_employee(restaurant_business_id, id)
    logging.debug(_resp)
    assert isinstance(_resp, RestaurantEmployeeInfo)


def test_get_rrestaurant_employee_with_mock_error():
    try:
        mock_repo = MockRestaurantEmployeeRepository()
        restaurant_business_id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1675")
        id = UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674")
        _resp = mock_repo.get_restaurant_employee(restaurant_business_id, id)
        logging.debug(_resp)
    except GQLApiException as e:
        assert e.msg == "Get restaurant employee info null" and e.error_code == 3005
