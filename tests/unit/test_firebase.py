from firebase_admin import App as FirebaseApp

from gqlapi.auth import initialize_firebase
from gqlapi.config import FIREBASE_SERVICE_ACCOUNT
from gqlapi.repository.user.firebase import MockTokenRepository


def test_firebase_admin_init_ok():
    _app = initialize_firebase(FIREBASE_SERVICE_ACCOUNT)
    assert isinstance(_app, FirebaseApp), "Error: Firebase App not initialized"


def test_firebase_admin_init_error():
    try:
        fake_creds = '{"user": "fake}'
        initialize_firebase(fake_creds)
    except Exception as e:
        assert isinstance(
            e, ValueError | FileNotFoundError), "Error: Unexpected Firebase App error"


def test_firebase_token_verif_handler_with_mock_ok():
    mock_token = 'osdfipdfjdspfij'
    mock_repo = MockTokenRepository()
    _creds = mock_repo.verify_token(mock_token)
    assert ('token' in _creds and _creds['token'] == mock_token)
