from typing import Dict, List, Optional
from uuid import UUID, uuid4
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import (
    CloudinaryApi,
    Folders,
    construct_route,
)
from gqlapi.domain.models.v2.supplier import SupplierProductImage
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from strawberry.file_uploads import Upload

from gqlapi.domain.interfaces.v2.services.image import (
    ImageHandlerInterface,
    ImageRepositoryInterface,
    ImageRoute,
    SupplierProductImageInput,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductRepositoryInterface,
)

from gqlapi.config import CLOUDINARY_BASE_URL, ENV as DEV_ENV

logger = get_logger(get_app())


class SupplierProductImageHandler(ImageHandlerInterface):
    def __init__(
        self,
        image_repo: ImageRepositoryInterface,
        supp_prod_repo: Optional[SupplierProductRepositoryInterface] = None,
    ):
        self.repository = image_repo
        if supp_prod_repo:
            self.supp_prod_repo = supp_prod_repo

    async def new_image(
        self, supplier_product_id: UUID, image: Upload
    ) -> SupplierProductImage:
        # validate pk
        if not await self.supp_prod_repo.validate(supplier_product_id):
            raise GQLApiException(
                msg=str(supplier_product_id) + " doesn't exists",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        file_data: bytes = await image.read()  # type: ignore
        _supp_image_count = await self.repository.count(
            supplier_product_id=supplier_product_id
        )
        priority = await self.repository.get_last_priority(supplier_product_id) + 1
        img_key = str(supplier_product_id) + "_" + str(_supp_image_count)
        route = cloudinary_api.upload(
            folder=Folders.MARKETPLACE.value,
            img_file=file_data,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.SUPPLIER_PRODUCTS.value}",
            img_key=img_key,
        )
        if "status" in route and route["status"] == "ok" and "data" in route:
            supplier_product_image = SupplierProductImage(
                id=uuid4(),
                supplier_product_id=supplier_product_id,
                deleted=False,
                image_url=route["data"],
                priority=priority,
            )
            _resp = await self.repository.add(supplier_product_image)
            if not _resp:
                raise GQLApiException(
                    msg="Error to save supplier prod image",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            return supplier_product_image
        else:
            raise GQLApiException(
                msg="Error to save supplier prod image",
                error_code=GQLApiErrorCodeType.INSERT_CLOUDINARY_DB_ERROR.value,
            )

    async def edit_image(
        self, supplier_product_image_id: UUID, image: Upload
    ) -> SupplierProductImage:
        # validate pk
        supplier_product_image = await self.repository.fetch(supplier_product_image_id)
        if not supplier_product_image:
            raise GQLApiException(
                msg="supplier prodict image "
                + str(supplier_product_image_id)
                + " doesn't exists",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        file_data: bytes = await image.read()  # type: ignore
        # Split the path by '/'
        img_key = supplier_product_image.image_url.split("/")[-1]
        cloudinary_api.delete(
            folder=Folders.MARKETPLACE.value,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.SUPPLIER_PRODUCTS.value}",
            img_key=img_key,
        )
        route = cloudinary_api.upload(
            folder=Folders.MARKETPLACE.value,
            img_file=file_data,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.SUPPLIER_PRODUCTS.value}",
            img_key=img_key,
        )
        if "status" in route and route["status"] == "ok" and "data" in route:
            _resp = await self.repository.edit(supplier_product_image)
            if not _resp:
                raise GQLApiException(
                    msg="Error to update supplier prod image",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            return supplier_product_image
        else:
            raise GQLApiException(
                msg="Error to save supplier product image",
                error_code=GQLApiErrorCodeType.INSERT_CLOUDINARY_DB_ERROR.value,
            )

    async def delete_image(self, supplier_product_image_id: UUID) -> bool:
        # validate pk
        supplier_product_image = await self.repository.fetch(supplier_product_image_id)
        if not supplier_product_image:
            raise GQLApiException(
                msg="supplier prodict image "
                + str(supplier_product_image_id)
                + " doesn't exists",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        cloudinary_api = CloudinaryApi(env=DEV_ENV)
        # Split the path by '/'
        img_key = supplier_product_image.image_url.split("/")[-1]
        route = cloudinary_api.delete(
            folder=Folders.MARKETPLACE.value,
            subfolder=f"{Folders.SUPPLIER.value}/{Folders.SUPPLIER_PRODUCTS.value}",
            img_key=img_key,
        )
        if "status" in route and route["status"] == "ok":
            _resp = await self.repository.edit(
                SupplierProductImage(
                    id=supplier_product_image.id,
                    supplier_product_id=supplier_product_image.supplier_product_id,
                    image_url=supplier_product_image.image_url,
                    priority=supplier_product_image.priority,
                    deleted=True,
                )
            )
            if not _resp:
                raise GQLApiException(
                    msg="Error to update supplier prod image",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            supplier_product_images = await self.fetch_images(
                supplier_product_image.supplier_product_id
            )
            if not supplier_product_images:
                return True
            if await self.reorganize_priority(supplier_product_images):
                return True
            return False
        else:
            raise GQLApiException(
                msg="Error to save supplier product image",
                error_code=GQLApiErrorCodeType.INSERT_CLOUDINARY_DB_ERROR.value,
            )

    async def fetch_images(
        self, supplier_product_id: UUID
    ) -> List[SupplierProductImage]:
        return await self.repository.find_by_supplier_product(supplier_product_id)

    async def reorganize_priority(
        self,
        supplier_product_image_list: List[SupplierProductImage],
        new_priorities: List[SupplierProductImageInput] = [],
    ) -> List[SupplierProductImage]:
        # Create a mapping from id to priorities
        priority_mapping = {}
        if new_priorities:
            for new_priority in new_priorities:
                priority_mapping[new_priority.id] = new_priority.priority
        else:
            for prioty, img in enumerate(
                sorted(supplier_product_image_list, key=lambda x: x.priority), start=1
            ):
                priority_mapping[img.id] = prioty
        # Update priorities in the list
        updated_images = []
        for image in supplier_product_image_list:
            image.priority = priority_mapping.get(image.id, image.priority)
            resp = await self.repository.edit(
                SupplierProductImage(
                    id=image.id,
                    supplier_product_id=image.supplier_product_id,
                    image_url=image.image_url,
                    priority=image.priority,
                    deleted=image.deleted,
                )
            )
            if not resp:
                raise GQLApiException(
                    msg="Error to update supplier prod image",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
            updated_images.append(image)
        return updated_images

    async def fetch_multiple_images(
        self, ids: List[UUID], width: int
    ) -> Dict[UUID, List[ImageRoute]]:
        # get order status
        prodsd_url_list = {}
        _resp = await self.repository.raw_query(
            query=f"""
                SELECT * FROM supplier_product_image
                WHERE supplier_product_id IN {list_into_strtuple(ids)}
            """,
            vals={},
        )
        if _resp:
            for image in _resp:
                image_obj = SupplierProductImage(**image)
                route = ImageRoute(
                    route=construct_route(
                        base_url=CLOUDINARY_BASE_URL,
                        width=str(width),
                        route=image_obj.image_url,
                    )
                )
                if image_obj.supplier_product_id not in prodsd_url_list:
                    prodsd_url_list[image_obj.supplier_product_id] = []
                prodsd_url_list[image_obj.supplier_product_id].append(route)
        else:
            # [TODO] - find supplier product image from alima product
            return {_id: [] for _id in ids}
        return prodsd_url_list
