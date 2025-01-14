from typing import Any, Dict
from datetime import datetime, timedelta
import uuid
from firebase_admin import App as FirebaseApp
from firebase_admin.auth import Client as FirebaseAuthClient
from gqlapi.domain.interfaces.v2.user import FirebaseTokenRepositoryInterface
from gqlapi.domain.models.v2.core import CoreUser


class MockTokenRepository(FirebaseTokenRepositoryInterface):
    def verify_token(self, token: str) -> Dict[Any, Any]:
        """ Verify token is valid in Firebase

        Parameters
        ----------
        token : str
            Session Token

        Returns
        -------
        Dict[Any, Any]
            Firebase response
        """
        return {
            'token': token,
            'is_valid': True,
            'valid_until': (datetime.utcnow() + timedelta(days=7)),
            'info': CoreUser(
                id=uuid.uuid4(),
                first_name='Test', last_name='User',
                email='test@user.com', phone_number='5566778899',
                firebase_id='340598001',
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
        }


class FirebaseTokenRepository(FirebaseTokenRepositoryInterface):
    def __init__(self, fire_app: FirebaseApp) -> None:
        self._fb_client = FirebaseAuthClient(fire_app)

    @property
    def fb_client(self) -> FirebaseAuthClient:
        return self._fb_client

    def verify_token(self, token: str) -> Dict[Any, Any]:
        """ Verify token is valid in Firebase

        Parameters
        ----------
        token : str
            Session Token

        Returns
        -------
        Dict[Any, Any]
            Firebase response
        """
        token_verif = self.fb_client.verify_id_token(token)
        display_name = token_verif.get('displayName', '').split(' ')
        return {
            'token': token,
            'is_valid': True,
            'valid_until': datetime.fromtimestamp(token_verif['exp']),
            'info': CoreUser(
                first_name=display_name[0],
                last_name=display_name[1] if len(display_name) >= 2 else '',
                email=token_verif['email'],
                firebase_id=token_verif['uid'],
            )
        }
