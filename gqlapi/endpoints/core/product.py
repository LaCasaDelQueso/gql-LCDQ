import logging
from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.catalog.product import (
    ProductError,
    ProductInput,
    ProductResult,
)
from gqlapi.domain.interfaces.v2.catalog.product_family import (
    MxSatProductCodeResult,
    ProductFamilyError,
    ProductFamilyResult,
)
from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.handlers.core.product import ProductFamilyHandler, ProductHandler
from gqlapi.repository.core.product import ProductFamilyRepository, ProductRepository
from gqlapi.repository.user.core_user import CoreUserRepository

import strawberry
from strawberry.types import Info as StrawberryInfo


@strawberry.type
class ProductMutation:
    @strawberry.mutation(name="newProduct")
    async def post_new_product(
        self,
        info: StrawberryInfo,
        product_family_id: UUID,
        name: str,
        description: str,
        sku: str,
        keywords: List[str],
        sell_unit: UOMType,
        conversion_factor: float,
        buy_unit: UOMType,
        estimated_weight: float,
        upc: Optional[str] = None,
    ) -> ProductResult:  # type: ignore
        logging.info("Create new product")
        # instantiate handler
        _handler = ProductHandler(
            prod_repo=ProductRepository(info),
            prod_fam_repo=ProductFamilyRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # call validation
        if (
            not product_family_id
            or not name
            or not description
            or not buy_unit
            or not sku
            or not keywords
            or not sell_unit
            or not conversion_factor
            or not estimated_weight
        ):
            return ProductError(
                msg="Empty values for creating Product",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_product(
                product_family_id,
                name,
                description,
                sku,
                keywords,
                sell_unit,
                conversion_factor,
                buy_unit,
                estimated_weight,
                fb_id,
                upc,
            )
            return _resp
        except GQLApiException as ge:
            return ProductError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(name="updateProduct")
    async def patch_edit_product(
        self,
        info: StrawberryInfo,
        product_id: UUID,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        sku: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        sell_unit: Optional[UOMType] = None,
        conversion_factor: Optional[float] = None,
        buy_unit: Optional[UOMType] = None,
        estimated_weight: Optional[float] = None,
        upc: Optional[str] = None,
    ) -> ProductResult:  # type: ignore
        logging.info("Update product")
        # instantiate handler
        _handler = ProductHandler(
            prod_repo=ProductRepository(info),
            prod_fam_repo=ProductFamilyRepository(info),
        )
        # call validation
        if (
            not name
            and not buy_unit
            and not product_id
            and not product_family_id
            and not name
            and not description
            and not sku
            and not keywords
            and not sell_unit
            and not conversion_factor
            and not buy_unit
            and not estimated_weight
            and not upc
        ):
            return ProductError(
                msg="Empty values for updating Product",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.edit_product(
                product_id,
                product_family_id,
                name,
                description,
                sku,
                keywords,
                sell_unit,
                conversion_factor,
                buy_unit,
                estimated_weight,
                upc,
            )
            return _resp
        except GQLApiException as ge:
            return ProductError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(name="newBatchProduct")
    async def post_batch_product(
        self, info: StrawberryInfo, catalog: List[ProductInput]
    ) -> List[ProductResult]:  # type: ignore
        logging.info("Create batch product")
        # instantiate handler
        _handler = ProductHandler(
            prod_repo=ProductRepository(info),
            prod_fam_repo=ProductFamilyRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # call validation
        for products in catalog:
            if (
                not products.product_family_id
                or not products.name
                or not products.description
                or not products.buy_unit
                or not products.sku
                or not products.keywords
                or not products.sell_unit
                or not products.conversion_factor
                or not products.estimated_weight
            ):
                return [
                    ProductError(
                        msg="Empty values for creating Product",
                        code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
                ]
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_batch_products(fb_id, catalog)
            return _resp
        except GQLApiException as ge:
            return [ProductError(msg=ge.msg, code=ge.error_code)]


@strawberry.type
class ProductQuery:
    @strawberry.field(name="getProducts")
    async def get_products(
        self,
        info: StrawberryInfo,
        product_id: Optional[UUID] = None,
        name: Optional[str] = None,
        search: Optional[str] = None,
        product_family_id: Optional[UUID] = None,
        upc: Optional[str] = None,
        page_size: Optional[int] = 50,
        current_page: Optional[int] = 1,
    ) -> List[ProductResult]:  # type: ignore
        logging.info("Search Products")
        # data validation
        if page_size is not None and (page_size > 2000 or page_size < 1):
            return [
                ProductError(
                    msg="Page size must be between 1 and 2000",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        if current_page is not None and current_page < 1:
            return [
                ProductError(
                    msg="Current page must be greater than 0",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        if search is not None and len(search) < 2:
            return [
                ProductError(
                    msg="Search must be at least 2 characters long",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        if name is not None and len(name) < 2:
            return [
                ProductError(
                    msg="Name must be at least 2 characters long",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        if upc is not None and len(upc) < 12:
            return [
                ProductError(
                    msg="UPC must be at least 12 characters long",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        # instantiate handler
        _handler = ProductHandler(
            prod_repo=ProductRepository(info),
            prod_fam_repo=ProductFamilyRepository(info),
        )
        try:
            # call handler
            _resp = await _handler.search_products(
                product_id,
                name,
                search,
                product_family_id,
                upc,
            )
            return _resp
        except GQLApiException as ge:
            logging.warning(ge)
            return [ProductError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logging.error(e)
            return [
                ProductError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]


@strawberry.type
class ProductFamilyMutation:
    @strawberry.mutation(name="newProductFamily")
    async def post_new_product_family(
        self,
        info: StrawberryInfo,
        name: str,
        buy_unit: UOMType,
    ) -> ProductFamilyResult:  # type: ignore
        logging.info("Create new product family")
        # instantiate handler
        _handler = ProductFamilyHandler(
            prod_fam_repo=ProductFamilyRepository(info),
            core_user_repo=CoreUserRepository(info),
        )
        # call validation
        if not name or not buy_unit:
            return ProductFamilyError(
                msg="Empty values for creating Product Family",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            fb_id = info.context["request"].user.firebase_user.firebase_id
            # call handler
            _resp = await _handler.new_product_family(fb_id, name, buy_unit)
            return _resp
        except GQLApiException as ge:
            return ProductFamilyError(msg=ge.msg, code=ge.error_code)

    @strawberry.mutation(name="updateProductFamily")
    async def patch_edit_product_family(
        self,
        info: StrawberryInfo,
        product_family_id: UUID,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
    ) -> ProductFamilyResult:  # type: ignore
        logging.info("Update product_family")
        # instantiate handler
        _handler = ProductFamilyHandler(
            prod_fam_repo=ProductFamilyRepository(info),
        )
        # call validation
        if not (name or buy_unit) or not product_family_id:
            return ProductFamilyError(
                msg="Empty values for updating ProductFamily",
                code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        try:
            # call handler
            _resp = await _handler.edit_product_family(
                product_family_id, name, buy_unit
            )
            return _resp
        except GQLApiException as ge:
            return ProductFamilyError(msg=ge.msg, code=ge.error_code)


@strawberry.type
class ProductFamilyQuery:
    @strawberry.field(name="getProductFamilies")
    async def get_product_families(
        self,
        info: StrawberryInfo,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
        search: Optional[str] = None,
    ) -> List[ProductFamilyResult]:  # type: ignore
        logging.info("Search Product Family")
        # instantiate handler
        _handler = ProductFamilyHandler(
            prod_fam_repo=ProductFamilyRepository(info),
        )
        try:
            # call handler
            _resp = await _handler.search_product_families(
                product_family_id,
                name,
                buy_unit,
                search,
            )
            return _resp
        except GQLApiException as ge:
            return [ProductFamilyError(msg=ge.msg, code=ge.error_code)]

    @strawberry.field(name="getProductSATCodes")
    async def get_product_sat_codes(
        self,
        info: StrawberryInfo,
        search: Optional[str] = None,
        current_page: Optional[int] = 1,
        page_size: Optional[int] = 200,
    ) -> List[MxSatProductCodeResult]:  # type: ignore (safe)
        logging.info("Search Product SAT Codes")
        # validate search
        if search is not None and len(search) < 1:
            return [
                ProductFamilyError(
                    msg="Search must be at least 1 character long",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        # validate page size
        if page_size is not None and (page_size > 20000 or page_size < 1):
            return [
                ProductFamilyError(
                    msg="Page size must be between 1 and 20000",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        # validate current_page
        if current_page is not None and current_page < 1:
            return [
                ProductFamilyError(
                    msg="Current page must be greater than 0",
                    code=GQLApiErrorCodeType.WRONG_DATA_FORMAT.value,
                )
            ]
        # instantiate handler
        _handler = ProductFamilyHandler(
            prod_fam_repo=ProductFamilyRepository(info),
        )
        try:
            # call handler
            _resp = await _handler.find_mx_sat_product_codes(
                search,
                current_page,
                page_size,
            )
            return _resp
        except GQLApiException as ge:
            logging.error(ge)
            return [ProductFamilyError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logging.error(e)
            return [
                ProductFamilyError(
                    msg=str(e), code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
                )
            ]
