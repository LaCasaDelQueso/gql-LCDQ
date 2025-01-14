import datetime
import json
from types import NoneType
from typing import Any, Dict, Optional, List, Tuple
from uuid import UUID
import uuid
from bson import Binary
from gqlapi.lib.clients.clients.cloudinaryapi.cloudinary import construct_route
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.config import CLOUDINARY_BASE_URL
from gqlapi.lib.logger.logger.basic_logger import get_logger
import pandas as pd

from gqlapi.domain.interfaces.v2.services.image import ImageHandlerInterface, ImageRoute
from gqlapi.domain.interfaces.v2.catalog.category import (
    CategoryRepositoryInterface,
    SupplierUnitCategoryRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.catalog.product import ProductRepositoryInterface
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_suppliers import (
    ProductsBatchGQL,
    RestaurantBusinessSupplierBusinessRelation,
    RestaurantSupplierAssignationHandlerInterface,
    RestaurantSupplierAssignationRepositoryInterface,
    RestaurantSupplierCreationGQL,
    RestaurantSupplierHandlerInterface,
    SupplierBatchGQL,
    SupplierProductCreation,
    SupplierProductCreationInput,
    SupplierProductInput,
    SupplierProductPriceInput,
    SupplierUnitRestoGQL,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_user import (
    RestaurantUserPermissionRepositoryInterface,
    RestaurantUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessAccountRepositoryInterface,
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductPriceRepositoryInterface,
    SupplierProductRepositoryInterface,
    SupplierProductStockRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import (
    SupplierUnitDeliveryRepositoryInterface,
    SupplierUnitRepositoryInterface,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBranch, RestaurantSupplierRelation
from gqlapi.domain.models.v2.supplier import (
    MinimumOrderValue,
    SupplierBusiness,
    SupplierBusinessAccount,
    SupplierBusinessCommertialConditions,
    SupplierProduct,
    SupplierProductPrice,
    SupplierUnit,
    SupplierUnitCategory,
    SupplierUnitDeliveryOptions,
)
from gqlapi.domain.models.v2.utils import (
    CategoryType,
    CurrencyType,
    DataTypeTraslate,
    NotificationChannelType,
    PayMethodType,
    SellingOption,
    ServiceDay,
    SupplierBusinessType,
    UOMType,
)
from gqlapi.handlers.core.category import CategoryHandler
from gqlapi.handlers.restaurant.restaurant_branch import RestaurantBranchHandler
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.handlers.supplier.supplier_restaurants import SupplierRestaurantsHandler
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.helpers import (
    get_min_quantity,
    list_into_strtuple,
    phone_format,
    price_format,
    serialize_product_description,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException, error_code_decode
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.models.delivery_zones import DZ_IDX

# logger
logger = get_logger(get_app())


class RestaurantSupplierAssignationHandler(
    RestaurantSupplierAssignationHandlerInterface
):
    def __init__(
        self,
        rest_supp_assig_repo: RestaurantSupplierAssignationRepositoryInterface,
        rest_branch_repo: RestaurantBranchRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        restaurant_user_repo: Optional[RestaurantUserRepositoryInterface] = None,
        restaurant_perm_repo: Optional[
            RestaurantUserPermissionRepositoryInterface
        ] = None,
        restaurant_business_repo: Optional[
            RestaurantBusinessRepositoryInterface
        ] = None,
        supplier_business_repo: Optional[SupplierBusinessRepositoryInterface] = None,
        supplier_business_account_repo: Optional[
            SupplierBusinessAccountRepositoryInterface
        ] = None,
        supplier_unit_repo: Optional[SupplierUnitRepositoryInterface] = None,
        supplier_unit_category_repo: Optional[
            SupplierUnitCategoryRepositoryInterface
        ] = None,
        supplier_product_repo: Optional[SupplierProductRepositoryInterface] = None,
        supplier_product_price_repo: Optional[
            SupplierProductPriceRepositoryInterface
        ] = None,
        supplier_unit_delivery_repo: Optional[
            SupplierUnitDeliveryRepositoryInterface
        ] = None,
        supplier_product_image_handler: Optional[ImageHandlerInterface] = None,
        supplier_product_stock_repo: Optional[
            SupplierProductStockRepositoryInterface
        ] = None,
    ):
        self.repository = rest_supp_assig_repo
        self.branch_repo = rest_branch_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if supplier_business_repo:
            self.supp_business_repo = supplier_business_repo
        if supplier_business_account_repo:
            self.supp_business_account_repo = supplier_business_account_repo
        if supplier_unit_repo:
            self.supp_unit_repo = supplier_unit_repo
        if supplier_unit_category_repo:
            self.supp_unit_category_repo = supplier_unit_category_repo
        if supplier_unit_delivery_repo:
            self.supp_unit_delivery_repo = supplier_unit_delivery_repo
        if supplier_product_repo:
            self.supp_product_repo = supplier_product_repo
        if restaurant_user_repo:
            self.restaurant_user_repo = restaurant_user_repo
        if restaurant_perm_repo:
            self.restaurant_perm_repo = restaurant_perm_repo
        if restaurant_business_repo:
            self.restaurant_business_repo = restaurant_business_repo
        if supplier_product_price_repo:
            self.supp_product_price_repo = supplier_product_price_repo
        if supplier_product_image_handler:
            self.supp_product_image_handler = supplier_product_image_handler
        if supplier_product_stock_repo:
            self.supplier_product_stock_repo = supplier_product_stock_repo

    async def new_restaurant_supplier_assignation(
        self,
        restaurant_branch_id: UUID,
        supplier_business_id: UUID,
        firebase_id: str,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> RestaurantSupplierRelation:
        """New_restaurant_supplier_assignation

        Args:
            restaurant_branch_id (UUID): unique rest branch id
            supplier_business_id (UUID): unique supp business id
            core_user_id (UUID): unique core user id
            rating (Optional[int], optional): restaurant satisfaction. Defaults to None.
            review (Optional[str], optional): restaurant comment. Defaults to None.

        Returns:
            RestaurantSupplierRelation: RestaurantSupplierRelation model
        """
        # validate fk
        await self.branch_repo.exist(restaurant_branch_id)
        await self.supp_business_repo.exists(supplier_business_id)
        await self.branch_repo.exist_relation_rest_supp(
            restaurant_branch_id, supplier_business_id
        )
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        rest_supp_assig_id = await self.repository.new(
            restaurant_branch_id,
            supplier_business_id,
            core_user.id,
            rating,
            review,
        )
        restaurant_branch = await self.repository.get(rest_supp_assig_id)
        return RestaurantSupplierRelation(**restaurant_branch)

    async def edit_restaurant_supplier_assignation(
        self,
        rest_supp_assig_id: UUID,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> RestaurantSupplierRelation:  # type: ignore
        """Edit_restaurant_supplier_assignation

        Args:
            rest_supp_assig_id (UUID): unique restaurant supplier assignation id
            rating (Optional[int], optional): restaurant satisfaction. Defaults to None.
            review (Optional[str], optional): restaurant comment. Defaults to None.

        Returns:
            RestaurantSupplierRelation: RestaurantSupplierRelation model
        """
        # validate fk
        await self.repository.exists(rest_supp_assig_id)
        # post supplier business
        if await self.repository.update(
            rest_supp_assig_id,
            rating,
            review,
        ):
            restaurant_branch = await self.repository.get(rest_supp_assig_id)
            return RestaurantSupplierRelation(**restaurant_branch)

    async def fetch_restaurant_suppliers_assignation(
        self, restaurant_branch_id: Optional[UUID] = None
    ) -> List[RestaurantSupplierRelation]:
        """Fetch restaurant suppliers assignation

        Args:
            restaurant_business_id (UUID): unique restaurant business id

        Returns:
            List[RestaurantUserPermCont]
        """
        if restaurant_branch_id:
            if not await self.branch_repo.exists(restaurant_branch_id):
                raise GQLApiException(
                    msg="Restaurant branch not found",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
        # update
        return await self.repository.search(restaurant_branch_id)

    async def fetch_restaurant_suppliers(
        self,
        firebase_id: str,
        restaurant_branch_id: Optional[UUID] = None,
        restaurant_supplier_id: Optional[UUID] = None,
        with_products: Optional[bool] = False,
    ) -> List[RestaurantSupplierCreationGQL]:
        """Fetch restaurant suppliers

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id

        Returns:
            List[RestaurantSupplierCreationGQL]
        """
        # get core user
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user or not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get restaurant user
        res_user = await self.restaurant_user_repo.fetch(core_user.id)
        if not res_user or not res_user.id:
            raise GQLApiException(
                msg="Restaurant user not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get permissions to validate association
        perms = await self.restaurant_perm_repo.fetch(res_user.id)
        if not perms or perms.restaurant_business_id is None:
            raise GQLApiException(
                msg="Restaurant business not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get branch ids associated to account
        branch_ids = []
        if restaurant_branch_id:
            branch_ids.append(restaurant_branch_id)
        else:
            allowed_br_ids = [
                b.id
                for b in await self.branch_repo.get_restaurant_branches(
                    perms.restaurant_business_id
                )
            ]
            # [TODO] - validate which branches has access this restaurant user
            branch_ids += allowed_br_ids
        # get assigned suppliers
        sup_asigs = []
        for branch_id in branch_ids:
            try:
                sup_asigs += await self.repository.search(
                    branch_id, restaurant_supplier_id
                )
            except GQLApiException as ge:
                if ge.error_code != GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
                    raise ge
            except Exception as e:
                logger.warning("Error fetching assigned branches from user")
                logger.error(e)
                raise e
        # verify if sups
        if not sup_asigs:
            raise GQLApiException(
                msg="No suppliers found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get suppliers
        _suppliers = []
        for sup_asig in sup_asigs:
            supplier_creation = {}
            supplier_creation["relation"] = sup_asig
            supplier_creation["supplier_business"] = SupplierBusiness(
                **await self.supp_business_repo.fetch(sup_asig.supplier_business_id)
            )
            supplier_creation["supplier_business_account"] = SupplierBusinessAccount(
                **await self.supp_business_account_repo.fetch(
                    sup_asig.supplier_business_id
                )
            )
            _sunits = []
            supp_units = await self.supp_unit_repo.find(sup_asig.supplier_business_id)
            for su_dict in supp_units:
                su = SupplierUnit(**su_dict)
                _su_d = await self.supp_unit_delivery_repo.fetch(su.id)
                try:
                    if _su_d:
                        deliv_info = SupplierUnitDeliveryOptions(
                            supplier_unit_id=_su_d["supplier_unit_id"],
                            selling_option=[
                                SellingOption(so) for so in _su_d["selling_option"]
                            ],
                            service_hours=[
                                ServiceDay(**_servd)
                                for _servd in _su_d["service_hours"]
                            ],
                            regions=[str(r).upper() for r in _su_d["regions"]],
                            delivery_time_window=_su_d["delivery_time_window"],
                            warning_time=_su_d["warning_time"],
                            cutoff_time=_su_d["cutoff_time"],
                        )
                    else:
                        deliv_info = None
                except Exception as e:
                    logger.warning("Error fetching supplier unit delivery info")
                    logger.error(e)
                    deliv_info = None
                sunit_cat_dict = await self.supp_unit_category_repo.fetch(su.id)
                if not sunit_cat_dict:
                    logger.warning("Supplier unit category not found")
                    continue
                _sunits.append(
                    SupplierUnitRestoGQL(
                        supplier_unit=su,
                        category=SupplierUnitCategory(**sunit_cat_dict),
                        delivery_info=deliv_info,
                    )
                )
            supplier_creation["unit"] = _sunits
            supplier_creation["products"] = []
            try:
                if with_products:
                    products = await self.supp_product_repo.find(
                        sup_asig.supplier_business_id
                    )
                    supplier_prod_stock_by_unit_idx = {}
                    supp_prod_stock_idx = {}
                    for su_dict in supp_units:
                        su = SupplierUnit(**su_dict)
                        supp_prod_stocks = (
                            await self.supplier_product_stock_repo.fetch_latest_by_unit(
                                su.id
                            )
                        )
                        supp_prod_stocks_availability = (
                            await self.supplier_product_stock_repo.find_availability(
                                su.id, supp_prod_stocks
                            )
                        )
                        for sp_stock in supp_prod_stocks_availability:
                            supp_prod_stock_idx[sp_stock.supplier_product_id] = sp_stock
                        supplier_prod_stock_by_unit_idx[su.id] = supp_prod_stock_idx

                    supplier_creation["products"] = [
                        SupplierProductCreation(
                            product=SupplierProduct(**p),
                            price=(
                                await self.supp_product_price_repo.get_latest_active(
                                    p["id"]
                                )
                            ),
                            images=(
                                [
                                    ImageRoute(
                                        route=construct_route(
                                            base_url=CLOUDINARY_BASE_URL,
                                            width=str(48),
                                            route=sp_img.image_url,
                                        )
                                    )
                                    for sp_img in await self.supp_product_image_handler.fetch_images(
                                        p["id"]
                                    )
                                ]
                            ),
                        )
                        for p in products
                    ]
            except GQLApiException as ge:
                if ge.error_code != GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
                    raise ge
            except Exception as e:
                logger.warning("Error fetching supplier products")
                logger.error(e)
            _suppliers.append(RestaurantSupplierCreationGQL(**supplier_creation))
        return _suppliers

    async def search_restaurant_business_supplier(
        self,
        restaurant_business_id: UUID,
        supplier_unit_name: Optional[str] = None,
        supplier_unit_id: Optional[UUID] = None,
    ) -> List[RestaurantBusinessSupplierBusinessRelation]:
        """Search for a supplier unit with the same name
            that has related restaurant_supplier_relation within
            the same restaurant business

        Parameters
        ----------
        restaurant_business_id : UUID
        supplier_unit_name : Optional[str], optional
        supplier_unit_id : Optional[UUID], optional

        Returns
        -------
        List[RestaurantBusinessSupplierBusinessRelation]
        """
        qry = """
            SELECT
                rb.restaurant_business_id,
                su.supplier_business_id
            FROM restaurant_supplier_relation rsr
            LEFT JOIN restaurant_branch rb ON rb.id = rsr.restaurant_branch_id
            LEFT JOIN supplier_business sb ON sb.id = rsr.supplier_business_id
            LEFT JOIN supplier_unit su ON su.supplier_business_id = sb.id
            WHERE
                rb.restaurant_business_id = :restaurant_business_id
        """
        if supplier_unit_name:
            qry += """
            AND
                su.unit_name = :unit_name
            """
            _val = {
                "restaurant_business_id": restaurant_business_id,
                "unit_name": supplier_unit_name,
            }
        elif supplier_unit_id:
            qry += """
            AND
                su.id = :supplier_unit_id
            """
            _val = {
                "restaurant_business_id": restaurant_business_id,
                "supplier_unit_id": supplier_unit_id,
            }
        else:
            return []
        res = await self.repository.raw_query(
            qry,
            _val,
        )
        if not res:
            return []
        return [RestaurantBusinessSupplierBusinessRelation(**dict(row)) for row in res]


class RestaurantSupplierHandler(RestaurantSupplierHandlerInterface):
    def __init__(
        self,
        rest_supp_assig_repo: RestaurantSupplierAssignationRepositoryInterface,
        rest_branch_repo: RestaurantBranchRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        supplier_business_repo: Optional[SupplierBusinessRepositoryInterface] = None,
        supp_business_account_repo: Optional[
            SupplierBusinessAccountRepositoryInterface
        ] = None,
        category_repo: Optional[CategoryRepositoryInterface] = None,
        supp_unit_cat_repo: Optional[SupplierUnitCategoryRepositoryInterface] = None,
        supp_unit_repo: Optional[SupplierUnitRepositoryInterface] = None,
        product_repo: Optional[ProductRepositoryInterface] = None,
        supp_prod_repo: Optional[SupplierProductRepositoryInterface] = None,
        supp_prod_price_repo: Optional[SupplierProductPriceRepositoryInterface] = None,
        supplier_product_image_handler: Optional[ImageHandlerInterface] = None,
        supplier_product_stock_repo: Optional[
            SupplierProductStockRepositoryInterface
        ] = None,
    ):
        self.rest_supp_assig_repo = rest_supp_assig_repo
        self.branch_repo = rest_branch_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if supplier_business_repo:
            self.supp_business_repo = supplier_business_repo
        if category_repo:
            self.category_repo = category_repo
        if supp_unit_cat_repo:
            self.supp_unit_cat_repo = supp_unit_cat_repo
        if supp_unit_repo:
            self.supp_unit_repo = supp_unit_repo
        if supp_business_account_repo:
            self.supp_business_account_repo = supp_business_account_repo
        if product_repo:
            self.product_repo = product_repo
        if supp_prod_repo:
            self.supp_prod_repo = supp_prod_repo
        if supp_prod_price_repo:
            self.supp_prod_price_repo = supp_prod_price_repo
        if supplier_product_image_handler:
            self.supp_product_image_handler = supplier_product_image_handler
        if supplier_product_stock_repo:
            self.supplier_product_stock_repo = supplier_product_stock_repo

    async def new_restaurant_supplier_creation(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
        category_id: UUID,  # For supplier category
        restaurant_branch_id: UUID,
        email: str,
        phone_number: str,
        contact_name: str,
        firebase_id: str,
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
    ) -> RestaurantSupplierCreationGQL:
        # validate fk
        await self.branch_repo.exist(restaurant_branch_id)
        await self.category_repo.exist(category_id)
        # Validar Alima product_id si es que tiene
        if catalog:
            for product in catalog:
                if product.product.product_id:
                    await self.product_repo.exist(product.product.product_id)
        # get core user
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )

        # New supplier business
        supplier_business_id = await self.supp_business_repo.new(
            name, country, notification_preference
        )

        # New supplier business account (id)
        await self.supp_business_account_repo.new(
            supplier_business_id,
            email=email,
            phone_number=phone_number,
            legal_rep_name=contact_name,
        )

        # Nuevo supplier Unit
        supplier_unit_id = await self.supp_unit_repo.new(
            supplier_business_id,
            name,
            full_address,
            street,
            external_num,
            internal_num,
            neighborhood,
            city,
            state,
            country,
            zip_code,
        )

        # Nuevo supplier unit category
        await self.supp_unit_cat_repo.new(
            SupplierUnitCategory(
                supplier_unit_id=supplier_unit_id,
                supplier_category_id=category_id,
                created_by=core_user.id,
            )
        )

        # New restaurant supplier assignation
        rest_supp_assig_id = await self.rest_supp_assig_repo.new(
            restaurant_branch_id,
            supplier_business_id,
            core_user.id,
            rating,
            review,
        )
        supp_prod_dir = []
        if catalog:
            # Nuevo supplier product (En lote), con price opcional
            supp_prod = {}
            for products in catalog:
                if products.product.product_id:
                    product_id = products.product.product_id
                else:
                    product_id = None
                spid = await self.supp_prod_repo.new(
                    SupplierProduct(
                        id=uuid.uuid4(),
                        product_id=product_id,
                        supplier_business_id=supplier_business_id,
                        sku=products.product.sku,
                        upc=products.product.upc,
                        description=products.product.description,
                        tax_id=products.product.tax_id,
                        sell_unit=products.product.sell_unit,
                        tax_unit=products.product.tax_unit,
                        tax=products.product.tax,
                        conversion_factor=products.product.conversion_factor,
                        buy_unit=products.product.buy_unit,
                        unit_multiple=products.product.unit_multiple,
                        min_quantity=products.product.min_quantity,
                        estimated_weight=products.product.estimated_weight,
                        is_active=products.product.is_active,
                        created_by=core_user.id,
                    )
                )
                supp_prod["product"] = SupplierProduct(
                    **await self.supp_prod_repo.get(spid)
                )
                if products.price:
                    sppid = await self.supp_prod_price_repo.new(
                        SupplierProductPrice(
                            id=uuid.uuid4(),
                            supplier_product_id=spid,
                            price=products.price.price,
                            currency=products.price.currency,
                            valid_from=products.price.valid_from,
                            valid_upto=products.price.valid_upto,
                            created_by=core_user.id,
                        )
                    )
                    supp_prod["price"] = SupplierProductPrice(
                        **await self.supp_prod_price_repo.get(sppid)
                    )
                supp_prod_dir.append(SupplierProductCreation(**supp_prod))

        # Checar formato de RestaurantSupplierCrationGQL
        supplier_creation = {}
        supplier_creation["relation"] = RestaurantSupplierRelation(
            **await self.rest_supp_assig_repo.get(rest_supp_assig_id)
        )
        supplier_creation["supplier_business"] = SupplierBusiness(
            **await self.supp_business_repo.get(supplier_business_id)
        )
        supplier_creation["supplier_business_account"] = SupplierBusinessAccount(
            **await self.supp_business_account_repo.get(supplier_business_id)
        )
        supplier_creation["unit"] = [
            SupplierUnitRestoGQL(
                supplier_unit=SupplierUnit(
                    **await self.supp_unit_repo.get(supplier_unit_id)
                ),
                category=await self.supp_unit_cat_repo.get(supplier_unit_id),
            )
        ]
        if catalog:
            supplier_creation["products"] = supp_prod_dir
        return RestaurantSupplierCreationGQL(**supplier_creation)

    async def edit_restaurant_supplier_creation(
        self,
        supplier_business_id: UUID,
        firebase_id: str,
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
    ) -> RestaurantSupplierCreationGQL:
        # validate fk
        if restaurant_branch_id:
            await self.branch_repo.exist(restaurant_branch_id)
        if category_id:
            await self.category_repo.exist(category_id)
        # get core user
        core_user = await self.core_user_repo.get_by_firebase_id(firebase_id)
        if not core_user.id:
            raise GQLApiException(
                msg="User not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # update restaurant supplier assignation
        if restaurant_branch_id:
            res_asig = await self.rest_supp_assig_repo.search(
                restaurant_branch_id, supplier_business_id
            )
        else:
            res_asig = await self.rest_supp_assig_repo.search(
                supplier_business_id=supplier_business_id
            )
        if res_asig and len(res_asig) >= 1:
            if rating or review:
                await self.rest_supp_assig_repo.update(
                    res_asig[0].id,
                    rating,
                    review,
                )
        else:
            logger.warning("Restaurant Supplier assignation not found")
            raise GQLApiException(
                msg="Restaurant Supplier assignation not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # [TODO] - verify if this user has the autority to edit this supplier
        # It should not be able to edit a supplier that:
        #  1. Is already active (is a Supplier in Alima)
        #  2. Or is not active but is not assigned to the restaurant the user belongs to
        # Update supplier business
        await self.supp_business_repo.update(
            supplier_business_id, name, country, notification_preference
        )

        # update business account (id)
        await self.supp_business_account_repo.update(
            supplier_business_id,
            email=email,
            phone_number=phone_number,
            legal_rep_name=contact_name,
        )

        # [TOREV] - restaurant can't update supplier Unit

        # update catalog
        supp_prod_dir = []
        if catalog:
            # Nuevo supplier product (En lote), con price opcional
            supp_prod = {}
            for p in catalog:
                if not p.product.id:
                    # if not ID -> means new product
                    prod_dict = p.product.__dict__
                    prod_dict.update(
                        {
                            "id": uuid.uuid4(),
                            "supplier_business_id": supplier_business_id,
                            "created_by": core_user.id,
                        }
                    )
                    p_id = await self.supp_prod_repo.add(SupplierProduct(**prod_dict))
                else:
                    # exists = update
                    p_id = p.product.id
                    _pdict = p.product.__dict__
                    _tmp_prod = await self.supp_prod_repo.fetch(p.product.id)
                    tmp_prod = SupplierProduct(**_tmp_prod)
                    for k in [
                        "description",
                        "sell_unit",
                        "buy_unit",
                        "unit_multiple",
                        "min_quantity",
                    ]:
                        tmp_prod.__setattr__(k, _pdict[k])
                    if not await self.supp_prod_repo.edit(
                        tmp_prod,
                    ):
                        raise GQLApiException(
                            msg="Issues updating product",
                            error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                        )
                supp_prod["product"] = SupplierProduct(
                    **await self.supp_prod_repo.get(p_id)
                )
                if p.price:
                    # updates price - it is the same as creating new price
                    sppid = await self.supp_prod_price_repo.add(
                        SupplierProductPrice(
                            id=uuid.uuid4(),
                            supplier_product_id=p_id,
                            price=p.price.price,
                            currency=p.price.currency,
                            valid_from=p.price.valid_from,
                            valid_upto=p.price.valid_upto,
                            created_by=core_user.id,
                        )
                    )
                    if not sppid:
                        raise GQLApiException(
                            msg="Issues updating product price",
                            error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                        )
                    supp_prod["price"] = SupplierProductPrice(
                        **await self.supp_prod_price_repo.get(sppid)
                    )
                supp_prod_dir.append(SupplierProductCreation(**supp_prod))

        # Checar formato de RestaurantSupplierCrationGQL
        supplier_creation = {}
        sup_asig = res_asig[0]  # type: ignore - is safe with above exception
        supplier_creation["relation"] = sup_asig
        supplier_creation["supplier_business"] = SupplierBusiness(
            **await self.supp_business_repo.get(supplier_business_id)
        )
        supplier_creation["supplier_business_account"] = SupplierBusinessAccount(
            **await self.supp_business_account_repo.get(supplier_business_id)
        )
        supplier_creation["unit"] = [
            SupplierUnitRestoGQL(
                supplier_unit=su,
                category=await self.supp_unit_cat_repo.get(su.id),
            )
            for su in await self.supp_unit_repo.search(sup_asig.supplier_business_id)
        ]
        if catalog:
            supplier_creation["products"] = supp_prod_dir
        return RestaurantSupplierCreationGQL(**supplier_creation)

    async def search_restaurant_branch_supplier(
        self,
        restaurant_branch_id: UUID,
        supplier_business_name: str,
    ) -> List[RestaurantBusinessSupplierBusinessRelation]:
        assignation = []
        rest_branch = await self.branch_repo.get(restaurant_branch_id)
        try:
            assignation = (
                await self.rest_supp_assig_repo.get_product_supplier_assignation(
                    rest_branch["restaurant_business_id"],
                    supplier_business_name,
                )
            )
        except GQLApiException as ge:
            if ge.error_code != GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value:
                raise ge
        except Exception as e:
            logger.error(e)
            logger.warning("not find restaurant supplier relation")
            raise GQLApiException(
                msg="not find restaurant supplier relation",
                error_code=GQLApiErrorCodeType.CONNECTION_SQL_DB_ERROR.value,
            )
        return assignation

    async def upload_suppliers(
        self,
        df_supplier: pd.DataFrame,
        _handler_supp_business: SupplierBusinessHandler,
        _handler_assignation: RestaurantSupplierAssignationHandler,
        _handler_category: CategoryHandler,
        _handler_rest_branch: RestaurantBranchHandler,
        restaurant_branch_id: UUID,
        firebase_id: Any,
    ) -> List[SupplierBatchGQL]:
        supplier_data = self.normalize_supplier_data(df_supplier)
        suppliers = []

        for supplier in supplier_data:
            try:
                supplier_business_dir = (
                    await _handler_supp_business.search_supplier_business(
                        name=supplier["supplier_business_name"]
                    )
                )
                rest_branch = RestaurantBranch(
                    **await _handler_rest_branch.repository.get(
                        restaurant_branch_id=restaurant_branch_id
                    )
                )
                supplier_batch_val = None
                supplier_batch_val = await self.validate_assignation(
                    supplier_name=supplier["supplier_business_name"],
                    restaurant_business_id=rest_branch.restaurant_business_id,
                    supplier_business_dir=supplier_business_dir,
                    return_assignation_validation=_handler_assignation,
                )
                if supplier_batch_val:
                    suppliers.append(supplier_batch_val)
                    continue
                else:
                    raise Exception
            except Exception:
                # Validate category
                if not supplier["category"]:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg="No contiene categoria",
                        )
                    )
                    continue

                # Validate notification preference
                if not supplier["notification_preference"]:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg="No contiene notificacion preferente",
                        )
                    )
                    continue

                # Validate phone number exist
                if not supplier["phone_number"]:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg="No contiene número telefonico",
                        )
                    )
                    continue

                supplier["phone_number"] = phone_format(supplier["phone_number"])

                # Validate phone number exist
                if len(supplier["phone_number"]) != 10:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg="El número telefónico debe contener 10 dígitos",
                        )
                    )
                    continue

                # Validate notification preference format
                try:
                    supplier["notification_preference"] = NotificationChannelType(
                        supplier["notification_preference"].lower()
                    )
                except Exception:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg="""Formato incorrecto de notificación
                            (Valores permitidos: 'sms', 'email', 'phone_number')""",
                        )
                    )
                    continue

                # [TODO] # Validate email in firebase
                try:
                    _category_dir = await _handler_category.search_categories(
                        name=supplier["category"], category_type=CategoryType.SUPPLIER
                    )
                    _category = _category_dir[0]
                except GQLApiException:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg="Categoria no existe",
                        )
                    )
                    continue
                try:
                    _resp = await self.new_restaurant_supplier_creation(
                        name=supplier["supplier_business_name"],
                        country="México",
                        notification_preference=supplier["notification_preference"],
                        restaurant_branch_id=restaurant_branch_id,
                        category_id=_category.id,
                        email=supplier["email"],
                        phone_number=supplier["phone_number"],
                        firebase_id=firebase_id,
                        contact_name=supplier["supplier_business_name"],
                    )
                    if not _resp.supplier_business or not _resp.supplier_business.id:
                        raise GQLApiException(
                            msg="Issues creating supplier",
                            error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                        )
                    supplierbatch = SupplierBatchGQL(
                        name=supplier["supplier_business_name"],
                        uuid=_resp.supplier_business.id,
                        status=True,
                        msg="Datos del Proveedor correctamente registrados",
                    )
                    suppliers.append(supplierbatch)
                except GQLApiException as ge:
                    suppliers.append(
                        self.create_error_supplier_input(
                            supplier["supplier_business_name"],
                            msg=error_code_decode(ge.error_code),
                        )
                    )
                    continue

        return suppliers

    def normalize_supplier_data(self, df: pd.DataFrame) -> List[Dict[Any, Any]]:
        # validate that it contains the most important columns
        if not set(df.columns).issuperset(
            {
                "supplier_business_name",
                "notification_preference",
                "phone_number",
                "email",
                "category",
            }
        ):
            raise GQLApiException(
                msg="Archivo de Provedores tiene columnas faltantes!",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )

        # clean data
        data = df[~df["supplier_business_name"].isnull()]
        data = data.fillna("")

        # If no data on the shee
        if data.empty:
            raise GQLApiException(
                msg="No se puede cargar archivo, el archivo tiene datos vacios está vacía!",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )

        data_dir = data.to_dict("records")

        return data_dir

    async def validate_assignation(
        self,
        supplier_business_dir: List[SupplierBusiness],
        return_assignation_validation: RestaurantSupplierAssignationHandler,
        restaurant_business_id: UUID,
        supplier_name: str,
    ) -> SupplierBatchGQL | NoneType:
        for registered_supp in supplier_business_dir:
            try:
                assignation_validation = await return_assignation_validation.repository.find_by_restaurant_business(
                    restaurant_business_id=restaurant_business_id,
                    supplier_business_id=registered_supp.id,
                )
            except GQLApiException:
                continue

            if assignation_validation:
                supplierbatch = SupplierBatchGQL(
                    name=supplier_name,
                    status=False,
                    msg="Proveedor ya registrado",
                )
                return supplierbatch
        return None

    def create_error_supplier_input(self, supplier: str, msg: str) -> SupplierBatchGQL:
        supplierbatch = SupplierBatchGQL(
            name=supplier,
            status=False,
            msg=msg,
        )
        return supplierbatch

    async def upload_product(
        self,
        df_product: pd.DataFrame,
        restaurant_branch_id: UUID,
        firebase_id: Any,
    ) -> List[ProductsBatchGQL]:
        product_data = self.normalize_product_data(df_product)
        products = []

        for product in product_data:
            # Get by name
            try:
                supp_bus_dir = await self.search_restaurant_branch_supplier(
                    restaurant_branch_id=restaurant_branch_id,
                    supplier_business_name=product["supplier_business_name"],
                )
                supp_bus = self.get_supp_bus(supp_bus_dir)
            except GQLApiException:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No existe proveedor con ese nombre",
                        description=product["description"],
                    )
                )
                continue
            if not product["description"]:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No contiene descripción",
                    )
                )
                continue
            if not product["sell_unit"]:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No contiene unidad de compra",
                        description=product["description"],
                    )
                )
                continue
            try:
                product["sell_unit"] = UOMType(
                    DataTypeTraslate.get_uomtype_decode(product["sell_unit"].lower())
                )

            except Exception:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No contiene formato de unidad de venta correcto",
                        description=product["description"],
                    )
                )
                continue
            # Validar formato de price
            if product["price"]:
                try:
                    product["price"] = price_format(product["price"])
                except GQLApiException as ge:
                    products.append(
                        self.create_error_response_product_input(
                            supplier=product["supplier_business_name"],
                            msg=ge.msg,
                            description=product["description"],
                        )
                    )
                    continue
            try:
                _resp_supp_prod_dir = await self.supp_prod_repo.search(
                    supplier_business_id=supp_bus[1],
                    description=product["description"],
                )
                if _resp_supp_prod_dir[0]:
                    products.append(
                        self.create_error_response_product_input(
                            supplier=product["supplier_business_name"],
                            msg="Ya existe ese producto",
                            description=product["description"],
                        )
                    )
                    continue
            except GQLApiException:
                min_quantity = get_min_quantity(product["sell_unit"])
                try:
                    id = uuid.uuid4()
                    sku = str(uuid.uuid4())
                    catalog = self.create_catalog(
                        product=product, sku=sku, min_quantity=min_quantity
                    )

                    await self.edit_restaurant_supplier_creation(
                        supplier_business_id=supp_bus[1],
                        firebase_id=firebase_id,
                        catalog=catalog,
                    )
                    product_batch = ProductsBatchGQL(
                        supplier_product_id=id,
                        sku=sku,
                        supplier_name=product["supplier_business_name"],
                        status=True,
                        msg="Datos de producto correctamente registrados",
                        description=product["description"],
                    )
                    products.append(product_batch)
                except GQLApiException as ge:
                    products.append(
                        self.create_error_response_product_input(
                            supplier=product["supplier_business_name"],
                            msg=error_code_decode(ge.error_code),
                            description=product["description"],
                        )
                    )
                    continue
        return products

    async def update_product(
        self,
        df_product: pd.DataFrame,
        restaurant_branch_id: UUID,
        firebase_id: Any,
    ) -> List[ProductsBatchGQL]:
        product_data = self.normalize_product_data(df_product)
        products = []

        for product in product_data:
            # Get by name
            try:
                supp_bus_dir = await self.search_restaurant_branch_supplier(
                    restaurant_branch_id=restaurant_branch_id,
                    supplier_business_name=product["supplier_business_name"],
                )
                supp_bus = self.get_supp_bus(supp_bus_dir)
            except GQLApiException:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No existe proveedor con ese nombre",
                        description=product["description"],
                    )
                )
                continue
            if not product["description"]:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No contiene descripción",
                    )
                )
                continue
            if not product["sell_unit"]:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No contiene unidad de compra",
                        description=product["description"],
                    )
                )
                continue
            try:
                product["sell_unit"] = UOMType(
                    DataTypeTraslate.get_uomtype_decode(product["sell_unit"].lower())
                )

            except Exception:
                products.append(
                    self.create_error_response_product_input(
                        supplier=product["supplier_business_name"],
                        msg="No contiene formato de unidad de venta correcto",
                        description=product["description"],
                    )
                )
                continue
            # Validar formato de price
            if product["price"]:
                try:
                    product["price"] = price_format(product["price"])
                except GQLApiException as ge:
                    products.append(
                        self.create_error_response_product_input(
                            supplier=product["supplier_business_name"],
                            msg=ge.msg,
                            description=product["description"],
                        )
                    )
                    continue
            try:
                _resp_supp_prod_dir = await self.supp_prod_repo.search(
                    supplier_business_id=supp_bus[1],
                    description=product["description"],
                )
                if _resp_supp_prod_dir[0]:
                    min_quantity = get_min_quantity(product["sell_unit"])
                    try:
                        id = _resp_supp_prod_dir[0].id
                        sku = _resp_supp_prod_dir[0].sku
                        catalog = self.create_catalog(
                            product=product, sku=sku, min_quantity=min_quantity, id=id
                        )

                        await self.edit_restaurant_supplier_creation(
                            supplier_business_id=supp_bus[1],
                            firebase_id=firebase_id,
                            catalog=catalog,
                        )
                        product_batch = ProductsBatchGQL(
                            supplier_product_id=id,
                            sku=sku,
                            supplier_name=product["supplier_business_name"],
                            status=True,
                            msg="Datos de producto correctamente registrados",
                            description=product["description"],
                        )
                        products.append(product_batch)
                    except GQLApiException as ge:
                        products.append(
                            self.create_error_response_product_input(
                                supplier=product["supplier_business_name"],
                                msg=error_code_decode(ge.error_code),
                                description=product["description"],
                            )
                        )
                        continue
            except GQLApiException:
                min_quantity = get_min_quantity(product["sell_unit"])
                try:
                    sku = str(uuid.uuid4())
                    catalog = self.create_catalog(
                        product=product, sku=sku, min_quantity=min_quantity
                    )

                    await self.edit_restaurant_supplier_creation(
                        supplier_business_id=supp_bus[1],
                        firebase_id=firebase_id,
                        catalog=catalog,
                    )
                    product_batch = ProductsBatchGQL(
                        sku=sku,
                        supplier_name=product["supplier_business_name"],
                        status=True,
                        msg="Datos de producto correctamente registrados",
                        description=product["description"],
                    )
                    products.append(product_batch)
                except GQLApiException as ge:
                    products.append(
                        self.create_error_response_product_input(
                            supplier=product["supplier_business_name"],
                            msg=error_code_decode(ge.error_code),
                            description=product["description"],
                        )
                    )
                    continue
        return products

    def normalize_product_data(self, df: pd.DataFrame) -> List[Dict[Any, Any]]:
        # validate that it contains the most important columns
        if not set(df.columns).issuperset(
            {"supplier_business_name", "description", "sell_unit", "price"}
        ):
            raise GQLApiException(
                msg="Archivo de Provedores tiene columnas faltantes!",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )

        # remove columns that do not have quantity
        data = df[~df["supplier_business_name"].isnull()]
        data = data.fillna("")

        # If no data on the shee
        if data.empty:
            raise GQLApiException(
                msg="No se puede cargar archivo, el archivo tiene datos vacios!",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )

        data_dir = data.to_dict("records")

        return data_dir

    def create_catalog(
        self,
        product: Dict[Any, Any],
        sku: str,
        min_quantity: float,
        id: Optional[UUID] = None,
    ) -> List[SupplierProductCreationInput]:
        products_dict = {}
        products_dict["product"] = SupplierProductInput(
            sku=sku,
            tax_id="",
            description=product["description"],
            sell_unit=product["sell_unit"],
            tax_unit="",
            tax=0,
            conversion_factor=1,
            buy_unit=product["sell_unit"],
            unit_multiple=1,
            min_quantity=min_quantity,
            estimated_weight=1,
            is_active=True,
        )
        if id:
            products_dict["product"].id = id
        if product["price"]:
            products_dict["price"] = SupplierProductPriceInput(
                price=product["price"],
                currency=CurrencyType.MXN,
                valid_from=datetime.datetime.utcnow(),
                valid_upto=datetime.datetime.utcnow() + datetime.timedelta(days=30),
            )
        supp_prod_inp = SupplierProductCreationInput(**products_dict)
        catalog = []
        catalog.append(supp_prod_inp)
        return catalog

    def get_supp_bus(
        self, supp_bus_dir: List[RestaurantBusinessSupplierBusinessRelation]
    ):
        value_set = set(
            [(s.restaurant_business_id, s.supplier_business_id) for s in supp_bus_dir]
        )
        if len(value_set) != 1:
            raise GQLApiException(
                msg="",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        return list(value_set)[0]

    def create_error_response_product_input(
        self, supplier: str, msg: str, description: Optional[str] = None
    ) -> ProductsBatchGQL:
        product_batch = ProductsBatchGQL(
            supplier_name=supplier,
            status=False,
            msg=msg,
            description=description,
        )
        return product_batch

    def compute_result(self, supplier_batch: Dict[Any, Any]) -> Dict[Any, Any]:
        if "suppliers" in supplier_batch:
            num_provs = sum(
                map(lambda s: 1 if s.status else 0, supplier_batch["suppliers"])
            )
        else:
            num_provs = 0
        if "products" in supplier_batch:
            num_prods = sum(
                map(lambda p: 1 if p.status else 0, supplier_batch["products"])
            )
        else:
            num_prods = 0
        if num_provs == 0 and num_prods == 0:
            supplier_batch["msg"] = "No se crearon proveedores ni productos."
        else:
            supplier_batch["msg"] = (
                f"Se crearon {num_provs} proveedores y {num_prods} productos."
            )
        return supplier_batch

    async def _fetch_all_supplier_products_with_idxs(
        self, supplier_business_ids: List[UUID]
    ) -> Tuple[Any, ...]:
        # Get all products from suppliers
        supplier_products = await self.supp_prod_repo.find_many(
            cols=["sp.*"],
            tablename="supplier_product sp",
            filter_values=[
                {
                    "column": "sp.supplier_business_id",
                    "operator": "IN",
                    "value": list_into_strtuple(supplier_business_ids),
                }
            ],
        )
        # Get all products from suppliers that have a product_id
        sp_with_product_id_idx: Dict[str, Any] = {}  # indexed by product_id
        prods_to_match_idx: Dict[str, Any] = (
            {}
        )  # indexed by serialized description + sell unit
        for sp in supplier_products:
            # if product_id -> add to index
            if sp["product_id"]:
                if sp["product_id"] not in sp_with_product_id_idx:
                    sp_with_product_id_idx[str(sp["product_id"])] = sp
            else:
                # if no product_id -> add to list to match later with serialized description + sell unit
                ser_idx = serialize_product_description(
                    sp["description"],
                    (
                        UOMType(sp["sell_unit"])
                        if isinstance(sp["sell_unit"], str)
                        else sp["sell_unit"]
                    ),
                )
                if ser_idx not in prods_to_match_idx:
                    prods_to_match_idx[ser_idx] = sp
        # return
        return supplier_products, sp_with_product_id_idx, prods_to_match_idx

    async def _fetch_alima_supplier_products_with_idxs(
        self,
        sp_with_product_id_idx: Dict[str, Any],
        prods_to_match_idx: Dict[str, Any],
    ) -> Tuple[Any, ...]:
        # get Alima Supplier business
        find_sups = await self.supp_business_repo.find(name="Alima")
        if not find_sups:
            raise GQLApiException(
                msg="Alima supplier not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        alima_supplier_b = find_sups[0]
        # for products to match -> get supplier product from Alima
        alima_sup_prods_from_sku = await self.supp_prod_repo.find_many(
            cols=["asp.*"],
            tablename="supplier_product asp",
            filter_values=[
                {
                    "column": "asp.sku",
                    "operator": "IN",
                    "value": list_into_strtuple(list(prods_to_match_idx.keys())),
                },
                {
                    "column": "asp.supplier_business_id",
                    "operator": "=",
                    "value": f"'{str(alima_supplier_b['id'])}'",
                },
            ],
        )
        if len(sp_with_product_id_idx) > 0:
            alima_sup_prods_from_id = await self.supp_prod_repo.find_many(
                cols=["asp.*"],
                tablename="supplier_product asp",
                filter_values=[
                    {
                        "column": "asp.product_id",
                        "operator": "IN",
                        "value": list_into_strtuple(
                            list(sp_with_product_id_idx.keys())
                        ),
                    },
                    {
                        "column": "asp.supplier_business_id",
                        "operator": "=",
                        "value": f"'{str(alima_supplier_b['id'])}'",
                    },
                ],
            )
        else:
            alima_sup_prods_from_id = []
        alima_sup_prods_idx = {}
        sup_prods_missing_alima_idx = prods_to_match_idx.copy()
        for asp in alima_sup_prods_from_sku + alima_sup_prods_from_id:
            # add to alima supplier product index
            if asp["id"] in alima_sup_prods_idx:
                continue
            alima_sup_prods_idx[asp["id"]] = SupplierProduct(**asp)
            # if sku not in prods to match -> add to missing alima
            if asp["sku"] in sup_prods_missing_alima_idx:
                del sup_prods_missing_alima_idx[asp["sku"]]
        # return
        return alima_supplier_b, alima_sup_prods_idx, sup_prods_missing_alima_idx

    async def find_restaurant_supplier_products(
        self, supplier_business_ids: List[UUID]
    ) -> List[SupplierProduct]:
        """Retrieve all products from a list of suppliers, and return the
            related Alima Supplier Product that is related.
                - The matching process is first done by Product ID
                    - if no Product ID -> then by serialized Description + Sell Unit
                - If no match is found in DB
                    - then create a new Alima Supplier Product
                    - return the product with the new Alima Supplier Product ID

            ** This supplier products will only be used to create Draft Orders

        Parameters
        ----------
        supplier_business_ids : List[UUID]

        Returns
        -------
        List[SupplierProduct]
        """
        # Get all products from suppliers & index them
        (
            supplier_products,
            sp_with_product_id_idx,
            prods_to_match_idx,
        ) = await self._fetch_all_supplier_products_with_idxs(supplier_business_ids)
        # get alima supplier products indexed by id, and missing alima products (if any)
        (
            alima_supplier_b,
            alima_sup_prods_idx,
            sup_prods_missing_alima_idx,
        ) = await self._fetch_alima_supplier_products_with_idxs(
            sp_with_product_id_idx, prods_to_match_idx
        )
        # if there are missing alima products -> create them
        if sup_prods_missing_alima_idx:
            for sp in sup_prods_missing_alima_idx.values():
                _sp = sp.copy()
                _sp["id"] = uuid.uuid4()
                _sp["supplier_business_id"] = alima_supplier_b["id"]
                if isinstance(_sp["sell_unit"], str):
                    _sp["sell_unit"] = UOMType(_sp["sell_unit"])
                if isinstance(_sp["buy_unit"], str):
                    _sp["buy_unit"] = UOMType(_sp["buy_unit"])
                _sp["sku"] = serialize_product_description(
                    _sp["description"],
                    _sp["sell_unit"],
                )
                _tmp_sprod = SupplierProduct(**_sp)
                _id = await self.supp_prod_repo.add(_tmp_sprod)
                # add to alima index
                alima_sup_prods_idx[str(_id)] = _tmp_sprod
        # append all supplier products
        return list(alima_sup_prods_idx.values())

    async def _find_all_marketplace_suppliers(
        self,
    ) -> List[RestaurantSupplierCreationGQL]:
        # get all supplier business
        _suppliers = await self.supp_business_repo.find(active=True)
        # get all supplier business accounts
        _suppliers_accounts = await self.supp_business_account_repo.find(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            core_query={
                "displays_in_marketplace": True,
            },
        )
        sa_idx = {
            Binary.as_uuid(s["supplier_business_id"]): s for s in _suppliers_accounts
        }
        # needed supplier business ids
        _suppliers_ids = set(sa_idx.keys()).union(set([s["id"] for s in _suppliers]))
        # get all supplier units
        _suppliers_units = await self.supp_unit_repo.raw_query(
            query="SELECT * FROM supplier_unit WHERE supplier_business_id IN {} AND deleted <> 't' ".format(
                list_into_strtuple(list(_suppliers_ids))
            ),
            vals={},
        )
        _suppliers_units_categs = await self.supp_unit_repo.raw_query(
            query="SELECT * FROM supplier_unit_category WHERE supplier_unit_id IN {}".format(
                list_into_strtuple([su["id"] for su in _suppliers_units])
            ),
            vals={},
        )
        _suppliers_unit_delivs = await self.supp_business_account_repo.find(
            core_element_collection="supplier_unit_delivery_info",
            core_element_name="Supplier Unit DeliveryInfo",
            core_query={
                "supplier_unit_id": {
                    "$in": [Binary.from_uuid(su["id"]) for su in _suppliers_units]
                },
            },
        )
        suc_idx = {s["supplier_unit_id"]: s for s in _suppliers_units_categs}
        sud_idx = {
            Binary.as_uuid(s["supplier_unit_id"]): s for s in _suppliers_unit_delivs
        }
        su_idx = {}
        for _su in _suppliers_units:
            if _su["supplier_business_id"] not in su_idx:
                su_idx[_su["supplier_business_id"]] = []
            su = SupplierUnit(**_su)
            su_c = SupplierUnitCategory(**suc_idx.get(su.id, {}))
            _su_d = sud_idx.get(su.id, None)
            if _su_d:
                su_d = SupplierUnitDeliveryOptions(
                    supplier_unit_id=Binary.as_uuid(_su_d["supplier_unit_id"]),
                    selling_option=[
                        SellingOption(so) for so in _su_d["selling_option"]
                    ],
                    service_hours=[
                        ServiceDay(**_servd) for _servd in _su_d["service_hours"]
                    ],
                    regions=[str(r).upper() for r in _su_d["regions"]],
                    delivery_time_window=_su_d["delivery_time_window"],
                    warning_time=_su_d["warning_time"],
                    cutoff_time=_su_d["cutoff_time"],
                )
            else:
                su_d = None
            su_idx[_su["supplier_business_id"]].append(
                SupplierUnitRestoGQL(
                    supplier_unit=su,
                    category=su_c,
                    delivery_info=su_d,
                )
            )
        # iterate over all suppliers
        all_sups = []
        for _s in _suppliers:
            # get supplier business account
            _sba = sa_idx.get(_s["id"], None)
            if not _sba:
                continue
            _sba["supplier_business_id"] = Binary.as_uuid(_sba["supplier_business_id"])
            if _sba.get("business_type", None):
                _sba["business_type"] = SupplierBusinessType(_sba["business_type"])
            if _sba.get("default_commertial_conditions", None):
                _sba["default_commertial_conditions"] = (
                    SupplierBusinessCommertialConditions(
                        minimum_order_value=MinimumOrderValue(
                            **_sba["default_commertial_conditions"]["minimum_order"]
                        ),
                        allowed_payment_methods=[
                            PayMethodType(pm)
                            for pm in _sba["default_commertial_conditions"][
                                "allowed_payment_methods"
                            ]
                        ],
                        policy_terms=_sba["default_commertial_conditions"][
                            "policy_terms"
                        ],
                        account_number=_sba["default_commertial_conditions"][
                            "account_number"
                        ],
                    )
                )
            if _sba.get("legal_rep_id", None):
                _sba["legal_rep_id"] = _sba["legal_rep_id"].decode("utf-8")
            if _sba.get("incorporation_file", None):
                _sba["incorporation_file"] = _sba["incorporation_file"].decode("utf-8")
            if _sba.get("mx_sat_csf", None):
                _sba["mx_sat_csf"] = _sba["mx_sat_csf"].decode("utf-8")
            # get supplier units
            _sus = su_idx.get(_s["id"], [])
            # iterate over units
            _rsc = RestaurantSupplierCreationGQL(
                supplier_business=SupplierBusiness(**_s),
                supplier_business_account=SupplierBusinessAccount(**_sba),
                unit=_sus,
            )
            all_sups.append(_rsc)
        # return all suppliers
        return all_sups

    async def find_available_marketplace_suppliers(
        self,
        restaurant_branch_id: UUID,
    ) -> List[RestaurantSupplierCreationGQL]:
        """Find all suppliers that are available in the marketplace
            for a given restaurant branch

        Parameters
        ----------
        restaurant_branch_id : UUID

        Returns
        -------
        List[RestaurantSupplierCreationGQL]
        """
        # get restaurant branch
        _rb_dict = await self.branch_repo.fetch(restaurant_branch_id)
        if not _rb_dict:
            raise GQLApiException(
                msg="Restaurant Branch not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        rest_branch = RestaurantBranch(**_rb_dict)
        assigned_dz = DZ_IDX.get(rest_branch.zip_code, None)
        if not assigned_dz:
            logger.warning("Delivery zone currently not available")
            return []
        # get all suppliers
        _suppliers = await self._find_all_marketplace_suppliers()
        # filter upon those suppliers that meet criteria with the branch
        avail_suppliers: List[RestaurantSupplierCreationGQL] = []
        for _sup in _suppliers:
            # verify if rest branch is in delivery zone
            if not _sup.unit:
                continue
            for _su in _sup.unit:
                if not _su.delivery_info:
                    continue
                if not _su.delivery_info.regions:
                    continue
                for dz in _su.delivery_info.regions:
                    if str(dz).lower() == assigned_dz.lower():
                        _unit_copy = _su
                        _s_copy = _sup
                        _s_copy.unit = [_unit_copy]
                        avail_suppliers.append(_sup)
                        # only one unit per supplier
                        break
        if not avail_suppliers:
            logger.warning("No available suppliers")
            return avail_suppliers
        # complete if it has or not relation
        assigned_sups = await self.rest_supp_assig_repo.find_by_restaurant_business(
            restaurant_business_id=rest_branch.restaurant_business_id
        )
        assign_idx = {a.supplier_business_id: a for a in assigned_sups}
        for i, _asup in enumerate(avail_suppliers):
            _assigned = assign_idx.get(_asup.supplier_business.id, None)  # type: ignore (safe)
            if _assigned:
                avail_suppliers[i].relation = _assigned
        # return available suppliers
        return avail_suppliers

    async def find_products_with_price(
        self,
        sp_handler: SupplierRestaurantsHandler,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
    ) -> List[SupplierProductCreation]:
        """Find all products with price from a supplier unit

        Parameters
        ----------
        sp_handler : SupplierRestaurantsHandler
        supplier_unit_id : UUID
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierProductCreation]
        """
        spec_pl_ids = await sp_handler.find_business_specific_price_ids(
            supplier_unit_id, restaurant_branch_id
        )
        prods = []
        if spec_pl_ids:
            # get supplier prices
            pr_qry = f"""
                SELECT
                    spr.*,
                    row_to_json(last_price.*) AS last_price_json
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                """
            sp_prices = await sp_handler.supplier_restaurants_repo.raw_query(pr_qry, {})
            _images = await self.supp_product_image_handler.fetch_multiple_images(
                [dict(p)["id"] for p in sp_prices], 180
            )
            supp_prod_stocks = (
                await self.supplier_product_stock_repo.fetch_latest_by_unit(
                    supplier_unit_id
                )
            )
            supp_prod_stocks_availability = (
                await self.supplier_product_stock_repo.find_availability(
                    supplier_unit_id, supp_prod_stocks
                )
            )
            supp_prod_stock_idx = {}
            for sp_stock in supp_prod_stocks_availability:
                supp_prod_stock_idx[sp_stock.supplier_product_id] = sp_stock

            for p in sp_prices:
                # format sup prod
                pr_dict = dict(p)
                pr_dict["sell_unit"] = UOMType(pr_dict["sell_unit"])
                pr_dict["buy_unit"] = UOMType(pr_dict["sell_unit"])
                # format sup prod price
                _prx = json.loads(pr_dict["last_price_json"])
                _prx["id"] = UUID(_prx["id"])
                _prx["supplier_product_id"] = UUID(_prx["supplier_product_id"])
                _prx["created_by"] = UUID(_prx["created_by"])
                _prx["currency"] = CurrencyType(_prx["currency"])
                for _k in ["valid_from", "valid_upto", "created_at"]:
                    _prx[_k] = from_iso_format(_prx[_k])
                # past option
                # pimages = await self.supp_product_image_handler.fetch_image(pr_dict['id'], 180)
                pimages = _images.get(pr_dict["id"], [])
                prods.append(
                    SupplierProductCreation(
                        product=SupplierProduct(
                            **{
                                k: v
                                for k, v in pr_dict.items()
                                if k != "last_price_json"
                            }
                        ),
                        price=SupplierProductPrice(**_prx),
                        images=pimages,
                        stock=supp_prod_stock_idx.get(pr_dict["id"], None),
                    )
                )
        return prods
