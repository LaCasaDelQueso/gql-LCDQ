from datetime import date, datetime, timedelta
import json
import ast
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from gqlapi.repository.supplier.supplier_price_list import DEFAULT_SP_PRICE_LIST_NAME
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
import pandas as pd

from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.models.v2.restaurant import RestaurantBranch
from gqlapi.domain.models.v2.supplier import (
    SupplierPriceList,
    SupplierProductImage,
    SupplierProductPrice,
    SupplierUnit,
)
from gqlapi.domain.models.v2.utils import CurrencyType
from gqlapi.domain.interfaces.v2.supplier.supplier_price_list import (
    PriceListItemDetails,
    SupplierPriceListBatch,
    SupplierPriceListDetails,
    SupplierPriceListHandlerInterface,
    SupplierPriceListRepositoryInterface,
    SupplierUnitDefaultPriceListsGQL
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductHandlerInterface,
    SupplierProductPriceRepositoryInterface,
    SupplierProductRepositoryInterface,
)
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.utils.batch_files import verify_supplier_product_row_is_complete
from gqlapi.utils.helpers import list_into_strtuple

logger = get_logger(get_app())


class SupplierPriceListHandler(SupplierPriceListHandlerInterface):
    def __init__(
        self,
        supplier_price_list_repo: SupplierPriceListRepositoryInterface,
        supplier_unit_repo: SupplierUnitRepositoryInterface,
        restaurant_branch_repo: RestaurantBranchRepositoryInterface,
        supplier_product_repo: SupplierProductRepositoryInterface,
        supplier_product_price_repo: SupplierProductPriceRepositoryInterface,
        supplier_product_handler: SupplierProductHandlerInterface,
    ) -> None:
        self.supplier_price_list_repo = supplier_price_list_repo
        self.supplier_unit_repo = supplier_unit_repo
        self.restaurant_branch_repo = restaurant_branch_repo
        self.supplier_product_repo = supplier_product_repo
        self.supplier_product_price_repo = supplier_product_price_repo
        self.supplier_product_handler = supplier_product_handler

    # Private Methods
    async def _validate_input_upsert_spl(
        self,
        supplier_unit_ids: List[UUID],
        restaurant_branch_ids: List[UUID],
    ) -> None:
        if len(supplier_unit_ids) == 0:
            raise GQLApiException(
                msg="Missing supplier unit ids",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        for su in supplier_unit_ids:
            if not await self.supplier_unit_repo.exists(su):
                raise GQLApiException(
                    msg="Supplier Unit does not exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
        for rb in restaurant_branch_ids:
            if not await self.restaurant_branch_repo.exists(rb):
                raise GQLApiException(
                    msg="Restaurant Branch does not exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )

    async def fetch_supplier_product_idxs(
        self, supplier_business_id: UUID
    ) -> Dict[str, Any]:
        # get supplier products
        curr_supplier_prods = await self.supplier_product_repo.find_many(
            cols=["id", "product_id", "sku", "upc", "description", "sell_unit"],
            tablename="supplier_product",
            filter_values=[
                {
                    "column": "supplier_business_id",
                    "operator": "=",
                    "value": f"'{supplier_business_id}'",
                }
            ],
        )
        # create idxs by sku
        curr_supplier_prods_idx = {p["sku"]: p for p in curr_supplier_prods}
        # return idxs
        return curr_supplier_prods_idx

    async def _upsert_supplier_product_price(
        self, sp: SupplierProductPrice, feedb: Dict[str, Any]
    ) -> SupplierPriceListBatch:
        spp_id = await self.supplier_product_price_repo.add(sp)
        # update feedb
        feedb["supplier_product_price_id"] = spp_id
        feedb["status"] = True if spp_id else False
        feedb["msg"] = (
            "Precio actualizado correctamente"
            if spp_id
            else "No se pudo actualizar el precio"
        )
        # return formated response
        return SupplierPriceListBatch(**feedb)

    async def _batch_upsert_from_filedata(
        self,
        data: pd.DataFrame,
        curr_supplier_prods_idx: Dict[Any, Any],
        core_user_id: UUID,
        valid_upto: date,
    ) -> List[SupplierPriceListBatch]:
        feedb_collector = []
        # iterate over all products
        for _, row in data.iterrows():
            row_dict = row.to_dict()
            # data validation
            data_integr = verify_supplier_product_row_is_complete(
                row=row_dict,
                valid_tax_ids=set(),
                supplier_product_idx={},
                sku_supplier_product_idx=curr_supplier_prods_idx,
                skip_tax_rev=True,
            )
            # return feedback if there is an issue
            if not data_integr["status"]:
                feedb_collector.append(
                    SupplierPriceListBatch(**data_integr["feedback"])
                )
                continue
            # validate if product exists
            sp_id = data_integr["data"].get("id", None)
            if not sp_id:
                _feedb = data_integr["feedback"]
                _feedb["msg"] = "No se encontró producto con el sku indicado"
                _feedb["status"] = False
                feedb_collector.append(SupplierPriceListBatch(**_feedb))
                continue
            if not data_integr["data"]["product_price"]:
                _feedb = data_integr["feedback"]
                _feedb["msg"] = "El precio del producto está vacío"
                _feedb["status"] = False
                feedb_collector.append(SupplierPriceListBatch(**_feedb))
                continue
            # build supplier price
            spp = SupplierProductPrice(
                id=uuid4(),
                supplier_product_id=sp_id,
                price=data_integr["data"]["product_price"],
                currency=CurrencyType.MXN,
                valid_from=datetime.utcnow(),
                valid_upto=datetime(valid_upto.year, valid_upto.month, valid_upto.day),
                created_by=core_user_id,
            )
            # upsert supplier product price
            feedb_collector.append(
                await self._upsert_supplier_product_price(spp, data_integr["feedback"])
            )
        # return feedback
        return feedb_collector

    def build_price_id_list_from_feedbacks(
        self, feedbacks: List[SupplierPriceListBatch]
    ) -> List[UUID]:
        return [
            fd.supplier_product_price_id
            for fd in feedbacks
            if fd.status and fd.supplier_product_price_id
        ]

    async def fetch_supplier_price_lists(
        self, supplier_unit_id: UUID
    ) -> List[SupplierPriceListDetails]:
        """Fetch supplier price lists
            - It takes all latest supplier price lists
              - the query groups by name to get the latest (by valid_upto) price list
              - the query filters by supplier_unit_id

        Parameters
        ----------
        firebase_id : str
        supplier_unit_id : UUID

        Returns
        -------
        List[SupplierPriceListDetails]
        """
        # get supplier price lists
        qry = """
            WITH last_price_list AS (
                WITH rcos AS (
                    SELECT id, supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                        name, is_default, valid_from, valid_upto, created_by, created_at, last_updated,
                        ROW_NUMBER() OVER (PARTITION BY name, supplier_unit_id ORDER BY last_updated DESC) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
            )
            SELECT * FROM last_price_list
            WHERE supplier_unit_id = :supplier_unit_id
            """
        supplier_price_lists = await self.supplier_price_list_repo.raw_query(
            qry, {"supplier_unit_id": supplier_unit_id}
        )

        if not supplier_price_lists:
            return []

        # parse supplier price lists & restaurant branch ids
        parsed_price_ids = []
        parsed_rb_ids = []
        for _spl in supplier_price_lists:
            parsed_price_ids.extend(json.loads(_spl["supplier_product_price_ids"]))
            _rbs = json.loads(_spl["supplier_restaurant_relation_ids"])
            parsed_rb_ids.extend(_rbs if _rbs else [])
        # get supplier product prices
        sp_ids = []
        if parsed_price_ids:
            pr_qry = f"""
                SELECT
                    last_price.id, supplier_product_id, price, currency,valid_from,
                    valid_upto, last_price.created_by, last_price.created_at,
                    spr.description as spr_description, spr.sell_unit as spr_sell_unit, spr.sku as spr_sku
                FROM supplier_product_price as last_price
                JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                WHERE last_price.id IN {list_into_strtuple(parsed_price_ids)}
                """
            sp_prices = await self.supplier_price_list_repo.raw_query(pr_qry, {})
        else:
            sp_prices = []
        for spp in sp_prices:
            sp_ids.append(spp["supplier_product_id"])
        img_qry = f"""
                SELECT *
                FROM supplier_product_image
                WHERE supplier_product_id IN {list_into_strtuple(sp_ids)}
                AND deleted = 'f' ORDER BY priority ASC
                """
        _imgs = await self.supplier_product_repo.raw_query(img_qry, {})
        imgs_idx = {i["supplier_product_id"]: [] for i in _imgs}
        for i in _imgs:
            imgs_idx[i["supplier_product_id"]].append(SupplierProductImage(**i))
        sp_prices_idx = {
            p["id"]: PriceListItemDetails(
                description=p["spr_description"],
                sell_unit=p["spr_sell_unit"],
                sku=p["spr_sku"],
                price=SupplierProductPrice(
                    currency=CurrencyType(p["currency"]),
                    **{
                        k: v
                        for k, v in dict(p).items()
                        if k
                        not in [
                            "spr_description",
                            "spr_sell_unit",
                            "spr_sku",
                            "currency",
                        ]
                    },
                ),
                images=imgs_idx.get(p["supplier_product_id"], None),
            )
            for p in sp_prices
        }
        # get restaurant branches
        if parsed_rb_ids:
            rb_qry = f"""
                SELECT * FROM restaurant_branch
                WHERE id IN {list_into_strtuple(parsed_rb_ids)}
                """
            rbranches = await self.supplier_price_list_repo.raw_query(rb_qry, {})
        else:
            rbranches = []
        rbranches_idx = {rb["id"]: RestaurantBranch(**rb) for rb in rbranches}
        # build response
        spl_gql_list = []
        for spl in supplier_price_lists:
            # supplier product price
            p_ids = [UUID(p) for p in json.loads(spl["supplier_product_price_ids"])]
            rb_ids = [
                UUID(rb) for rb in json.loads(spl["supplier_restaurant_relation_ids"])
            ]
            # gql obj
            spl_gql = SupplierPriceListDetails(
                prices_details=[
                    sp_prices_idx[p_id]
                    for p_id in p_ids
                    if p_id in sp_prices_idx.keys()
                ],
                clients=[
                    rbranches_idx[rb_id]
                    for rb_id in rb_ids
                    if rb_id in rbranches_idx.keys()
                ],
                supplier_product_price_ids=p_ids,
                supplier_restaurant_relation_ids=rb_ids,
                **{
                    k: v
                    for k, v in dict(spl).items()
                    if k
                    not in [
                        "supplier_product_price_ids",
                        "supplier_restaurant_relation_ids",
                        "currency",
                        "row_num",
                    ]
                },
            )
            spl_gql_list.append(spl_gql)
        # return supplier price lists
        return spl_gql_list

    async def fetch_supplier_product_default_price_list(
        self, supplier_product_id: UUID, supplier_business_id: UUID
    ) -> List[SupplierUnitDefaultPriceListsGQL]:
        """Fetch supplier product default price lists
            - It takes all latest supplier price lists
              - the query groups by name to get the latest (by valid_upto) price list
              - the query filters by supplier_unit_id

        Parameters
        ----------
        firebase_id : str
        supplier_product_id : UUID

        Returns
        -------
        List[SupplierUnit]
        """
        # get supplier price lists
        qry = """
            WITH last_price_list AS (
                WITH rcos AS (
                    SELECT id, supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                        name, is_default, valid_from, valid_upto, created_by, created_at, last_updated,
                        ROW_NUMBER() OVER (PARTITION BY name, supplier_unit_id ORDER BY last_updated DESC) row_num
                    FROM supplier_price_list
                )
                SELECT * FROM rcos WHERE row_num = 1
            )
            SELECT * FROM last_price_list
            WHERE supplier_unit_id IN (
                SELECT id FROM supplier_unit WHERE supplier_business_id = :supplier_business_id
            )
            """
        supplier_price_lists = await self.supplier_price_list_repo.raw_query(
            qry, {"supplier_business_id": supplier_business_id}
        )
        if not supplier_price_lists:
            return []
        # parse supplier price lists & restaurant branch ids

        parsed_su_ids = set()
        price_list_result=[]
        for _spl in supplier_price_lists:
            parsed_price_ids = []
            parsed_price_ids.extend(json.loads(_spl["supplier_product_price_ids"]))
            _spl_dict = dict(_spl)
            # get supplier product prices
            if parsed_price_ids:
                pr_qry = f"""
                    SELECT
                        last_price.id, supplier_product_id, price, currency,valid_from,
                        valid_upto, last_price.created_by, last_price.created_at
                    FROM supplier_product_price as last_price
                    JOIN supplier_product spr on spr.id = last_price.supplier_product_id
                    WHERE last_price.id IN {list_into_strtuple(parsed_price_ids)}
                    AND supplier_product_id = :supplier_product_id
                    """
                sp_prices = await self.supplier_price_list_repo.raw_query(
                    pr_qry, {"supplier_product_id": supplier_product_id}
                )
                if not sp_prices:
                    continue
                parsed_su_ids.add(_spl_dict["supplier_unit_id"])
                spl_dict = dict(_spl)
                del spl_dict["row_num"]
                price_list_result.append(
                    SupplierUnitDefaultPriceListsGQL(
                        unit=None,
                        price=SupplierProductPrice(**sp_prices[0]),
                        price_list=SupplierPriceList(**spl_dict),
                    )
                )
            else:
                continue
        # get restaurant branches
        if parsed_su_ids:
            rb_qry = f"""
                SELECT * FROM supplier_unit
                WHERE id IN {list_into_strtuple(list(parsed_su_ids))}
                """
            runits = await self.supplier_price_list_repo.raw_query(rb_qry, {})
        else:
            runits = []
        runits_idx = {su["id"]: SupplierUnit(**su) for su in runits}
        # build response
        for spl in price_list_result:
            su_find = runits_idx.get(spl.price_list.supplier_unit_id, None)
            if not su_find:
                continue
            spl.unit = su_find
        # return supplier price lists
        return price_list_result

    async def fetch_last_supplier_price_list(
        self,
        supplier_price_list_id: UUID,
    ) -> SupplierPriceList | NoneType:
        """Fetch supplier price list

        Parameters
        ----------
        supplier_price_list_id : UUID

        Returns
        -------
        SupplierPriceList
        """
        # get supplier price list
        _spl = await self.supplier_price_list_repo.raw_query(
            query="""
                WITH last_price_list AS (
                    WITH rcos AS (
                        SELECT id, supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                            name, is_default, valid_from, valid_upto, created_by, created_at, last_updated,
                            ROW_NUMBER() OVER (PARTITION BY name, supplier_unit_id ORDER BY last_updated DESC) row_num
                        FROM supplier_price_list
                    )
                    SELECT * FROM rcos WHERE row_num = 1
                )
                SELECT lpl.id, lpl.supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                    lpl.name, lpl.is_default, valid_from, valid_upto, lpl.created_by, lpl.created_at,
                    lpl.last_updated
                FROM last_price_list lpl
                WHERE lpl.id = :id
                """,
            vals={"id": supplier_price_list_id},
        )
        if not _spl or not _spl[0]:
            logger.warning(
                f"Could not find supplier price list with id: {supplier_price_list_id}"
            )
            return None
        spl = dict(_spl[0])
        # parse supplier price list
        spl["supplier_product_price_ids"] = json.loads(
            spl["supplier_product_price_ids"]
        )
        spl["supplier_restaurant_relation_ids"] = json.loads(
            spl["supplier_restaurant_relation_ids"]
        )
        # return supplier price list
        return SupplierPriceList(**spl)

    async def _fetch_core_user_id(self, firebase_id: str) -> UUID | NoneType:
        # fetch core user
        core_user_id = await self.supplier_price_list_repo.raw_query(
            query="SELECT id FROM core_user WHERE firebase_id = :firebase_id",
            vals={"firebase_id": firebase_id},
        )
        if not core_user_id or not core_user_id[0]:
            return None
        return core_user_id[0]["id"]

    # Class Methods
    async def upsert_supplier_price_list_file(
        self,
        firebase_id: str,
        name: str,
        supplier_unit_ids: List[UUID],
        price_list_file: bytes | str,
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
    ) -> List[SupplierPriceListBatch]:
        """Upser supplier price list file

        Parameters
        ----------
        firebase_id : str
        supplier_unit_id : UUID
        price_list_file : bytes | str
        restaurant_branch_ids : List[UUID]
        is_default : bool
        valid_until : date
        supplier_price_list_id : Optional[UUID], optional

        Returns
        -------
        List[SupplierPriceListBatch]
        """
        # validate input data
        await self._validate_input_upsert_spl(supplier_unit_ids, restaurant_branch_ids)
        # validate file
        xls = pd.ExcelFile(price_list_file)
        if len(xls.sheet_names) > 1:
            if "Sheet1" not in xls.sheet_names:
                return [
                    SupplierPriceListBatch(
                        status=False,
                        msg="El Archivo debe tener una sola hoja, o con nombre `Sheet1`",
                    )
                ]
            else:
                df = pd.read_excel(
                    xls, "Sheet1", dtype={"sat_product_code": str, "sku": str}
                )
        else:
            df = pd.read_excel(
                xls, xls.sheet_names[0], dtype={"sat_product_code": str, "sku": str}
            )
        # product / price data
        data: pd.DataFrame = (
            self.supplier_product_handler.validate_cols_supplier_products_file(df)
        )
        # get supplier business
        (
            core_user,
            supplier_business,
        ) = await self.supplier_product_handler.fetch_supplier_business(firebase_id)
        # build supplier product index by sku
        curr_supplier_prods_idx = await self.fetch_supplier_product_idxs(
            supplier_business["id"]
        )
        # batch upsert supplier products
        feedbacks = await self._batch_upsert_from_filedata(
            data,
            curr_supplier_prods_idx,
            core_user.id,  # type: ignore (safe to ignore)
            valid_upto=valid_until,
        )
        # create price list
        price_ids = self.build_price_id_list_from_feedbacks(feedbacks)
        if not price_ids:
            raise GQLApiException(
                msg="No valid products with price were found",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_MATCH.value,
            )
        for su in supplier_unit_ids:
            spl = SupplierPriceList(
                id=uuid4(),
                name=name,
                supplier_unit_id=su,
                supplier_restaurant_relation_ids=restaurant_branch_ids,
                supplier_product_price_ids=price_ids,
                is_default=is_default,
                valid_from=datetime.utcnow(),
                valid_upto=datetime(
                    valid_until.year, valid_until.month, valid_until.day
                ),
                created_by=core_user.id,  # type: ignore (safe to ignore)
            )
            if not await self.supplier_price_list_repo.add(spl):
                raise GQLApiException(
                    msg="Could not create Supplier Price List",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
        # return feedback
        return feedbacks

    async def add_price_to_price_list(
        self,
        firebase_id: str,
        price_list_id: UUID,
        supplier_product_id: UUID,
        price: float,
        valid_until: Optional[date] = None,
    ) -> bool:
        # fetch core user
        core_user_id = await self._fetch_core_user_id(firebase_id)
        if not core_user_id:
            raise GQLApiException(
                msg="Could not find Core User",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch price list
        spp_list = await self.fetch_last_supplier_price_list(price_list_id)
        if not spp_list:  # [TOREV] @Viz Not return False,
            logger.warning("Could not find Supplier Price List")
            return False
        # set valid until date based on: 1) passed value, 2) price list valid_upto, 3) tomorrow
        _valid_until = (
            valid_until
            if valid_until is not None
            else (
                spp_list.valid_upto
                if spp_list is not None
                else (date.today() + timedelta(days=1))
            )
        )
        # create product price
        spp = SupplierProductPrice(
            id=uuid4(),
            supplier_product_id=supplier_product_id,
            price=price,
            currency=CurrencyType.MXN,
            valid_from=datetime.utcnow(),
            valid_upto=datetime(
                _valid_until.year, _valid_until.month, _valid_until.day
            ),
            created_by=core_user_id,
        )
        sp_fb = await self._upsert_supplier_product_price(spp, {})
        if not sp_fb.status or not sp_fb.supplier_product_price_id:
            logger.warning("Could not create Supplier Product Price")
            return False
        # fetch supplier product ids from supplier price id list
        if len(spp_list.supplier_product_price_ids) > 0:
            sp_ids = await self.supplier_price_list_repo.raw_query(
                query=f"""SELECT id, supplier_product_id
                        FROM supplier_product_price
                        WHERE id IN {list_into_strtuple(spp_list.supplier_product_price_ids)}""",
                vals={},
            )
        else:
            sp_ids = []
        # get all supplier product ids except the one we are adding
        sp_spp_list = [
            sp["id"]
            for sp in sp_ids
            if sp["supplier_product_id"] != supplier_product_id
        ]
        sp_spp_list.append(sp_fb.supplier_product_price_id)
        spp_list.supplier_product_price_ids = sp_spp_list
        # create new uuid to update price list
        spp_list.id = uuid4()
        # return status
        _sp_id = await self.supplier_price_list_repo.add(spp_list)
        return _sp_id is not None

    async def add_price_to_default_price_lists(
        self,
        firebase_id: str,
        supplier_business_id: UUID,
        supplier_product_id: UUID,
        price: float,
    ) -> bool:
        # fetch core user
        core_user_id = await self._fetch_core_user_id(firebase_id)
        if not core_user_id:
            raise GQLApiException(
                msg="Could not find Core User",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch existing price lists
        qry = """
            WITH last_price_list AS (
                    WITH rcos AS (
                        SELECT id, supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                            name, is_default, valid_from, valid_upto, created_by, created_at, last_updated,
                            ROW_NUMBER() OVER (PARTITION BY name, supplier_unit_id ORDER BY last_updated DESC) row_num
                        FROM supplier_price_list
                    )
                    SELECT * FROM rcos WHERE row_num = 1
                )
            SELECT lpl.id, lpl.supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                    lpl.name, lpl.is_default, valid_from, valid_upto, lpl.created_by, lpl.created_at,
                    lpl.last_updated
            FROM last_price_list lpl
            JOIN supplier_unit su ON su.id = lpl.supplier_unit_id
            WHERE su.supplier_business_id = :supplier_business_id AND lpl.is_default = 't'
            """
        sp_price_lists_dict = await self.supplier_price_list_repo.raw_query(
            query=qry, vals={"supplier_business_id": supplier_business_id}
        )
        supplier_price_lists: List[SupplierPriceList] = []
        # if no supplier price lists, create one default per supplier_unit
        if not sp_price_lists_dict:
            s_units = await self.supplier_unit_repo.find(
                supplier_business_id=supplier_business_id
            )
            if not s_units:
                logger.warning("There are no Supplier Units created in this business")
                return False
            for su in s_units:
                _spp_list = SupplierPriceList(
                    id=uuid4(),
                    name=DEFAULT_SP_PRICE_LIST_NAME,
                    supplier_unit_id=su["id"],
                    supplier_restaurant_relation_ids=[],
                    supplier_product_price_ids=[],
                    is_default=True,
                    valid_from=datetime.utcnow(),
                    valid_upto=datetime.utcnow() + timedelta(days=1),
                    created_by=core_user_id,
                )
                _spp_list_id = await self.supplier_price_list_repo.add(_spp_list)
                if not _spp_list_id:
                    logger.warning(
                        f"Could not create Supplier Price List for Supplier Unit: {su['id']}"
                    )
                    return False
                # add price to price list
                supplier_price_lists.append(_spp_list)
        else:
            supplier_price_lists = [
                SupplierPriceList(**spl) for spl in sp_price_lists_dict
            ]
        # update price to all
        for spl in supplier_price_lists:
            if not await self.add_price_to_price_list(
                firebase_id=firebase_id,
                price_list_id=spl.id,
                supplier_product_id=supplier_product_id,
                price=price,
                valid_until=spl.valid_upto,
            ):
                logger.warning(f"Could not add price to Supplier Price List: {spl.id}")
                return False
        return True

    async def new_supplier_price_list(
        self,
        firebase_id: str,
        name: str,
        supplier_unit_ids: List[UUID],
        supplier_prices: List[Dict[str, Any]],
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
    ) -> List[SupplierPriceListBatch]:
        """New Supplier Price List

        - It validates if the supplier unit has a default price list
        and if it does, it will not create a new one.
        - It validates if the supplier unit has a price list with the same name
        and if it does, it will not create a new one.
        """
        # fetch core user
        core_user_id = await self._fetch_core_user_id(firebase_id)
        if not core_user_id:
            raise GQLApiException(
                msg="Could not find Core User",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # validate input data
        await self._validate_input_upsert_spl(supplier_unit_ids, restaurant_branch_ids)
        # for speed we will assume all supplier_product_ids are valid
        feedbacks = []
        valid_spp_ids = []
        for _sp in supplier_prices:
            sp = SupplierProductPrice(
                id=uuid4(),
                supplier_product_id=_sp["supplier_product_id"],
                price=_sp["price"],
                currency=CurrencyType.MXN,
                valid_from=datetime.utcnow(),
                valid_upto=datetime(
                    valid_until.year, valid_until.month, valid_until.day
                ),
                created_by=core_user_id,
            )
            _fdbk = await self._upsert_supplier_product_price(sp, {})
            feedbacks.append(_fdbk)
            if _fdbk.status and _fdbk.supplier_product_price_id:
                valid_spp_ids.append(_fdbk.supplier_product_price_id)
        # iterate over all supplier units
        for su in supplier_unit_ids:
            if is_default:
                # verify if there is a default price list
                _query = """SELECT id
                    FROM supplier_price_list
                    WHERE supplier_unit_id = :supplier_unit_id
                    AND is_default = 't'
                """
                default_id = await self.supplier_price_list_repo.raw_query(
                    query=_query, vals={"supplier_unit_id": su}
                )
                if default_id:
                    logger.warning(
                        f"There is already a default price list for supplier unit: {su}, we cannot create another one."
                    )
                    raise GQLApiException(
                        msg=f"Ya existe una Lista de Precios por Defecto para este CEDIS ({su}).",
                        error_code=GQLApiErrorCodeType.RECORD_ALREADY_EXIST.value,
                    )
            else:
                # verify if there is a price list with the same name
                _query = """SELECT id
                    FROM supplier_price_list
                    WHERE supplier_unit_id = :supplier_unit_id
                    AND name = :name
                """
                spl_id = await self.supplier_price_list_repo.raw_query(
                    query=_query,
                    vals={"supplier_unit_id": su, "name": name},
                )
                if spl_id:
                    logger.warning(
                        "There is already a price list with the same name for supplier unit: "
                        + f"{su}, we cannot create another one."
                    )
                    raise GQLApiException(
                        msg=f"Ya existe una Lista de Precios con el mismo nombre para este CEDIS ({su}).",
                        error_code=GQLApiErrorCodeType.RECORD_ALREADY_EXIST.value,
                    )
            # if all good, create price list
            spl = SupplierPriceList(
                id=uuid4(),
                name=name,
                supplier_unit_id=su,
                supplier_restaurant_relation_ids=restaurant_branch_ids,
                supplier_product_price_ids=valid_spp_ids,
                is_default=is_default,
                valid_from=datetime.utcnow(),
                valid_upto=datetime(
                    valid_until.year, valid_until.month, valid_until.day
                ),
                created_by=core_user_id,
            )
            if not await self.supplier_price_list_repo.add(spl):
                raise GQLApiException(
                    msg="Could not create Supplier Price List",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
        # return feedbacks
        return feedbacks
    
    async def edit_supplier_price_list(
        self,
        firebase_id: str,
        name: str,
        supplier_unit_ids: List[UUID],
        supplier_prices: List[Dict[str, Any]],
        restaurant_branch_ids: List[UUID],
        is_default: bool,
        valid_until: date,
    ) -> List[SupplierPriceListBatch]:
        """Edit Supplier Price List

        - It is a passthrough method, it will always create a new price list
        as the way to query it is by taking lastest version by the name and supplier_unit_id
        """
        # fetch core user
        core_user_id = await self._fetch_core_user_id(firebase_id)
        if not core_user_id:
            raise GQLApiException(
                msg="Could not find Core User",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # validate input data
        await self._validate_input_upsert_spl(supplier_unit_ids, restaurant_branch_ids)
        # for speed we will assume all supplier_product_ids are valid
        feedbacks = []
        valid_spp_ids = []
        for _sp in supplier_prices:
            sp = SupplierProductPrice(
                id=uuid4(),
                supplier_product_id=_sp["supplier_product_id"],
                price=_sp["price"],
                currency=CurrencyType.MXN,
                valid_from=datetime.utcnow(),
                valid_upto=datetime(
                    valid_until.year, valid_until.month, valid_until.day
                ),
                created_by=core_user_id,
            )
            _fdbk = await self._upsert_supplier_product_price(sp, {})
            feedbacks.append(_fdbk)
            if _fdbk.status and _fdbk.supplier_product_price_id:
                valid_spp_ids.append(_fdbk.supplier_product_price_id)
        # iterate over all supplier units
        for su in supplier_unit_ids:
            # create price list
            spl = SupplierPriceList(
                id=uuid4(),
                name=name,
                supplier_unit_id=su,
                supplier_restaurant_relation_ids=restaurant_branch_ids,
                supplier_product_price_ids=valid_spp_ids,
                is_default=is_default,
                valid_from=datetime.utcnow(),
                valid_upto=datetime(
                    valid_until.year, valid_until.month, valid_until.day
                ),
                created_by=core_user_id,
            )
            if not await self.supplier_price_list_repo.add(spl):
                raise GQLApiException(
                    msg="Could not create Supplier Price List",
                    error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
                )
        # return feedbacks
        return feedbacks

    async def edit_product_supplier_price_list(
        self,
        firebase_id: str,
        supplier_price_list_id: UUID,
        supplier_product_price_id: UUID,
        price: float,
    ) -> bool:
        """Edit Product Of Supplier Price List

        - It is a passthrough method, it will always create a new price list
        as the way to query it is by taking lastest version by the name and supplier_unit_id
        """
        # fetch core user
        
        core_user_id = await self._fetch_core_user_id(firebase_id)
        if not core_user_id:
            raise GQLApiException(
                msg="Could not find Core User",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # for speed we will assume all supplier_product_ids are valid
        supplier_product_price = await self.supplier_product_price_repo.get(
            supplier_product_price_id
        )
        if not supplier_product_price:
            raise GQLApiException(
                msg="Could not find Product Price",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_product_price_obj = SupplierProductPrice(**supplier_product_price)
        new_supp_prod_price = await self.supplier_product_price_repo.add(
            SupplierProductPrice(
                id=uuid4(),
                supplier_product_id=supplier_product_price_obj.supplier_product_id,
                price=price,
                currency=CurrencyType(supplier_product_price_obj.currency),
                valid_from=supplier_product_price_obj.valid_from,
                valid_upto=supplier_product_price_obj.valid_upto,
                created_by=core_user_id,
            )
        )
        price_list = await self.supplier_price_list_repo.raw_query(
            query="SELECT * from supplier_price_list WHERE id = :id",
            vals={"id": supplier_price_list_id},
        )
        if not price_list:
            raise GQLApiException(
                msg="Could not find Price List",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        price_list_obj = SupplierPriceList(**price_list[0])
        uuid_replacements = {
            supplier_product_price_id: new_supp_prod_price,
        }

        # Replace UUIDs in the list
        updated_uuid_list = price_list_obj.supplier_product_price_ids.replace(str(supplier_product_price_id), str(new_supp_prod_price))
        list_products = ast.literal_eval(updated_uuid_list)
        relation_list = ast.literal_eval(price_list_obj.supplier_restaurant_relation_ids)

        # Step 2: Convert each string to a UUID object
        uuid_list_products = [UUID(uuid_str) for uuid_str in list_products]
        uuid_relation_list = [UUID(uuid_str) for uuid_str in relation_list]
        
        if not updated_uuid_list:
            raise GQLApiException(
                msg="Could not find Price in Price ListList",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        spl = SupplierPriceList(
            id=uuid4(),
            name=price_list_obj.name,
            supplier_unit_id=price_list_obj.supplier_unit_id,
            supplier_restaurant_relation_ids=uuid_relation_list,
            supplier_product_price_ids=uuid_list_products,
            is_default=price_list_obj.is_default,
            valid_from=datetime.utcnow(),
            valid_upto=price_list_obj.valid_upto,
            created_by=core_user_id,
        )
        if not await self.supplier_price_list_repo.add(spl):
            raise GQLApiException(
                msg="Could not create Supplier Price List",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        # return feedbacks
        return True

    async def get_customer_product_price_list_to_export(
        self, supplier_product_price_list_id: UUID, supplier_unit_id: UUID
    ) -> List[Dict[Any, Any]]:
        # fetch supplier unit and supplier_business permissions
        supplier_unit = await self.supplier_unit_repo.fetch(supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Supplier Unit not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        su = SupplierUnit(**supplier_unit)
        # fetch invoices, suppliers and branches
        _prods_price_list = (
            await self.supplier_price_list_repo.fetch_price_list_to_export(
                supplier_product_price_list_id=supplier_product_price_list_id,
                supplier_business_id=su.supplier_business_id,
            )
        )
        if not _prods_price_list:
            logger.warning("No price list fetch")
            return []
        return _prods_price_list

    async def get_all_product_price_lists_to_export(
        self, supplier_unit_id: UUID
    ) -> List[Dict[Any, Any]]:
        # fetch supplier unit and supplier_business permissions
        supplier_unit = await self.supplier_unit_repo.fetch(supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Supplier Unit not found",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        su = SupplierUnit(**supplier_unit)
        # fetch invoices, suppliers and branches
        _prods = await self.supplier_price_list_repo.fetch_all_price_list_to_export(
            supplier_business_id=su.supplier_business_id
        )
        if not _prods:
            logger.warning("No price list fetch")
            return []
        return _prods

    async def delete_supplier_price_list(
        self, firebase_id: str, unit_id: UUID, supplier_product_price_list_id: UUID
    ) -> bool | NoneType:
        """Delete Supplier Price List

        - It is a passthrough method, it will always create a new price list
        as the way to query it is by taking lastest version by the name and supplier_unit_id
        """
        # fetch core user
        unit = await self.supplier_unit_repo.fetch(unit_id)
        if not unit:
            raise GQLApiException(
                msg="Could not find Unit",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        unit_obj = SupplierUnit(**unit)
        # validate input data
        supplier_product_price_list = await self.fetch_last_supplier_price_list(
            supplier_product_price_list_id
        )
        # for speed we will assume all supplier_product_ids are valid
        if not supplier_product_price_list:
            raise GQLApiException(
                msg="Could not find Supplier Price List",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if supplier_product_price_list.name == "Lista General de Precios":
            raise GQLApiException(
                msg="Could not delete defauls Supplier Price List",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if await self.supplier_price_list_repo.delete(
            supplier_product_price_list.name, unit_obj.supplier_business_id
        ):
            return True
