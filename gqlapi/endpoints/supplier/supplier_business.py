from typing import Optional
from uuid import UUID

import strawberry
from strawberry.types import Info as StrawberryInfo
from strawberry.file_uploads import Upload
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

from gqlapi.domain.models.v2.supplier import (
    MinimumOrderValue,
    SupplierBusinessAccount,
    SupplierBusinessCommertialConditions,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessError,
    SupplierBusinessAccountInput,
    SupplierBusinessImageResult,
    SupplierBusinessImageStatus,
    SupplierBusinessResult,
)
from gqlapi.domain.models.v2.utils import NotificationChannelType, PayMethodType
from gqlapi.utils.helpers import serialize_encoded_file
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.handlers.supplier.supplier_business import (
    SupplierBusinessHandler,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessRepository,
    SupplierBusinessAccountRepository,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

logger = get_logger(get_app())


@strawberry.type
class SupplierBusinessMutation:
    @strawberry.mutation(
        name="newSupplierBusiness",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_supplier_business(
        self,
        info: StrawberryInfo,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
        account: SupplierBusinessAccountInput,
    ) -> SupplierBusinessResult:  # type: ignore
        logger.info("Create new supplier business")
        # data validation
        if (
            account.minimum_order_value is None
            or account.policy_terms is None
            or account.phone_number is None
            or account.email is None
            or account.business_type is None
        ):
            return SupplierBusinessError(
                msg="Missing required fields",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # instantiate handler
        _handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call
            _resp = await _handler.new_supplier_business(
                fb_id,
                name,
                country,
                notification_preference,
                account.business_type,
                account.phone_number,
                account.email,
                MinimumOrderValue(
                    measure=account.minimum_order_value.measure,
                    amount=account.minimum_order_value.amount,
                ),
                account.policy_terms,
                account.website,
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierBusinessError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierBusinessError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="updateSupplierBusiness",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_supplier_business(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        name: Optional[str] = "",
        country: Optional[str] = "",
        notification_preference: Optional[NotificationChannelType] = None,
        account: Optional[SupplierBusinessAccountInput] = None,
    ) -> SupplierBusinessResult:  # type: ignore
        logger.info("Edit supplier business")
        # data validation
        if not name and not country and not notification_preference and not account:
            return SupplierBusinessError(
                msg="Nothing to update",
                code=GQLApiErrorCodeType.EMPTY_DATA.value,
            )
        # instantiate handler
        _handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        try:
            _def_cc = None
            if (
                (account is not None)
                and (account.minimum_order_value is not None)
                and (account.policy_terms is not None)
            ):
                # only updating Commertial conditions if all fields are present
                _def_cc = SupplierBusinessCommertialConditions(
                    minimum_order_value=MinimumOrderValue(
                        measure=account.minimum_order_value.measure,
                        amount=account.minimum_order_value.amount,
                    ),
                    allowed_payment_methods=[
                        PayMethodType.CASH
                    ],  # Hard-coded because is deprecated
                    policy_terms=account.policy_terms,
                    account_number="000000000000000000",  # Hard-coded because is deprecated
                )
            # convert input to model
            account_model = None
            if account:
                account_model = SupplierBusinessAccount(
                    supplier_business_id=supplier_business_id,
                    incorporation_file=(
                        await serialize_encoded_file(account.incorporation_file)
                        if account.incorporation_file
                        else None
                    ),
                    legal_rep_id=(
                        await serialize_encoded_file(account.legal_rep_id)
                        if account.legal_rep_id
                        else None
                    ),
                    mx_sat_csf=(
                        await serialize_encoded_file(account.mx_sat_csf)
                        if account.mx_sat_csf
                        else None
                    ),
                    default_commertial_conditions=_def_cc,
                    **{
                        k: v
                        for k, v in account.__dict__.items()
                        if k
                        not in [
                            "minimum_order_value",
                            "allowed_payment_methods",
                            "policy_terms",
                            "account_number",
                            "mx_sat_csf",
                            "legal_rep_id",
                            "incorporation_file",
                        ]
                    }
                )
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call validation
            result = await _handler.edit_supplier_business(
                fb_id,
                supplier_business_id,
                name,
                country,
                notification_preference,
                account_model,
            )
            return result
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierBusinessError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierBusinessError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="deleteSupplierBusinessImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def delete_supplier_business_image(
        self, info: StrawberryInfo, supplier_business_id: UUID
    ) -> SupplierBusinessImageResult:  # type: ignore
        logger.info("Edit supplier business")
        # data validation
        if not supplier_business_id:
            return SupplierBusinessError(
                msg="Nothing add supplier image",
                code=GQLApiErrorCodeType.EMPTY_DATA.value,
            )
        # instantiate handler
        _handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        try:
            # call validation
            result = await _handler.delete_supplier_business_image(supplier_business_id)
            return SupplierBusinessImageStatus(
                msg="Upload supplier business image", status=result
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierBusinessError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierBusinessError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="addSupplierBusinessImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_add_supplier_business_image(
        self, info: StrawberryInfo, supplier_business_id: UUID, img_file: Upload
    ) -> SupplierBusinessImageResult:  # type: ignore
        logger.info("Edit supplier business")
        # data validation
        if not img_file or not supplier_business_id:
            return SupplierBusinessError(
                msg="Nothing add supplier image",
                code=GQLApiErrorCodeType.EMPTY_DATA.value,
            )
        # instantiate handler
        _handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        try:
            # call validation
            result = await _handler.patch_add_supplier_business_image(
                supplier_business_id, img_file
            )
            return SupplierBusinessImageStatus(
                msg="Upload supplier business image", status=result
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierBusinessError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierBusinessError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )


@strawberry.type
class SupplierBusinessQuery:
    @strawberry.field(
        name="getSupplierBusinessFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_business_from_token(
        self, info: StrawberryInfo
    ) -> SupplierBusinessResult:  # type: ignore
        """Get supplier business from token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            SupplierBusinessResult: supplier business model
        """
        logger.info("Get supplier business from token")
        # instantiate handler
        _handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        # get restaurant user by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _rest_bus = await _handler.fetch_supplier_business_by_firebase_id(fb_id)
            # return supplier business
            return _rest_bus
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierBusinessError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierBusinessError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )
