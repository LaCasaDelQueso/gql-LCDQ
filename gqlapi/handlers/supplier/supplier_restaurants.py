import json
from types import NoneType
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import uuid
from bson import Binary

from gqlapi.domain.interfaces.v2.catalog.category import (
    CategoryRepositoryInterface,
    RestaurantBranchCategoryRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.catalog.product import ProductRepositoryInterface
from gqlapi.domain.interfaces.v2.orden.invoice import MxSatCertificateRepositoryInterface
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchInvoicingOptionsRepositoryInterface,
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepositoryInterface,
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductDetails,
    SupplierProductHandlerInterface,
    SupplierProductPriceRepositoryInterface,
    SupplierProductRepositoryInterface,
    SupplierProductStockRepositoryInterface,
    SupplierProductStockWithAvailability,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_restaurants import (
    RestaurantBranchSupGQL,
    SupplierRestaurantCreationGQL,
    SupplierRestaurantsHandlerInterface,
    SupplierRestaurantsRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.models.v2.core import CoreUser, MxSatInvoicingCertificateInfo
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranch,
    RestaurantBranchCategory,
    RestaurantBranchMxInvoiceInfo,
    RestaurantBranchTag,
    RestaurantBusiness,
    RestaurantBusinessAccount,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
    SupplierProductPrice,
    SupplierProductTag,
    SupplierRestaurantRelation,
    SupplierRestaurantRelationMxInvoicingOptions,
    SupplierUser,
    SupplierUserPermission,
)
from gqlapi.domain.models.v2.utils import (
    CategoryType,
    CurrencyType,
    DataTypeDecoder,
    InvoiceTriggerTime,
    UOMType,
)
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.lib.logger.logger.basic_logger import get_logger

# logger
logger = get_logger(get_app())


class SupplierRestaurantsHandler(SupplierRestaurantsHandlerInterface):
    def __init__(
        self,
        supplier_restaurants_repo: SupplierRestaurantsRepositoryInterface,
        supplier_unit_repo: SupplierUnitRepositoryInterface,
        supplier_user_repo: SupplierUserRepositoryInterface,
        supplier_user_permission_repo: SupplierUserPermissionRepositoryInterface,
        restaurant_branch_repo: RestaurantBranchRepositoryInterface,
        core_user_repo: Optional[CoreUserRepositoryInterface] = None,
        restaurant_business_repo: Optional[
            RestaurantBusinessRepositoryInterface
        ] = None,
        restaurant_business_account_repo: Optional[
            RestaurantBusinessAccountRepositoryInterface
        ] = None,
        category_repo: Optional[CategoryRepositoryInterface] = None,
        restaurant_branch_category_repo: Optional[
            RestaurantBranchCategoryRepositoryInterface
        ] = None,
        product_repo: Optional[ProductRepositoryInterface] = None,
        supplier_product_repo: Optional[SupplierProductRepositoryInterface] = None,
        supplier_product_price_repo: Optional[
            SupplierProductPriceRepositoryInterface
        ] = None,
        supplier_restaurant_relation_mx_invoice_options_repo: Optional[
            RestaurantBranchInvoicingOptionsRepositoryInterface
        ] = None,
        supplier_product_handler: Optional[SupplierProductHandlerInterface] = None,
        mx_sat_cer_repo: Optional[MxSatCertificateRepositoryInterface] = None,
        invoicing_options_repo: Optional[
            RestaurantBranchInvoicingOptionsRepositoryInterface
        ] = None,
        supplier_product_stock_repo: Optional[
            SupplierProductStockRepositoryInterface
        ] = None,
    ):
        self.supplier_restaurants_repo = supplier_restaurants_repo
        self.supplier_unit_repo = supplier_unit_repo
        self.supplier_user_repo = supplier_user_repo
        self.supplier_user_permission_repo = supplier_user_permission_repo
        self.restaurant_branch_repo = restaurant_branch_repo
        if core_user_repo:
            self.core_user_repo = core_user_repo
        if restaurant_business_repo:
            self.restaurant_business_repo = restaurant_business_repo
        if restaurant_business_account_repo:
            self.restaurant_business_account_repo = restaurant_business_account_repo
        if category_repo:
            self.category_repo = category_repo
        if restaurant_branch_category_repo:
            self.restaurant_branch_category_repo = restaurant_branch_category_repo
        if product_repo:
            self.product_repo = product_repo
        if supplier_product_repo:
            self.supplier_product_repo = supplier_product_repo
        if supplier_product_price_repo:
            self.supplier_product_price_repo = supplier_product_price_repo
        if supplier_restaurant_relation_mx_invoice_options_repo:
            self.supplier_restaurant_relation_mx_invoice_options_repo = (
                supplier_restaurant_relation_mx_invoice_options_repo
            )
        if supplier_product_handler:
            self.supplier_product_handler = supplier_product_handler
        if mx_sat_cer_repo:
            self.mx_sat_cer_repo = mx_sat_cer_repo
        if invoicing_options_repo:
            self.invoicing_options_repo = invoicing_options_repo
        if supplier_product_stock_repo:
            self.supplier_product_stock_repo = supplier_product_stock_repo

    async def _verify_foreign_keys(
        self,
        category_id: UUID | NoneType,
    ):
        if category_id is not None:
            if not await self.category_repo.exists(category_id):
                raise GQLApiException(
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                    msg=f"Category with id {category_id} not found",
                )

    async def fetch_supplier_business_id(
        self, firebase_id: str
    ) -> Tuple[CoreUser, UUID]:
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if core_user is not None:
            supplier_user = await self.supplier_user_repo.fetch(core_user.id)  # type: ignore
            if supplier_user is not None:
                supplier_perms = await self.supplier_user_permission_repo.fetch(
                    supplier_user["id"]  # type: ignore
                )
                if supplier_perms is not None:
                    return core_user, supplier_perms["supplier_business_id"]
        raise GQLApiException(
            msg="No se pudo encontrar el negocio del proveedor",
            error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
        )

    async def _build_supplier_restaurant_gql(
        self,
        relation: SupplierRestaurantRelation,
        restaurant_business: RestaurantBusiness | Dict[str, Any] | NoneType = None,
        restaurant_business_account: (
            RestaurantBusinessAccount | Dict[str, Any] | NoneType
        ) = None,
        branch: RestaurantBranchSupGQL | Dict[str, Any] | NoneType = None,
        products: List[SupplierProductDetails] | List[Dict[str, Any]] = [],
        pl_name: Optional[str] = None
    ) -> SupplierRestaurantCreationGQL:
        # restaurant business
        rb = None
        if isinstance(restaurant_business, dict):
            _rb = await self.restaurant_business_repo.fetch(restaurant_business["id"])
            if _rb:
                rb = RestaurantBusiness(**_rb)
        elif restaurant_business:
            rb = restaurant_business
        # restaurant business account
        rba = None
        if isinstance(restaurant_business_account, dict):
            rba = await self.restaurant_business_account_repo.fetch(
                restaurant_business_account["restaurant_business_id"]
            )
        elif restaurant_business_account:
            rba = restaurant_business_account
        # branch
        br = None
        if isinstance(branch, dict):
            _br = await self.restaurant_branch_repo.fetch(relation.restaurant_branch_id)
            if _br:
                _brc = await self.restaurant_branch_category_repo.fetch(_br["id"])
                inv_info = await self.restaurant_branch_repo.get_tax_info(_br["id"])
                _tax_info = None
                if inv_info:
                    _tax_info = RestaurantBranchMxInvoiceInfo(**inv_info)
                if _brc:
                    br = RestaurantBranchSupGQL(
                        restaurant_branch=RestaurantBranch(**_br),
                        category=_brc,
                        tax_info=_tax_info,
                    )
        else:
            br = branch
        # products
        pr = []
        for p in products:
            if isinstance(p, dict):
                pr.append(SupplierProductDetails(**p))
            else:
                pr.append(p)
        return SupplierRestaurantCreationGQL(
            relation=relation,
            restaurant_business=rb,
            restaurant_business_account=rba,
            branch=br,
            products=pr,
            price_list_name=pl_name
        )

    async def fetch_supplier_unit_info(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        category_id: Optional[UUID] = None,
    ) -> Tuple[Dict[str, Any], CoreUser]:
        # verify fks
        await self._verify_foreign_keys(category_id)
        # get supplier unit
        supplier_unit = await self.supplier_unit_repo.fetch(supplier_unit_id)
        # get sup business id and core user
        core_user, supplier_business_id = await self.fetch_supplier_business_id(
            firebase_id
        )
        # verify if User is from the supplier business
        if (
            not supplier_unit
            or supplier_unit["supplier_business_id"] != supplier_business_id
        ):
            raise GQLApiException(
                msg="Supplier Business cannot be found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        return supplier_unit, core_user

    async def new_supplier_restaurant_creation(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        name: str,
        country: str,
        email: str,
        phone_number: str,
        contact_name: str,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        zip_code: str,
        rating: Optional[int] = None,
        review: Optional[str] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
    ) -> SupplierRestaurantCreationGQL:
        category = await self.category_repo.get_categories(
            name="Otro", category_type=CategoryType.RESTAURANT
        )
        if not category:
            raise GQLApiException(
                msg="Error to find category with value 'Otro'",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        # verify req user
        supplier_unit, core_user = await self.fetch_supplier_unit_info(
            firebase_id, supplier_unit_id
        )
        # verify if this restaurant branch already exists
        # with other supplier units of the same supplier business
        if await self.search_supplier_business_restaurant(
            supplier_unit["supplier_business_id"], branch_name
        ):
            raise GQLApiException(
                msg="Supplier Restaurant Relation already exists",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED.value,
            )
        # create new restaurant business
        rb_id = await self.restaurant_business_repo.add(
            name=name, country=country, active=False
        )
        if not rb_id:
            raise GQLApiException(
                msg="Error creating Restaurant Business",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create new restaurant business account
        rb_account = RestaurantBusinessAccount(
            restaurant_business_id=rb_id,
            email=email,
            phone_number=phone_number,
            legal_rep_name=contact_name,
        )
        if not await self.restaurant_business_account_repo.add(rb_account):
            raise GQLApiException(
                msg="Error creating Restaurant Business Account",
                error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
            )
        # create new restaurant branch
        branch = RestaurantBranch(
            id=uuid.uuid4(),
            restaurant_business_id=rb_id,
            branch_name=branch_name,
            full_address=full_address,
            street=street,
            external_num=external_num,
            internal_num=internal_num,
            neighborhood=neighborhood,
            city=city,
            state=state,
            country=country,
            zip_code=zip_code,
            deleted=False,
        )
        br_id = await self.restaurant_branch_repo.add(
            branch,
        )
        if not br_id:
            raise GQLApiException(
                msg="Error creating Restaurant Branch",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create new restaurant branch category
        br_category = RestaurantBranchCategory(
            restaurant_branch_id=branch.id,
            restaurant_category_id=category[0].id,
            created_by=core_user.id,  # type: ignore (safe)
        )
        if not await self.restaurant_branch_category_repo.add(br_category):
            raise GQLApiException(
                msg="Error creating Restaurant Branch Category",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # create new supplier restaurant relation
        sr_rel = await self.add_supplier_restaurant_relation(
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=branch.id,
            created_by=core_user.id,  # type: ignore (safe)
            approved=False,
            priority=1,
            rating=rating,
            review=review,
        )
        # if tags insert them
        if tags is not None and (isinstance(tags, list) and len(tags) > 0):
            _tgs = [
                RestaurantBranchTag(
                    id=uuid4(),
                    restaurant_branch_id=br_id,
                    tag_key=tag["tag_key"],
                    tag_value=tag["tag_value"],
                )
                for tag in tags
            ]
            if not await self.restaurant_branch_repo.add_tags(br_id, _tgs):
                logger.warning("Could not add tags to Restaurant Branch")
        # return built SupplierRestaurantCreationGQL
        return await self._build_supplier_restaurant_gql(
            relation=sr_rel,
            restaurant_business={"id": rb_id},
            restaurant_business_account=rb_account,
            branch=RestaurantBranchSupGQL(
                restaurant_branch=branch,
                category=br_category,
            ),
            products=[],
        )

    async def add_supplier_restaurant_relation(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        created_by: UUID,
        approved: bool,
        priority: int,
        rating: Optional[int] = None,
        review: Optional[str] = None,
    ) -> SupplierRestaurantRelation:
        # create new supplier restaurant relation
        sr_rel = SupplierRestaurantRelation(
            id=uuid.uuid4(),
            supplier_unit_id=supplier_unit_id,
            restaurant_branch_id=restaurant_branch_id,
            approved=approved,
            priority=priority,
            rating=rating,
            review=review,
            created_by=created_by,
        )
        if not await self.supplier_restaurants_repo.add(sr_rel):
            raise GQLApiException(
                msg="Error creating Supplier Restaurant Relation",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        return sr_rel

    async def search_supplier_business_restaurant(
        self,
        supplier_business_id: UUID,
        restaurant_branch_name: Optional[str] = None,
        restaurant_branch_id: Optional[UUID] = None,
    ) -> List[SupplierRestaurantRelation]:
        """Search for a restaurant branch with the same name
            that has related supplier_restaurant_relation within
            the same supplier business

        Parameters
        ----------
        supplier_business_id : UUID
        restaurant_branch_name : str
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierRestaurantRelation]
        """
        qry = """
            SELECT
                srr.*
            FROM supplier_restaurant_relation srr
            LEFT JOIN supplier_unit su ON su.id = srr.supplier_unit_id
            LEFT JOIN restaurant_branch rb ON rb.id = srr.restaurant_branch_id
            WHERE
                su.supplier_business_id = :supplier_business_id
        """
        if restaurant_branch_name:
            qry += """
            AND
                rb.branch_name = :branch_name
            """
            _val = {
                "supplier_business_id": supplier_business_id,
                "branch_name": restaurant_branch_name,
            }
        elif restaurant_branch_id:
            qry += """
            AND
                rb.id = :restaurant_branch_id
            """
            _val = {
                "supplier_business_id": supplier_business_id,
                "restaurant_branch_id": restaurant_branch_id,
            }
        else:
            return []
        res = await self.supplier_restaurants_repo.raw_query(
            qry,
            _val,
        )
        if not res:
            return []
        return [SupplierRestaurantRelation(**dict(row)) for row in res]

    async def edit_supplier_restaurant_creation(
        self,
        firebase_id: str,
        supplier_restaurant_relation_id: UUID,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        # Rest Branch Data
        email: Optional[str] = None,
        phone_number: Optional[str] = None,
        contact_name: Optional[str] = None,
        branch_name: Optional[str] = None,
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
        tags: Optional[List[Dict[str, Any]]] = None,
    ) -> SupplierRestaurantCreationGQL:
        # verify req user
        supplier_unit, _ = await self.fetch_supplier_unit_info(
            firebase_id, supplier_unit_id
        )
        # fetch supplier restaurant relation
        sr_rel = await self.supplier_restaurants_repo.fetch(
            supplier_restaurant_relation_id
        )
        restaurant_branch = await self.restaurant_branch_repo.fetch(
            restaurant_branch_id
        )
        if not restaurant_branch:
            raise GQLApiException(
                msg="Restaurant Branch not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        restaurant_branch_obj = RestaurantBranch(**restaurant_branch)
        if not sr_rel:
            raise GQLApiException(
                msg="Supplier Restaurant Relation not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # if the restaurant branch is not the same from the relation return error
        if sr_rel["restaurant_branch_id"] != restaurant_branch_id:
            raise GQLApiException(
                msg="Supplier Restaurant Relation not valid, restaurant branch cannot be changed",
                error_code=GQLApiErrorCodeType.INVALID_SQL_DB_OPERATION.value,
            )
        # if the supplier unit is different -> update relation
        if (
            sr_rel["supplier_unit_id"] != supplier_unit_id
            or rating is not None
            or review is not None
        ):
            if sr_rel["supplier_unit_id"] != supplier_unit_id:
                sr_rel["supplier_unit_id"] = supplier_unit_id
            if rating is not None:
                sr_rel["rating"] = rating
            if review is not None:
                sr_rel["review"] = review
            sr_relation = SupplierRestaurantRelation(**sr_rel)
            if not await self.supplier_restaurants_repo.edit(sr_relation):
                raise GQLApiException(
                    msg="Error updating Supplier Restaurant Relation",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        else:
            sr_relation = SupplierRestaurantRelation(**sr_rel)
        # if name or country are not None -> update restaurant business
        if name or country:
            if not await self.restaurant_business_repo.edit(
                id=restaurant_branch_obj.restaurant_business_id,
                name=name,
                country=country,
            ):
                raise GQLApiException(
                    msg="Error updating Restaurant Business",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # if email, phone_number or contact_name are not None -> update restaurant business account
        if email or phone_number or contact_name:
            if not await self.restaurant_business_account_repo.edit(
                restaurant_business_id=restaurant_branch_obj.restaurant_business_id,
                account=RestaurantBusinessAccount(
                    restaurant_business_id=restaurant_branch_obj.restaurant_business_id,
                    email=email,
                    phone_number=phone_number,
                    legal_rep_name=contact_name,
                ),
            ):
                raise GQLApiException(
                    msg="Error updating Restaurant Business Account",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # if branch_name, full_address, street, external_num, internal_num, neighborhood,
        # city, state, zip_code are not None -> update restaurant branch
        if (
            branch_name
            or full_address
            or street
            or external_num
            or internal_num
            or neighborhood
            or city
            or state
            or zip_code
        ):
            if not await self.restaurant_branch_repo.edit(
                restaurant_branch_id=restaurant_branch_id,
                branch_name=branch_name,
                full_address=full_address,
                street=street,
                external_num=external_num,
                internal_num=internal_num,
                neighborhood=neighborhood,
                city=city,
                state=state,
                zip_code=zip_code,
            ):
                raise GQLApiException(
                    msg="Error updating Restaurant Branch",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # fetch branch
        br = None
        _br = await self.restaurant_branch_repo.fetch(sr_relation.restaurant_branch_id)
        if _br:
            _brc = await self.restaurant_branch_category_repo.fetch(_br["id"])
            inv_info = await self.restaurant_branch_repo.get_tax_info(_br["id"])
            _tax_info = None
            if inv_info:
                _tax_info = RestaurantBranchMxInvoiceInfo(**inv_info)
            if _brc:
                br = RestaurantBranchSupGQL(
                    restaurant_branch=RestaurantBranch(**_br),
                    category=_brc,
                    tax_info=_tax_info,
                )

        # if tags insert them
        if tags is not None and (isinstance(tags, list) and len(tags) > 0):
            _tgs = [
                RestaurantBranchTag(
                    id=uuid4(),
                    restaurant_branch_id=restaurant_branch_id,
                    tag_key=tag["tag_key"],
                    tag_value=tag["tag_value"],
                )
                for tag in tags
            ]
            if not await self.restaurant_branch_repo.add_tags(
                restaurant_branch_id, _tgs
            ):
                logger.warning("Could not add tags to Restaurant Branch")

        # build SupplierRestaurantCreationGQL
        return await self._build_supplier_restaurant_gql(
            relation=sr_relation,
            restaurant_business=(
                {"id": br.restaurant_branch.restaurant_business_id} if br else None
            ),
            restaurant_business_account=(
                {"restaurant_business_id": br.restaurant_branch.restaurant_business_id}
                if br
                else None
            ),
            branch=br,
            products=[],
        )

    async def find_supplier_restaurants(
        self,
        supplier_unit_ids: List[UUID],
        firebase_id: Optional[str] = None,
        supplier_business_id: Optional[UUID] = None,
    ) -> List[SupplierRestaurantCreationGQL]:
        if firebase_id:
            # core user and supplier business id
            _, supplier_business_id = await self.fetch_supplier_business_id(firebase_id)
        else:
            if not supplier_business_id:
                raise GQLApiException(
                    msg="Error to find supplier Business",
                    error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
                )
        # get all supplier units
        su_qry = """
            SELECT id as supplier_unit_id FROM supplier_unit
            WHERE supplier_business_id = :supplier_business_id
        """
        s_units = await self.supplier_restaurants_repo.raw_query(
            su_qry,
            {
                "supplier_business_id": supplier_business_id,
            },
        )
        # filter to verify access to the supplier units
        s_units = [
            su["supplier_unit_id"]
            for su in s_units
            if su["supplier_unit_id"] in supplier_unit_ids
        ]
        if not s_units:
            return []
        # get the restaurant business & branches
        srr_qry = f"""
            SELECT
                row_to_json(srr.*) AS srr_json,
                row_to_json(rb.*) AS rb_json,
                rbr.*,
                row_to_json(rbc.*) AS rbc_json
            FROM supplier_restaurant_relation srr
            LEFT JOIN restaurant_branch rbr ON rbr.id = srr.restaurant_branch_id
            JOIN restaurant_branch_category rbc ON rbc.restaurant_branch_id = rbr.id
            JOIN restaurant_business rb ON rb.id = rbr.restaurant_business_id
            WHERE srr.supplier_unit_id IN {list_into_strtuple(s_units)}
        """
        srrs = await self.supplier_restaurants_repo.raw_query(srr_qry, {})
        if not srrs:
            return []
        # get restaurant business accounts
        rbas = await self.restaurant_business_account_repo.find(
            {
                "restaurant_business_id": {
                    "$in": [
                        Binary.from_uuid(UUID(json.loads(srr["rb_json"])["id"]))
                        for srr in srrs
                    ]
                }
            }
        )

        rb_uuid_list = []
        for srr in srrs:
            srr_dict = dict(srr)
            rb_uuid_list.append(srr_dict["id"])
        _tags = await self.restaurant_branch_repo.fetch_tags_from_many(rb_uuid_list)
        tags_idx = {t.restaurant_branch_id: [] for t in _tags}
        for t in _tags:
            tags_idx[t.restaurant_branch_id].append(t)
        mx_info = await self.restaurant_branch_repo.fetch_tax_info_from_many(rb_uuid_list)
        mx_info_idx = {}
        for mi in mx_info:
            mx_info_idx[mi.branch_id] = mi

        # build restaurant business account idx
        rba_idx = {}
        for r in rbas:
            rba = r.copy()
            rba["restaurant_business_id"] = Binary.as_uuid(
                rba["restaurant_business_id"]
            )
            if rba_idx.get(rba["restaurant_business_id"]):
                continue
            if "legal_rep_id" in rba and rba["legal_rep_id"]:
                rba["legal_rep_id"] = rba["legal_rep_id"].decode("utf-8")
            if "incorporation_file" in rba and rba["incorporation_file"]:
                rba["incorporation_file"] = rba["incorporation_file"].decode("utf-8")
            if "mx_sat_csf" in rba and rba["mx_sat_csf"]:
                rba["mx_sat_csf"] = rba["mx_sat_csf"].decode("utf-8")
            rba_idx[rba["restaurant_business_id"]] = rba

        # format results
        gql_list = []
        for s in srrs:
            srr = dict(s)
            # restaurant business
            _rb = json.loads(srr["rb_json"])
            _rb["id"] = UUID(_rb["id"])
            rb = RestaurantBusiness(**_rb)
            # restaurant business account
            rba = rba_idx.get(rb.id)
            # restaurant branch
            _rbc = json.loads(srr["rbc_json"])
            _rbc["restaurant_category_id"] = UUID(_rbc["restaurant_category_id"])
            _rbc["restaurant_branch_id"] = UUID(_rbc["restaurant_branch_id"])
            _rbc["created_by"] = UUID(_rbc["created_by"])
            
            restaurant_branch_tags = tags_idx.get(_rbc["restaurant_branch_id"], None)
            _tax_info = None
            _tax_info = mx_info_idx.get(_rbc["restaurant_branch_id"], None)
            rb_branch = RestaurantBranchSupGQL(
                restaurant_branch=RestaurantBranch(
                    **{
                        k: v
                        for k, v in srr.items()
                        if k not in ["srr_json", "rb_json", "rbc_json"]
                    }
                ),
                category=RestaurantBranchCategory(**_rbc),
                tax_info=_tax_info,
                tags=restaurant_branch_tags,
            )
            # supplier restaurant relation
            _srrel = json.loads(srr["srr_json"])
            _srrel["id"] = UUID(_srrel["id"])
            _srrel["supplier_unit_id"] = UUID(_srrel["supplier_unit_id"])
            _srrel["restaurant_branch_id"] = UUID(_srrel["restaurant_branch_id"])
            _srrel["created_by"] = UUID(_srrel["created_by"])
            supr_rel = SupplierRestaurantRelation(**_srrel)
            # build gql
            gql_list.append(
                await self._build_supplier_restaurant_gql(
                    relation=supr_rel,
                    restaurant_business=rb,
                    restaurant_business_account=rba,
                    branch=rb_branch,
                    products=[],
                    # pl_name=spec_pl_name
                )
            )
        # return built response
        return gql_list

    async def find_business_specific_price_ids(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        skip_specific: bool = False,
    ) -> List[UUID]:
        # verify if restaurant branch has a price list assigned
        spec_pl_qry = """
            WITH last_price_list AS (
                WITH rcos AS (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY name, supplier_unit_id
                            ORDER BY last_updated DESC
                        ) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
            ),
                expanded_restaurant_pls AS (
                    SELECT
                        id, supplier_unit_id, name,
                        json_array_elements(supplier_restaurant_relation_ids) as branch_id,
                        supplier_product_price_ids,
                        valid_upto
                    FROM last_price_list
            )
            SELECT id, supplier_unit_id, name,
                REPLACE(branch_id::varchar, '"', '')::UUID as branch_id,
                supplier_product_price_ids,
                valid_upto
            FROM expanded_restaurant_pls
            WHERE
                valid_upto::date >= current_date
            AND
                supplier_unit_id = :supplier_unit_id
            AND
                REPLACE(branch_id::varchar, '"', '')::UUID = :branch_id
            """
        spec_pl = []
        if not skip_specific:
            spec_pl = await self.supplier_restaurants_repo.raw_query(
                spec_pl_qry,
                {
                    "supplier_unit_id": supplier_unit_id,
                    "branch_id": restaurant_branch_id,
                },
            )
        if not spec_pl:
            # fetch default price list
            def_pl_qry = """
                WITH last_price_list AS (
                    WITH rcos AS (
                        SELECT *,
                            ROW_NUMBER() OVER (
                                PARTITION BY name, supplier_unit_id
                                ORDER BY last_updated DESC
                            ) row_num
                        FROM supplier_price_list
                    )
                    SELECT * FROM rcos WHERE row_num = 1
                )
                SELECT id, supplier_unit_id,
                    name,
                    supplier_product_price_ids,
                    valid_upto
                FROM last_price_list
                WHERE
                    valid_upto::date >= current_date
                AND
                    is_default = 't'
                AND
                    supplier_unit_id = :supplier_unit_id
                """
            spec_pl = await self.supplier_restaurants_repo.raw_query(
                def_pl_qry,
                {
                    "supplier_unit_id": supplier_unit_id,
                },
            )
            if not spec_pl:
                return []
            # get default prices
        return [UUID(p) for p in json.loads(spec_pl[0]["supplier_product_price_ids"])]

    async def find_business_specific_price_list_name(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
    ) -> str | NoneType:
        # verify if restaurant branch has a price list assigned
        spec_pl_qry = """
            WITH last_price_list AS (
                WITH rcos AS (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY name, supplier_unit_id
                            ORDER BY last_updated DESC
                        ) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
            ),
                expanded_restaurant_pls AS (
                    SELECT
                        id, supplier_unit_id, name, valid_upto,
                        json_array_elements(supplier_restaurant_relation_ids) as branch_id
                    FROM last_price_list
            )
            SELECT id, supplier_unit_id, name,
                REPLACE(branch_id::varchar, '"', '')::UUID as branch_id,
                valid_upto
            FROM expanded_restaurant_pls
            WHERE
                valid_upto::date >= current_date
            AND
                supplier_unit_id = :supplier_unit_id
            AND
                REPLACE(branch_id::varchar, '"', '')::UUID = :branch_id
            """    
        spec_pl = await self.supplier_restaurants_repo.raw_query(
            spec_pl_qry,
            {
                "supplier_unit_id": supplier_unit_id,
                "branch_id": restaurant_branch_id,
            },
        )
        if not spec_pl:
            return None
        return spec_pl[0]["name"]
    
    async def find_business_default_price_list_name(
        self,
        supplier_unit_id: UUID,
    ) -> str | NoneType:
        # verify if restaurant branch has a price list assigned
        
        # fetch default price list
        def_pl_qry = """
            WITH last_price_list AS (
                WITH rcos AS (
                    SELECT *,
                        ROW_NUMBER() OVER (
                            PARTITION BY name, supplier_unit_id
                            ORDER BY last_updated DESC
                        ) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
            )
            SELECT id, supplier_unit_id,
                name,
                valid_upto
            FROM last_price_list
            WHERE
                valid_upto::date >= current_date
            AND
                is_default = 't'
            AND
                supplier_unit_id = :supplier_unit_id
            """
        spec_pl = await self.supplier_restaurants_repo.raw_query(
            def_pl_qry,
            {
                "supplier_unit_id": supplier_unit_id,
            },
        )
        # Test
        if not spec_pl:
            return None
        return spec_pl[0]["name"]
    
    async def find_supplier_restaurant_products(
        self,
        firebase_id: str,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
    ) -> SupplierRestaurantCreationGQL:
        """Find all products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        firebase_id : str
        supplier_unit_id : UUID
        restaurant_branch_id : UUID

        Returns
        -------
        SupplierRestaurantCreationGQL
        """
        # verify req user
        supplier_unit, _ = await self.fetch_supplier_unit_info(
            firebase_id, supplier_unit_id, None
        )
        # fetch supplier restaurant relation
        sr_rel = await self.supplier_restaurants_repo.raw_query(
            """SELECT * FROM supplier_restaurant_relation
                WHERE supplier_unit_id = :supplier_unit_id
                AND restaurant_branch_id = :restaurant_branch_id
            """,
            {
                "supplier_unit_id": supplier_unit_id,
                "restaurant_branch_id": restaurant_branch_id,
            },
        )
        if not sr_rel:
            raise GQLApiException(
                msg="Supplier Restaurant Relation not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id, restaurant_branch_id
        )

        _tags = await self.restaurant_branch_repo.fetch_tags(restaurant_branch_id)
        supp_prod_stock = await self.supplier_product_stock_repo.fetch_latest_by_unit(
            supplier_unit_id
        )
        sup_prod_avail = await self.supplier_product_stock_repo.find_availability(
            supplier_unit_id, supp_prod_stock
        )
        supp_prod_stock_dict: Dict[UUID, SupplierProductStockWithAvailability] = {}
        for sps in sup_prod_avail:
            supp_prod_stock_dict[sps.supplier_product_id] = sps
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
            sp_prices = await self.supplier_restaurants_repo.raw_query(pr_qry, {})

            for p in sp_prices:
                # format sup prod
                pr_dict = dict(p)
                pr_dict["sell_unit"] = UOMType(pr_dict["sell_unit"])
                pr_dict["buy_unit"] = UOMType(pr_dict["buy_unit"])
                # format sup prod price
                _prx = json.loads(p["last_price_json"])
                _prx["id"] = UUID(_prx["id"])
                _prx["supplier_product_id"] = UUID(_prx["supplier_product_id"])
                _prx["created_by"] = UUID(_prx["created_by"])
                _prx["currency"] = CurrencyType(_prx["currency"])
                for _k in ["valid_from", "valid_upto", "created_at"]:
                    _prx[_k] = from_iso_format(_prx[_k])
                prods.append(
                    SupplierProductDetails(
                        last_price=SupplierProductPrice(**_prx),
                        **{
                            **{
                                k: v
                                for k, v in pr_dict.items()
                                if k != "last_price_json"
                            },
                        },
                        stock=supp_prod_stock_dict.get(pr_dict["id"], None),
                    )
                )
        # get resto branch
        br = None
        _br = await self.restaurant_branch_repo.fetch(sr_rel[0]["restaurant_branch_id"])
        if _br:
            _brc = await self.restaurant_branch_category_repo.fetch(_br["id"])
            inv_info = await self.restaurant_branch_repo.get_tax_info(_br["id"])
            _tax_info = None
            if inv_info:
                _tax_info = RestaurantBranchMxInvoiceInfo(**inv_info)
            io_info = (
                await self.supplier_restaurant_relation_mx_invoice_options_repo.fetch(
                    sr_rel[0]["id"]
                )
            )
            if _brc:
                br = RestaurantBranchSupGQL(
                    restaurant_branch=RestaurantBranch(**_br),
                    category=_brc,
                    tax_info=_tax_info,
                    tags=_tags,
                    invoicing_options=io_info,
                )
        spec_pl_name = await self.find_business_specific_price_list_name(
            supplier_unit_id, restaurant_branch_id
        )
        if not spec_pl_name:
            spec_pl_name = await self.find_business_default_price_list_name(supplier_unit_id)
            
        # build gql
        return await self._build_supplier_restaurant_gql(
            relation=SupplierRestaurantRelation(**sr_rel[0]),
            restaurant_business=(
                {"id": br.restaurant_branch.restaurant_business_id} if br else None
            ),
            restaurant_business_account=(
                {"restaurant_business_id": br.restaurant_branch.restaurant_business_id}
                if br
                else None
            ),
            branch=br,
            products=prods,
            pl_name=spec_pl_name
        )

    async def get_ecommerce_supplier_restaurant_products(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> List[SupplierProductDetails]:
        """Find all products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        supplier_unit_id : UUID
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierProductDetails]
        """
        # fetch supplier restaurant relation
        sr_rel = await self.supplier_restaurants_repo.raw_query(
            """SELECT * FROM supplier_restaurant_relation
                WHERE supplier_unit_id = :supplier_unit_id
                AND restaurant_branch_id = :restaurant_branch_id
            """,
            {
                "supplier_unit_id": supplier_unit_id,
                "restaurant_branch_id": restaurant_branch_id,
            },
        )
        if not sr_rel:
            return []
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id, restaurant_branch_id
        )
        prods = []
        if spec_pl_ids:
            filter_qry = ""
            if search:
                filter_qry = f"""
                    AND (
                        unaccent(spr.description) ILIKE unaccent('%{search.replace(' ', '%')}%')
                        OR spt.tag_value ILIKE '%{search.replace(' ', '%')}%'
                    )
                """
            filter_qry += f"""
                ORDER BY spr.description
                LIMIT {page_size}
                OFFSET {page_size * (page - 1)}
            """
            # get supplier prices
            pr_qry = f"""
                WITH category_tag AS (
                    SELECT
                        supplier_product_id,
                        string_agg(tag_value, ',') as tag_value
                    FROM supplier_product_tag
                    GROUP BY supplier_product_id
                )
                SELECT
                    spr.*,
                    row_to_json(last_price.*) AS last_price_json
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                LEFT JOIN category_tag spt on spt.supplier_product_id = spr.id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                {filter_qry}
                """
            sp_prices = await self.supplier_restaurants_repo.raw_query(pr_qry, {})
            # get images
            sprod_ids = [p["id"] for p in sp_prices]
            if sprod_ids:
                img_qry = f"""
                    SELECT
                        supplier_product_id,
                        image_url
                    FROM supplier_product_image
                    WHERE supplier_product_id IN {list_into_strtuple(sprod_ids)}
                    AND deleted = 'f' ORDER BY priority ASC
                    """
                sp_imgs = await self.supplier_restaurants_repo.raw_query(img_qry, {})
            else:
                sp_imgs = []
            sp_imgs_idx: Dict[UUID, List[str]] = {}
            for img in sp_imgs:
                if img["supplier_product_id"] not in sp_imgs_idx:
                    sp_imgs_idx[img["supplier_product_id"]] = []
                sp_imgs_idx[img["supplier_product_id"]].append(img["image_url"])
            # get tags
            if sprod_ids:
                tag_qry = f"""
                    SELECT
                        *
                    FROM supplier_product_tag
                    WHERE supplier_product_id IN {list_into_strtuple(sprod_ids)}
                    """
                sp_tags = await self.supplier_restaurants_repo.raw_query(tag_qry, {})
            else:
                sp_tags = []
            sp_tags_idx: Dict[UUID, List[SupplierProductTag]] = {}
            for tg in sp_tags:
                if tg["supplier_product_id"] not in sp_tags_idx:
                    sp_tags_idx[tg["supplier_product_id"]] = []
                sp_tags_idx[tg["supplier_product_id"]].append(SupplierProductTag(**tg))
            # get stock
            supp_prod_stock = (
                await self.supplier_product_stock_repo.fetch_latest_by_unit(
                    supplier_unit_id
                )
            )
            sup_prod_avail = await self.supplier_product_stock_repo.find_availability(
                supplier_unit_id, supp_prod_stock
            )
            supp_prod_stock_dict: Dict[UUID, SupplierProductStockWithAvailability] = {}
            for sps in sup_prod_avail:
                supp_prod_stock_dict[sps.supplier_product_id] = sps
            # format
            for p in sp_prices:
                # format sup prod
                pr_dict = dict(p)
                pr_dict["sell_unit"] = UOMType(pr_dict["sell_unit"])
                pr_dict["buy_unit"] = UOMType(pr_dict["buy_unit"])
                # format sup prod price
                _prx = json.loads(p["last_price_json"])
                _prx["id"] = UUID(_prx["id"])
                _prx["supplier_product_id"] = UUID(_prx["supplier_product_id"])
                _prx["created_by"] = UUID(_prx["created_by"])
                _prx["currency"] = CurrencyType(_prx["currency"])
                for _k in ["valid_from", "valid_upto", "created_at"]:
                    _prx[_k] = from_iso_format(_prx[_k])
                _imgs = sp_imgs_idx.get(pr_dict["id"], [])
                _tags = sp_tags_idx.get(pr_dict["id"], [])
                prods.append(
                    SupplierProductDetails(
                        last_price=SupplierProductPrice(**_prx),
                        images=_imgs,
                        **{
                            **{
                                k: v
                                for k, v in pr_dict.items()
                                if k != "last_price_json"
                            },
                        },
                        tags=_tags,
                        stock=supp_prod_stock_dict.get(pr_dict["id"], None),
                    )
                )
        # build gql
        return prods

    async def count_ecommerce_supplier_restaurant_products(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        search: str,
    ) -> int:
        """Count all products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        supplier_unit_id : UUID
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierProductDetails]
        """
        # fetch supplier restaurant relation
        sr_rel = await self.supplier_restaurants_repo.raw_query(
            """SELECT * FROM supplier_restaurant_relation
                WHERE supplier_unit_id = :supplier_unit_id
                AND restaurant_branch_id = :restaurant_branch_id
            """,
            {
                "supplier_unit_id": supplier_unit_id,
                "restaurant_branch_id": restaurant_branch_id,
            },
        )
        if not sr_rel:
            return 0
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id, restaurant_branch_id
        )
        count = 0
        if spec_pl_ids:
            filter_qry = ""
            if search:
                filter_qry = f"""
                    AND (
                        unaccent(spr.description) ILIKE unaccent('%{search.replace(' ', '%')}%')
                        OR spt.tag_value ILIKE '%{search.replace(' ', '%')}%'
                    )
                """
            # get supplier prices
            pr_qry = f"""
                WITH category_tag AS (
                    SELECT
                        supplier_product_id,
                        string_agg(tag_value, ',') as tag_value
                    FROM supplier_product_tag
                    GROUP BY supplier_product_id
                )
                SELECT
                    count(spr.id) as total
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                LEFT JOIN category_tag spt on spt.supplier_product_id = spr.id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                {filter_qry}
                """
            sp_count = await self.supplier_restaurants_repo.raw_query(pr_qry, {})
            if sp_count and len(sp_count) > 0:
                count = sp_count[0]["total"]
        # build gql
        return count

    async def get_ecommerce_default_supplier_products(
        self,
        supplier_unit_id: UUID,
        search: str,
        page: int,
        page_size: int,
    ) -> List[SupplierProductDetails]:
        """Find all products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        supplier_unit_id : UUID
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierProductDetails]
        """
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id,
            uuid4(),  # random branch id - not used
            skip_specific=True,
        )
        prods = []
        if spec_pl_ids:
            # get supplier prices
            filter_qry = ""
            if search:
                filter_qry = f"""
                    AND (
                        unaccent(spr.description) ILIKE unaccent('%{search.replace(' ', '%')}%')
                        OR spt.tag_value ILIKE '%{search.replace(' ', '%')}%'
                    )
                """
            filter_qry += f"""
                ORDER BY spr.description
                LIMIT {page_size}
                OFFSET {page_size * (page - 1)}
            """
            pr_qry = f"""
                WITH category_tag AS (
                    SELECT
                        supplier_product_id,
                        string_agg(tag_value, ',') as tag_value
                    FROM supplier_product_tag
                    GROUP BY supplier_product_id
                )
                SELECT
                    spr.*,
                    row_to_json(last_price.*) AS last_price_json
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                LEFT JOIN category_tag spt on spt.supplier_product_id = spr.id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                {filter_qry}
                """
            sp_prices = await self.supplier_restaurants_repo.raw_query(pr_qry, {})
            # get images
            sprod_ids = [p["id"] for p in sp_prices]
            if sprod_ids:
                img_qry = f"""
                    SELECT
                        supplier_product_id,
                        image_url
                    FROM supplier_product_image
                    WHERE supplier_product_id IN {list_into_strtuple(sprod_ids)}
                    AND deleted = 'f' ORDER BY priority ASC
                    """
                sp_imgs = await self.supplier_restaurants_repo.raw_query(img_qry, {})
            else:
                sp_imgs = []
            sp_imgs_idx: Dict[UUID, List[str]] = {}
            for img in sp_imgs:
                if img["supplier_product_id"] not in sp_imgs_idx:
                    sp_imgs_idx[img["supplier_product_id"]] = []
                sp_imgs_idx[img["supplier_product_id"]].append(img["image_url"])
            # get tags
            if sprod_ids:
                tag_qry = f"""
                    SELECT
                        *
                    FROM supplier_product_tag
                    WHERE supplier_product_id IN {list_into_strtuple(sprod_ids)}
                    """
                sp_tags = await self.supplier_restaurants_repo.raw_query(tag_qry, {})
            else:
                sp_tags = []
            sp_tags_idx: Dict[UUID, List[SupplierProductTag]] = {}
            for tg in sp_tags:
                if tg["supplier_product_id"] not in sp_tags_idx:
                    sp_tags_idx[tg["supplier_product_id"]] = []
                sp_tags_idx[tg["supplier_product_id"]].append(SupplierProductTag(**tg))
            # get stock
            supp_prod_stock = (
                await self.supplier_product_stock_repo.fetch_latest_by_unit(
                    supplier_unit_id
                )
            )
            sup_prod_avail = await self.supplier_product_stock_repo.find_availability(
                supplier_unit_id, supp_prod_stock
            )
            supp_prod_stock_dict: Dict[UUID, SupplierProductStockWithAvailability] = {}
            for sps in sup_prod_avail:
                supp_prod_stock_dict[sps.supplier_product_id] = sps
            for p in sp_prices:
                # format sup prod
                pr_dict = dict(p)
                pr_dict["sell_unit"] = UOMType(pr_dict["sell_unit"])
                pr_dict["buy_unit"] = UOMType(pr_dict["buy_unit"])
                # format sup prod price
                _prx = json.loads(p["last_price_json"])
                _prx["id"] = UUID(_prx["id"])
                _prx["supplier_product_id"] = UUID(_prx["supplier_product_id"])
                _prx["created_by"] = UUID(_prx["created_by"])
                _prx["currency"] = CurrencyType(_prx["currency"])
                for _k in ["valid_from", "valid_upto", "created_at"]:
                    _prx[_k] = from_iso_format(_prx[_k])
                _imgs = sp_imgs_idx.get(pr_dict["id"], [])
                _tags = sp_tags_idx.get(pr_dict["id"], [])
                prods.append(
                    SupplierProductDetails(
                        last_price=SupplierProductPrice(**_prx),
                        images=_imgs,
                        **{
                            **{
                                k: v
                                for k, v in pr_dict.items()
                                if k != "last_price_json"
                            },
                        },
                        tags=_tags,
                        stock=supp_prod_stock_dict.get(pr_dict["id"], None),
                    )
                )
        # build gql
        return prods

    async def count_ecommerce_default_supplier_products(
        self,
        supplier_unit_id: UUID,
        search: str,
    ) -> int:
        """Count all products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        supplier_unit_id : UUID
        restaurant_branch_id : UUID

        Returns
        -------
        List[SupplierProductDetails]
        """
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id,
            uuid4(),  # random branch id - not used
            skip_specific=True,
        )
        count = 0
        if spec_pl_ids:
            # get supplier prices
            filter_qry = ""
            if search:
                filter_qry = f"""
                    AND (
                        unaccent(spr.description) ILIKE unaccent('%{search.replace(' ', '%')}%')
                        OR spt.tag_value ILIKE '%{search.replace(' ', '%')}%'
                    )
                """
            pr_qry = f"""
                WITH category_tag AS (
                    SELECT
                        supplier_product_id,
                        string_agg(tag_value, ',') as tag_value
                    FROM supplier_product_tag
                    GROUP BY supplier_product_id
                )
                SELECT
                    count(spr.id) as total
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                LEFT JOIN category_tag spt on spt.supplier_product_id = spr.id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                {filter_qry}
                """
            sp_count = await self.supplier_restaurants_repo.raw_query(pr_qry, {})
            # get images
            if sp_count and len(sp_count) > 0:
                count = sp_count[0]["total"]
        # build gql
        return count

    async def get_ecommerce_categories(
        self,
        supplier_unit_id: UUID,
    ) -> List[str]:
        """Get all supplier categories

        Args:
            supplier_unit_id (UUID)

        Returns:
            List[str]
        """
        qry = """
                SELECT
                    DISTINCT(spt.tag_value) as category
                FROM supplier_product spr
                LEFT JOIN supplier_product_tag spt on spt.supplier_product_id = spr.id
                WHERE spr.supplier_business_id IN (
                    SELECT supplier_business_id FROM supplier_unit WHERE id = :supplier_unit_id
                )
                AND spt.tag_key = 'category'
                """
        sp_categs = await self.supplier_restaurants_repo.raw_query(
            qry, {"supplier_unit_id": supplier_unit_id}
        )
        return [c["category"] for c in sp_categs]

    async def get_ecommerce_default_supplier_product_detail(
        self,
        supplier_unit_id: UUID,
        supplier_product_id: UUID,
    ) -> SupplierProductDetails | NoneType:
        """Find products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        supplier_unit_id : UUID
        supplier_product_id : UUID

        Returns
        -------
        SupplierProductDetails | NoneType
        """
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id,
            uuid4(),  # random branch id - not used
            skip_specific=True,
        )
        prod = None
        if spec_pl_ids:
            # get supplier prices
            pr_qry = f"""
                SELECT
                    spr.*,
                    row_to_json(last_price.*) AS last_price_json
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                AND spr.id = :supplier_product_id
                """
            sp_prices = await self.supplier_restaurants_repo.raw_query(
                pr_qry, {"supplier_product_id": supplier_product_id}
            )
            if not sp_prices:
                return None
            # get images
            sprod_ids = [p["id"] for p in sp_prices]
            if sprod_ids:
                img_qry = f"""
                    SELECT
                        supplier_product_id,
                        image_url
                    FROM supplier_product_image
                    WHERE supplier_product_id IN {list_into_strtuple(sprod_ids)}
                    AND deleted = 'f' ORDER BY priority ASC
                    """
                sp_imgs = await self.supplier_restaurants_repo.raw_query(img_qry, {})
            else:
                sp_imgs = []
            sp_imgs_idx: Dict[UUID, List[str]] = {}
            for img in sp_imgs:
                if img["supplier_product_id"] not in sp_imgs_idx:
                    sp_imgs_idx[img["supplier_product_id"]] = []
                sp_imgs_idx[img["supplier_product_id"]].append(img["image_url"])
            # get stock
            supp_prod_stock = await self.supplier_product_stock_repo.fetch_latest(
                supplier_product_id, supplier_unit_id=supplier_unit_id
            )
            sp_stock: SupplierProductStockWithAvailability | NoneType = None
            if supp_prod_stock:
                supp_prod_avail = await self.supplier_product_stock_repo.find_availability(
                    supplier_unit_id, [supp_prod_stock]
                )
                if len(supp_prod_avail) > 0:
                    sp_stock = supp_prod_avail[0]
            # format sup prod
            p = sp_prices[0]
            pr_dict = dict(p)
            pr_dict["sell_unit"] = UOMType(pr_dict["sell_unit"])
            pr_dict["buy_unit"] = UOMType(pr_dict["buy_unit"])
            # format sup prod price
            _prx = json.loads(p["last_price_json"])
            _prx["id"] = UUID(_prx["id"])
            _prx["supplier_product_id"] = UUID(_prx["supplier_product_id"])
            _prx["created_by"] = UUID(_prx["created_by"])
            _prx["currency"] = CurrencyType(_prx["currency"])
            for _k in ["valid_from", "valid_upto", "created_at"]:
                _prx[_k] = from_iso_format(_prx[_k])
            _imgs = sp_imgs_idx.get(pr_dict["id"], [])
            prod = SupplierProductDetails(
                last_price=SupplierProductPrice(**_prx),
                images=_imgs,
                **{
                    **{k: v for k, v in pr_dict.items() if k != "last_price_json"},
                },
                stock=sp_stock,
            )
        # build gql
        return prod

    async def get_ecommerce_supplier_restaurant_product_details(
        self,
        supplier_unit_id: UUID,
        restaurant_branch_id: UUID,
        supplier_product_id: UUID,
    ) -> SupplierProductDetails | NoneType:
        """Find products from a supplier restaurant
            - Business rules apply depending on the price list
                assigned to that restaurant branch

        Parameters
        ----------
        supplier_unit_id : UUID
        restaurant_branch_id : UUID
        supplier_product_id : UUID

        Returns
        -------
        SupplierProductDetails | NoneType
        """
        # fetch supplier restaurant relation
        sr_rel = await self.supplier_restaurants_repo.raw_query(
            """SELECT * FROM supplier_restaurant_relation
                WHERE supplier_unit_id = :supplier_unit_id
                AND restaurant_branch_id = :restaurant_branch_id
            """,
            {
                "supplier_unit_id": supplier_unit_id,
                "restaurant_branch_id": restaurant_branch_id,
            },
        )
        if not sr_rel:
            return None
        # get specific price list ids
        spec_pl_ids = await self.find_business_specific_price_ids(
            supplier_unit_id, restaurant_branch_id
        )
        prod = None
        if spec_pl_ids:
            # get supplier prices
            pr_qry = f"""
                SELECT
                    spr.*,
                    row_to_json(last_price.*) AS last_price_json
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                LEFT JOIN supplier_product_tag spt on spt.supplier_product_id = spr.id
                WHERE last_price.id IN {list_into_strtuple(spec_pl_ids)}
                AND spr.id = :supplier_product_id
                """
            sp_prices = await self.supplier_restaurants_repo.raw_query(
                pr_qry, {"supplier_product_id": supplier_product_id}
            )
            if not sp_prices:
                return None
            # get images
            sprod_ids = [p["id"] for p in sp_prices]
            if sprod_ids:
                img_qry = f"""
                    SELECT
                        supplier_product_id,
                        image_url
                    FROM supplier_product_image
                    WHERE supplier_product_id IN {list_into_strtuple(sprod_ids)}
                    AND deleted = 'f' ORDER BY priority ASC
                    """
                sp_imgs = await self.supplier_restaurants_repo.raw_query(img_qry, {})
            else:
                sp_imgs = []
            sp_imgs_idx: Dict[UUID, List[str]] = {}
            for img in sp_imgs:
                if img["supplier_product_id"] not in sp_imgs_idx:
                    sp_imgs_idx[img["supplier_product_id"]] = []
                sp_imgs_idx[img["supplier_product_id"]].append(img["image_url"])
            # get stock
            supp_prod_stock = await self.supplier_product_stock_repo.fetch_latest(
                supplier_product_id, supplier_unit_id=supplier_unit_id
            )
            sp_stock: SupplierProductStockWithAvailability | NoneType = None
            if supp_prod_stock:
                supp_prod_avail = await self.supplier_product_stock_repo.find_availability(
                    supplier_unit_id, [supp_prod_stock]
                )
                if len(supp_prod_avail) > 0:
                    sp_stock = supp_prod_avail[0]
            # format
            p = sp_prices[0]
            # format sup prod
            pr_dict = dict(p)
            pr_dict["sell_unit"] = UOMType(pr_dict["sell_unit"])
            pr_dict["buy_unit"] = UOMType(pr_dict["buy_unit"])
            # format sup prod price
            _prx = json.loads(p["last_price_json"])
            _prx["id"] = UUID(_prx["id"])
            _prx["supplier_product_id"] = UUID(_prx["supplier_product_id"])
            _prx["created_by"] = UUID(_prx["created_by"])
            _prx["currency"] = CurrencyType(_prx["currency"])
            for _k in ["valid_from", "valid_upto", "created_at"]:
                _prx[_k] = from_iso_format(_prx[_k])
            _imgs = sp_imgs_idx.get(pr_dict["id"], [])
            prod = SupplierProductDetails(
                last_price=SupplierProductPrice(**_prx),
                images=_imgs,
                **{
                    **{k: v for k, v in pr_dict.items() if k != "last_price_json"},
                },
                stock=sp_stock,
            )
        # build gql
        return prod

    async def assigned_supplier_restaurant(
        self,
        firebase_id: str,
        restaurant_branch_id: UUID,
        set_supplier_unit_id: UUID,
    ) -> SupplierRestaurantRelation:
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if not core_user:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="User not found",
            )
        # if core_user.id:
        supp_user = await self.supplier_user_repo.fetch(core_user.id)  # type: ignore
        if not supp_user:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="Supplier User not found",
            )
        supp_user.pop("user", None)
        supp_user_obj = SupplierUser(**supp_user)

        supp_user_perm = await self.supplier_user_permission_repo.fetch(
            supp_user_obj.id
        )
        if not supp_user_perm:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="Supplier User not found",
            )
        supp_user_perm_obj = SupplierUserPermission(**supp_user_perm)

        if not await self.restaurant_branch_repo.exists(restaurant_branch_id):
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg=f"Branch with id {restaurant_branch_id} not found",
            )

        restaurant_branch = await self.restaurant_branch_repo.fetch(
            restaurant_branch_id
        )
        if not restaurant_branch:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg=f"Branch with id {restaurant_branch_id} not found",
            )
        restaurant_branch_obj = RestaurantBranch(**restaurant_branch)

        actual_supplier_restaurant_relations = await self.search_supplier_business_restaurant(
            supp_user_perm_obj.supplier_business_id, restaurant_branch_obj.branch_name  # type: ignore
        )
        if not actual_supplier_restaurant_relations:
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg="Supplier Restaurant Relation not found",
            )

        if not await self.supplier_unit_repo.exists(set_supplier_unit_id):
            raise GQLApiException(
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                msg=f"Supplier Unit with id {set_supplier_unit_id} not found",
            )
        if actual_supplier_restaurant_relations:
            await self.supplier_restaurants_repo.reasign(
                restaurant_branch_id=restaurant_branch_id,
                supplier_unit_id=actual_supplier_restaurant_relations[
                    0
                ].supplier_unit_id,
                set_supplier_unit_id=set_supplier_unit_id,
            )
        # create new supplier restaurant relation
        sr_rel = await self.search_supplier_business_restaurant(
            supplier_business_id=supp_user_perm_obj.supplier_business_id,  # type: ignore
            restaurant_branch_id=restaurant_branch_id,
        )
        return sr_rel[0]

    async def get_clients_to_export(
        self,
        firebase_id: str,
    ) -> List[Dict[Any, Any]]:
        # get supplier business
        _, supplier_business = (
            await self.supplier_product_handler.fetch_supplier_business(firebase_id)
        )
        if not supplier_business:
            raise GQLApiException(
                msg="Issues to find supplier business",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        supp_bus_obd = SupplierBusiness(**supplier_business)
        # fetch invoices, suppliers and branches
        _clients = await self.supplier_restaurants_repo.fetch_clients_to_export(
            supplier_business_id=supp_bus_obd.id,
        )
        s_units = await self.supplier_restaurants_repo.raw_query(
            """SELECT id as supplier_unit_id FROM supplier_unit
            WHERE supplier_business_id = :supplier_business_id and deleted = 'f' """,
            {
                "supplier_business_id": supp_bus_obd.id,
            },
        )
        supplier_unit_ids = []
        cert_dict = {}
        for unit in s_units:
            unit = dict(unit)
            supplier_unit_ids.append(unit["supplier_unit_id"])
            # fetch certificate info
            certificate = await self.mx_sat_cer_repo.fetch_certificate(
                unit["supplier_unit_id"]
            )
            if not certificate:
                continue
            cert_dict[unit["supplier_unit_id"]] = MxSatInvoicingCertificateInfo(
                **certificate
            )
        _restaurants_info = await self.find_supplier_restaurants(
            supplier_unit_ids=supplier_unit_ids, firebase_id=firebase_id
        )
        rest_dict = {}
        for rest in _restaurants_info:
            if rest.restaurant_business_account:
                if rest.restaurant_business_account.restaurant_business_id:
                    rest_dict[
                        rest.restaurant_business_account.restaurant_business_id
                    ] = {
                        "account": rest.restaurant_business_account,
                        "relation": rest.relation,
                    }
        if not _clients:
            logger.warning("No clients found")
            return []
        for client in _clients:
            rba = rest_dict.get(client["restaurant_business_id"], None)
            if not rba:
                continue
            client["Nombre Contacto"] = rba["account"].legal_rep_name
            client["Correo electrónico"] = rba["account"].phone_number
            client["Teléfono"] = rba["account"].email
            if client["Régimen Fiscal"]:
                client["Régimen Fiscal"] = DataTypeDecoder.get_sat_regimen_status_key(
                    int(client["Régimen Fiscal"])
                )
            if client["Uso CFDI"]:
                client["Uso CFDI"] = DataTypeDecoder.get_cfdi_use_status_key(
                    int(client["Uso CFDI"])
                )
            if "relation" in rba:
                if not client["Tipo de Factura"]:
                    cert = cert_dict.get(rba["relation"].supplier_unit_id, None)
                    if cert:
                        client["Tipo de Factura"] = (
                            cert.invoicing_options.invoice_type.value
                        )
                        if not cert.invoicing_options.automated_invoicing:
                            client["Facturación Automática"] = "Desactivada"
                        else:
                            if (
                                cert.invoicing_options.triggered_at
                                == InvoiceTriggerTime.AT_DELIVERY
                            ):
                                client["Facturación Automática"] = "Al Marcar Entregado"
                            if (
                                cert.invoicing_options.triggered_at
                                == InvoiceTriggerTime.AT_PURCHASE
                            ):
                                client["Facturación Automática"] = "Al Confirmar"
                            if (
                                cert.invoicing_options.triggered_at
                                == InvoiceTriggerTime.AT_DAY_CLOSE
                            ):
                                client["Facturación Automática"] = "Al terminar el día"
                            if (
                                cert.invoicing_options.triggered_at
                                == InvoiceTriggerTime.AT_DELIVERY
                            ):
                                client["Facturación Automática"] = "Desactivada"
                        pass
        return _clients

    async def fetch_restaurant_branch_infocing_options(
        self, supplier_business_id: UUID, restaurant_branch_id: UUID
    ) -> SupplierRestaurantRelationMxInvoicingOptions | NoneType:
        spr = await self.supplier_restaurants_repo.search_supplier_business_restaurant(
            supplier_business_id=supplier_business_id,
            restaurant_branch_id=restaurant_branch_id,
        )
        if not spr:
            raise GQLApiException(
                msg="Does Not Found Supplier RestauranT Relation.",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED,
            )
        if spr and len(spr) > 1:
            raise GQLApiException(
                msg="This branch has more that 2 relations.",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED,
            )

        restaurant_branch_invoicing_options = await self.invoicing_options_repo.fetch(
            spr[0].id
        )
        return restaurant_branch_invoicing_options
