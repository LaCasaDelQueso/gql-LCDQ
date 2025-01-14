from typing import List, Optional
from uuid import UUID
import uuid
from gqlapi.domain.interfaces.v2.catalog.product import (
    ProductHandlerInterface,
    ProductInput,
    ProductRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.catalog.product_family import (
    MxSatProductCodeGQL,
    ProductFamilyHandlerInterface,
    ProductFamilyRepositoryInterface,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.models.v2.core import Product, ProductFamily
from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface

logger = get_logger(get_app())


class ProductHandler(ProductHandlerInterface):
    def __init__(
        self,
        prod_repo: ProductRepositoryInterface,
        prod_fam_repo: ProductFamilyRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
    ):
        self.repository = prod_repo
        self.prod_fam_repo = prod_fam_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo

    async def new_product(
        self,
        product_family_id: UUID,
        name: str,
        description: str,
        sku: str,
        keywords: List[str],
        sell_unit: UOMType,
        conversion_factor: float,
        buy_unit: UOMType,
        estimated_weight: float,
        firebase_id: str,
        upc: Optional[str] = None,
    ) -> Product:  # type: ignore
        # validate pk
        await self.prod_fam_repo.exists(product_family_id)
        validate_by = "sku"
        validate_against = sku
        if upc:
            validate_by = "upc"
            validate_against = upc

        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # post product family
        product_id = await self.repository.new(
            product=Product(
                id=uuid.uuid4(),
                product_family_id=product_family_id,
                sku=sku,
                upc=upc,
                name=name,
                description=description,
                keywords=keywords,
                sell_unit=sell_unit,
                conversion_factor=conversion_factor,
                buy_unit=buy_unit,
                estimated_weight=estimated_weight,
                created_by=core_user.id,
            ),
            validate_by=validate_by,
            validate_against=validate_against,
        )

        return Product(**await self.repository.get(product_id))

    async def edit_product(
        self,
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
    ) -> Product:  # type: ignore
        if product_family_id:
            await self.prod_fam_repo.exists(product_family_id)
        validate_by = None
        validate_against = None
        if sku:
            validate_by = "sku"
            validate_against = sku
        if upc:
            validate_by = "upc"
            validate_against = upc
        if await self.repository.update(
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
            validate_by,
            validate_against,
        ):
            return Product(**await self.repository.get(product_id))

    async def search_products(
        self,
        product_id: Optional[UUID] = None,
        name: Optional[str] = None,
        search: Optional[str] = None,
        product_family_id: Optional[UUID] = None,
        upc: Optional[str] = None,
        sku: Optional[str] = None,
        current_page: int = 1,
        page_size: int = 200,
    ) -> List[Product]:  # type: ignore
        # get order status
        return await self.repository.get_products(
            product_id,
            name,
            search,
            product_family_id,
            upc,
            sku,
            current_page=current_page,
            page_size=page_size,
        )

    async def new_batch_products(
        self, firebase_id: str, catalog: List[ProductInput]
    ) -> List[Product]:
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        products_dir = []
        for products in catalog:
            await self.prod_fam_repo.exists(products.product_family_id)
        try:
            for products in catalog:
                validate_by = "sku"
                validate_against = products.sku
                if products.upc:
                    validate_by = "upc"
                    validate_against = products.upc

                # post product
                product_id = await self.repository.new(
                    product=Product(
                        id=uuid.uuid4(),
                        product_family_id=products.product_family_id,
                        sku=products.sku,
                        upc=products.upc,
                        name=products.name,
                        description=products.description,
                        keywords=products.keywords,
                        sell_unit=products.sell_unit,
                        conversion_factor=products.conversion_factor,
                        buy_unit=products.buy_unit,
                        estimated_weight=products.estimated_weight,
                        created_by=core_user.id,
                    ),
                    validate_by=validate_by,
                    validate_against=validate_against,
                )
                products_dir.append(Product(**await self.repository.get(product_id)))
            logger.info(f"create {len(catalog)} products")
        except Exception as e:
            logger.error(e)
            logger.warning(
                f"create {len(products_dir)} products - missing {len(catalog)-len(products_dir)} products"
            )
            raise GQLApiException(
                msg="Error creating product",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        return products_dir


class ProductFamilyHandler(ProductFamilyHandlerInterface):
    def __init__(
        self,
        prod_fam_repo: ProductFamilyRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
    ):
        self.repository = prod_fam_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo

    async def new_product_family(
        self,
        firebase_id: str,
        name: str,
        buy_unit: UOMType,
    ) -> ProductFamily:  # type: ignore
        # validate pk

        await self.repository.exists_relation_buy_name(name, buy_unit)
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        # post product family
        product_family_id = await self.repository.new(
            product_family=ProductFamily(
                id=uuid.uuid4(),
                name=name,
                buy_unit=buy_unit,
                created_by=core_user.id,
            )
        )

        return ProductFamily(**await self.repository.get(product_family_id))

    async def edit_product_family(
        self,
        product_family_id: UUID,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
    ) -> ProductFamily:  # type: ignore
        prod_fam_val = await self.repository.get(product_family_id)
        if name:
            prod_fam_val["name"] = name
        if buy_unit:
            prod_fam_val["buy_unit"] = buy_unit
        await self.repository.exists_relation_buy_name(
            prod_fam_val["name"], UOMType(prod_fam_val["buy_unit"])
        )

        if await self.repository.update(product_family_id, name, buy_unit):
            return ProductFamily(**await self.repository.get(product_family_id))

    async def search_product_families(
        self,
        product_family_id: Optional[UUID] = None,
        name: Optional[str] = None,
        buy_unit: Optional[UOMType] = None,
        search: Optional[str] = None,
    ) -> List[ProductFamily]:  # type: ignore
        # get order status
        return await self.repository.get_product_families(
            product_family_id,
            name,
            buy_unit,
            search,
        )

    async def find_mx_sat_product_codes(
        self,
        search: Optional[str] = None,
        current_page: Optional[int] = 1,
        page_size: Optional[int] = 200,
    ) -> List[MxSatProductCodeGQL]:
        """Find MX SAT Product Codes

        Args:
            search (Optional[str], optional): Defaults to None.
            current_page (Optional[int], optional): Defaults to 1.
            page_size (Optional[int], optional): Defaults to 200.

        Returns:
            List[MxSatProductCodeGQL]
        """
        mxs_codes = await self.repository.find_mx_sat_product_codes(
            search,
            current_page if current_page is not None else 1,
            page_size if page_size is not None else 200,
        )
        return [
            MxSatProductCodeGQL(
                **mxs_code,
            )
            for mxs_code in mxs_codes
        ]
