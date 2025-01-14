from datetime import datetime
from types import NoneType
from uuid import UUID

from databases import Database as SQLDatabase
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.authos.ecommerce_pwd import PwdRestoreRepositoryInterface
from gqlapi.domain.interfaces.v2.authos.ecommerce_user import (
    EcommerceUser,
    EcommerceUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.authos.ecommerce_session import UserSessionRepositoryInterface
from gqlapi.domain.models.v2.authos import IEcommerceUser, IPwdRestore, IUserSession
from gqlapi.config import DATABASE_AUTHOS_URL
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain
from gqlapi.repository import CoreRepository
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


class UserSessionRepository(CoreRepository, UserSessionRepositoryInterface):
    def __init__(self, info: StrawberryInfo) -> None:
        try:
            _db = info.context["db"].authos
        except Exception as e:
            logger.error(e)
            logger.warning("Issues connect Authos DB")
            raise GQLApiException(
                msg="Error creating connect Authos DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        self.db = _db

    async def verify_table_exists(self, ref_secret_key: str) -> bool:
        qry = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_catalog = :table_catalog
            AND table_name = :table_name
            """
        resp = await super().raw_query(
            query=qry,
            vals={
                "table_name": f"user_session_{ref_secret_key}",
                "table_catalog": DATABASE_AUTHOS_URL.database,
            },
        )
        if resp:
            return True
        return False

    async def fetch_session(
        self, session_token: str, ref_secret_key: str, expires_after: datetime
    ) -> IUserSession | NoneType:
        """Fetch Ecommerce session

        Args:
            session_token (str): Session token
            ref_secret_key (str): Reference secret key
            expires_after (datetime): Expires after given timestamp

        Returns:
            IUserSession | NoneType: Session token
        """
        _sess = await super().raw_query(
            query=f"""
                SELECT *
                FROM user_session_{ref_secret_key}
                WHERE session_token = :session_token
                AND expiration >= :expires_after
            """,
            vals={
                "session_token": session_token,
                "expires_after": expires_after,
            },
        )
        if not _sess:
            return None
        return IUserSession(**sql_to_domain(_sess[0], IUserSession))

    async def create_session(self, session: IUserSession, ref_secret_key: str) -> bool:
        """Create Ecommerce session

        Args:
            session (IUserSession): session
            ref_secret_key (str): Reference seller secret key

        Returns:
            bool: True if created else False
        """
        sess_dict = domain_to_dict(session, skip=["created_at", "last_updated"])
        # verify table exists - if not raise error
        if not await self.verify_table_exists(ref_secret_key):
            raise GQLApiException(
                msg="Error creating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_TABLE_NOT_FOUND.value,
            )
        fback = await super().add(
            core_element_name="User Sesion",
            core_element_tablename=f"user_session_{ref_secret_key}",
            core_query=f"""
                INSERT INTO user_session_{ref_secret_key} (
                    session_token,
                    ecommerce_user_id,
                    session_data,
                    expiration
                ) VALUES (
                    :session_token,
                    :ecommerce_user_id,
                    :session_data,
                    :expiration
                )
            """,
            core_values=sess_dict,
            validate_by="session_token",
            validate_against=sess_dict["session_token"],
        )
        return True if fback else False

    async def update_session(self, session: IUserSession, ref_secret_key: str) -> bool:
        """Update Ecommerce session

        Args:
            session (IUserSession): Session
            ref_secret_key (str): Reference seller secret key

        Returns:
            bool: Flag if updated
        """
        sess_dict = domain_to_dict(session, skip=["created_at", "last_updated"])
        sess_dict["last_updated"] = datetime.utcnow()
        # verify if table exists - if not raise error
        if not await self.verify_table_exists(ref_secret_key):
            raise GQLApiException(
                msg="Error updating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_TABLE_NOT_FOUND.value,
            )
        fback = await super().edit(
            core_element_name="User Sesion",
            core_element_tablename=f"user_session_{ref_secret_key}",
            core_query=f"""
                UPDATE user_session_{ref_secret_key}
                SET session_data = :session_data,
                    ecommerce_user_id = :ecommerce_user_id,
                    expiration = :expiration,
                    last_updated = :last_updated
                WHERE session_token = :session_token
            """,
            core_values=sess_dict,
        )
        return fback

    async def clear_session(self, session_token: str, ref_secret_key: str) -> bool:
        """Clear session - remove ecommerce_user_id

        Args:
            session_token (str): Session token
            ref_secret_key (str): Reference seller secret key

        Returns:
            bool: Flag if updated
        """
        sess_dict = {
            "session_token": session_token,
            "ecommerce_user_id": None,
            "last_updated": datetime.utcnow(),
        }
        # verify if table exists - if not raise error
        if not await self.verify_table_exists(ref_secret_key):
            raise GQLApiException(
                msg="Error updating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_TABLE_NOT_FOUND.value,
            )
        fback = await super().edit(
            core_element_name="User Sesion",
            core_element_tablename=f"user_session_{ref_secret_key}",
            core_query=f"""
                UPDATE user_session_{ref_secret_key}
                SET ecommerce_user_id = :ecommerce_user_id,
                    last_updated = :last_updated
                WHERE session_token = :session_token
            """,
            core_values=sess_dict,
        )
        return fback


class EcommerceUserRepository(CoreRepository, EcommerceUserRepositoryInterface):
    def __init__(self, info: StrawberryInfo) -> None:
        try:
            _db = info.context["db"].authos
        except Exception as e:
            logger.error(e)
            logger.warning("Issues connect Authos DB")
            raise GQLApiException(
                msg="Error creating connect Authos DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        self.db = _db

    async def verify_table_exists(self, ref_secret_key: str) -> bool:
        qry = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_catalog = :table_catalog
            AND table_name = :table_name
            """
        resp = await super().raw_query(
            query=qry,
            vals={
                "table_name": f"ecommerce_user_{ref_secret_key}",
                "table_catalog": DATABASE_AUTHOS_URL.database,
            },
        )
        if resp:
            return True
        return False

    async def set_password(
        self,
        ecommerce_user_id: UUID,
        password: str,
        ref_secret_key: str,
    ) -> bool:
        flag = await super().edit(
            core_element_name="Ecommerce User",
            core_element_tablename=f"ecommerce_user_{ref_secret_key}",
            core_query=f"""
                UPDATE ecommerce_user_{ref_secret_key}
                SET password = :password
                WHERE id = :id
            """,
            core_values={"id": ecommerce_user_id, "password": password},
        )
        return flag

    async def fetch(
        self,
        id: UUID,
        ref_secret_key: str,
    ) -> EcommerceUser | NoneType:
        resp = await super().fetch(
            core_element_name="Ecommerce User",
            core_element_tablename=f"ecommerce_user_{ref_secret_key}",
            id_key="id",
            id=id,
            core_columns=["*"],
        )
        if not resp:
            return None
        return EcommerceUser(
            **sql_to_domain(resp, IEcommerceUser), ref_secret_key=ref_secret_key
        )

    async def fetch_by_email(
        self,
        email: str,
        ref_secret_key: str,
    ) -> EcommerceUser | NoneType:
        resp = await super().fetch(
            core_element_name="Ecommerce User",
            core_element_tablename=f"ecommerce_user_{ref_secret_key}",
            id_key="email",
            id=email,
            core_columns=["*"],
        )
        if not resp:
            return None
        return EcommerceUser(
            **sql_to_domain(resp, IEcommerceUser), ref_secret_key=ref_secret_key
        )

    async def add(
        self,
        ecommerce_user: IEcommerceUser,
        ref_secret_key: str,
    ) -> bool:
        # verify table exists - if not raise error
        if not await self.verify_table_exists(ref_secret_key):
            raise GQLApiException(
                msg="Error creating ecommerce user",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_TABLE_NOT_FOUND.value,
            )
        vals = domain_to_dict(
            ecommerce_user, skip=["disabled", "created_at", "last_updated"]
        )
        flag = await super().add(
            core_element_name="Ecommerce User",
            core_element_tablename=f"ecommerce_user_{ref_secret_key}",
            core_query=f"""
                INSERT INTO ecommerce_user_{ref_secret_key} (
                    id,
                    email,
                    password,
                    first_name,
                    last_name,
                    phone_number
                ) VALUES (
                    :id,
                    :email,
                    :password,
                    :first_name,
                    :last_name,
                    :phone_number
                )
            """,
            core_values=vals,
            validate_by="email",
            validate_against=ecommerce_user.email,
        )
        return True if flag else False

    async def edit(
        self,
        ecommerce_user: IEcommerceUser,
        ref_secret_key: str,
    ) -> bool:
        vals = domain_to_dict(
            ecommerce_user, skip=["disabled", "password", "created_at", "last_updated"]
        )
        vals["last_updated"] = datetime.utcnow()
        flag = await super().edit(
            core_element_name="Ecommerce User",
            core_element_tablename=f"ecommerce_user_{ref_secret_key}",
            core_query=f"""
                UPDATE ecommerce_user_{ref_secret_key}
                SET first_name = :first_name,
                    email = :email,
                    last_name = :last_name,
                    phone_number = :phone_number,
                    last_updated = :last_updated
                WHERE id = :id
            """,
            core_values=vals,
        )
        return flag

    async def delete(self, id: UUID, ref_secret_key: str) -> bool:
        try:
            await super()._query(
                query=f"""
                    DELETE FROM ecommerce_user_{ref_secret_key}
                    WHERE id = :id
                """,
                values={"id": id},
                core_element_name="Ecommerce User",
            )
            return True
        except Exception as e:
            logger.error(e)
            logger.warning("Error to delete ecommerce user")
            return False


class PwdRestoreRepository(CoreRepository, PwdRestoreRepositoryInterface):
    def __init__(self, info: StrawberryInfo) -> None:
        try:
            _db = info.context["db"].authos
        except Exception as e:
            logger.error(e)
            logger.warning("Issues connect Authos DB")
            raise GQLApiException(
                msg="Error creating connect Authos DB",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        self.db = _db

    async def verify_table_exists(self, ref_secret_key: str) -> bool:
        qry = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_catalog = :table_catalog
            AND table_name = :table_name
            """
        resp = await super().raw_query(
            query=qry,
            vals={
                "table_name": f"pwd_restore_{ref_secret_key}",
                "table_catalog": DATABASE_AUTHOS_URL.database,
            },
        )
        if resp:
            return True
        return False

    async def delete_pwd_restore(
        self,
        email: str,
        ref_secret_key: str,
    ) -> bool:
        try:
            await self.db.execute(
                f"""
                    DELETE FROM pwd_restore_{ref_secret_key}
                    WHERE ecommerce_user_id IN (
                        SELECT id
                        FROM ecommerce_user_{ref_secret_key}
                        WHERE email = :email
                    )
                """,
                {"email": email},
            )
            return True
        except Exception as e:
            logger.error(e)
            logger.warning("Error to delete pwd_restore table")
            return False

    async def create_pwd_restore(
        self,
        pwd_restore: IPwdRestore,
        ref_secret_key: str,
    ) -> bool:
        # verify table exists - if not raise error
        if not await self.verify_table_exists(ref_secret_key):
            raise GQLApiException(
                msg="Error creating session",
                error_code=GQLApiErrorCodeType.AUTHOS_ERROR_TABLE_NOT_FOUND.value,
            )
        pwdr_dict = domain_to_dict(pwd_restore, skip=["created_at", "last_updated"])
        fback = await super().add(
            core_element_name="Pwd Restore",
            core_element_tablename=f"pwd_restore_{ref_secret_key}",
            core_query=f"""
                INSERT INTO pwd_restore_{ref_secret_key} (
                    restore_token,
                    ecommerce_user_id,
                    expiration
                ) VALUES (
                    :restore_token,
                    :ecommerce_user_id,
                    :expiration
                )
            """,
            core_values=pwdr_dict,
            validate_by="restore_token",
            validate_against=pwdr_dict["restore_token"],
        )
        return True if fback else False

    async def fetch_pwd_restore(
        self,
        restore_token: str,
        ref_secret_key: str,
        expires_after: datetime = datetime.utcnow(),
    ) -> IPwdRestore | NoneType:
        _pwdr = await super().raw_query(
            query=f"""
                SELECT *
                FROM pwd_restore_{ref_secret_key}
                WHERE restore_token = :restore_token
                AND expiration >= :expires_after
            """,
            vals={
                "restore_token": restore_token,
                "expires_after": expires_after,
            },
        )
        if not _pwdr:
            return None
        return IPwdRestore(**sql_to_domain(_pwdr[0], IPwdRestore))


# Authos Authenticator Repos
class AuthosUserSessionRepository(UserSessionRepository):
    def __init__(self, authos_db: SQLDatabase) -> None:
        self.db = authos_db


class AuthosEcommerceUserRepository(EcommerceUserRepository):
    def __init__(self, authos_db: SQLDatabase) -> None:
        self.db = authos_db
