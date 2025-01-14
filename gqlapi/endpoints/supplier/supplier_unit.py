from typing import List, Optional
from uuid import UUID
from gqlapi.repository.core.invoice import MxSatCertificateRepository

import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.models.v2.supplier import DeliveryOptions
from gqlapi.domain.models.v2.utils import PayMethodType, ServiceDay
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import (
    SupplierUnitContactInfo,
    SupplierUnitDeliveryOptionsInput,
    SupplierUnitError,
    SupplierUnitResult,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.handlers.supplier.supplier_unit import SupplierUnitHandler
from gqlapi.repository.core.category import (
    CategoryRepository,
    SupplierUnitCategoryRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.repository.user.employee import EmployeeRepository
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated
from gqlapi.utils.domain_mapper import domain_inp_to_out

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


@strawberry.type
class SupplierUnitMutation:
    # [TODO] - validate whether the user is allowed to create a unit
    @strawberry.mutation(
        name="newSupplierUnit",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_supplier_unit(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        unit_name: str,
        full_address: str,
        street: str,
        external_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        category_id: UUID,
        allowed_payment_methods: List[PayMethodType],
        account_number: str,
        delivery_options: SupplierUnitDeliveryOptionsInput,
        internal_num: str = "",
    ) -> SupplierUnitResult:  # type: ignore
        logger.info("Create new supplier unit")
        # instantiate handler
        _handler = SupplierUnitHandler(
            supplier_unit_repo=SupplierUnitRepository(info),
            unit_category_repo=SupplierUnitCategoryRepository(info),
            supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
            category_repo=CategoryRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            employee_repo=EmployeeRepository(info),
            tax_info_repo=MxSatCertificateRepository(info),
        )
        # call validation
        if (
            not supplier_business_id
            or not unit_name
            or not full_address
            or not street
            or not external_num
            or not zip_code
            or not neighborhood
            or not city
            or not state
            or not country
            or not category_id
        ):
            return SupplierUnitError(
                msg="Empty values for creating Supplier Unit",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # map delivery options
        delivery_options_out = DeliveryOptions(
            **domain_inp_to_out(delivery_options, DeliveryOptions)
        )
        delivery_options_out.service_hours = [
            ServiceDay(**domain_inp_to_out(sh, ServiceDay))
            for sh in delivery_options.service_hours
        ]
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_supplier_unit(
                supplier_business_id,
                unit_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                country,
                zip_code,
                fb_id,
                category_id,
                delivery_options_out,
                allowed_payment_methods,
                account_number,
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUnitError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUnitError(
                msg="Error creating supplier unit",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    # [TODO] - validate whether the user is allowed to update a unit
    @strawberry.mutation(
        name="updateSupplierUnit",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_supplier_unit(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
        unit_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        category_id: Optional[UUID] = None,
        deleted: Optional[bool] = None,
        delivery_options: Optional[SupplierUnitDeliveryOptionsInput] = None,
        internal_num: Optional[str] = None,
        allowed_payment_methods: Optional[List[PayMethodType]] = None,
        account_number: Optional[str] = None,
    ) -> SupplierUnitResult:  # type: ignore
        logger.info("Update supplier unit")
        # instantiate handler
        _handler = SupplierUnitHandler(
            supplier_unit_repo=SupplierUnitRepository(info),
            unit_category_repo=SupplierUnitCategoryRepository(info),
            supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
            category_repo=CategoryRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            employee_repo=EmployeeRepository(info),
            tax_info_repo=MxSatCertificateRepository(info),
        )
        # call validation
        if (
            unit_name is None
            and full_address is None
            and street is None
            and external_num is None
            and zip_code is None
            and neighborhood is None
            and city is None
            and state is None
            and country is None
            and category_id is None
            and delivery_options is None
            and internal_num is None
            and deleted is None
        ):
            return SupplierUnitError(
                msg="Empty values for updating Supplier Unit",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # map delivery options
        dopts_model = None
        if delivery_options:
            # delivery options have to be passed as a full object
            dopts_model = DeliveryOptions(
                **domain_inp_to_out(delivery_options, DeliveryOptions)
            )
            dopts_model.service_hours = [
                ServiceDay(**domain_inp_to_out(sh, ServiceDay))
                for sh in delivery_options.service_hours
            ]
        try:
            # call handler
            result = await _handler.edit_supplier_unit(
                supplier_unit_id,
                unit_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                country,
                zip_code,
                category_id,
                deleted,
                dopts_model,
                allowed_payment_methods,
                account_number,
            )
            return result
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierUnitError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierUnitError(
                msg="Error updating supplier unit",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class SupplierUnitQuery:
    @strawberry.field(
        name="getSupplierUnitsFromToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_units_from_token(
        self,
        info: StrawberryInfo,
        supplier_unit_id: Optional[UUID] = None,
    ) -> List[SupplierUnitResult]:  # type: ignore
        """Get supplier units from token

        Args:
            info (StrawberryInfo): info to connect to DB Defaults to None.

        Returns:
            List[SupplierUnitResult]: list of supplier units
        """
        logger.info("Get supplier units from token")
        # instantiate handler
        try:
            _handler = SupplierUnitHandler(
                supplier_unit_repo=SupplierUnitRepository(info),
                unit_category_repo=SupplierUnitCategoryRepository(info),
                supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
                category_repo=CategoryRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                employee_repo=EmployeeRepository(info),
                tax_info_repo=MxSatCertificateRepository(info),
            )
            supb_handler = SupplierBusinessHandler(
                supplier_business_repo=SupplierBusinessRepository(info),
                supplier_user_repo=SupplierUserRepository(info),
                supplier_user_permission_repo=SupplierUserPermissionRepository(info),
                supplier_business_account_repo=SupplierBusinessAccountRepository(info),
                core_user_repo=CoreUserRepository(info),
            )
            # get FB id from context
            fb_id = info.context["request"].user.firebase_user.firebase_id
            sbiz = await supb_handler.fetch_supplier_business_by_firebase_id(fb_id)
            _contact_info = SupplierUnitContactInfo(
                business_name=sbiz.name,
                display_name=sbiz.account.legal_rep_name if sbiz.account else "",
                email=sbiz.account.email if sbiz.account else "",
                phone_number=sbiz.account.phone_number if sbiz.account else "",
            )
            # call handler
            sunits = await _handler.fetch_suppliers_asoc_with_user(
                fb_id,
                supplier_unit_id,
            )
            # add business contact info
            for su in sunits:
                su.contact_info = _contact_info
            # return supplier units
            return sunits
        except GQLApiException as ge:
            logger.warning(ge)
            return [SupplierUnitError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                SupplierUnitError(
                    msg="Error fetching supplier units",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]
