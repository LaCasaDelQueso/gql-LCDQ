from types import NoneType
from typing import List
from uuid import UUID
from gqlapi.domain.interfaces.v2.services.image import ImageRepositoryInterface
from gqlapi.domain.models.v2.supplier import SupplierProductImage
from gqlapi.repository import CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain

from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger

logger = get_logger(get_app())


class ImageRepository(CoreRepository, ImageRepositoryInterface):
    async def add(self, supplier_product_image: SupplierProductImage) -> bool:
        """ """
        spi_dict = domain_to_dict(
            supplier_product_image, skip=["created_at", "last_updated"]
        )
        res = await super().add(
            core_element_name="Supplier Product Image",
            core_element_tablename="supplier_product_image",
            core_query="""INSERT INTO supplier_product_image
                        (id, supplier_product_id, image_url, deleted, priority)
                        VALUES
                        (:id, :supplier_product_id, :image_url, :deleted, :priority)""",
            core_values=spi_dict,
        )
        return False if res is None else True

    async def edit(self, supplier_product_image: SupplierProductImage) -> bool:
        """ """
        ser_dict = domain_to_dict(
            supplier_product_image, skip=["id", "created_at", "last_updated"]
        )
        qry = "UPDATE supplier_product_image SET "
        q_vals = {}
        for key, val in ser_dict.items():
            if val is not None:
                qry += f"{key} = :{key}, "
                q_vals[key] = val
        if len(q_vals) == 0:
            logger.warning("No values to update")
            return True
        # add last updated
        qry += "last_updated = now() "
        qry += "WHERE id = :id"
        q_vals["id"] = supplier_product_image.id
        # call super method
        return await super().edit(
            core_element_name="Supplier Product Image",
            core_element_tablename="supplier_product_image",
            core_query=qry,
            core_values=q_vals,
        )

    async def fetch(
        self, supplier_product_image_id: UUID
    ) -> SupplierProductImage | NoneType:
        """ """
        _data = await super().fetch(
            id=supplier_product_image_id,
            core_element_name="Supplier Product Image",
            core_element_tablename="supplier_product_image",
            core_columns="*",
            id_key="id",
        )
        if not _data:
            return None

        return SupplierProductImage(**sql_to_domain(_data, SupplierProductImage))

    async def find_by_supplier_product(
        self, supplier_product_id: UUID
    ) -> List[SupplierProductImage]:
        """ """
        _data = await super().find(
            core_element_name="Supplier Product Image",
            core_element_tablename="supplier_product_image",
            core_columns="*",
            filter_values="supplier_product_id= :supplier_product_id and deleted = 'f' ORDER BY priority ASC",
            values={"supplier_product_id": supplier_product_id},
        )
        if not _data:
            return []
        spi_list = []
        for spi in _data:
            spi_list.append(
                SupplierProductImage(**sql_to_domain(spi, SupplierProductImage))
            )
        return spi_list

    async def count(self, supplier_product_id: UUID) -> int:
        """ """
        _data = await super().find(
            core_element_name="supplier_product_image",
            core_element_tablename="supplier_product_image",
            core_columns="id",
            filter_values="""supplier_product_id=:supplier_product_id""",
            values={"supplier_product_id": supplier_product_id},
        )
        if not _data:
            return 0
        return len(_data)

    async def get_last_priority(self, supplier_product_id: UUID) -> int:
        """ """
        _data = await super().find(
            core_element_name="supplier_product_image",
            core_element_tablename="supplier_product_image",
            core_columns="*",
            filter_values="""supplier_product_id=:supplier_product_id order by priority DESC""",
            values={"supplier_product_id": supplier_product_id},
        )
        if not _data:
            return 0
        data = dict(_data[0])
        supplier_product_image = SupplierProductImage(**data)
        return supplier_product_image.priority
