from datetime import timedelta
from typing import Optional
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.handlers.restaurant.restaurant_business import RestaurantBusinessHandler
from gqlapi.repository.b2bcommerce.ecommerce_seller import (
    EcommerceSellerRepository,
    EcommerceUserRestaurantRelationRepository,
)
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)
from gqlapi.repository.restaurant.restaurant_user import (
    RestaurantUserPermissionRepository,
    RestaurantUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.utils.notifications import (
    send_authos_email_restore_password_token,
    send_authos_email_welcome,
)
from gqlapi.lib.logger.logger.basic_logger import get_logger

import strawberry
from strawberry.types import Info as StrawberryInfo
from starlette.background import BackgroundTasks

from gqlapi.domain.interfaces.v2.authos.ecommerce_pwd import (
    EcommercePasswordError,
    EcommercePasswordResetMsg,
    EcommercePasswordResetResult,
    EcommercePasswordResult,
)
from gqlapi.domain.interfaces.v2.authos.ecommerce_user import (
    EcommerceUserError,
    EcommerceUserMsg,
    EcommerceUserMsgResult,
    EcommerceUserResult,
)
from gqlapi.domain.interfaces.v2.authos.ecommerce_session import (
    EcommerceSessionError,
    EcommerceSessionResult,
)
from gqlapi.handlers.services.authos import (
    EcommercePasswordHandler,
    EcommerceSessionHandler,
    EcommerceUserHandler,
)
from gqlapi.utils.authos import serialize_request_headers
from gqlapi.repository.services.authos import (
    EcommerceUserRepository,
    PwdRestoreRepository,
    UserSessionRepository,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

# logger
logger = get_logger(get_app())

# ----------------
# Query Classes
# ----------------


@strawberry.type
class AuthosEcommerceSessionQuery:
    @strawberry.field(
        name="getEcommerceSessionToken",
    )
    async def get_ecommerce_session_token(
        self, info: StrawberryInfo, ref_secret_key: str, refresh: bool = False
    ) -> EcommerceSessionResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Get ecommerce session token")
        # get serialized headers
        sess_data = await serialize_request_headers(info.context["request"])
        token_hdr = sess_data.get("authorization", None)
        try:
            # instance handler
            _handler = EcommerceSessionHandler(
                user_session_repo=UserSessionRepository(info)
            )
            if token_hdr is None:
                # if no token - create one
                resp_token = await _handler.create_session_token(
                    data=sess_data,
                    ref_secret_key=ref_secret_key,
                )
            else:
                # is token exists - get session token
                token = token_hdr.split(" ")[-1]
                resp_token = await _handler.get_session_token(
                    session_token=token,
                    data=sess_data,
                    ref_secret_key=ref_secret_key,
                    refresh=refresh,
                )
            return resp_token
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceSessionError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceSessionError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )


@strawberry.type
class AuthosEcommerceUserQuery:
    @strawberry.field(
        name="isEcommerceUserLoggedIn",
    )
    async def get_verify_ecommerce_user_is_logged(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
    ) -> EcommerceUserMsgResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Verify ecommerce user is logged")
        # data validation
        try:
            # instance handlers
            usess_handler = EcommerceSessionHandler(
                user_session_repo=UserSessionRepository(info)
            )
            _handler = EcommerceUserHandler(
                user_session_handler=usess_handler,
                ecommerce_user_repo=EcommerceUserRepository(info),
            )
            # authos token
            if not hasattr(info.context["request"].user, "authos_session"):
                return EcommerceUserMsg(
                    status=False,
                    ref_secret_key=ref_secret_key,
                    msg="Ecommerce User is not logged in",
                )
            token = info.context["request"].user.authos_session
            # verify session
            sess_flag = await _handler.is_logged(
                ref_secret_key=ref_secret_key,
                session_token=token,
            )
            return EcommerceUserMsg(
                status=sess_flag,
                ref_secret_key=ref_secret_key,
                msg=(
                    "Ecommerce User is logged in"
                    if sess_flag
                    else "Ecommerce User is not logged in"
                ),
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )


# ----------------
# Mutation Classes
# ----------------


@strawberry.type
class AuthosEcommercePwdRestoreMutation:
    @strawberry.mutation(
        name="postEcommerceSendRestoreCode",
    )
    async def post_ecommerce_send_restore_code(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
        email: str,
        url: str,
    ) -> EcommercePasswordResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Post ecommerce send restore token")
        try:
            # instance handler
            _handler = EcommercePasswordHandler(
                pwd_restore_repo=PwdRestoreRepository(info),
                ecommerce_user_repo=EcommerceUserRepository(info),
            )
            # seller repo
            ec_repo = EcommerceSellerRepository(info)
            # send restore code
            resp_token = await _handler.create_restore_token(
                email=email,
                ref_secret_key=ref_secret_key,
                expires_delta=timedelta(hours=24),
            )
            # fetch eecommerce seller name
            eseller = await ec_repo.fetch(id_key="secret_key", id_value=ref_secret_key)
            seller_name = eseller.seller_name if eseller else "Ecommerce B2B"
            # - send email with token and URL to submit new password
            bg_tasks = BackgroundTasks()
            bg_tasks.add_task(
                send_authos_email_restore_password_token,
                seller_name,
                email,
                resp_token.restore_token,
                url,  # [TODO] add customized template to send restore token
            )
            info.context["response"].background = bg_tasks
            return resp_token
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommercePasswordError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommercePasswordError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="postEcommerceResetPassword",
    )
    async def post_ecommerce_reset_password(
        self,
        info: StrawberryInfo,
        password: str,
        restore_token: str,
        ref_secret_key: str,
    ) -> EcommercePasswordResetResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Post ecommerce reset password")
        try:
            # instance handler
            _handler = EcommercePasswordHandler(
                pwd_restore_repo=PwdRestoreRepository(info),
                ecommerce_user_repo=EcommerceUserRepository(info),
            )
            # reset passwd if token is valid
            resp_flag = await _handler.reset_password(
                password=password,
                restore_token=restore_token,
                ref_secret_key=ref_secret_key,
            )
            return EcommercePasswordResetMsg(
                **resp_flag,
                ref_secret_key=ref_secret_key,
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommercePasswordError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommercePasswordError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )


@strawberry.type
class AuthosEcommerceUserMutation:
    @strawberry.mutation(
        name="signupEcommerceUser",
    )
    async def post_signup_ecommerce_user(
        self,
        info: StrawberryInfo,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        phone_number: str,
        ref_secret_key: str,
        ref_url: str,
        business_name: Optional[str] = None,
    ) -> EcommerceUserResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Signup ecommerce user")
        # data validation
        if email == "" or "@" not in email:
            return EcommerceUserError(
                msg="Invalid email",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        if len(password) < 8:
            return EcommerceUserError(
                msg="Invalid password (must be at least 8 characters)",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        if len(phone_number) != 10:
            return EcommerceUserError(
                msg="Invalid phone number (must be 10 digits)",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        if first_name == "" or last_name == "":
            return EcommerceUserError(
                msg="Invalid Name",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # serialized data
        sdata = await serialize_request_headers(info.context["request"])
        try:
            # instance handlers
            usess_handler = EcommerceSessionHandler(
                user_session_repo=UserSessionRepository(info)
            )
            biz_handler = RestaurantBusinessHandler(
                restaurant_business_repo=RestaurantBusinessRepository(info),
                restaurant_business_account_repo=RestaurantBusinessAccountRepository(
                    info
                ),
                restaurant_permission_repo=RestaurantUserPermissionRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            _handler = EcommerceUserHandler(
                user_session_handler=usess_handler,
                ecommerce_user_repo=EcommerceUserRepository(info),
                ecommerce_user_restaurant_relation_repo=EcommerceUserRestaurantRelationRepository(
                    info
                ),
                restaurant_business_handler=biz_handler,
            )
            # seller repo
            ec_repo = EcommerceSellerRepository(info)
            # authos token
            token_hdr = sdata.get("authorization", None)
            token = token_hdr.split(" ")[-1] if token_hdr else None
            if not token:
                return EcommerceUserError(
                    msg="Invalid authos token not found",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # signup user
            resp_user = await _handler.signup_email(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                password=password,
                ref_secret_key=ref_secret_key,
                session_token=token,
                data=sdata,
                business_name=business_name,
            )
            # fetch eecommerce seller name
            eseller = await ec_repo.fetch(id_key="secret_key", id_value=ref_secret_key)
            seller_name = eseller.seller_name if eseller else "Ecommerce B2B"
            # - send welcome email
            bg_tasks = BackgroundTasks()
            bg_tasks.add_task(
                send_authos_email_welcome,
                seller_name,
                {"email": email, "name": first_name},
                ref_url,  # [TODO] add customized template to send welcome msg token
            )
            info.context["response"].background = bg_tasks
            return resp_user
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="loginEcommerceUser",
    )
    async def post_login_ecommerce_user(
        self,
        info: StrawberryInfo,
        email: str,
        password: str,
        ref_secret_key: str,
    ) -> EcommerceUserResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Login ecommerce user")
        # data validation
        if email == "" or "@" not in email:
            return EcommerceUserError(
                msg="Invalid email",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        if len(password) < 8:
            return EcommerceUserError(
                msg="Invalid password (must be at least 8 characters)",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # serialized data
        sdata = await serialize_request_headers(info.context["request"])
        try:
            # instance handlers
            usess_handler = EcommerceSessionHandler(
                user_session_repo=UserSessionRepository(info)
            )
            _handler = EcommerceUserHandler(
                user_session_handler=usess_handler,
                ecommerce_user_repo=EcommerceUserRepository(info),
            )
            # authos token
            token_hdr = sdata.get("authorization", None)
            token = token_hdr.split(" ")[-1] if token_hdr else None
            if not token:
                return EcommerceUserError(
                    msg="Invalid authos token not found",
                    code=GQLApiErrorCodeType.AUTHOS_ERROR_ELEMENT_NOT_FOUND.value,
                )
            # verify is user id logged
            is_logged = await _handler.is_logged(
                ref_secret_key=ref_secret_key,
                session_token=token,
            )
            if is_logged:
                raise GQLApiException(
                    msg="Ecommerce User is already logged in",
                    error_code=GQLApiErrorCodeType.AUTHOS_ERROR_USER_ALREADY_LOGGED.value,
                )
            # login user
            resp_user = await _handler.login(
                email=email,
                password=password,
                ref_secret_key=ref_secret_key,
                session_token=token,
                data=sdata,
            )
            return resp_user
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="logoutEcommerceUser",
    )
    async def post_logout_ecommerce_user(
        self,
        info: StrawberryInfo,
        ref_secret_key: str,
    ) -> EcommerceUserMsgResult:  # type: ignore
        logger.info(f"[authos:{ref_secret_key}] Logout ecommerce user")
        # get serialized headers
        sess_data = await serialize_request_headers(info.context["request"])
        try:
            # instance handlers
            usess_handler = EcommerceSessionHandler(
                user_session_repo=UserSessionRepository(info)
            )
            _handler = EcommerceUserHandler(
                user_session_handler=usess_handler,
                ecommerce_user_repo=EcommerceUserRepository(info),
            )
            # authos token
            if not hasattr(info.context["request"].user, "authos_session"):
                return EcommerceUserMsg(
                    ref_secret_key=ref_secret_key,
                    status=False,
                    msg="Ecommerce User is not logged in",
                )
            token = info.context["request"].user.authos_session
            # verify is user id logged
            is_logged = await _handler.is_logged(
                ref_secret_key=ref_secret_key,
                session_token=token,
            )
            if not is_logged:
                return EcommerceUserMsg(
                    ref_secret_key=ref_secret_key,
                    status=False,
                    msg="Ecommerce User is not logged in",
                )
            # logout user
            resp_flag = await _handler.logout(
                session_token=token,
                data=sess_data,
                ref_secret_key=ref_secret_key,
            )
            return EcommerceUserMsg(
                ref_secret_key=ref_secret_key,
                status=resp_flag,
                msg=(
                    "Ecommerce User successfully logged out"
                    if not resp_flag
                    else "Ecommerce User could not be logged out"
                ),
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return EcommerceUserError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return EcommerceUserError(
                msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )
