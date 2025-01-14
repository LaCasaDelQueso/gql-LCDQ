import json
import logging
import pytest
from typing import Any, Dict, Optional
from gqlapi import __version__  # noqa
from gqlapi.repository.user.firebase import FirebaseTokenRepository, FirebaseApp  # noqa
import requests  # noqa
from .firebase import setup_fb_admin, setup_fb_auth, FirebaseAuthApi  # noqa
from ..mocks.gqlapi import mock_fb_user
from ..config import url_test

# from lib.logger import get_logger


def fixture_gql_api(
    method: str,
    query: str,
    variables: Optional[Dict[Any, Any]] = None,
    token: Optional[Any] = None,
    authorization: Optional[str] = None,
) -> Any:
    payload = json.dumps({"query": query, "variables": variables})
    headers = {
        "Content-Type": "application/json",
    }
    if authorization and token:
        headers["Authorization"] = f"{authorization} {token}"
    response = requests.request(method, url_test, headers=headers, data=payload)
    resp_js = response.json()
    return resp_js


@pytest.fixture(scope="session")
def test_ficture_firebase_signup_ok_delete_ok(
    setup_fb_auth: Dict[str, FirebaseAuthApi]  # noqa
):
    _fb = setup_fb_auth["firebase"]
    # create user
    usr_creds = _fb.signup_with_email(mock_fb_user["email"], mock_fb_user["password"])
    logging.info(usr_creds)
    logging.debug("Signed up user in firebase")
    # assert data type
    assert isinstance(usr_creds, dict)
    assert usr_creds["email"] == mock_fb_user["email"]
    assert "idToken" in usr_creds
    # yield values
    yield setup_fb_auth
    logging.debug("Closing Firebase Sign up process")
    fback = _fb.delete(usr_creds["idToken"])
    logging.debug(fback)
    assert "Delete" in fback["kind"]


@pytest.fixture(scope="session")
def test_ficture_firebase_signin_ok(
    test_ficture_firebase_signup_ok_delete_ok: Dict[str, FirebaseAuthApi]
):  # noqa
    try:
        _fb = test_ficture_firebase_signup_ok_delete_ok["firebase"]
        usr_creds = _fb.signin_with_email(
            mock_fb_user["email"], mock_fb_user["password"]
        )
        logging.debug("Signed in user in firebase")
        # yield as fixture
        yield {"user": usr_creds}
    except Exception:
        print("False")
