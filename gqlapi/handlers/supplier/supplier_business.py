from typing import Any, List, Optional, Dict
from uuid import UUID
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import CloudinaryApi, Folders
from strawberry.file_uploads import Upload
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessGQL,
    SupplierBusinessHandlerInterface,
    SupplierBusinessRepositoryInterface,
    SupplierBusinessAccountRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import (
    MinimumOrderValue,
    SupplierBusiness,
    SupplierBusinessAccount,
    SupplierBusinessCommertialConditions,
    SupplierUser,
    SupplierUserPermission,
)
from gqlapi.domain.models.v2.utils import (
    NotificationChannelType,
    PayMethodType,
    SupplierBusinessType,
)
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.utils.cx import send_business_docs
from gqlapi.utils.domain_mapper import sql_to_domain
from gqlapi.utils.notifications import send_new_sup_user_welcome_msg
from gqlapi.config import ENV as DEV_ENV

logger = get_logger(get_app())


class SupplierBusinessHandler(SupplierBusinessHandlerInterface):
    def __init__(
        self,
        supplier_business_repo: SupplierBusinessRepositoryInterface,
        supplier_business_account_repo: Optional[
            SupplierBusinessAccountRepositoryInterface
        ] = None,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        supplier_user_repo: Optional[SupplierUserRepositoryInterface] = None,
        supplier_user_permission_repo: Optional[
            SupplierUserPermissionRepositoryInterface
        ] = None,
    ):
        self.repository = supplier_business_repo
        if supplier_business_account_repo:
            self.account_repository = supplier_business_account_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if supplier_user_repo:
            self.supplier_user_repo = supplier_user_repo
        if supplier_user_permission_repo:
            self.supplier_user_permission_repo = supplier_user_permission_repo

    def _format_business_account(
        self, sb_account: Dict[str, Any]
    ) -> SupplierBusinessAccount:
        f_account = SupplierBusinessAccount(**sb_account)
        return f_account

    async def _build_supplier_business_gql(
        self,
        supplier_business_id: UUID,
        supplier_user_id: UUID,
    ) -> SupplierBusinessGQL:
        # fetch for all data
        s_business = await self.repository.fetch(supplier_business_id)
        sb_account = await self.account_repository.fetch(supplier_business_id)
        su_perms = await self.supplier_user_permission_repo.fetch(supplier_user_id)
        # format response
        sgql = SupplierBusinessGQL(**s_business)
        sgql.account = self._format_business_account(sb_account)
        sgql.permission = SupplierUserPermission(**su_perms)
        return sgql

    async def new_supplier_business(
        self,
        firebase_id: str,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
        business_type: SupplierBusinessType,
        phone_number: str,
        email: str,
        minimum_order_value: MinimumOrderValue,
        policy_terms: str,
        website: Optional[str] = None,
    ) -> SupplierBusinessGQL:
        """Create Supplier Business

        Parameters:
        ----------
            firebase_id (str): firebase id
            name (str): supplier business name
            country (str): supplier business country
            notification_preference (NotificationChannelType): Chanel to notification
            minimum_order_value (MinimumOrderValue): MinimumOrderValue model
            allowed_payment_methods (List[PayMethodType]): List of PayMethodType
            policy_terms (str): policy terms
            account_number (Optional[str], optional): account number. Defaults to None.

        Raises:
        -------
            GQLApiException

        Returns:
        --------
            SupplierBusiness: Supplier Business model
        """
        # get supplier user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_user_dict = await self.supplier_user_repo.fetch(core_user.id)
        if not sup_user_dict or not sup_user_dict["id"]:  # type: ignore
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_user = SupplierUser(**sql_to_domain(sup_user_dict, SupplierUser))  # type: ignore
        # add supplier business
        sup_bus_id = await self.repository.add(name, country, notification_preference)
        # add supplier user permission
        await self.supplier_user_permission_repo.add(
            sup_user.id, sup_bus_id, True, True
        )
        # add supplier business account
        await self.account_repository.add(
            sup_bus_id,
            SupplierBusinessAccount(
                supplier_business_id=sup_bus_id,
                business_type=business_type,
                phone_number=phone_number,
                email=email,
                website=website,
                default_commertial_conditions=SupplierBusinessCommertialConditions(
                    minimum_order_value=minimum_order_value,
                    policy_terms=policy_terms,
                    allowed_payment_methods=[PayMethodType.CREDIT],
                    account_number="000000000000000000",
                ),
            ),
        )
        # notify new supplier business
        try:
            # new user welcome email
            await send_new_sup_user_welcome_msg(
                subject="Bienvenido a Alima",
                to_email={"name": f"{name}", "email": email},
            )
        except Exception as e:
            logger.warning("Error sending email to new user")
            logger.error(e)
        # build response
        return await self._build_supplier_business_gql(sup_bus_id, sup_user.id)

    async def edit_supplier_business(
        self,
        firebase_id: str,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        account: Optional[SupplierBusinessAccount] = None,
    ) -> SupplierBusinessGQL:  # type: ignore
        """Edit Supplier Business

        Args:
            firebase_id (str): firebase id
            id: unique supplier business id
            name (str): supplier business name, optional_
            country (str): supplier business country, optional
            notification_preference (NotificationChannelType): Chanel to notification, optional
            account (SupplierBusinessAccount): Supplier Business Account model, optional

        Raises:
            GQLApiException

        Returns:
            SupplierBusiness: Supplier Business model
        """
        # verify if business exists
        if not await self.repository.exists(id):
            raise GQLApiException(
                msg="Supplier Business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get supplier user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_user_dict = await self.supplier_user_repo.fetch(core_user.id)
        if not sup_user_dict or not sup_user_dict["id"]:  # type: ignore
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_user = SupplierUser(**sql_to_domain(sup_user_dict, SupplierUser))  # type: ignore
        # update supplier business
        if name or country or notification_preference:
            if not await self.repository.edit(
                id, name, country, notification_preference
            ):
                raise GQLApiException(
                    msg="Supplier Business not updated",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # add supplier business account
        if account:
            if not await self.account_repository.edit(
                supplier_business_id=id,
                account=account,
            ):
                raise GQLApiException(
                    msg="Supplier Business Account not updated",
                    error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
                )
        # build response
        return await self._build_supplier_business_gql(id, sup_user.id)

    async def search_supplier_business(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[SupplierBusiness]:
        return await self.repository.search(
            id, name, country, notification_preference, active, search
        )

    async def fetch_supplier_business_by_firebase_id(
        self, firebase_id: str
    ) -> SupplierBusinessGQL:
        """Fetch Supplier Business by firebase id

        Args:
            firebase_id (str): firebase id

        Raises:
            GQLApiException

        Returns:
            SupplierBusinessGQL: Supplier Business model
        """
        # get supplier user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_user_dict = await self.supplier_user_repo.fetch(core_user.id)
        if not sup_user_dict or not sup_user_dict["id"]:  # type: ignore
            raise GQLApiException(
                msg="Supplier User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_user = SupplierUser(**sql_to_domain(sup_user_dict, SupplierUser))  # type: ignore
        su_perms = await self.supplier_user_permission_repo.fetch(sup_user.id)
        if not su_perms:
            raise GQLApiException(
                msg="Supplier User Permission not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        s_business = await self.repository.fetch(su_perms["supplier_business_id"])
        sb_account = await self.account_repository.fetch(
            su_perms["supplier_business_id"]
        )
        # build response
        sgql = SupplierBusinessGQL(**s_business)
        sgql.account = SupplierBusinessAccount(**sb_account)
        sgql.permission = SupplierUserPermission(**su_perms)
        return sgql

    async def fetch_supplier_business(
        self, supplier_business_id: UUID
    ) -> SupplierBusinessGQL:
        """Fetch Supplier Business by firebase id

        Args:
            supplier_business_id (UUID): supplier business id

        Raises:
            GQLApiException

        Returns:
            SupplierBusinessGQL: Supplier Business model
        """
        # get supplier user
        s_business = await self.repository.fetch(supplier_business_id)
        sb_account = await self.account_repository.fetch(
            supplier_business_id=supplier_business_id
        )
        if not s_business or not sb_account:
            raise GQLApiException(
                msg="Supplier Business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # build response
        sgql = SupplierBusinessGQL(**s_business)
        sgql.account = SupplierBusinessAccount(**sb_account)
        return sgql

    async def patch_add_supplier_business_image(
        self, supplier_business_id, logo: Upload
    ) -> bool:
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        file_data: bytes = await logo.read()  # type: ignore
        # Split the path by '/'
        img_key = str(supplier_business_id)
        cloudinary_api.delete(
            folder=Folders.MARKETPLACE.value,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
            img_key=img_key,
        )
        route = cloudinary_api.upload(
            folder=Folders.MARKETPLACE.value,
            img_file=file_data,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
            img_key=img_key,
        )
        if "status" in route and route["status"] == "ok" and "data" in route:
            _resp = await self.repository.edit(
                id=supplier_business_id, logo_url=route["data"]
            )
            if not _resp:
                raise GQLApiException(
                    msg="Error to update supplier image url",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            return True
        else:
            raise GQLApiException(
                msg="Error to save supplier profile image url",
                error_code=GQLApiErrorCodeType.INSERT_CLOUDINARY_DB_ERROR.value,
            )

    async def delete_supplier_business_image(self, supplier_business_id) -> bool:
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        # Split the path by '/'
        img_key = str(supplier_business_id)
        cloudinary_api.delete(
            folder=Folders.MARKETPLACE.value,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.PROFILE.value}",
            img_key=img_key,
        )
        _resp = await self.repository.delete_image(
            supplier_business_id=supplier_business_id
        )
        if not _resp:
            raise GQLApiException(
                msg="Error to update supplier image url",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        return True
