from typing import List

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.app.permissions import (
    IsAlimaRestaurantAuthorized,
    IsAlimaSupplyAuthorized,
    IsAuthenticated,
)
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.interfaces.v2.services.image import (
    SupplierImageMsg,
    SupplierProductImageError,
    SupplierProductImageInput,
    SupplierProductImageResult,
    SupplierProductMsgResult,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException

from uuid import UUID
from gqlapi.handlers.services.image import SupplierProductImageHandler
from gqlapi.repository.services.image import ImageRepository
from gqlapi.repository.supplier.supplier_product import SupplierProductRepository
from strawberry.file_uploads import Upload

import strawberry
from strawberry.types import Info as StrawberryInfo

logger = get_logger(get_app())


@strawberry.type
class ImageMutation:
    @strawberry.mutation(
        name="newSupplierProductImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_new_image(
        self, info: StrawberryInfo, supplier_product_id: UUID, image: Upload
    ) -> SupplierProductImageResult:  # type: ignore
        logger.info("Upload new image")
        # call validation
        try:
            _handler = SupplierProductImageHandler(
                image_repo=ImageRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
            )
            # call handler
            _resp = await _handler.new_image(
                supplier_product_id=supplier_product_id, image=image
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierProductImageError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierProductImageError(
                msg="Unexpected Error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="editSupplierProductImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def post_edit_image(
        self, info: StrawberryInfo, supplier_product_image_id: UUID, image: Upload
    ) -> SupplierProductImageResult:  # type: ignore
        logger.info("Upload edit image")
        # call validation
        try:
            _handler = SupplierProductImageHandler(
                image_repo=ImageRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
            )
            # call handler
            _resp = await _handler.edit_image(
                supplier_product_image_id=supplier_product_image_id, image=image
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierProductImageError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierProductImageError(
                msg="Unexpected Error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="deleteSupplierProductImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def delete_image(
        self, info: StrawberryInfo, supplier_product_image_id: UUID
    ) -> SupplierProductMsgResult:  # type: ignore
        logger.info("Delete image")
        # call validation
        try:
            _handler = SupplierProductImageHandler(
                image_repo=ImageRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
            )
            # call handler
            _resp = await _handler.delete_image(
                supplier_product_image_id=supplier_product_image_id
            )
            return SupplierImageMsg(
                status=_resp,
                msg="Image deleted successfully" if _resp else "Image was not deleted",
            )
        except GQLApiException as ge:
            logger.warning(ge)
            return SupplierProductImageError(msg=ge.msg, code=ge.error_code)
        except Exception as e:
            logger.error(e)
            return SupplierProductImageError(
                msg="Unexpected Error", code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value
            )

    @strawberry.mutation(
        name="reorganizeSupplierProductImage",
        permission_classes=[IsAuthenticated, IsAlimaSupplyAuthorized],
    )
    async def reorganize_images(
        self,
        info: StrawberryInfo,
        supplier_product_id: UUID,
        supplier_product_images_input: List[SupplierProductImageInput],
    ) -> List[SupplierProductImageResult]:  # type: ignore
        logger.info("Reorganize images")
        # call validation
        try:
            _handler = SupplierProductImageHandler(
                image_repo=ImageRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
            )
            if len(supplier_product_images_input) == 0:
                raise GQLApiException(
                    msg="Error, no supplier product images input",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            fetch_spi = await _handler.fetch_images(supplier_product_id)
            if len(supplier_product_images_input) != len(fetch_spi):
                logger.warning(
                    f"Image List lenght is incorrect: {len(supplier_product_images_input)} != {len(fetch_spi)}"
                )
                raise GQLApiException(
                    msg="Image List lenght is incorrect",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            # call handler
            _resp = await _handler.reorganize_priority(
                fetch_spi, supplier_product_images_input
            )
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return [SupplierProductImageError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                SupplierProductImageError(
                    msg="Unexpected Error",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]


@strawberry.type
class ImageQuery:
    @strawberry.field(
        name="fetchSupplierProductImage",
        permission_classes=[IsAuthenticated, IsAlimaRestaurantAuthorized],
    )
    async def get_fetch_image(
        self,
        info: StrawberryInfo,
        supplier_product_id: UUID,
    ) -> List[SupplierProductImageResult]:  # type: ignore
        logger.info("Fetch image")
        # call validation
        try:
            _handler = SupplierProductImageHandler(
                image_repo=ImageRepository(info),
                supp_prod_repo=SupplierProductRepository(info),
            )
            # call handler
            _resp = await _handler.fetch_images(supplier_product_id)
            return _resp
        except GQLApiException as ge:
            logger.warning(ge)
            return [SupplierProductImageError(msg=ge.msg, code=ge.error_code)]
        except Exception as e:
            logger.error(e)
            return [
                SupplierProductImageError(
                    msg="Unexpected Error",
                    code=GQLApiErrorCodeType.UNEXPECTED_ERROR.value,
                )
            ]
