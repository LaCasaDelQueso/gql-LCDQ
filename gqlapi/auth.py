import logging
from typing import Any, Dict

from starlette.authentication import (
    AuthenticationBackend,
    AuthCredentials,
    SimpleUser,
    AuthenticationError,
)
from firebase_admin import auth as fb_auth
from firebase_admin import credentials
from firebase_admin import initialize_app
from firebase_admin import App as FirebaseApp

from gqlapi.domain.models.v2.utils import AlimaCustomerType
from gqlapi.domain.interfaces.v2.authos.ecommerce_session import (
    AuthosTokenHandlerInterface,
)
from gqlapi.domain.interfaces.v2.user.firebase import FirebaseTokenRepositoryInterface


def initialize_firebase(fb_service_account: str) -> FirebaseApp:
    """Firebase Initialization

    Raises
    ------
    IOERROR: Not found Credentials
    ValueError: Invalid Credentials

    Returns
    -------
    FirebaseApp
        _description_
    """
    try:
        cred = credentials.Certificate(fb_service_account)
        return initialize_app(cred)
    except Exception as err:
        logging.warning("Could not connect to Firebase")
        logging.error(err)
        raise err


class AlimaRestoUser(SimpleUser):
    def __init__(self, user: Dict[str, Any]) -> None:
        super().__init__(user["info"].firebase_id)
        self.firebase_user = user["info"]
        self.user_type = AlimaCustomerType.DEMAND


class AlimaSupplyUser(SimpleUser):
    def __init__(self, user: Dict[str, Any]) -> None:
        super().__init__(user["info"].firebase_id)
        self.firebase_user = user["info"]
        self.user_type = AlimaCustomerType.SUPPLY


class AlimaDriverUser(SimpleUser):
    def __init__(self, user: Dict[str, Any]) -> None:
        super().__init__(user["info"].firebase_id)
        self.firebase_user = user["info"]
        self.user_type = AlimaCustomerType.LOGISTICS


class AlimaEmployeeUser(SimpleUser):
    def __init__(self, user: Dict[str, Any]) -> None:
        super().__init__(user["info"].firebase_id)
        self.firebase_user = user["info"]
        self.user_type = AlimaCustomerType.INTERNAL_USER


class AuthosEcommerceUser(SimpleUser):
    def __init__(self, user: Dict[str, Any]) -> None:
        super().__init__(user["info"].id)
        self.authos_user = user["info"]
        self.authos_session = user["token"]
        self.user_type = AlimaCustomerType.B2B_ECOMMERCE


class AlimaAuthBackend(AuthenticationBackend):
    def __init__(
        self,
        auth_repo: FirebaseTokenRepositoryInterface,
        authos_token_handler: AuthosTokenHandlerInterface,
    ) -> None:
        super().__init__()
        self.repo = auth_repo
        self.authos_token_handler = authos_token_handler

    async def authenticate(self, request):
        if "Authorization" not in request.headers:
            return
        _auth = request.headers["Authorization"]
        try:
            scheme, credentials = _auth.split()
            if scheme.lower() == "restobasic":
                # alima restaurant validation
                decoded = self.repo.verify_token(credentials)
                return AuthCredentials(["authenticated"]), AlimaRestoUser(decoded)
            if scheme.lower() == "supplybasic":
                # alima supplier validation
                decoded = self.repo.verify_token(credentials)
                return AuthCredentials(["authenticated"]), AlimaSupplyUser(decoded)
            if scheme.lower() == "driverbasic":
                # alima driver validation
                decoded = self.repo.verify_token(credentials)
                return AuthCredentials(["authenticated"]), AlimaDriverUser(decoded)
            if scheme.lower() == "employeebasic":
                # alima employee validation
                decoded = self.repo.verify_token(credentials)
                return AuthCredentials(["authorized_employee"]), AlimaEmployeeUser(
                    decoded
                )
            if scheme.split("-")[0].lower() == "ecbasic":
                # authos ecommerce validation
                secret_key = scheme.split("-")[1]
                decoded = await self.authos_token_handler.verify_token(
                    credentials, secret_key, False
                )
                if decoded["info"] is None:
                    return
                return AuthCredentials(["authenticated"]), AuthosEcommerceUser(decoded)
            else:
                return
        except (
            ValueError,
            UnicodeDecodeError,
            fb_auth.InvalidIdTokenError,
            fb_auth.ExpiredIdTokenError,
        ) as exc:
            logging.warning("Could not Authenticate User")
            logging.error(exc)
            raise AuthenticationError("Invalid basic auth credentials")
        except Exception as e:
            logging.warning("Unexpected error at Authenticate User")
            logging.error(e)
            raise AuthenticationError("Unexpected error")
