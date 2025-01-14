import base64
import datetime
from io import BytesIO, StringIO
import json
from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.catalog.product import ProductError
import pandas as pd

import strawberry
from strawberry.types import Info as StrawberryInfo
from strawberry.file_uploads import Upload
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.handlers.supplier.supplier_price_list import SupplierPriceListHandler
from gqlapi.repository.restaurant.restaurant_branch import RestaurantBranchRepository
from gqlapi.repository.supplier.supplier_price_list import SupplierPriceListRepository
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.utils.batch_files import INTEGER_UOMS
from gqlapi.handlers.supplier.supplier_product import SupplierProductHandler
from gqlapi.repository.core.category import CategoryRepository
from gqlapi.repository.core.product import ProductRepository
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
from gqlapi.repository.supplier.supplier_product import (
    SupplierProductPriceRepository,
    SupplierProductRepository,
    SupplierProductStockRepository,
)
from gqlapi.repository.supplier.supplier_user import (
    SupplierUserPermissionRepository,
    SupplierUserRepository,
)
from gqlapi.repository.user.core_user import CoreUserRepository
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    ExportProductGQL,
    ExportSupplierProductResult,
    SupplierProductDetailsListResult,
    SupplierProductError,
    SupplierProductStockInput,
    SupplierProductTagInput,
    SupplierProductsBatchGQL,
    SupplierProductsBatchResult,
    SupplierProductsBatchStockGQL,
    SupplierProductsDetailsListGQL,
    SupplierProductsStockBatchResult,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.app.permissions import IsAlimaSupplyAuthorized, IsAuthenticated

logger = get_logger(get_app())


@strawberry.type
class SupplierProductMutation:
    @strawberry.mutation(
        name="upsertSupplierProductsByFile",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_upsert_supplier_products_file(
        self,
        info: StrawberryInfo,
        product_file: Upload,
        # supplier_unit_id: UUID,
    ) -> SupplierProductsBatchResult:  # type: ignore
        logger.info("Upsert supplier products in batch file")
        # file validation
        if product_file.filename.split(".")[-1] != "xlsx":  # type: ignore
            # return False
            return SupplierProductsBatchGQL(
                msg="Tu archivo tiene un formato incorrecto, debe de ser .xlsx",
                products=[],
            )
        # instantiate handler
        _handler = SupplierProductHandler(
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
        spl_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=_handler,
        )
        _handler.supplier_price_list_handler = spl_handler
        try:
            product_file = await product_file.read()  # type: ignore
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prods_feedback = await _handler.upsert_supplier_products_file(
                firebase_id,
                product_file=product_file,
            )
            # count successful loads
            success_count = len([x for x in sup_prods_feedback if x.status is True])
            msg = (
                f"Tus productos se guardaron correctamente ({success_count} productos)"
                if success_count > 0
                else "No se guardaron productos"
            )
            # compute results
            return SupplierProductsBatchGQL(
                products=sup_prods_feedback,
                msg=msg,
            )
        except GQLApiException as ge:
            logger.warning(f"Error upserting supplier products: {ge.msg}")
            return SupplierProductsBatchGQL(
                msg=f"Hubo un error cargando tus productos ({ge.msg})", products=[]
            )
        except Exception as e:
            logger.error(e)
            return SupplierProductsBatchGQL(
                msg=f"Hubo un error cargando tus productos ({str(e)})", products=[]
            )

    @strawberry.mutation(
        name="upsertSupplierProductsStockByFile",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_upsert_supplier_products_stock_file(
        self,
        info: StrawberryInfo,
        product_stock_file: Upload,
        supplier_unit_ids: List[UUID],
        # supplier_unit_id: UUID,
    ) -> SupplierProductsStockBatchResult:  # type: ignore
        logger.info("Upsert supplier products in batch file")
        # file validation
        if product_stock_file.filename.split(".")[-1] != "xlsx":  # type: ignore
            # return False
            return SupplierProductsBatchStockGQL(
                msg="Tu archivo tiene un formato incorrecto, debe de ser .xlsx",
                stock=[],
            )
        # instantiate handler
        _handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        spl_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=_handler,
        )
        _handler.supplier_price_list_handler = spl_handler
        try:
            product_stock_file = await product_stock_file.read()  # type: ignore
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prods_feedback = await _handler.upsert_supplier_products_stock_file(
                firebase_id,
                product_stock_file=product_stock_file,
                supplier_units=supplier_unit_ids,
            )
            # count successful loads
            success_count = len([x for x in sup_prods_feedback if x.status is True])
            msg = (
                f"Tu inventario se guardo correctamente ({success_count} productos)"
                if success_count > 0
                else "No se guardaron productos"
            )
            # compute results
            return SupplierProductsBatchStockGQL(
                stock=sup_prods_feedback,
                msg=msg,
            )
        except GQLApiException as ge:
            logger.warning(f"Error upserting supplier products: {ge.msg}")
            return SupplierProductsBatchStockGQL(
                stock=[],
                msg=f"Hubo un error cargando tus productos ({ge.msg})"
            )
        except Exception as e:
            logger.error(e)
            return SupplierProductsBatchStockGQL(
                stock=[],
                msg=f"Hubo un error cargando tus productos ({str(e)})"
            )

    @strawberry.mutation(
        name="newSupplierStockList",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_supplier_stock_list(
        self,
        info: StrawberryInfo,
        supplier_unit_ids: List[UUID],
        supplier_product_stock: List[SupplierProductStockInput],
    ) -> SupplierProductsStockBatchResult:  # type: ignore
        logger.info("New supplier stock list")
        # map input data
        supplier_stock_dict = [
            {
                "supplier_product_id": x.supplier_product_id,
                "stock": x.stock if x.stock is not None else 0,
                "keep_selling_without_stock": x.keep_selling_without_stock,
                "active": x.active,
                "sku": x.sku,
            }
            for x in supplier_product_stock
        ]
        # instantiate handler
        _handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        spl_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=_handler,
        )
        _handler.supplier_price_list_handler = spl_handler
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prods_feedback = await _handler.upsert_supplier_products_stock_list(
                firebase_id,
                supplier_stock=supplier_stock_dict,
                supplier_units=supplier_unit_ids,
            )
            # count successful loads
            success_count = len([x for x in sup_prods_feedback if x.status is True])
            msg = (
                f"Tu inventario se guardo correctamente ({success_count} productos)"
                if success_count > 0
                else "No se guardaron productos"
            )
            # compute results
            return SupplierProductsBatchStockGQL(
                stock=sup_prods_feedback,
                msg=msg,
            )
        except GQLApiException as ge:
            logger.warning(f"Error upserting supplier products: {ge.msg}")
            return SupplierProductsBatchStockGQL(
                stock=[],
                msg=f"Hubo un error cargando tus productos ({ge.msg})"
            )
        except Exception as e:
            logger.error(e)
            return SupplierProductsBatchStockGQL(
                stock=[],
                msg=f"Hubo un error cargando tus productos ({str(e)})"
            )

    @strawberry.mutation(
        name="newSupplierProduct",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_supplier_product(
        self,
        info: StrawberryInfo,
        supplier_business_id: UUID,
        sku: str,  # Internal supplier code
        description: str,
        tax_id: str,  # MX: SAT Unique Product tax id
        sell_unit: UOMType,  # SellUOM
        tax: float,  # percentage rate of the product value to apply for tax
        conversion_factor: float,
        buy_unit: UOMType,  # BuyUOM
        unit_multiple: float,
        min_quantity: float,
        product_id: Optional[UUID] = None,
        upc: Optional[str] = None,  # International UPC - Barcode (optional)
        estimated_weight: Optional[float] = None,
        long_description: Optional[str] = None,
        default_price: Optional[float] = None,
        mx_ieps: Optional[
            float
        ] = None,  # percentage rate of the product value to apply for tax
        tags: Optional[List[SupplierProductTagInput]] = None,
    ) -> SupplierProductDetailsListResult:  # type: ignore (safe)
        # data validation
        if len(sku) < 1:
            return SupplierProductError(
                msg="SKU must be provided, and more than 1 character",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if len(description) < 3:
            return SupplierProductError(
                msg="Description must be provided, and more than 1 character",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if len(tax_id) < 1:
            return SupplierProductError(
                msg="Tax id must be provided, and more than 1 character",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if conversion_factor <= 0:
            return SupplierProductError(
                msg="Conversion factor must be greater than 0",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if sell_unit in INTEGER_UOMS:
            if unit_multiple < 1:
                return SupplierProductError(
                    msg="Unit multiple must be greater than 1",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            if min_quantity < 1:
                return SupplierProductError(
                    msg="Min quantity must be greater than 1",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
        if default_price is not None and default_price <= 0:
            return SupplierProductError(
                msg="Default price must be greater than 0",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if estimated_weight is not None and estimated_weight <= 0:
            return SupplierProductError(
                msg="Estimated weight must be greater than 0",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if tax < 0 or tax > 1:
            return SupplierProductError(
                msg="Tax must be between 0 and 1",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if mx_ieps is not None and (mx_ieps < 0 or mx_ieps > 1):
            return SupplierProductError(
                msg="mx_ieps must be between 0 and 1",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if upc is not None and len(upc) not in [12, 13]:
            return SupplierProductError(
                msg="UPC must be 12 or 13 digits",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        tags_dict = None
        if tags is not None:
            tags_dict = [
                {
                    "tag_key": tag.tag,
                    "tag_value": tag.value,
                }
                for tag in tags
            ]
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
        _spp_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        sp_handler.supplier_price_list_handler = _spp_handler
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prod = await sp_handler.add_supplier_product(
                firebase_id,
                supplier_business_id,
                sku,
                description,
                tax_id,
                sell_unit,
                tax,
                conversion_factor,
                buy_unit,
                unit_multiple,
                min_quantity,
                product_id,
                upc,
                estimated_weight,
                default_price,
                tags_dict,
                long_description,
                mx_ieps,
            )
            # compute results
            return SupplierProductsDetailsListGQL(
                products=[sup_prod],
            )
        except GQLApiException as ge:
            logger.warning(f"Error adding new supplier products: {ge.msg}")
            return SupplierProductError(
                msg=f"Error adding new supplier products: {ge.msg}",
                code=ge.error_code,
            )
        except Exception as e:
            logger.error(e)
            return SupplierProductError(
                msg="Error adding new supplier products",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.mutation(
        name="editSupplierProduct",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def patch_edit_supplier_product(
        self,
        info: StrawberryInfo,
        supplier_product_id: UUID,
        sku: Optional[str] = None,  # Internal supplier code
        description: Optional[str] = None,
        tax_id: Optional[str] = None,  # MX: SAT Unique Product tax id
        sell_unit: Optional[UOMType] = None,  # SellUOM
        tax: Optional[
            float
        ] = None,  # percentage rate of the product value to apply for tax
        conversion_factor: Optional[float] = None,
        buy_unit: Optional[UOMType] = None,  # BuyUOM
        unit_multiple: Optional[float] = None,
        min_quantity: Optional[float] = None,
        product_id: Optional[UUID] = None,
        upc: Optional[str] = None,  # International UPC - Barcode (optional)
        estimated_weight: Optional[float] = None,
        default_price: Optional[float] = None,
        tags: Optional[List[SupplierProductTagInput]] = None,
        long_description: Optional[str] = None,
        mx_ieps: Optional[float] = None,
    ) -> SupplierProductDetailsListResult:  # type: ignore (safe)
        # data validation
        if sku is not None and len(sku) < 1:
            return SupplierProductError(
                msg="SKU must be provided, and more than 1 character",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if description is not None and len(description) < 3:
            return SupplierProductError(
                msg="Description must be provided, and more than 1 character",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if tax_id is not None and len(tax_id) < 1:
            return SupplierProductError(
                msg="Tax id must be provided, and more than 1 character",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if conversion_factor is not None and conversion_factor <= 0:
            return SupplierProductError(
                msg="Conversion factor must be greater than 0",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if default_price is not None and default_price <= 0:
            return SupplierProductError(
                msg="Default price must be greater than 0",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if estimated_weight is not None and estimated_weight <= 0:
            return SupplierProductError(
                msg="Estimated weight must be greater than 0",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if tax is not None and (tax < 0 or tax > 1):
            return SupplierProductError(
                msg="Tax must be between 0 and 1",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if mx_ieps is not None and (mx_ieps < 0 or mx_ieps > 1):
            return SupplierProductError(
                msg="mx_ieps must be between 0 and 1",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        if upc is not None and len(upc) not in [12, 13]:
            return SupplierProductError(
                msg="UPC must be 12 or 13 digits",
                code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
            )
        tags_dict = None
        if tags is not None:
            tags_dict = [
                {
                    "tag_key": tag.tag,
                    "tag_value": tag.value,
                }
                for tag in tags
            ]
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
        _spp_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=sp_handler,
        )
        sp_handler.supplier_price_list_handler = _spp_handler
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prod = await sp_handler.edit_supplier_product(
                firebase_id,
                supplier_product_id,
                sku,
                description,
                tax_id,
                sell_unit,
                tax,
                conversion_factor,
                buy_unit,
                unit_multiple,
                min_quantity,
                product_id,
                upc,
                estimated_weight,
                default_price,
                tags_dict,
                long_description,
                mx_ieps,
            )
            # compute results
            return SupplierProductsDetailsListGQL(
                products=[sup_prod],
            )
        except GQLApiException as ge:
            logger.warning(f"Error editing supplier products: {ge.msg}")
            return SupplierProductError(
                msg=ge.msg,
                code=ge.error_code,
            )
        except Exception as e:
            logger.error(e)
            return SupplierProductError(
                msg="Error editing supplier products",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )


@strawberry.type
class SupplierProductQuery:
    @strawberry.field(
        name="getSupplierProductsByToken",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_products_by_token(
        self,
        info: StrawberryInfo,
        # supplier_unit_id: UUID,
    ) -> SupplierProductDetailsListResult:  # type: ignore
        logger.info("Get supplier products by token")
        # instantiate handler
        _handler = SupplierProductHandler(
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
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prods = await _handler.fetch_supplier_products(
                firebase_id,
            )
            # compute results
            return SupplierProductsDetailsListGQL(
                products=sup_prods,
            )
        except GQLApiException as ge:
            logger.warning(f"Error fetching supplier products: {ge.msg}")
            return SupplierProductError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierProductError(
                msg="Error upserting supplier products",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="getSupplierProduct",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_product_by_token(
        self,
        info: StrawberryInfo,
        supplier_product_id: UUID,
    ) -> SupplierProductDetailsListResult:  # type: ignore
        logger.info("Get supplier product ")
        # instantiate handler
        _handler = SupplierProductHandler(
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
        # supplier price list handler
        spl_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=_handler,
        )
        _handler.supplier_price_list_handler = spl_handler
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prod = await _handler.fetch_supplier_product(
                firebase_id,
                supplier_product_id,
            )
            # compute results
            return SupplierProductsDetailsListGQL(
                products=[sup_prod],
            )
        except GQLApiException as ge:
            logger.warning(f"Error fetching supplier product: {ge.msg}")
            return SupplierProductError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierProductError(
                msg="Error upserting supplier product",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="exportProductsFile",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def export_customer_product_files(
        self,
        info: StrawberryInfo,
        export_format: str,
        type: str,
        supplier_unit_id: Optional[UUID] = None,
        supplier_product_price_list_id: Optional[UUID] = None,
        receiver: Optional[str] = None,
    ) -> ExportSupplierProductResult:  # type: ignore
        """Endpoint to retrieve product type

        Parameters
        ----------
        info : StrawberryInfo
        supplier_unit_id: UUID
            Supplier Unit Id
        export_format: str
            Export format (csv or xlsx)
        from_date: Optional[date]
            From Date
        until_date: Optional[date]
            Until Date
        receiver: Optional[str]
            Client name (restaurant busines name or branch name)
        page: Optional[int]
            Page number
        page_size: Optional[int]
            Page size

        Returns
        -------
        List[MxInvoiceResult]
        """
        logger.info("Export product file")
        # validate format
        if export_format.lower() not in ["csv", "xlsx"]:
            return ProductError(
                msg="Invalid format",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        if type not in [
            "products",
            "all_product_price_lists",
            "product_price_list",
            "stock",
        ]:
            return ProductError(
                msg="Invalid format",
                code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
            )
        # if type == "products":
        # instantiate handler MxInvoice
        _sup_prod_handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_stock_repo=SupplierProductStockRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
        )
        _spp_handler = SupplierPriceListHandler(
            supplier_price_list_repo=SupplierPriceListRepository(info),
            supplier_unit_repo=SupplierUnitRepository(info),
            restaurant_branch_repo=RestaurantBranchRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_handler=_sup_prod_handler,
        )
        try:
            file_name = ""
            if type == "products":
                firebase_id = info.context["request"].user.firebase_user.firebase_id
                # call handler to get products
                prods = await _sup_prod_handler.get_customer_products_to_export(
                    firebase_id=firebase_id, receiver=receiver
                )
                _df = pd.DataFrame(prods)
                file_name = "products"

            if type == "product_price_list":
                if not supplier_product_price_list_id or not supplier_unit_id:
                    return ProductError(
                        msg="invalida supplier product price list id",
                        code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                    )
                # call handler to get products
                ppl = await _spp_handler.get_customer_product_price_list_to_export(
                    supplier_unit_id=supplier_unit_id,
                    supplier_product_price_list_id=supplier_product_price_list_id,
                )
                _df = pd.DataFrame(ppl)
                file_name = f"lista_{str(supplier_product_price_list_id)}"
            if type == "all_product_price_lists":
                if not supplier_unit_id:
                    return ProductError(
                        msg="invalid supplier unit id",
                        code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                    )
                # call handler to get products
                ppl = await _spp_handler.get_all_product_price_lists_to_export(
                    supplier_unit_id=supplier_unit_id
                )
                _df = pd.DataFrame(ppl)
                _df["price_list_name"] = (
                    _df["unit_name"] + " - " + _df["price_list_name"]
                )
                _df.drop("unit_name", axis=1, inplace=True)
                _df = _df.pivot_table(
                    index="product",
                    columns="price_list_name",
                    values="price",
                    aggfunc="first",
                )
                _df.reset_index(inplace=True)
                file_name = "lista_de_precios"

            if type == "stock":
                if not supplier_unit_id:
                    return ProductError(
                        msg="invalid supplier unit id",
                        code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                    )
                # call handler to get products
                stock = await _sup_prod_handler.get_customer_products_stock_to_export(
                    supplier_unit_id=supplier_unit_id
                )
                _df = pd.DataFrame(stock)
                file_name = "Inventario"

            # export
            if _df.empty:
                return ProductError(
                    msg="empty data",
                    code=GQLApiErrorCodeType.DATAVAL_WRONG_DATATYPE.value,
                )
            if export_format == "csv":
                in_memory_csv = StringIO()
                _df.to_csv(in_memory_csv, index=False)
                in_memory_csv.seek(0)
                return ExportProductGQL(
                    file=json.dumps(
                        {
                            "filename": f"{file_name}_{datetime.datetime.utcnow().date().isoformat()}.csv",
                            "mimetype": "text/csv",
                            "content": base64.b64encode(
                                in_memory_csv.read().encode("utf-8")
                            ).decode(),
                        }
                    ),
                    extension="csv",
                )
            elif export_format == "xlsx":
                in_memory_xlsx = BytesIO()
                _df.to_excel(in_memory_xlsx, index=False)
                in_memory_xlsx.seek(0)
                return ExportProductGQL(
                    file=json.dumps(
                        {
                            "filename": f"{file_name}_{datetime.datetime.utcnow().date().isoformat()}.xlsx",
                            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "content": base64.b64encode(in_memory_xlsx.read()).decode(),
                        }
                    ),
                    extension="xlsx",
                )
        except GQLApiException as ge:
            logger.warning(ge)
            return ProductError(
                msg=ge.msg,
                code=int(ge.error_code),
            )
        except Exception as e:
            logger.error(e)
            return ProductError(
                msg="Error retrieving products",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )

    @strawberry.field(
        name="getSupplierProductsStock",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def get_supplier_products_stock(
        self,
        info: StrawberryInfo,
        supplier_unit_id: UUID,
    ) -> SupplierProductDetailsListResult:  # type: ignore
        logger.info("Get supplier products by token")
        # instantiate handler
        _handler = SupplierProductHandler(
            supplier_business_repo=SupplierBusinessRepository(info),
            core_user_repo=CoreUserRepository(info),
            supplier_user_repo=SupplierUserRepository(info),
            supplier_user_permission_repo=SupplierUserPermissionRepository(info),
            product_repo=ProductRepository(info),
            category_repo=CategoryRepository(info),
            supplier_product_repo=SupplierProductRepository(info),
            supplier_product_price_repo=SupplierProductPriceRepository(info),
            supplier_product_stock_repo=SupplierProductStockRepository(info),
        )
        try:
            # firebase
            firebase_id = info.context["request"].user.firebase_user.firebase_id
            sup_prods_stock = await _handler.fetch_supplier_products_stock(
                firebase_id,
                supplier_unit_id,
            )
            # compute results
            return SupplierProductsDetailsListGQL(
                products=sup_prods_stock,
            )
        except GQLApiException as ge:
            logger.warning(f"Error fetching supplier products: {ge.msg}")
            return SupplierProductError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierProductError(
                msg="Error upserting supplier products",
                code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
            )
