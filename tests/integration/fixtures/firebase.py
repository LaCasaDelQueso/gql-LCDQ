import logging
import pytest

from gqlapi.lib.clients.clients.firebaseapi.firebase_auth import FirebaseAuthApi
from gqlapi.auth import initialize_firebase
from gqlapi.config import FIREBASE_SERVICE_ACCOUNT, FIREBASE_SECRET_KEY


@pytest.fixture(scope="session")
def setup_fb_admin():
    _fb = initialize_firebase(FIREBASE_SERVICE_ACCOUNT)
    logging.debug('Test Firebase connected')
    yield {'firebase': _fb}
    logging.debug('Test Firebase disconnected')


@pytest.fixture(scope="session")
def setup_fb_auth():
    _fb = FirebaseAuthApi(FIREBASE_SECRET_KEY)
    logging.debug('Test Firebase Auth connected')
    yield {'firebase': _fb}
    logging.debug('Test Firebase Auth disconnected')
