from datetime import date
from typing import List
from uuid import UUID
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

import strawberry
from strawberry.types import Info as StrawberryInfo
from strawberry.file_uploads import Upload

from gqlapi.domain.interfaces.v2.supplier.supplier_price_list import (
    DeleteSupplierPriceListResult,
    DeleteSupplierPriceListStatus,
    SupplierPriceInput,
    SupplierPriceListBatchGQL,
    SupplierPriceListBatchResult,
    SupplierPriceListError,
    SupplierPriceListsGQL,
    SupplierPriceListsResult,
    SupplierUnitDefaultPriceListsGQL,
    SupplierUnitsDefaultPriceListsResult,
    UpdateOneSupplierPriceListResult,
    UpdateOneSupplierPriceListStatus,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.supplier.supplier_price_list import SupplierPriceListHandler
from gqlapi.handlers.supplier.supplier_product import SupplierProductHandler
from gqlapi.repository.core.category import CategoryRepository
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
from gqlapi.repository.supplier.supplier_price_list import SupplierPriceListRepository
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated

# logger
logger = get_logger(get_app())


@strawberry.type
class SupplierPriceListMutation:
    @strawberry.mutation(
        name="upsertSupplierPriceListByFile",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_upsert_supplier_price_list_file(
        self,
        info: StrawberryInfo,
        name: str,
        supplier_unit_ids: List[UUID],
        price_list_file: Upload,
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
    ) -> SupplierPriceListBatchResult:  # type: ignore
        logger.info("Upsert supplier price list in batch file")
        # validate input data
        if price_list_file.filename.split(".")[-1] != "xlsx":  # type: ignore
            # return False
            return SupplierPriceListBatchGQL(
                msg="Tu archivo tiene un formato incorrecto, debe de ser .xlsx",
                prices=[],
            )
        # instantiate handlers
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        try:
            price_list_file = await price_list_file.read()  # type: ignore
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            prices_feedback = await _handler.upsert_supplier_price_list_file(
                firebase_id,
                name=name,
                supplier_unit_ids=supplier_unit_ids,
                price_list_file=price_list_file,
                restaurant_branch_ids=restaurant_branch_ids,
                is_default=is_default,
                valid_until=valid_until,
            )
            # count successful loads
            success_count = len([x for x in prices_feedback if x.status is True])
            msg = (
                f"Tus precios se guardaron correctamente ({success_count} productos)."
                if success_count > 0
                else "No se guardaron los precios."
            )
            if (len(prices_feedback) - success_count) > 0:
                msg += (
                    f" {len(prices_feedback) - success_count} productos no se cargaron."
                )
            # compute results
            return SupplierPriceListBatchGQL(
                prices=prices_feedback,
                msg=msg,
            )
        except GQLApiException as ge:
            logger.warning(f"Error upserting supplier prices: {ge.msg}")
            return SupplierPriceListBatchGQL(
                msg=f"Hubo un error cargando tu lista de precio ({ge.msg})", prices=[]
            )
        except Exception as e:
            logger.error(e)
            return SupplierPriceListBatchGQL(
                msg=f"Hubo un error cargando tu lista de precio ({str(e)})", prices=[]
            )

    @strawberry.mutation(
        name="newSupplierPriceList",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_supplier_price_list(
        self,
        info: StrawberryInfo,
        name: str,
        supplier_unit_ids: List[UUID],
        restaurant_branch_ids: List[UUID],
        supplier_product_prices: List[SupplierPriceInput],
        is_default: bool,
        valid_until: date,
    ) -> SupplierPriceListBatchResult:  # type: ignore
        logger.info("New supplier price list")
        # map input data
        supplier_prices_dict = [
            {
                "supplier_product_id": x.supplier_product_id,
                "price": x.price,
                "valid_until": valid_until,
            }
            for x in supplier_product_prices
        ]
        # instantiate handlers
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        sp_handler.supplier_price_list_handler = _handler
        try:
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            prices_feedback = await _handler.new_supplier_price_list(
                firebase_id,
                name=name,
                supplier_unit_ids=supplier_unit_ids,
                supplier_prices=supplier_prices_dict,
                restaurant_branch_ids=restaurant_branch_ids,
                is_default=is_default,
                valid_until=valid_until,
            )
            # count successful loads
            success_count = len([x for x in prices_feedback if x.status is True])
            msg = (
                f"Tus precios se guardaron correctamente ({success_count} productos)."
                if success_count > 0
                else "No se guardaron los precios."
            )
            if (len(prices_feedback) - success_count) > 0:
                msg += (
                    f" {len(prices_feedback) - success_count} productos no se cargaron."
                )
            # compute results
            return SupplierPriceListBatchGQL(
                prices=prices_feedback,
                msg=msg,
            )
        except GQLApiException as ge:
            logger.warning(f"Error creating supplier price list: {ge.msg}")
            return SupplierPriceListBatchGQL(
                msg=f"Hubo un error creando tu lista de precio ({ge.msg})", prices=[]
            )
        except Exception as e:
            logger.error(e)
            return SupplierPriceListBatchGQL(
                msg=f"Hubo un error creando tu lista de precio ({str(e)})", prices=[]
            )

    @strawberry.mutation(
        name="editSupplierPriceList",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_supplier_price_list(
        self,
        info: StrawberryInfo,
        name: str,
        supplier_unit_ids: List[UUID],
        restaurant_branch_ids: List[UUID],
        supplier_product_prices: List[SupplierPriceInput],
        is_default: bool,
        valid_until: date,
    ) -> SupplierPriceListBatchResult:  # type: ignore
        logger.info("Edit supplier price list")
        # map input data
        supplier_prices_dict = [
            {
                "supplier_product_id": x.supplier_product_id,
                "price": x.price,
                "valid_until": valid_until,
            }
            for x in supplier_product_prices
        ]
        # instantiate handlers
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        sp_handler.supplier_price_list_handler = _handler
        try:
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            prices_feedback = await _handler.edit_supplier_price_list(
                firebase_id,
                name=name,
                supplier_unit_ids=supplier_unit_ids,
                supplier_prices=supplier_prices_dict,
                restaurant_branch_ids=restaurant_branch_ids,
                is_default=is_default,
                valid_until=valid_until,
            )
            # count successful loads
            success_count = len([x for x in prices_feedback if x.status is True])
            msg = (
                f"Tus precios se actualizaron correctamente ({success_count} productos)."
                if success_count > 0
                else "No se actualizaron los precios."
            )
            if (len(prices_feedback) - success_count) > 0:
                msg += f" {len(prices_feedback) - success_count} productos no se actualizaron."
            # compute results
            return SupplierPriceListBatchGQL(
                prices=prices_feedback,
                msg=msg,
            )
        except GQLApiException as ge:
            logger.warning(f"Error updating supplier price list: {ge.msg}")
            return SupplierPriceListBatchGQL(
                msg=f"Hubo un error actualizando tu lista de precio ({ge.msg})",
                prices=[],
            )
        except Exception as e:
            logger.error(e)
            return SupplierPriceListBatchGQL(
                msg=f"Hubo un error actualizando tu lista de precio ({str(e)})",
                prices=[],
            )
            
    @strawberry.mutation(
        name="editProductSupplierPriceList",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_product_of_supplier_price_list(
        self,
        info: StrawberryInfo,
        supplier_price_list_id: UUID,
        supplier_product_price_id: UUID,
        price: float,
    ) -> UpdateOneSupplierPriceListResult:  # type: ignore
        logger.info("Edit product supplier price list")
        # map input data

        # instantiate handlers
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        sp_handler.supplier_price_list_handler = _handler
        try:
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            prices_feedback = await _handler.edit_product_supplier_price_list(
                firebase_id, supplier_price_list_id, supplier_product_price_id, price
            )
            return UpdateOneSupplierPriceListStatus(
                msg="ok",
            )
        except GQLApiException as ge:
            logger.warning(f"Error updating supplier price list: {ge.msg}")
            return SupplierPriceListError(
                msg=f"Hubo un error actualizando tu lista de precio ({ge.msg})",
                code=ge.error_code,
            )
        except Exception as e:
            logger.error(e)
            return SupplierPriceListError(
                msg=f"Hubo un error actualizando tu lista de precio ({str(e)})",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="deleteSupplierPriceList",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def delete_supplier_price_list(
        self,
        info: StrawberryInfo,
        unit_id: UUID,
        supplier_product_price_list_id: UUID,
    ) -> DeleteSupplierPriceListResult:  # type: ignore
        logger.info("Delete supplier price list")
        # instantiate handlers
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        sp_handler.supplier_price_list_handler = _handler
        try:
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            await _handler.delete_supplier_price_list(
                firebase_id,
                unit_id=unit_id,
                supplier_product_price_list_id=supplier_product_price_list_id,
            )
            # count successful loads

            return DeleteSupplierPriceListStatus(
                msg="ok",
            )
        except GQLApiException as ge:
            logger.warning(f"Error deleting supplier price list: {ge.msg}")
            return SupplierPriceListError(
                msg=f"{ge.msg}",
                code=ge.error_code,
            )
        except Exception as e:
            logger.error(e)
            return SupplierPriceListError(
                msg=f"Hubo un error eliminando tu lista de precio ({str(e)})",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class SupplierPriceListQuery:
    @strawberry.mutation(
        name="getSupplierUnitPriceLists",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_unit_price_lists(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
    ) -> SupplierPriceListsResult:  # type: ignore
        logger.info("Get supplier unit price lists")
        # instantiate handler
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        try:
            # firebase
            # firebase_id = info.context["request"].user.firebase_user.firebase_id
            sp_prices = await _handler.fetch_supplier_price_lists(
                supplier_unit_id=supplier_unit_id,
            )
            # compute results
            return SupplierPriceListsGQL(
                price_lists=sp_prices,
            )
        except GQLApiException as ge:
            logger.warning(f"Error fetching supplier price lists: {ge.msg}")
            return SupplierPriceListError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierPriceListError(
                msg="Error upserting supplier price lists",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="getSupplierProductDefaultPriceLists",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_product_default_price_lists(
        self,
        info: StrawberryInfo,
        supplier_product_id: UUID,
    ) -> List[SupplierUnitsDefaultPriceListsResult]:  # type: ignore
        logger.info("Get supplier product price lists")
        # instantiate handler
        sp_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            # supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        _handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            _, supplier_business_id = await sp_handler.fetch_supplier_business(
                firebase_id
            )
            sp_prices = await _handler.fetch_supplier_product_default_price_list(
                supplier_product_id=supplier_product_id,
                supplier_business_id=supplier_business_id["id"],
            )
            # compute results
            return sp_prices
        except GQLApiException as ge:
            logger.warning(f"Error fetching supplier price lists: {ge.msg}")
            return [SupplierPriceListError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                SupplierPriceListError(
                    msg="Error upserting supplier price lists",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]
