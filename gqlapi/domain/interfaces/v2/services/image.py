from abc import ABC, abstractmethod
from typing import List, Dict, Any
from uuid import UUID
from gqlapi.domain.models.v2.supplier import SupplierProductImage


import strawberry
from strawberry.file_uploads import Upload


@strawberry.input
class SupplierProductImageInput:
    id: UUID
    priority: int


@strawberry.type
class ImageError:
    msg: str
    code: int


@strawberry.type
class SupplierProductImageError:
    msg: str
    code: int


@strawberry.type
class ImageRoute:
    route: str


@strawberry.type
class SupplierImageMsg:
    status: bool
    msg: str


ImageResult = strawberry.union(
    "ImageResult",
    (ImageRoute, ImageError),
)

SupplierProductImageResult = strawberry.union(
    "SupplierProductImageResult",
    (SupplierProductImage, SupplierProductImageError),
)

SupplierProductMsgResult = strawberry.union(
    "SupplierProductMsgResult",
    (SupplierImageMsg, SupplierProductImageError),
)


class ImageHandlerInterface(ABC):
    @abstractmethod
    async def new_image(
        self,
        id: UUID,
        image: Upload,
    ) -> List[ImageRoute]:
        raise NotImplementedError

    @abstractmethod
    async def edit_image(
        self, supplier_product_image_id: UUID, image: Upload
    ) -> SupplierProductImage:
        raise NotImplementedError

    @abstractmethod
    async def fetch_images(
        self, supplier_product_id: UUID
    ) -> List[SupplierProductImage]:
        raise NotImplementedError

    @abstractmethod
    async def delete_image(self, supplier_product_image_id: UUID) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def reorganize_priority(
        self, supplier_product_image_list: List[SupplierProductImage]
    ) -> List[SupplierProductImage]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_multiple_images(
        self, ids: List[UUID], width: int
    ) -> Dict[UUID, List[ImageRoute]]:
        raise NotImplementedError


class ImageRepositoryInterface(ABC):
    @abstractmethod
    async def add(self, supplier_product_image: SupplierProductImage) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(self, supplier_product_image: SupplierProductImage) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, supplier_product_image_id: UUID) -> SupplierProductImage:
        raise NotImplementedError

    @abstractmethod
    async def count(self, supplier_product_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def get_last_priority(self, supplier_product_id: UUID) -> int:
        raise NotImplementedError

    @abstractmethod
    async def find_by_supplier_product(
        self, supplier_product_id: UUID
    ) -> List[SupplierProductImage]:
        raise NotImplementedError

    @abstractmethod
    async def raw_query(
        self, query: str, vals: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
