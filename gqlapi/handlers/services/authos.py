from datetime import datetime, timedelta
import json
import logging
from types import NoneType
from typing import Any, Dict, Optional
from uuid import UUID, uuid4
from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    EcommerceUserRestaurantRelationRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountInput,
    RestaurantBusinessHandlerInterface,
)
from gqlapi.domain.models.v2.utils import RestaurantBusinessType

from jose import jwt, JWTError
from passlib.context import CryptContext
from gqlapi.domain.interfaces.v2.authos.ecommerce_pwd import (
    EcommercePassword,
    EcommercePasswordHandlerInterface,
    PwdRestoreRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.authos.ecommerce_user import (
    EcommerceUser,
    EcommerceUserHandlerInterface,
    EcommerceUserRepositoryInterface,
)
from gqlapi.domain.models.v2.authos import IEcommerceUser, IPwdRestore, IUserSession
from gqlapi.domain.interfaces.v2.authos.ecommerce_session import (
    AuthosTokenHandlerInterface,
    EcommerceSession,
    EcommerceSessionHandlerInterface,
    UserSessionRepositoryInterface,
)

from gqlapi.config import AUTHOS_ALGORITHM, AUTHOS_SECRET_KEY, AUTHOS_TOKEN_TTL
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


class EcommerceJWTHandler:
    @staticmethod
    async def decode_jwt(session_token: str) -> Dict[str, Any]:
        """Decode JWT token

        Args:
            session_token (str): Session Token

        Returns:
            Dict[str, Any]: decoded data | empty dict
        """
        try:
            return jwt.decode(
                session_token, AUTHOS_SECRET_KEY, algorithms=[AUTHOS_ALGORITHM]
            )
        except JWTError as e:
            logging.warning("Error decoding JWT token")
            logging.error(e)
        return {}

    @staticmethod
    async def encode_jwt(
        data: Dict[str, Any],
        expires_delta: timedelta,
    ) -> str:
        """Generate JWT token

        Args:
            data (Dict[str, Any]): data to store in the token
            expires_delta (timedelta): expires after given timedelta

        Returns:
            str: JWT Token
        """
        # add expiration
        _expire = datetime.utcnow() + expires_delta
        data.update({"exp": _expire})
        # if exists remove authorization from session data
        if "authorization" in data:
            del data["authorization"]
        # sign token
        enc_jwt = jwt.encode(data, AUTHOS_SECRET_KEY, algorithm=AUTHOS_ALGORITHM)
        return enc_jwt

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash Password

        Args:
            password (str): Password

        Returns:
            str: Hashed Password
        """
        crypto_ctx = CryptContext(schemes=["bcrypt"])
        return crypto_ctx.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify Password

        Args:
            password (str): Password
            hashed_password (str): Hashed Password

        Returns:
            bool: True if verified else False
        """
        crypto_ctx = CryptContext(schemes=["bcrypt"])
        return crypto_ctx.verify(password, hashed_password)


class AuthosTokenHandler(AuthosTokenHandlerInterface):
    def __init__(
        self,
        user_session_handler: EcommerceSessionHandlerInterface,
        ecommerce_user_handler: EcommerceUserHandlerInterface,
    ) -> None:
        # create repositories
        self.user_session_handler = user_session_handler
        self.ecommerce_user_handler = ecommerce_user_handler

    async def verify_token(
        self,
        session_token: str,
        ref_secret_key: str,
        with_expiration: bool = True,
    ) -> Dict[str, Any]:
        """Verify Token
            - Returns new session with Status False as it is not logged in

        Args:
            session_token (str): Session Token
            ref_secret_key (str): Reference seller secret key

        Returns:
            EcommerceSession: Ecommerce Session
        """
        # verify if token is valid
        token_session = await self.user_session_handler.is_session_valid(
            session_token, ref_secret_key, with_expiration=with_expiration
        )
        # [TODO] improve error handling
        if not token_session:
            logging.warning("Authos Token is invalid")
            raise ValueError
        if not token_session.ecommerce_user_id:
            logging.warning("Authos Token is not logged in")
            return {
                "token": session_token,
                "is_valid": True,
                "valid_until": token_session.expiration,
                "info": None,
            }
        # info
        info_user = await self.ecommerce_user_handler.fetch(
            token_session.ecommerce_user_id, ref_secret_key
        )
        if not info_user:
            logging.warning("Authos Token doesn't have associated user")
            raise ValueError
        info_user.session = token_session
        return {
            "token": session_token,
            "is_valid": True,
            "valid_until": token_session.expiration,
            "info": info_user,
        }


class EcommerceSessionHandler(EcommerceSessionHandlerInterface):
    def __init__(self, user_session_repo: UserSessionRepositoryInterface) -> None:
        self.user_session_repo = user_session_repo

    async def get_session_token(
        self,
        session_token: str,
        data: Dict[str, Any],
        ref_secret_key: str,
        refresh: bool = False,
    ) -> EcommerceSession:
        """Get Session Token

        Args:
            session_token (str): Session Token
            data (Dict[str, Any]): Data to store in the session token if refreshed
            ref_secret_key (str): Reference seller secret key
            refresh (bool, optional): If token expired Defaults to False.

        Returns:
            EcommerceSession: Session Token
        """
        # verify if its expired
        is_expired = await self.is_token_expired(session_token)
        _expirat = datetime.fromtimestamp(
            is_expired["data"].get(
                "exp", (datetime.utcnow() - timedelta(days=1)).timestamp()
            )
        )
        # if (refresh & expired) or not expired
        if (refresh and is_expired["status"]) or (not is_expired["status"]):
            # verify if token is valid
            valid_session_db = await self.is_session_valid(
                session_token, ref_secret_key, with_expiration=False
            )
            # if not valid - return token with status false
            if not valid_session_db:
                return EcommerceSession(
                    session_token=session_token,
                    ref_secret_key=ref_secret_key,
                    session_data=json.dumps(is_expired["data"]),
                    status=False,
                    expiration=_expirat,
                    msg="Session is invalid",
                )
            # if valid
            if refresh:
                # if refresh - update token with new data
                _new_usess = IUserSession(
                    session_token=session_token,
                    ecommerce_user_id=valid_session_db.ecommerce_user_id,
                    session_data=json.dumps(data),
                    expiration=datetime.utcnow() + timedelta(days=AUTHOS_TOKEN_TTL),
                )
                if not await self.user_session_repo.update_session(
                    _new_usess, ref_secret_key
                ):
                    raise GQLApiException(
                        msg="Error updating session",
                        error_code=GQLApiErrorCodeType.AUTHOS_ERROR_UPDATING_SESSION.value,
                    )
                return EcommerceSession(
                    **_new_usess.__dict__,
                    ref_secret_key=ref_secret_key,
                    status=True if _new_usess.ecommerce_user_id else False,
                    msg="Session updated",
                )
            #  return new token with status true
            return valid_session_db
        # else - if not refresh & expired - return same token with status false
        else:
            return EcommerceSession(
                session_token=session_token,
                ref_secret_key=ref_secret_key,
                session_data=json.dumps(is_expired["data"]),
                expiration=_expirat,
                status=False,
                msg="Session is expired",
            )

    async def is_session_valid(
        self, session_token: str, ref_secret_key: str, with_expiration: bool = True
    ) -> EcommerceSession | NoneType:
        """Check if session is valid
             - verify if token is in DB and has not expired

        Args:
            session_token (str): Session Token
            ref_secret_key (str): Reference seller secret key
            with_expiration (bool, optional): With Expiration. Defaults to True.

        Returns:
            EcommerceSession | NoneType: Ecommerce Session | None
        """
        expired_at = (
            datetime.utcnow()  # now
            if with_expiration
            else datetime(2023, 1, 1)  # date set before release
        )
        ecomm = await self.user_session_repo.fetch_session(
            session_token, ref_secret_key, expires_after=expired_at
        )
        if not ecomm:
            return None
        return EcommerceSession(
            **ecomm.__dict__,
            ref_secret_key=ref_secret_key,
            status=True if ecomm.ecommerce_user_id else False,
            msg="Session is valid",
        )

    async def is_token_expired(self, session_token: str) -> Dict[str, Any]:
        """Check if token is expired

        Args:
            session_token (str): Session Token

        Returns:
            Dict[str, Any]:
                - status: True if expired | False if not expired
                - data: decoded data | empty dict
        """
        # decode token
        decoded_token = await EcommerceJWTHandler.decode_jwt(session_token)
        # token not decoded - return True (expired)
        if not decoded_token:
            return {
                "status": True,
                "data": {},
            }
        # verify if token is expired
        if "exp" in decoded_token:
            return {
                "status": datetime.utcnow()
                > datetime.fromtimestamp(decoded_token["exp"]),
                "data": decoded_token,
            }
        # if no expiration - return True (expired)
        return {
            "status": True,
            "data": decoded_token,
        }

    async def create_session_token(
        self,
        data: Dict[str, Any],
        ref_secret_key: str,
        expires_delta: timedelta = timedelta(days=AUTHOS_TOKEN_TTL),
        ecommerce_user_id: Optional[UUID] = None,
    ) -> EcommerceSession:
        """Create Session Token
            - Returnrs new session with Status False as it is not logged in

        Args:
            data (Dict[str, Any]): Data to store in the session token
            ref_secret_key (str): Reference seller secret key
            expires_delta (timedelta): Expires after given timedelta
            ecommerce_user_id (Optional[UUID]): Ecommerce User ID

        Returns:
            EcommerceSession
        """
        # Add Seller Secret Key and generate JWT
        to_encode = data.copy()
        to_encode.update({"ref_secret_key": ref_secret_key})
        jwt_token = await EcommerceJWTHandler.encode_jwt(to_encode, expires_delta)
        # create new session in DB
        session = IUserSession(
            session_token=jwt_token,
            session_data=json.dumps(to_encode),
            expiration=datetime.utcnow() + expires_delta,
            ecommerce_user_id=ecommerce_user_id,
        )
        if not await self.user_session_repo.create_session(session, ref_secret_key):
            raise GQLApiException(
                msg="Error creating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_CREATING_SESSION.value,
            )
        return EcommerceSession(
            **session.__dict__,
            ref_secret_key=ref_secret_key,
            status=False,
            msg="Session created",
        )

    async def set_login_session_token(
        self,
        session_token: str,
        ecommerce_user_id: UUID,
        data: Dict[str, Any],
        ref_secret_key: str,
        expires_delta: timedelta = timedelta(hours=48),
    ) -> EcommerceSession:
        """Update Session Token with ecommerce user to assign sign up / login
            - Returns new session with Status False as it is not logged in

        Args:
            ecommerce_user_id (UUID): Ecommerce User ID
            data (Dict[str, Any]): Data to store in the session token
            ref_secret_key (str): Reference seller secret key
            expires_delta (timedelta): Expires after given timedelta

        Returns:
            EcommerceSession
        """
        # Add Seller Secret Key
        to_encode = data.copy()
        to_encode.update({"ref_secret_key": ref_secret_key})
        # update new session in DB
        session = IUserSession(
            session_token=session_token,
            ecommerce_user_id=ecommerce_user_id,
            session_data=json.dumps(to_encode),
            expiration=datetime.utcnow() + expires_delta,
        )
        if not await self.user_session_repo.update_session(session, ref_secret_key):
            raise GQLApiException(
                msg="Error updating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_UPDATING_SESSION.value,
            )
        return EcommerceSession(
            **session.__dict__,
            ref_secret_key=ref_secret_key,
            status=True,
            msg="Session updated",
        )

    async def set_logout_session_token(
        self,
        session_token: str,
        ref_secret_key: str,
        data: Dict[str, Any],
    ) -> EcommerceSession:
        """Set Logout Session Token
            - Returns new session with Status False as it is not logged in

        Args:
            session_token (str): Session Token
            ref_secret_key (str): Reference seller secret key
            data (Dict[str, Any]): Session data

        Returns:
            EcommerceSession: Ecommerce Session
        """
        # clear session
        if not await self.user_session_repo.clear_session(
            session_token, ref_secret_key
        ):
            raise GQLApiException(
                msg="Error updating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_UPDATING_SESSION.value,
            )
        to_enc = data.copy()
        to_enc.update({"ref_secret_key": ref_secret_key})
        return await self.get_session_token(
            session_token, to_enc, ref_secret_key, refresh=True
        )


class EcommerceUserHandler(EcommerceUserHandlerInterface):
    def __init__(
        self,
        user_session_handler: EcommerceSessionHandlerInterface,
        ecommerce_user_repo: EcommerceUserRepositoryInterface,
        ecommerce_user_restaurant_relation_repo: Optional[
            EcommerceUserRestaurantRelationRepositoryInterface
        ] = None,
        restaurant_business_handler: Optional[
            RestaurantBusinessHandlerInterface
        ] = None,
    ) -> None:
        self.user_session_handler = user_session_handler
        self.ecommerce_user_repo = ecommerce_user_repo
        if ecommerce_user_restaurant_relation_repo:
            self.ecommerce_user_restaurant_relation_repo = (
                ecommerce_user_restaurant_relation_repo
            )
        if restaurant_business_handler:
            self.restaurant_business_handler = restaurant_business_handler

    async def login(
        self,
        email: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
        data: Dict[str, Any],
    ) -> EcommerceUser:
        """Login with email & password
            - verify if email exists in ref seller DB
            - verify password with hashed password
            - verify if token exists
            -  if token exists - update token with ecommerce user
            -  else - create new token with ecommerce user

        Args:
            email (str): Email
            password (str): Password
            ref_secret_key (str): reference seller secret key
            session_token (str): session token
            data (Dict[str, Any]): session data

        Returns:
            EcommerceUser: Ecommerce User
        """
        # fetch user by email
        ecomm_usr = await self.ecommerce_user_repo.fetch_by_email(email, ref_secret_key)
        if not ecomm_usr:
            raise GQLApiException(
                msg="Email not registered",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        # verify password
        if not EcommerceJWTHandler.verify_password(password, ecomm_usr.password):
            raise GQLApiException(
                msg="Password is incorrect",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_WRONG_PASSWORD.value,
            )
        # verify token
        token_session = await self.user_session_handler.is_session_valid(
            session_token, ref_secret_key, with_expiration=False
        )
        if token_session:
            # update session token with ecommerce user
            upd_sess = await self.user_session_handler.set_login_session_token(
                session_token, ecomm_usr.id, data, ref_secret_key
            )
        else:
            # new session token with ecommerce user
            upd_sess = await self.user_session_handler.create_session_token(
                data, ref_secret_key
            )
        return EcommerceUser(
            **{k: v for k, v in ecomm_usr.__dict__.items() if k not in ["session"]},
            session=upd_sess,
        )

    async def is_logged(
        self,
        session_token: str,
        ref_secret_key: str,
    ) -> bool:
        """Check if user is logged in

        Args:
            session_token (str): Session Token
            ref_secret_key (str): Reference seller secret key

        Returns:
            bool: True if logged in else False
        """
        # verify if token is valid
        token_session = await self.user_session_handler.is_session_valid(
            session_token, ref_secret_key
        )
        if not token_session:
            return False
        # if valid - verify if ecommerce user id exists (which means it is logged)
        return token_session.status

    async def signup_email(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
        data: Dict[str, Any],
        business_name: Optional[str] = None,
    ) -> EcommerceUser:
        """Sign up with email & password (business name - optional)
            - verify token is valid
            - verify email is not registered in ref seller DB
            - create new ecommerce user
            - try
              - create an restaurant business with business name | first name + last name
              - create a ecomm user restaurant relation
            - except creating
              - delete ecommerce user

        Args:
            first_name (str): First Name
            last_name (str): Last Name
            email (str): Email
            phone_number (str): Phone Number
            password (str): Password
            ref_secret_key (str): Reference seller secret key
            session_token (str): Session Token

        Returns:
            EcommerceUser: Ecommerce User
        """
        ecomm_user = await self._signup_email(
            first_name,
            last_name,
            email,
            phone_number,
            password,
            ref_secret_key,
            session_token,
            data,
        )
        rest_biz = None
        ecomm_rest_rel = None
        country = "México"  # [TODO] make multi-country later
        try:
            rbiz_acc_inp = RestaurantBusinessAccountInput(
                business_type=RestaurantBusinessType.RESTAURANT,
                phone_number=phone_number,
                email=email,
            )
            # create restaurant business
            rest_biz = await self.restaurant_business_handler.new_ecommerce_restaurant_business(
                business_name if business_name else f"{first_name} {last_name}",
                country,
                rbiz_acc_inp,
            )
            # create ecomm user restaurant relation
            ecomm_rest_rel = await self.ecommerce_user_restaurant_relation_repo.add(
                ecomm_user.id, rest_biz.id
            )
            if not ecomm_rest_rel:
                raise GQLApiException(
                    msg="Error creating ecommerce user restaurant relation",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
        except Exception as e:
            logging.warning("Error creating ecommerce restaurant business")
            logging.error(e)
            # delete ecommerce user
            if not await self.delete(
                ecomm_user.id, session_token, data, ref_secret_key
            ):
                logging.warning("Error deleting ecommerce user")
            # [TODO] if error annd rest_biz is not None - delete rows created at rest_biz
            raise GQLApiException(
                msg="Error creating ecommerce user",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_CREATING_ECOMM_USER.value,
            )
        return ecomm_user

    async def _signup_email(
        self,
        first_name: str,
        last_name: str,
        email: str,
        phone_number: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
        data: Dict[str, Any],
    ) -> EcommerceUser:
        # validat token
        token_session = await self.user_session_handler.is_session_valid(
            session_token, ref_secret_key
        )
        if not token_session:
            raise GQLApiException(
                msg="Session is invalid",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_INVALID_SESSION.value,
            )
        # verify email is not registered
        email_exists = await self.ecommerce_user_repo.fetch_by_email(
            email, ref_secret_key
        )
        if email_exists:
            raise GQLApiException(
                msg=f"Email already registered at {ref_secret_key}",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_EMAIL_ALREADY_REGISTERED.value,
            )
        # encode password
        hpswd = EcommerceJWTHandler.hash_password(password)
        # create new ecommerce user
        ecomm_usr = IEcommerceUser(
            id=uuid4(),
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            password=hpswd,
        )
        if not await self.ecommerce_user_repo.add(ecomm_usr, ref_secret_key):
            raise GQLApiException(
                msg="Error creating ecommerce user",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_CREATING_ECOMM_USER.value,
            )
        # update session token with ecommerce user
        upd_sess = await self.user_session_handler.set_login_session_token(
            session_token, ecomm_usr.id, data, ref_secret_key
        )
        return EcommerceUser(
            **ecomm_usr.__dict__, ref_secret_key=ref_secret_key, session=upd_sess
        )

    async def update_password(
        self,
        email: str,
        password: str,
        ref_secret_key: str,
        session_token: str,
    ) -> bool:
        # [TODO]
        raise NotImplementedError

    async def logout(
        self,
        session_token: str,
        data: Dict[str, Any],
        ref_secret_key: str,
    ) -> bool:
        """Logout
            - clear session token

        Args:
            session_token (str): Session Token
            data (Dict[str, Any]): Session Data
            ref_secret_key (str): Reference seller secret key

        Returns:
            bool: False if logged out else True
        """
        # clear session token
        upd_sess = await self.user_session_handler.set_logout_session_token(
            session_token, ref_secret_key, data
        )
        # return status - if ecommerce user id exists (which means it is logged)
        return upd_sess.status

    async def fetch(
        self,
        id: UUID,
        ref_secret_key: str,
    ) -> EcommerceUser | NoneType:
        """Fetch Ecommerce User by ID

        Args:
            id (UUID): Ecommerce User ID
            ref_secret_key (str): Reference seller secret key

        Returns:
            EcommerceUser: Ecommerce User
        """
        return await self.ecommerce_user_repo.fetch(id, ref_secret_key)

    async def delete(
        self,
        id: UUID,
        session_token: str,
        data: Dict[str, Any],
        ref_secret_key: str,
    ) -> bool:
        """Delete Ecommerce User by ID

        Args:
            id (UUID): Ecommerce User ID
            ref_secret_key (str): Reference seller secret key

        Returns:
            bool: True if deleted else False
        """
        euser = await self.ecommerce_user_repo.fetch(id, ref_secret_key)
        if not euser:
            logging.info("Ecommerce User not found")
            return False
        # logout returns False if correctly logged out
        if await self.logout(
            session_token,
            data,
            ref_secret_key,
        ):
            logging.warning("Error logging out")
            return False
        return await self.ecommerce_user_repo.delete(id, ref_secret_key)


class EcommercePasswordHandler(EcommercePasswordHandlerInterface):
    def __init__(
        self,
        pwd_restore_repo: PwdRestoreRepositoryInterface,
        ecommerce_user_repo: EcommerceUserRepositoryInterface,
    ) -> None:
        self.pwd_restore_repo = pwd_restore_repo
        self.ecommerce_user_repo = ecommerce_user_repo

    async def create_restore_token(
        self,
        email: str,
        ref_secret_key: str,
        expires_delta: timedelta = timedelta(hours=48),
    ) -> EcommercePassword:
        """Create Restore Token
            - verify if email exists in Ref Seller DB
            - if exists
                - create restore token
                - save in Ref Seller DB
                - return status True
            - else
                - raise exception
        Args:
            email (str): Email
            ref_secret_key (str): Reference seller secret key
            expires_delta (timedelta, optional): Expiration. Defaults to timedelta(hours=48).

        Returns:
            EcommercePassword: Token, Status & Message
        """
        # get ecommerce user by email
        ecomm_usr = await self.ecommerce_user_repo.fetch_by_email(email, ref_secret_key)
        if not ecomm_usr:
            raise GQLApiException(
                msg="Email not registered",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        # create restore token with email in payload
        payload = {
            "email": email,
            "ref_secret_key": ref_secret_key,
        }
        restore_token = await EcommerceJWTHandler.encode_jwt(
            payload, expires_delta=expires_delta
        )
        # save restore token in Ref Seller DB
        pwd_restore = IPwdRestore(
            restore_token=restore_token,
            ecommerce_user_id=ecomm_usr.id,
            expiration=datetime.utcnow() + expires_delta,
        )
        pwd_flag = await self.pwd_restore_repo.create_pwd_restore(
            pwd_restore, ref_secret_key
        )
        return EcommercePassword(
            **pwd_restore.__dict__,
            ref_secret_key=ref_secret_key,
            status=pwd_flag,
            msg="Restore token created" if pwd_flag else "Error creating restore token",
        )

    async def is_restore_token_valid(
        self,
        restore_token: str,
        ref_secret_key: str,
        with_expiration: bool = True,
    ) -> bool:
        """Check if restore token is valid
            - verify if is not expired
            - Fetch token from Ref Seller DB
            - if token exists - return True

        Args:
            restore_token (str): Restore Token
            ref_secret_key (str): Reference seller secret key
            with_expiration (bool, optional): Validate Expiration Flag. Defaults to True.

        Returns:
            bool: True if valid else False
        """
        expired_at = (
            datetime.utcnow()  # now
            if with_expiration
            else datetime(2023, 1, 1)  # date set before release
        )
        pwresto = await self.pwd_restore_repo.fetch_pwd_restore(
            restore_token, ref_secret_key, expires_after=expired_at
        )
        if not pwresto:
            return False
        return True

    async def reset_password(
        self, password: str, restore_token: str, ref_secret_key: str
    ) -> Dict[str, Any]:
        """Reset Password
            - Verify if token exists & is not expired
            - If valid
                - find Ecommerce user email in Ref Seller DB
                - update password in Ref seller DB

        Args:
            password (str): Password
            restore_token (str): Restore Token
            ref_secret_key (str): Reference seller secret key

        Returns:
            Dict[str, Any]: Status & Message
                {
                    "status": True | False,
                    "msg": "Password updated" | "Error updating password"
                }
        """
        # verify if token exists & is not expired
        is_valid = await self.is_restore_token_valid(restore_token, ref_secret_key)
        if not is_valid:
            raise GQLApiException(
                msg="Restore token is invalid",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_INVALID_RESTORE.value,
            )
        # decode token
        decoded_token = await EcommerceJWTHandler.decode_jwt(restore_token)
        # fetch ecommerce user by email
        ecomm_usr = await self.ecommerce_user_repo.fetch_by_email(
            decoded_token["email"], ref_secret_key
        )
        if not ecomm_usr:
            raise GQLApiException(
                msg="Email not registered",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
            )
        # update password in Ref seller DB
        upd_pass = EcommerceJWTHandler.hash_password(password)
        pwd_flag = await self.ecommerce_user_repo.set_password(
            ecomm_usr.id, upd_pass, ref_secret_key
        )
        # delete restore token
        if not await self.pwd_restore_repo.delete_pwd_restore(
            decoded_token["email"], ref_secret_key
        ):
            logging.warning("Error deleting restore token")
        return {
            "status": pwd_flag,
            "msg": "Password updated" if pwd_flag else "Error updating password",
        }
