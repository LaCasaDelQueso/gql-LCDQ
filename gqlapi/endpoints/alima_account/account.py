from typing import Optional
from gqlapi.handlers.b2bcommerce.ecommerce_seller import EcommerceSellerHandler
from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
from gqlapi.repository.b2bcommerce.ecommerce_seller import EcommerceSellerRepository
from gqlapi.repository.core.category import SupplierUnitCategoryRepository
from gqlapi.repository.core.invoice import MxSatCertificateRepository
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from starlette.background import BackgroundTasks
import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.alima_account.account import (
    ALIMA_PLANS_WITH_ECOMM,
    AlimaAccountPlan,
    AlimaAccountPlanDiscount,
    SupplierAlimaAccountConfigResult,
    SupplierAlimaAccountError,
    SupplierAlimaAccountResult,
)
from gqlapi.domain.models.v2.utils import PayProviderType
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.handlers.alima_account.account import (
    AlimaAccountHandler,
    AlimaAccountListener,
)
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.repository.alima_account.account import AlimaAccountRepository
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

# logger
logger = get_logger(get_app())


@strawberry.type
class AlimaAccountQuery:
    @strawberry.field(
        name="getSupplierAlimaAccountFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_alima_account_from_token(
        self, info: StrawberryInfo
    ) -> SupplierAlimaAccountResult:  # type: ignore
        """Get supplier Alima account from token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            SupplierAlimaAccountResult: supplier Alima account
        """
        logger.info("Get supplier Alima account from token")
        # instantiate handler
        _handler = AlimaAccountHandler(
            AlimaAccountRepository(info),
            CoreUserRepository(info),
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        sb_handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        # get supplier account by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get supplier alima account
            al_account = await _handler.fetch_supplier_alima_account_by_firebase_id(
                fb_id
            )
            # call handler to get supplier business account
            sup_business = await sb_handler.fetch_supplier_business_by_firebase_id(
                fb_id
            )
            # add if supplier business is displayed in marketplace
            if sup_business.account:
                al_account.displayed_in_marketplace = (
                    sup_business.active and sup_business.account.displays_in_marketplace
                )
            else:
                al_account.displayed_in_marketplace = False
            # [TO REV]: active cedis should already come from DB.
            # call handler to add num active cedis
            # al_account.active_cedis = await su_handler.count_supplier_units(
            #     al_account.supplier_business_id
            # )
            if al_account.account:
                al_account.active_cedis = al_account.account.active_cedis
            # return supplier business
            return al_account
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.field(
        name="getSupplierAlimaAccountConfigFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_alima_account_config_from_token(
        self, info: StrawberryInfo
    ) -> SupplierAlimaAccountConfigResult:  # type: ignore
        """Get supplier Alima account Saas Config from token

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:

        """
        logger.info("Get supplier Alima account from token")
        # instantiate handler
        _handler = AlimaAccountHandler(
            AlimaAccountRepository(info),
            CoreUserRepository(info),
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        # get supplier account by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get supplier alima account
            al_account = (
                await _handler.fetch_supplier_alima_account_config_by_firebase_id(fb_id)
            )
            return al_account
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )


@strawberry.type
class AlimaAccountMutation:
    @strawberry.mutation(
        name="createSupplierAlimaAccountFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def create_supplier_alima_account_from_token(
        self,
        info: StrawberryInfo,
        account_name: AlimaAccountPlan,
        payment_method: PayProviderType = PayProviderType.CARD_STRIPE,
        active_cedis: int = 1,
        discount: Optional[AlimaAccountPlanDiscount] = None,
    ) -> SupplierAlimaAccountResult:  # type: ignore
        """Create supplier Alima account from token

        Args:
            info (StrawberryInfo): info to connect to DB
            account_name (AlimaAccountPlan): account name
            payment_method (PayProviderType): payment method
            active_cedis (int): active cedis
            discount (Optional[AlimaAccountPlanDiscount]): discounts

        Returns:
            SupplierAlimaAccountResult
        """
        logger.info("Create supplier Alima account from token")
        # instantiate handler
        _handler = AlimaAccountHandler(
            AlimaAccountRepository(info),
            CoreUserRepository(info),
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        sb_handler = SupplierBusinessHandler(
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            CoreUserRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        su_handler = SupplierUnitHandler(
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
            unit_category_repo=SupplierUnitCategoryRepository(info),
            tax_info_repo=MxSatCertificateRepository(info),
        )
        ecomm_seller_handler = EcommerceSellerHandler(
            ecommerce_seller_repo=EcommerceSellerRepository(info),
            supplier_business_handler=sb_handler,
            supplier_unit_handler=su_handler,
        )

        # get supplier account by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler to get supplier business account
            sup_business = await sb_handler.fetch_supplier_business_by_firebase_id(
                fb_id
            )
            # create account
            al_account = await _handler.create_alima_account(
                sup_business,
                account_name,
                payment_method,
                active_cedis,
                fb_id,
                discount,
            )
            if al_account.account is None:
                return SupplierAlimaAccountError(
                    msg="Could not create paid account",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            # create account config
            acc_config_flag = await _handler.create_alima_account_config(
                al_account.account
            )
            if not acc_config_flag:
                logger.warning(
                    f"Could not create account config: Supplier Business ({al_account.supplier_business_id})"
                )
            if account_name in ALIMA_PLANS_WITH_ECOMM:
                # get supplier unit id
                sup_units = await su_handler.fetch_supplier_units(
                    al_account.supplier_business_id
                )
                if len(sup_units) > 0:
                    # Run following steps as background Tasks
                    bg_tasks = BackgroundTasks()
                    bg_tasks.add_task(
                        AlimaAccountListener.on_new_alima_supply_account_created,
                        _handler,
                        ecomm_seller_handler,
                        sup_business,
                        sup_units[0].id,
                    )
                    info.context["response"].background = bg_tasks
                    logger.info("Ecommerce sent for creation created")
                else:
                    logger.warning(
                        f"No Supplier Units found for Supplier Business ({al_account.supplier_business_id})"
                    )
            # return supplier business
            return al_account
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="updateSupplierAlimaAccountPlanFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def update_supplier_alima_account_plan_from_token(
        self,
        info: StrawberryInfo,
        account_name: AlimaAccountPlan,
    ) -> SupplierAlimaAccountResult:  # type: ignore
        """Create supplier Alima account from token

        Args:
            info (StrawberryInfo): info to connect to DB
            account_name (AlimaAccountPlan): account name

        Returns:
            SupplierAlimaAccountResult
        """
        logger.info("Create supplier Alima account from token")
        # instantiate handler
        _handler = AlimaAccountHandler(
            AlimaAccountRepository(info),
            CoreUserRepository(info),
            SupplierBusinessRepository(info),
            SupplierBusinessAccountRepository(info),
            SupplierUserRepository(info),
            SupplierUserPermissionRepository(info),
        )
        # get supplier account by firebas_id
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # get paid account
            al_account = await _handler.fetch_supplier_alima_account_by_firebase_id(
                fb_id
            )
            if al_account.account is None:
                return SupplierAlimaAccountError(
                    msg="Could not find paid account",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            # update plan
            is_plan_updated = await _handler.change_alima_account_plan(
                al_account.account, al_account.charges, account_name
            )
            if not is_plan_updated:
                return SupplierAlimaAccountError(
                    msg="Could not update plan",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            # return supplier business
            return await _handler.fetch_supplier_alima_account_by_firebase_id(fb_id)
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierAlimaAccountError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierAlimaAccountError(
                msg="Unexpected error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )
