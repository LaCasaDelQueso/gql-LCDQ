from typing import List, Optional
from uuid import UUID
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

import strawberry
from strawberry.file_uploads import Upload
from strawberry.types import Info as StrawberryInfo
import pandas as pd

from gqlapi.domain.interfaces.v2.restaurant.restaurant_suppliers import (
    RestaurantSupplierAssignationResult,
    RestaurantSupplierBatchGQL,
    RestaurantSupplierBatchResult,
    RestaurantSupplierCreationResult,
    RestaurantSupplierError,
    RestaurantSupplierProductsResult,
    RestaurantSuppliersResult,
    SupplierProductCreationInput,
)
from gqlapi.domain.models.v2.utils import (
    NotificationChannelType,
)
from gqlapi.config import ALIMA_ADMIN_BRANCH
from gqlapi.handlers.restaurant.restaurant_branch import RestaurantBranchHandler
from gqlapi.handlers.services.image import SupplierProductImageHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.repository.services.image import ImageRepository
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.handlers.core.category import CategoryHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.app.permissions import (
    IsAlimaEmployeeAuthorized,
    IsAlimaRestaurantAuthorized,
    IsAuthenticated,
)
from gqlapi.handlers.restaurant.restaurant_suppliers import (
    RestaurantSupplierAssignationHandler,
    RestaurantSupplierHandler,
)
from gqlapi.repository.core.category import (
    CategoryRepository,
    RestaurantBranchCategoryRepository,
    SupplierUnitCategoryRepository,
)
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepository,
    RestaurantBusinessRepository,
)

from gqlapi.repository.restaurant.restaurant_suppliers import (
    RestaurantSupplierAssignationRepository,
)
from gqlapi.repository.restaurant.restaurant_user import (
    RestaurantUserPermissionRepository,
    RestaurantUserRepository,
)
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
    SupplierProductStockRepository,
)
from gqlapi.repository.supplier.supplier_unit import (
    SupplierUnitDeliveryRepository,
    SupplierUnitRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

# logger
logger = get_logger(get_app())


@strawberry.type
class RestaurantSuppliersMutation:
    @strawberry.mutation(
        name="newRestaurantSupplerAssignation",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_restaurant_supplier_assignation(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        supplier_business_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> RestaurantSupplierAssignationResult:  # type: ignore
        """new Restaurant Supplier Assignation

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            RestaurantBusinessResult: Restaurant bussines + restaurant business account model
        """
        logger.info("Create new restaurant_supplier_assignation")
        # instantiate handler
        _handler = RestaurantSupplierAssignationHandler(
            rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
            rest_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
        )
        # validate inputs
        if not (restaurant_branch_id and supplier_business_id):
            return RestaurantSupplierError(
                msg="Empty values for creating Restaurant Supplier Assignation",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if rating:
            if rating not in range(0, 6):
                return RestaurantSupplierError(
                    msg="Rating is out of range",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
        # call validation
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            _resp = await _handler.new_restaurant_supplier_assignation(
                restaurant_branch_id,
                supplier_business_id,
                fb_id,
                rating,
                review,
            )
            return _resp
        except GQLApiException as ge:
            return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(
        name="updateRestaurantSupplerAssignation", permission_classes=[IsAuthenticated]
    )
    async def patch_edit_restaurant_supplier_assignation(
        self,
        info: StrawberryInfo,
        rest_supp_assig_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> RestaurantSupplierAssignationResult:  # type: ignore
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            RestaurantBusinessResult: _description_
        """
        logger.info("Edit restaurant supplier assignation")
        # instantiate handler
        try:
            _handler = RestaurantSupplierAssignationHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
            )
            # validate inputs
            if not (rest_supp_assig_id) or not (review or rating):
                return RestaurantSupplierError(
                    msg="Empty values for updating Restaurant Supplier Assignation",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if rating:
                if rating not in range(0, 6):
                    return RestaurantSupplierError(
                        msg="Rating is out of range",
                        code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            # call validation
            return await _handler.edit_restaurant_supplier_assignation(
                rest_supp_assig_id,
                rating,
                review,
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return RestaurantSupplierError(
                msg="Error editing restaurant supplier assignation",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="newRestaurantSupplerCreation",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_restaurant_supplier_creation(
        self,
        info: StrawberryInfo,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
        category_id: UUID,
        restaurant_branch_id: UUID,
        email: str,
        phone_number: str,
        contact_name: str,
        unit_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        zip_code: Optional[str] = None,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        catalog: Optional[List[SupplierProductCreationInput]] = None,
    ) -> RestaurantSupplierCreationResult:  # type: ignore
        """Create a new restaurant's supplier

        Args:
            info (StrawberryInfo): info to connect to DB
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides. Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None.
                }
            . Defaults to None.

        Returns:
            RestaurantBusinessResult: _description_
        """
        logger.info("Creation restaurant supplier creation")
        # instantiate handler
        try:
            _handler = RestaurantSupplierHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                category_repo=CategoryRepository(info),
                supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                supp_business_account_repo=SupplierBusinessAccountRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
                product_repo=ProductRepository(info),
                supp_prod_price_repo=SupplierProductPriceRepository(info),
            )
            # validate inputs
            if not name and not country and not email and not phone_number:
                return RestaurantSupplierError(
                    msg="Empty values for creating Restaurant Supplier",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if rating:
                if rating not in range(0, 6):
                    return RestaurantSupplierError(
                        msg="Rating is out of range",
                        code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            # call validation
            fb_id = info.context["request"].user.firebase_user.firebase_id

            restaurant_assignation = await _handler.search_restaurant_branch_supplier(
                restaurant_branch_id=restaurant_branch_id,
                supplier_business_name=name,
            )
            if restaurant_assignation:
                return RestaurantSupplierError(
                    msg="restaurant_supplier_already exists",
                    code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )

            rest_supp_creation = await _handler.new_restaurant_supplier_creation(
                name,
                country,
                notification_preference,
                category_id,
                restaurant_branch_id,
                email,
                phone_number,
                contact_name,
                fb_id,
                unit_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                zip_code,
                rating,
                review,
                catalog,
            )
            return rest_supp_creation
        except GQLApiException as ge:
            logger.warning(ge)
            return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return RestaurantSupplierError(
                msg="Error creating restaurant supplier",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="updateRestaurantSupplerCreation",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_restaurant_supplier_creation(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        category_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        contact_name: Optional[str] = None,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        catalog: Optional[List[SupplierProductCreationInput]] = None,
    ) -> RestaurantSupplierCreationResult:  # type: ignore
        """Update restaurant's supplier

        Args:
            info (StrawberryInfo): info to connect to DB
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides. Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None.
                }
            . Defaults to None.

        Returns:
            RestaurantBusinessResult
        """
        logger.info("Creation restaurant supplier creation")
        # instantiate handler
        try:
            _handler = RestaurantSupplierHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                category_repo=CategoryRepository(info),
                supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                supp_business_account_repo=SupplierBusinessAccountRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
                product_repo=ProductRepository(info),
                supp_prod_price_repo=SupplierProductPriceRepository(info),
            )
            # validate inputs
            if not (
                name
                or country
                or email
                or phone_number
                or notification_preference
                or category_id
                or restaurant_branch_id
                or contact_name
                or rating
                or review
                or catalog
            ):
                return RestaurantSupplierError(
                    msg="Empty values for updating Restaurant Supplier",
                    code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            if rating:
                if rating not in range(0, 6):
                    return RestaurantSupplierError(
                        msg="Rating is out of range",
                        code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            # call validation
            fb_id = info.context["request"].user.firebase_user.firebase_id
            edited_res = await _handler.edit_restaurant_supplier_creation(
                supplier_business_id,
                fb_id,
                name,
                country,
                notification_preference,
                category_id,
                restaurant_branch_id,
                email,
                phone_number,
                contact_name,
                rating,
                review,
                catalog,
            )
            return edited_res
        except GQLApiException as ge:
            logger.warning(ge)
            return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return RestaurantSupplierError(
                msg="Error updating restaurant supplier",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="newSupplierFile",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def post_new_supplier_file(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        product_file: Upload,
        supplier_file: Upload,
    ) -> RestaurantSupplierBatchResult:  # type: ignore
        # firebase
        firebase_id = info.context["request"].user.firebase_user.firebase_id
        # file validation
        if supplier_file.filename.split(".")[-1] != "xlsx" or product_file.filename.split(".")[-1] != "xlsx":  # type: ignore
            # return False
            return RestaurantSupplierError(
                msg="Wrong file format",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            df_supplier = pd.read_excel(await supplier_file.read())  # type: ignore
            df_product = pd.read_excel(await product_file.read())  # type: ignore
            # Leer products
            logger.info("Create new_supplier_batch")
            # instantiate handler
            _handler = RestaurantSupplierHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                category_repo=CategoryRepository(info),
                supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                supp_business_account_repo=SupplierBusinessAccountRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
                product_repo=ProductRepository(info),
                supp_prod_price_repo=SupplierProductPriceRepository(info),
            )
            _handler_category = CategoryHandler(category_repo=CategoryRepository(info))
            _handler_assignation = RestaurantSupplierAssignationHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info=info),
                rest_branch_repo=RestaurantBranchRepository(info=info),
            )
            _handler_supp_business = SupplierBusinessHandler(
                supplier_business_repo=SupplierBusinessRepository(info)
            )
            _handler_rest_branch = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
            )
            supplier_batch = {}
        except GQLApiException as ge:
            return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)

        # validate inputs
        if not supplier_file and not restaurant_branch_id:
            # return False
            return RestaurantSupplierError(
                msg="Empty values for creating Supplier Batch",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # # call validation
        if not df_supplier.empty:
            try:
                supplier_batch["suppliers"] = await _handler.upload_suppliers(
                    df_supplier=df_supplier,
                    _handler_supp_business=_handler_supp_business,
                    _handler_assignation=_handler_assignation,
                    _handler_category=_handler_category,
                    restaurant_branch_id=restaurant_branch_id,
                    firebase_id=firebase_id,
                    _handler_rest_branch=_handler_rest_branch,
                )
            except GQLApiException as ge:
                return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        else:
            supplier_batch["msg"] = "No se crearon proveedores."
            supplier_batch["suppliers"] = []
            supplier_batch["products"] = []
            return RestaurantSupplierBatchGQL(**supplier_batch)

        if not df_product.empty:
            try:
                supplier_batch["products"] = await _handler.upload_product(
                    df_product=df_product,
                    restaurant_branch_id=restaurant_branch_id,
                    firebase_id=firebase_id,
                )
            except GQLApiException as ge:
                return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        else:
            supplier_batch["products"] = []
        # compute results
        supplier_batch = _handler.compute_result(supplier_batch)

        return RestaurantSupplierBatchGQL(**supplier_batch)

    @strawberry.mutation(
        name="editSupplierFile",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def patch_edit_supplier_file(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        product_file: Upload,
        supplier_file: Upload,
    ) -> RestaurantSupplierBatchResult:  # type: ignore
        # firebase
        firebase_id = info.context["request"].user.firebase_user.firebase_id

        # file validation
        if supplier_file.filename.split(".")[-1] != "xlsx" or product_file.filename.split(".")[-1] != "xlsx":  # type: ignore
            # return False
            return RestaurantSupplierError(
                msg="Wrong file format",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            df_supplier = pd.read_excel(await supplier_file.read())  # type: ignore
            df_product = pd.read_excel(await product_file.read())  # type: ignore
            # Leer products
            logger.info("Create new_supplier_batch")
            # instantiate handler
            _handler = RestaurantSupplierHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                category_repo=CategoryRepository(info),
                supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                supp_business_account_repo=SupplierBusinessAccountRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
                product_repo=ProductRepository(info),
                supp_prod_price_repo=SupplierProductPriceRepository(info),
            )
            _handler_category = CategoryHandler(category_repo=CategoryRepository(info))
            _handler_assignation = RestaurantSupplierAssignationHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info=info),
                rest_branch_repo=RestaurantBranchRepository(info=info),
            )
            _handler_supp_business = SupplierBusinessHandler(
                supplier_business_repo=SupplierBusinessRepository(info)
            )
            _handler_rest_branch = RestaurantBranchHandler(
                restaurant_branch_repo=RestaurantBranchRepository(info),
                branch_category_repo=RestaurantBranchCategoryRepository(info),
            )
            supplier_batch = {}
        except GQLApiException as ge:
            return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)

        # validate inputs
        if not supplier_file and not restaurant_branch_id:
            # return False
            return RestaurantSupplierError(
                msg="Empty values for creating Supplier Batch",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        # # call validation
        if not df_supplier.empty:
            try:
                supplier_batch["suppliers"] = await _handler.upload_suppliers(
                    df_supplier=df_supplier,
                    _handler_supp_business=_handler_supp_business,
                    _handler_assignation=_handler_assignation,
                    _handler_category=_handler_category,
                    _handler_rest_branch=_handler_rest_branch,
                    restaurant_branch_id=restaurant_branch_id,
                    firebase_id=firebase_id,
                )
            except GQLApiException as ge:
                return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        else:
            supplier_batch["msg"] = "No se crearon proveedores."
            supplier_batch["suppliers"] = []
            supplier_batch["products"] = []
            return RestaurantSupplierBatchGQL(**supplier_batch)

        if not df_product.empty:
            try:
                supplier_batch["products"] = await _handler.update_product(
                    df_product=df_product,
                    restaurant_branch_id=restaurant_branch_id,
                    firebase_id=firebase_id,
                )
            except GQLApiException as ge:
                return RestaurantSupplierError(msg=ge.msg, code=ge.error_code)
        else:
            supplier_batch["products"] = []
        # compute results
        supplier_batch = _handler.compute_result(supplier_batch)

        return RestaurantSupplierBatchGQL(**supplier_batch)


@strawberry.type
class RestaurantSuppliersQuery:
    @strawberry.field(
        name="getRestaurantSuppliersAssignation",
        permission_classes=[IsAuthenticated, IsAlimaEmployeeAuthorized],
    )
    async def get_restaurant_supplier_assignation(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> List[RestaurantSupplierAssignationResult]:  # type: ignore
        """Get restaurant supplier assignation

        Args:
            info (StrawberryInfo): info to connect to DB

        Returns:
            List[RestaurantUserResult]: {
            } list
        """
        logger.info("get restaurant suppliers assignation")
        # instantiate handler
        try:
            _handler = RestaurantSupplierAssignationHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
            )
            # call validation
            return await _handler.fetch_restaurant_suppliers_assignation(
                restaurant_branch_id
            )
        except GQLApiException as ge:
            return [RestaurantSupplierError(msg=ge.msg, code=ge.error_code)]

    @strawberry.field(
        name="getRestaurantSuppliers",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_restaurant_suppliers(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: Optional[UUID] = None,
        restaurant_supplier_id: Optional[UUID] = None,
        with_prods: Optional[bool] = True,
    ) -> List[RestaurantSuppliersResult]:  # type: ignore
        """Get restaurant suppliers from a given token

        Parameters
        ----------
        info : StrawberryInfo
        restaurant_branch_id : Optional[UUID], optional
            Restaurant branch id, by default None
        restaurant_supplier_id : Optional[UUID], optional
            Restaurant supplier id, by default None
        with_prods : Optional[bool], optional

        Returns
        -------
        RestaurantSuppliersResult
        """
        logger.info("get restaurant suppliers")
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # instantiate handler
            im_handler = SupplierProductImageHandler(
                image_repo=ImageRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
            )
            _handler = RestaurantSupplierAssignationHandler(
                core_user_repo=CoreUserRepository(info),
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                supplier_business_account_repo=SupplierBusinessAccountRepository(info),
                supplier_unit_repo=SupplierUnitRepository(info),
                supplier_unit_category_repo=SupplierUnitCategoryRepository(info),
                supplier_product_repo=SupplierProductRepository(info),
                supplier_product_price_repo=SupplierProductPriceRepository(info),
                restaurant_user_repo=RestaurantUserRepository(info),
                restaurant_perm_repo=RestaurantUserPermissionRepository(info),
                restaurant_business_repo=RestaurantBusinessRepository(info),
                supplier_unit_delivery_repo=SupplierUnitDeliveryRepository(info),
                supplier_product_image_handler=im_handler,
                supplier_product_stock_repo=SupplierProductStockRepository(info),
            )
            # call validation
            res_sup = await _handler.fetch_restaurant_suppliers(
                fb_id,
                restaurant_branch_id,
                restaurant_supplier_id,
                with_prods,
            )
            return res_sup
        except GQLApiException as ge:
            logger.warning(ge)
            return [RestaurantSupplierError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                RestaurantSupplierError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]

    @strawberry.field(
        name="getAllRestaurantSupplierProducts",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_all_restaurant_supplier_products(
        self,
        info: StrawberryInfo,
        supplier_business_ids: List[UUID],
    ) -> List[RestaurantSupplierProductsResult]:  # type: ignore
        """Get restaurant suppliers from a given token

        Parameters
        ----------
        info : StrawberryInfo
        supplier_business_ids : List[UUID]
            Supplier business ids

        Returns
        -------
        """
        logger.info("get restaurant supplier prods")
        try:
            # [TODO] - verify whether user has access to these suppliers
            # fb_id = info.context["request"].user.firebase_user.firebase_id

            # instantiate handler
            _handler = RestaurantSupplierHandler(
                rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
                rest_branch_repo=RestaurantBranchRepository(info),
                core_user_repo=CoreUserRepository(info),
                supplier_business_repo=SupplierBusinessRepository(info),
                supp_business_account_repo=SupplierBusinessAccountRepository(info),
                category_repo=CategoryRepository(info),
                supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
                supp_unit_repo=SupplierUnitRepository(info),
                product_repo=ProductRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
                supp_prod_price_repo=SupplierProductPriceRepository(info),
            )
            # call
            res_sup_prods = await _handler.find_restaurant_supplier_products(
                supplier_business_ids=supplier_business_ids,
            )
            return res_sup_prods
        except GQLApiException as ge:
            return [RestaurantSupplierError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                RestaurantSupplierError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]

    @strawberry.field(
        name="getMarketplaceSuppliers",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_marketplace_restaurant_suppliers(
        self,
        info: StrawberryInfo,
        restaurant_branch_id: UUID,
        supplier_unit_id: Optional[UUID] = None,
    ) -> List[RestaurantSuppliersResult]:  # type: ignore
        """Get restaurant suppliers available for given branch

        Parameters
        ----------
        info : StrawberryInfo
        restaurant_branch_id : UUID
            Restaurant branch id

        Returns
        -------
        List[RestaurantSuppliersResult]
        """
        logger.info("get marketplace suppliers")
        # instantiate handler
        im_handler = SupplierProductImageHandler(
            image_repo=ImageRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
        )
        _handler = RestaurantSupplierHandler(
            rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
            rest_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            supp_business_account_repo=SupplierBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            product_repo=ProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            supp_prod_price_repo=SupplierProductPriceRepository(info),
            supplier_product_image_handler=im_handler,
            supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        sp_handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            product_repo=ProductRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
        )
        try:
            # call validation
            res_sup = await _handler.find_available_marketplace_suppliers(
                restaurant_branch_id,
            )
            if supplier_unit_id:
                # fetch products with latest price
                _prods = await _handler.find_products_with_price(
                    sp_handler, supplier_unit_id, restaurant_branch_id
                )
                for rs in res_sup:
                    if not rs.unit:
                        continue
                    if rs.unit[0].supplier_unit.id == supplier_unit_id:
                        rs.products = _prods
                        return [rs]  # early return with only the supplier needed
            return res_sup
        except GQLApiException as ge:
            logger.warning(ge)
            return [RestaurantSupplierError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                RestaurantSupplierError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]

    @strawberry.field(
        name="getPublicMarketplaceSuppliers",
        permission_classes=[],
    )
    async def get_public_marketplace_restaurant_suppliers(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
    ) -> List[RestaurantSuppliersResult]:  # type: ignore
        """Get public restaurant suppliers available for given branch

        Parameters
        ----------
        info : StrawberryInfo
        restaurant_branch_id : UUID
            Restaurant branch id

        Returns
        -------
        List[RestaurantSuppliersResult]
        """
        logger.info("get marketplace suppliers")
        # instantiate handler
        im_handler = SupplierProductImageHandler(
            image_repo=ImageRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
        )
        _handler = RestaurantSupplierHandler(
            rest_supp_assig_repo=RestaurantSupplierAssignationRepository(info),
            rest_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_business_repo=SupplierBusinessRepository(info),
            supp_business_account_repo=SupplierBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            supp_unit_cat_repo=SupplierUnitCategoryRepository(info),
            supp_unit_repo=SupplierUnitRepository(info),
            product_repo=ProductRepository(info),
            supp_prod_repo=SupplierProductRepository(info),
            supp_prod_price_repo=SupplierProductPriceRepository(info),
            supplier_product_image_handler=im_handler,
        )
        sp_handler = SupplierRestaurantsHandler(
            supplier_restaurants_repo=SupplierRestaurantsRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            core_user_repo=CoreUserRepository(info),
            restaurant_business_repo=RestaurantBusinessRepository(info),
            restaurant_business_account_repo=RestaurantBusinessAccountRepository(info),
            category_repo=CategoryRepository(info),
            restaurant_branch_category_repo=RestaurantBranchCategoryRepository(info),
            product_repo=ProductRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
        )
        try:
            # call validation
            restaurant_branch_id = UUID(ALIMA_ADMIN_BRANCH)
            res_sup = await _handler.find_available_marketplace_suppliers(
                restaurant_branch_id,
            )
            # fetch products with latest price
            _prods = await _handler.find_products_with_price(
                sp_handler, supplier_unit_id, restaurant_branch_id
            )
            for rs in res_sup:
                if not rs.unit:
                    continue
                if rs.unit[0].supplier_unit.id == supplier_unit_id:
                    rs.products = _prods
                    return [rs]  # early return with only the supplier needed
            return res_sup
        except GQLApiException as ge:
            logger.warning(ge)
            return [RestaurantSupplierError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                RestaurantSupplierError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]
