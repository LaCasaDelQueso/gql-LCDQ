import math
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import UUID, uuid4
import pandas as pd

from gqlapi.domain.interfaces.v2.supplier.supplier_price_list import (
    SupplierPriceListHandlerInterface,
)
from gqlapi.domain.models.v2.core import CoreUser
from gqlapi.domain.models.v2.utils import DataTypeDecoder, DataTypeTraslate, UOMType
from gqlapi.domain.interfaces.v2.catalog.category import CategoryRepositoryInterface
from gqlapi.domain.interfaces.v2.catalog.product import ProductRepositoryInterface
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_product import (
    SupplierProductDetailsGQL,
    SupplierProductHandlerInterface,
    SupplierProductPriceRepositoryInterface,
    SupplierProductRepositoryInterface,
    SupplierProductStockRepositoryInterface,
    SupplierProductStockWithAvailability,
    SupplierProductsBatch,
    SupplierProductsStockBatch,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_user import (
    SupplierUserPermissionRepositoryInterface,
    SupplierUserRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import (
    SupplierBusiness,
    SupplierProduct,
    SupplierProductImage,
    SupplierProductPrice,
    SupplierProductStock,
    SupplierProductTag,
    SupplierUnit,
)
from gqlapi.domain.interfaces.v2.supplier.supplier_unit import SupplierUnitRepositoryInterface
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.config import ALIMA_ADMIN_BUSINESS
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.utils.batch_files import (
    INTEGER_UOMS,
    SUPPLIER_PRODUCT_BATCH_FILE_COLS,
    SUPPLIER_PRODUCT_STOCK_BATCH_FILE_COLS,
    get_tag_info,
    verify_mins_and_increments,
    verify_supplier_product_row_is_complete,
)
from gqlapi.utils.domain_mapper import sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple
from gqlapi.repository.user.core_user import CoreUserRepositoryInterface

# logger
logger = get_logger(get_app())


class SupplierProductHandler(SupplierProductHandlerInterface):
    def __init__(
        self,
        supplier_business_repo: SupplierBusinessRepositoryInterface,
        core_user_repo: CoreUserRepositoryInterface,
        supplier_user_repo: SupplierUserRepositoryInterface,
        supplier_user_permission_repo: SupplierUserPermissionRepositoryInterface,
        product_repo: ProductRepositoryInterface,
        category_repo: CategoryRepositoryInterface,
        supplier_product_repo: SupplierProductRepositoryInterface,
        supplier_product_price_repo: SupplierProductPriceRepositoryInterface,
        supplier_price_list_handler: Optional[SupplierPriceListHandlerInterface] = None,
        supplier_unit_repo: Optional[SupplierUnitRepositoryInterface] = None,
        supplier_product_stock_repo: Optional[
            SupplierProductStockRepositoryInterface
        ] = None,
    ) -> None:
        self.supplier_business_repo = supplier_business_repo
        self.core_user_repo = core_user_repo
        self.supplier_user_repo = supplier_user_repo
        self.supplier_user_permission_repo = supplier_user_permission_repo
        self.product_repo = product_repo
        self.category_repo = category_repo
        self.supplier_product_repo = supplier_product_repo
        self.supplier_product_price_repo = supplier_product_price_repo
        if supplier_price_list_handler is not None:
            self.supplier_price_list_handler = supplier_price_list_handler
        if supplier_unit_repo:
            self.supplier_unit_repo = supplier_unit_repo
        if supplier_product_stock_repo:
            self.supplier_product_stock_repo = supplier_product_stock_repo

    def validate_cols_supplier_products_file(self, df: pd.DataFrame) -> pd.DataFrame:
        # validate that it contains all needed columns
        df_columns_set = set(df.columns)
        if not df_columns_set.issuperset(SUPPLIER_PRODUCT_BATCH_FILE_COLS):
            extra_columns = set(SUPPLIER_PRODUCT_BATCH_FILE_COLS) - df_columns_set
            raise GQLApiException(
                msg=f"Archivo de Productos tiene columnas faltantes! ({', '.join(extra_columns)})",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )

        # drop products that do not have a description or no sell_unit
        data = df[(~df["description"].isnull()) | (df["description"] == "")].copy()
        data = data[~data["sell_unit"].isnull()].copy()
        # drop duplicates with same sell_unit and description
        data.drop_duplicates(subset=["description", "sell_unit"], inplace=True)
        data = data.fillna("")

        # column filling
        if "product_id" not in data.columns:
            data["product_id"] = ""
        else:
            # dups = data.product_id.value_counts().to_dict()
            # if any([v > 1 for k, v in dups.items() if k != ""]):
            #     raise GQLApiException(
            #         msg="Archivo de Productos tiene un Alima ID duplicado!",
            #         error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            #     )
            # # if it has product_id then drop duplicates
            # try:
            #     data["product_id"] = data["product_id"].apply(lambda x: UUID(x) if x != "" else None)  # type: ignore
            # except Exception:
            #     raise GQLApiException(
            #         msg="Archivo de Productos tiene un Alima ID no válido!",
            #         error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            #     )
            data["product_id"] = ""
        if "long_description" not in data.columns:
            data["long_description"] = ""
        else:
            data["long_description"].astype(str)
        if "ieps_percent" not in data.columns:
            data["ieps_percent"] = None
        else:

            def _format_ieps(x: Any) -> float | None:
                if not x:
                    return None
                try:
                    return float(x)
                except Exception:
                    return None

            data["ieps_percent"] = data["ieps_percent"].apply(_format_ieps)
            data["ieps_percent"].astype(float)
        # if "upc_barcode" in data.columns:
            # data["upc_barcode"] = data["upc_barcode"].astype(str)
        if "sat_product_code" in data.columns:
            data["sat_product_code"].astype(str)
            # if df["sat_product_code"].dtype == "float64" or "int64":
            #     data["sat_product_code"] = (
            #         data["sat_product_code"].astype(int).astype(str)
            #     )
            data["sat_product_code"] = data["sat_product_code"].apply(
                lambda d: "00000000" if d == "0" else d
            )
        if "sku" not in data.columns:
            data["sku"] = ""
        else:

            def _format_sku(x: Any) -> str:
                str_x = str(x)
                if str_x.isdecimal():
                    if str_x.isnumeric():
                        # this are numbers that are not floats
                        return str_x
                    else:
                        return str(int(str_x))
                else:
                    return str_x

            data["sku"] = data["sku"].apply(_format_sku)
        if "id" not in data.columns:
            data["id"] = ""
        # If no data on the shee
        if data.empty:
            raise GQLApiException(
                msg="No se puede cargar archivo, el archivo tiene datos vacios!",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )
        # Remove duplicates by sku
        return data.drop_duplicates("sku", keep="first")

    def validate_cols_supplier_products_stock_file(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        # validate that it contains all needed columns
        df_columns_set = set(df.columns)
        if not df_columns_set.issuperset(SUPPLIER_PRODUCT_STOCK_BATCH_FILE_COLS):
            extra_columns = set(SUPPLIER_PRODUCT_STOCK_BATCH_FILE_COLS) - df_columns_set
            raise GQLApiException(
                msg=f"Archivo de Productos tiene columnas faltantes! ({', '.join(extra_columns)})",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )

        # drop products that do not have a description or no sell_unit
        data = df.dropna(subset=["sku"]).copy()
        data["keep_selling_without_stock"].fillna(False, inplace=True)
        data["keep_selling_without_stock"] = data["keep_selling_without_stock"].astype(
            bool
        )
        if "stock" not in data.columns:
            data["stock"] = None
        else:

            def _format_stock(x: Any) -> float | None:
                if math.isnan(x):
                    return None
                try:
                    return float(x)
                except Exception:
                    return None

            data["stock"] = data["stock"].apply(_format_stock)
            data["stock"].astype(float)
        if "sku" not in data.columns:
            data["sku"] = ""
        if "sell_unit" in data.columns:
            data.drop("sell_unit", axis=1, inplace=True)
        if "description" in data.columns:
            data.drop("description", axis=1, inplace=True)
        else:

            def _format_sku(x: Any) -> str:
                str_x = str(x)
                if str_x.isdecimal():
                    if str_x.isnumeric():
                        # this are numbers that are not floats
                        return str_x
                    else:
                        return str(int(str_x))
                else:
                    return str_x

            data["sku"] = data["sku"].apply(_format_sku)
        if data.empty:
            raise GQLApiException(
                msg="No se puede cargar archivo, el archivo tiene datos vacios!",
                error_code=GQLApiErrorCodeType.WRONG_COLS_FORMAT.value,
            )
        # Remove duplicates by sku
        return data.drop_duplicates("sku", keep="first")

    async def fetch_supplier_business(
        self, firebase_id: str
    ) -> Tuple[CoreUser, Dict[Any, Any]]:
        core_user = await self.core_user_repo.fetch_by_firebase_id(firebase_id)
        if core_user is not None:
            supplier_user = await self.supplier_user_repo.fetch(core_user.id)  # type: ignore
            if supplier_user is not None:
                supplier_perms = await self.supplier_user_permission_repo.fetch(
                    supplier_user["id"]  # type: ignore
                )
                if supplier_perms is not None:
                    supplier_business = await self.supplier_business_repo.fetch(
                        supplier_perms["supplier_business_id"]
                    )
                    if supplier_business is not None:
                        return core_user, supplier_business
        raise GQLApiException(
            msg="No se pudo encontrar el negocio del proveedor",
            error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
        )

    async def _upsert_supplier_product(
        self, sp: SupplierProduct, action: str, tag: Optional[SupplierProductTag] = None
    ) -> SupplierProductsBatch:
        if action == "edit":
            flag = await self.supplier_product_repo.edit(sp)
            if tag:
                if not await self.supplier_product_repo.add_file_tags(
                    supplier_product_id=sp.id, tags=[tag]
                ):
                    logger.warning("Could not add tags to supplier product")
        else:
            flag = await self.supplier_product_repo.add(sp)
            if tag:
                if not await self.supplier_product_repo.add_file_tags(
                    supplier_product_id=flag, tags=[tag]
                ):
                    logger.warning("Could not add tags to supplier product")
        # return formated response
        return SupplierProductsBatch(
            product_id=sp.product_id,
            supplier_product_id=sp.id,
            sku=sp.sku,
            description=sp.description,
            status=True,
            msg=(
                (
                    "Producto "
                    + ("actualizado" if action == "edit" else "creado")
                    + " correctamente"
                )
                if flag
                else (
                    "No se pudo "
                    + ("actualizar" if action == "edit" else "crear")
                    + "  el producto"
                )
            ),
        )

    async def _batch_upsert_with_product_id(
        self,
        supplier_business_id: UUID,
        data: pd.DataFrame,
        alima_supplier_prods_idx: Dict[Any, Any],
        curr_supplier_prods_idx: Dict[Any, Any],
        core_user_id: UUID,
    ) -> List[SupplierProductsBatch]:
        feedb_collector = []
        aux_supplier_prods_idx = {
            p["product_id"]: p
            for p in curr_supplier_prods_idx.values()
            if p["product_id"] is not None
        }
        sku_supplier_prods_idx = {p["sku"]: p for p in curr_supplier_prods_idx.values()}
        # iterate over all products, if it already exists then update it
        for _, row in data.iterrows():
            row_dict = row.to_dict()
            # at insert / update -> use product info
            row_dict["sku"] = str(row_dict["sku"])
            product_id = row["product_id"]
            # set unit multiple and min quantity from users preference
            u_multi = verify_mins_and_increments(
                row_dict["unit_multiple"], row_dict["sell_unit"]
            )
            m_qty = verify_mins_and_increments(
                row_dict["min_quantity"], row_dict["sell_unit"]
            )
            est_wgt = (
                verify_mins_and_increments(row_dict["estimated_weight"], "kg")
                if row_dict["estimated_weight"]
                else None
            )
            tag_val = get_tag_info(row_dict)
            # if product_id is not an Alima ID then return error
            alima_sup_prod_flag = product_id in alima_supplier_prods_idx
            if (
                u_multi is None
                or m_qty is None
                or not alima_sup_prod_flag
                or isinstance(tag_val, str)
            ):
                feedb_collector.append(
                    SupplierProductsBatch(
                        product_id=product_id,
                        supplier_product_id=row_dict.get("id", None),
                        sku=row_dict.get("sku", None),
                        description=row_dict.get("description", None),
                        status=False,
                        msg=(
                            "La cantidad mínima no es válida"
                            if m_qty is None
                            else (
                                "El incremento de unidad no es válido"
                                if u_multi is None
                                else (
                                    tag_val
                                    if isinstance(tag_val, str)
                                    else "Product ID no es válido"
                                )
                            )
                        ),
                    )
                )
                continue
            # if it exists then update it
            if (
                product_id in aux_supplier_prods_idx
                or row_dict["sku"] in sku_supplier_prods_idx
            ):
                alima_sup_prod = alima_supplier_prods_idx[product_id]  # safe search
                prev_sp = (
                    aux_supplier_prods_idx[product_id]
                    if product_id in aux_supplier_prods_idx
                    else sku_supplier_prods_idx[row_dict["sku"]]
                )
                # update product
                sp = SupplierProduct(
                    id=prev_sp["id"],
                    product_id=product_id,
                    supplier_business_id=supplier_business_id,
                    sku=row_dict.get(
                        "sku", str(uuid4())
                    ),  # this is always given by supplier
                    upc=None,
                    min_quantity=m_qty,
                    unit_multiple=u_multi,
                    sell_unit=UOMType(alima_sup_prod["sell_unit"]),
                    buy_unit=UOMType(alima_sup_prod["buy_unit"]),
                    estimated_weight=est_wgt,
                    # complete with alima data
                    **{
                        k: v
                        for k, v in alima_sup_prod.items()
                        if k
                        not in {
                            "id",
                            "product_id",
                            "supplier_business_id",
                            "sku",
                            "upc",
                            "min_quantity",
                            "unit_multiple",
                            "sell_unit",
                            "buy_unit",
                            "estimated_weight",
                        }
                    },
                )
                # update and retrieve feedback
                feedb_collector.append(await self._upsert_supplier_product(sp, "edit"))
            # if it does not exist then create it
            else:
                alima_sup_prod = alima_supplier_prods_idx[product_id]  # safe search
                # create product
                id = uuid4()
                sp = SupplierProduct(
                    id=id,
                    product_id=product_id,
                    supplier_business_id=supplier_business_id,
                    sku=row_dict.get(
                        "sku", str(uuid4())
                    ),  # this is always given by supplier
                    upc=None,
                    min_quantity=m_qty,
                    unit_multiple=u_multi,
                    is_active=True,
                    created_by=core_user_id,
                    sell_unit=UOMType(alima_sup_prod["sell_unit"]),
                    buy_unit=UOMType(alima_sup_prod["buy_unit"]),
                    estimated_weight=est_wgt,
                    # complete with alima data
                    **{
                        k: v
                        for k, v in alima_sup_prod.items()
                        if k
                        not in {
                            "id",
                            "product_id",
                            "supplier_business_id",
                            "sku",
                            "upc",
                            "min_quantity",
                            "unit_multiple",
                            "estimated_weight",
                            "sell_unit",
                            "buy_unit",
                            "is_active",
                            "created_by",
                        }
                    },
                )
                if isinstance(tag_val, bool) and tag_val:
                    tag = SupplierProductTag(
                        id=uuid4(),
                        supplier_product_id=id,
                        tag_key=str(row_dict.get("tag_key", "")),
                        tag_value=str(row_dict.get("tag_value", "")),
                    )
                # save and retrieve feedback
                feedb_collector.append(
                    await self._upsert_supplier_product(
                        sp,
                        "add",
                        tag=tag if (isinstance(tag_val, bool) and tag_val) else None,  # type: ignore
                    )
                )
        # return each product feedback
        return feedb_collector

    async def _batch_upsert_stock(
        self,
        data: pd.DataFrame,
        curr_supplier_prods_idx: Dict[Any, Any],
        core_user_id: UUID,
        supplier_units: List[UUID],
    ) -> List[SupplierProductsStockBatch]:
        feedb_collector = []
        sku_supplier_prods_idx = {p["sku"]: p for p in curr_supplier_prods_idx.values()}
        # iterate over all products, if it already exists then update it
        for _, row in data.iterrows():
            # Convert NaN to None in the row
            row_dict = {k: v if pd.notna(v) else None for k, v in row.items()}
            # at insert / update -> use product info
            row_dict["sku"] = str(row_dict["sku"])
            supplier_product = sku_supplier_prods_idx.get(row_dict["sku"], None)
            if not supplier_product:
                try:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            sku=row_dict["sku"],
                            status=False,
                            msg="No existe producto con ese SKU",
                        )
                    )
                    continue
                except Exception as e:
                    raise GQLApiException(
                        msg=f"No se pudo encontrar el producto: {e}",
                        error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            # set unit multiple and min quantity from users preference
            stock = row_dict.get("stock", None)
            active = False
            if isinstance(stock, float):
                active = True
            for unit in supplier_units:
                sps = SupplierProductStock(
                    id=uuid4(),
                    supplier_product_id=supplier_product.get("id"),
                    supplier_unit_id=unit,
                    stock=stock if stock else 0,
                    stock_unit=supplier_product.get("sell_unit"),
                    keep_selling_without_stock=bool(
                        row_dict.get("keep_selling_without_stock", False)
                    ),
                    created_by=core_user_id,
                    active=active,
                )
                try:
                    flag = await self.supplier_product_stock_repo.add(sps)
                except Exception as e:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            supplier_product_id=supplier_product.get("id", None),
                            sku=supplier_product.get("sku", None),
                            description=supplier_product.get("description", None),
                            status=False,
                            msg=str(e),
                        )
                    )
                if flag:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            supplier_product_id=supplier_product.get("id", None),
                            sku=supplier_product.get("sku", None),
                            description=supplier_product.get("description", None),
                            status=True,
                            msg="Se guardo correctamente el stock",
                        )
                    )
                else:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            supplier_product_id=supplier_product.get("id", None),
                            sku=supplier_product.get("sku", None),
                            description=supplier_product.get("description", None),
                            status=False,
                            msg="Error al guardar el stock",
                        )
                    )
        # return each product feedback
        return feedb_collector

    async def _upsert_stock_list(
        self,
        data: pd.DataFrame,
        curr_supplier_prods_idx: Dict[Any, Any],
        core_user_id: UUID,
        supplier_units: List[UUID],
    ) -> List[SupplierProductsStockBatch]:
        feedb_collector = []
        sku_supplier_prods_idx = {p["sku"]: p for p in curr_supplier_prods_idx.values()}
        # iterate over all products, if it already exists then update it
        for _, row in data.iterrows():
            # Convert NaN to None in the row
            row_dict = {k: v if pd.notna(v) else None for k, v in row.items()}
            # at insert / update -> use product info
            row_dict["sku"] = str(row_dict["sku"])
            supplier_product = sku_supplier_prods_idx.get(row_dict["sku"], None)
            if not supplier_product:
                try:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            sku=row_dict["sku"],
                            status=False,
                            msg="No existe producto con ese SKU",
                        )
                    )
                    continue
                except Exception as e:
                    raise GQLApiException(
                        msg=f"No se pudo encontrar el producto: {e}",
                        error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            # set unit multiple and min quantity from users preference
            stock = row_dict.get("stock", None)
            active = bool(row_dict.get("active", False))
            for unit in supplier_units:
                sps = SupplierProductStock(
                    id=uuid4(),
                    supplier_product_id=supplier_product.get("id"),
                    supplier_unit_id=unit,
                    stock=stock if stock else 0,
                    stock_unit=supplier_product.get("sell_unit"),
                    keep_selling_without_stock=bool(
                        row_dict.get("keep_selling_without_stock", False)
                    ),
                    created_by=core_user_id,
                    active=active,
                )
                try:
                    flag = await self.supplier_product_stock_repo.add(sps)
                except Exception as e:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            supplier_product_id=supplier_product.get("id", None),
                            sku=supplier_product.get("sku", None),
                            description=supplier_product.get("description", None),
                            status=False,
                            msg=str(e),
                        )
                    )
                if flag:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            supplier_product_id=supplier_product.get("id", None),
                            sku=supplier_product.get("sku", None),
                            description=supplier_product.get("description", None),
                            status=True,
                            msg="Se guardo correctamente el stock",
                        )
                    )
                else:
                    feedb_collector.append(
                        SupplierProductsStockBatch(
                            supplier_product_id=supplier_product.get("id", None),
                            sku=supplier_product.get("sku", None),
                            description=supplier_product.get("description", None),
                            status=False,
                            msg="Error al guardar el stock",
                        )
                    )
        # return each product feedback
        return feedb_collector

    async def _batch_upsert_from_filedata(
        self,
        supplier_business_id: UUID,
        data: pd.DataFrame,
        curr_supplier_prods_idx: Dict[Any, Any],
        tax_codes: Set[str],
        core_user_id: UUID,
    ) -> List[SupplierProductsBatch]:
        feedb_collector = []
        desc_supplier_prods_idx = {
            p["description"].lower(): p for p in curr_supplier_prods_idx.values()
        }
        sku_supplier_prods_idx = {p["sku"]: p for p in curr_supplier_prods_idx.values()}
        # iterate over all products, if it already exists then update it
        for _, row in data.iterrows():
            row_dict = row.to_dict()
            # at insert / update ->  verify it contains all needed info (sat codes, etc)
            # data validation
            data_integr = verify_supplier_product_row_is_complete(
                row_dict, tax_codes, desc_supplier_prods_idx, sku_supplier_prods_idx
            )
            tag_val = get_tag_info(row_dict)
            # return feedback if there is an issue
            if not data_integr["status"]:
                feedb_collector.append(SupplierProductsBatch(**data_integr["feedback"]))
                continue
            if isinstance(tag_val, str):
                feedb_collector.append(
                    SupplierProductsBatch(
                        supplier_product_id=row_dict.get("id", None),
                        sku=row_dict.get("sku", None),
                        description=row_dict.get("description", None),
                        status=False,
                        msg=(
                            tag_val
                            if isinstance(tag_val, str)
                            else "Error al crear producto"
                        ),
                    )
                )
                continue
            # build supplier product - with passed id or create a new one
            sp_id = data_integr["data"].get("id", None)
            sp_id = sp_id if sp_id is not None else uuid4()
            sp = SupplierProduct(
                id=sp_id,
                supplier_business_id=supplier_business_id,
                created_by=core_user_id,
                is_active=True,
                **{
                    k: v
                    for k, v in data_integr["data"].items()
                    if k
                    not in {
                        "id",
                        "max_daily_stock",
                        "product_price",
                    }
                },
            )
            if isinstance(tag_val, bool) and tag_val:
                tag = SupplierProductTag(
                    id=uuid4(),
                    supplier_product_id=sp_id,
                    tag_key=str(row_dict.get("tag_key", "")),
                    tag_value=str(row_dict.get("tag_value", "")),
                )
            # if it exists then update it
            if (
                data_integr["data"]["id"]
                and data_integr["data"]["id"] in curr_supplier_prods_idx
            ):
                sup_prod = curr_supplier_prods_idx[data_integr["data"]["id"]]
                # update and retrieve feedback
                sp.id = sup_prod["id"]
                feedb_collector.append(
                    await self._upsert_supplier_product(
                        sp,
                        "edit",
                        tag=tag if (isinstance(tag_val, bool) and tag_val) else None,  # type: ignore
                    )
                )  # type: ignore
            # if not create one
            else:
                # save and retrieve feedback
                feedb_collector.append(
                    await self._upsert_supplier_product(
                        sp,
                        "add",
                        tag=tag if (isinstance(tag_val, bool) and tag_val) else None,  # type: ignore
                    )
                )
        # return each product feedback
        return feedb_collector

    async def get_sat_codes(
        self,
    ) -> Set[str]:
        # get sat codes
        qry = "SELECT sat_code FROM mx_sat_product_code"
        # fetch products
        tax_codes = await self.supplier_product_repo.raw_query(qry, {})
        # return codes
        return set(str(t["sat_code"]) for t in tax_codes if t["sat_code"] is not None)

    async def fetch_product_idxs(
        self, supplier_business_id: UUID
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        # get products
        alima_sup_prods = await self.supplier_product_repo.find(
            supplier_business_id=UUID(ALIMA_ADMIN_BUSINESS)
        )
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
        # create idxs
        alima_sup_prods_idx = {p["product_id"]: p for p in alima_sup_prods}
        curr_supplier_prods_idx = {p["id"]: p for p in curr_supplier_prods}
        # return idxs
        return alima_sup_prods_idx, curr_supplier_prods_idx

    async def upsert_supplier_products_file(
        self,
        firebase_id: str,
        product_file: bytes | str,
    ) -> List[SupplierProductsBatch]:
        """Upsert supplier products from file

        Parameters
        ----------
        firebase_id : str
        product_file : bytes | str

        Returns
        -------
        List[SupplierProductsBatch]
        """
        # validate file
        xls = pd.ExcelFile(product_file)
        if len(xls.sheet_names) > 1:
            if "Sheet1" not in xls.sheet_names:
                return [
                    SupplierProductsBatch(
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
        data = self.validate_cols_supplier_products_file(df)
        # get supplier business
        core_user, supplier_business = await self.fetch_supplier_business(firebase_id)
        # split validation between those with product id or not
        data_with_product_id = data[
            (data["product_id"] != "") & (~data["product_id"].isnull())
        ]
        data_without_product_id = data[
            (data["product_id"] == "") | (data["product_id"].isnull())
        ]
        (
            alima_supplier_prods_idx,
            curr_supplier_prods_idx,
        ) = await self.fetch_product_idxs(supplier_business["id"])
        tax_codes = await self.get_sat_codes()
        # batch upsert
        feedbacks = await self._batch_upsert_with_product_id(
            supplier_business["id"],
            data_with_product_id,
            alima_supplier_prods_idx,
            curr_supplier_prods_idx,
            core_user_id=core_user.id,  # type: ignore
        )
        feedbacks += await self._batch_upsert_from_filedata(
            supplier_business["id"],
            data_without_product_id,
            curr_supplier_prods_idx,
            tax_codes,
            core_user_id=core_user.id,  # type: ignore
        )
        # return data
        return feedbacks

    async def upsert_supplier_products_stock_file(
        self,
        firebase_id: str,
        product_stock_file: bytes | str,
        supplier_units: List[UUID],
    ) -> List[SupplierProductsStockBatch]:
        """Upsert supplier products from file

        Parameters
        ----------
        firebase_id : str
        product_stock_file : bytes | str

        Returns
        -------
        List[SupplierProductsStockBatch]
        """
        # validate file
        xls = pd.ExcelFile(product_stock_file)
        if len(xls.sheet_names) > 1:
            if "Sheet1" not in xls.sheet_names:
                return [
                    SupplierProductsStockBatch(
                        status=False,
                        msg="El Archivo debe tener una sola hoja, o con nombre `Sheet1`",
                    )
                ]
            else:
                df = pd.read_excel(xls, "Sheet1", dtype={"sku": str})
        else:
            df = pd.read_excel(xls, xls.sheet_names[0], dtype={"sku": str})
        data = self.validate_cols_supplier_products_stock_file(df)
        # get supplier business
        core_user, supplier_business = await self.fetch_supplier_business(firebase_id)
        # split validation between those with product id or not
        (
            alima_supplier_prods_idx,
            curr_supplier_prods_idx,
        ) = await self.fetch_product_idxs(supplier_business["id"])
        # batch upsert
        feedbacks = await self._batch_upsert_stock(
            data,
            curr_supplier_prods_idx,
            core_user_id=core_user.id,  # type: ignore
            supplier_units=supplier_units,
        )
        # return data
        return feedbacks

    async def upsert_supplier_products_stock_list(
        self,
        firebase_id: str,
        supplier_stock: List[Dict[str, Any]],
        supplier_units: List[UUID],
    ) -> List[SupplierProductsStockBatch]:
        """Upsert supplier products from file

        Parameters
        ----------
        firebase_id : str
        product_stock_file : bytes | str

        Returns
        -------
        List[SupplierProductsStockBatch]
        """
        # validate file
        # convert supplier_stock to df
        df = pd.DataFrame(supplier_stock)
        # get supplier business
        core_user, supplier_business = await self.fetch_supplier_business(firebase_id)
        # split validation between those with product id or not
        (
            alima_supplier_prods_idx,
            curr_supplier_prods_idx,
        ) = await self.fetch_product_idxs(supplier_business["id"])
        # batch upsert
        feedbacks = await self._upsert_stock_list(
            df,
            curr_supplier_prods_idx,
            core_user_id=core_user.id,  # type: ignore
            supplier_units=supplier_units,
        )
        # return data
        return feedbacks

    async def fetch_supplier_products(
        self, firebase_id: str
    ) -> List[SupplierProductDetailsGQL]:
        """Fetch supplier products

        Parameters
        ----------
        firebase_id : str

        Returns
        -------
        List[SupplierProductDetailsGQL]
        """
        # get supplier business
        _, supplier_business = await self.fetch_supplier_business(firebase_id)
        # get all products with last price and stock
        qry = """
            SELECT
                *
            FROM supplier_product sp
            WHERE sp.supplier_business_id = :supplier_business_id
        """
        # fetch products
        supplier_products = await self.supplier_product_repo.raw_query(
            qry, {"supplier_business_id": supplier_business["id"]}
        )
        # fetcch tags and build idx
        if supplier_products:
            sp_ids = [sp["id"] for sp in supplier_products]
            _tags = await self.supplier_product_repo.fetch_tags_from_many(sp_ids)
            img_qry = f"""
                    SELECT *
                    FROM supplier_product_image
                    WHERE supplier_product_id IN {list_into_strtuple(sp_ids)}
                    AND deleted = 'f' ORDER BY priority ASC
                    """
            _imgs = await self.supplier_product_repo.raw_query(img_qry, {})
        else:
            _tags, _imgs = [], []
        # build idxs
        tags_idx = {t.supplier_product_id: [] for t in _tags}
        for t in _tags:
            tags_idx[t.supplier_product_id].append(t)
        imgs_idx = {i["supplier_product_id"]: [] for i in _imgs}
        for i in _imgs:
            imgs_idx[i["supplier_product_id"]].append(SupplierProductImage(**i))
        # format response
        sup_prods_gql = []
        for sp in supplier_products:
            sp_dict = dict(sp)
            # format special data types - supplier product
            sp_dict["sell_unit"] = UOMType(sp_dict["sell_unit"])
            sp_dict["buy_unit"] = UOMType(sp_dict["buy_unit"])
            _sp = SupplierProduct(
                **{
                    k: v
                    for k, v in sp_dict.items()
                    if (not k.startswith("lpsp") and not k.startswith("lssp"))
                }
            )
            # format special data types - supplier product price
            _spp = None
            # else:
            _sps = None
            # add tags
            sp_tags = tags_idx.get(sp["id"], [])
            # add images
            sp_imgs = imgs_idx.get(sp["id"], [])
            # append to list
            sup_prods_gql.append(
                SupplierProductDetailsGQL(
                    last_price=_spp,
                    stock=_sps,
                    tags=sp_tags,
                    images=sp_imgs,
                    **_sp.__dict__,
                )
            )
        # return data
        return sup_prods_gql

    async def fetch_supplier_products_stock(
        self, firebase_id: str, supplier_unit_id: UUID
    ) -> List[SupplierProductDetailsGQL]:
        """Fetch supplier products

        Parameters
        ----------
        firebase_id : str

        Returns
        -------
        List[SupplierProductDetailsGQL]
        """
        products = await self.fetch_supplier_products(firebase_id)
        if not products:
            return []
        supplier_product_stock = (
            await self.supplier_product_stock_repo.fetch_latest_by_unit(
                supplier_unit_id
            )
        )
        if not supplier_product_stock:
            return []
        supplier_product_stock_availability = (
            await self.supplier_product_stock_repo.find_availability(
                supplier_unit_id, stock_products=supplier_product_stock
            )
        )
        if not supplier_product_stock_availability:
            return []
        supplier_product_stock_dict = {}
        for stock in supplier_product_stock_availability:
            supplier_product_stock_dict[stock.supplier_product_id] = stock
        product_unit_stock = []
        for prod in products:
            prod.stock = supplier_product_stock_dict.get(prod.id, None)
            # if prod.stock and prod.stock.created_at:
            #     # Convert utc to local time mexico city
            #     prod_stock_created_at_utc = prod.stock.created_at.replace(
            #         tzinfo=pytz.utc
            #     )
            #     prod.stock.created_at = prod_stock_created_at_utc.astimezone(APP_TZ)
            if prod.stock:
                product_unit_stock.append(prod)
        return product_unit_stock

    async def fetch_supplier_product(
        self, firebase_id: str, supplier_product_id: UUID
    ) -> SupplierProductDetailsGQL:
        """Fetch supplier product

        Parameters
        ----------
        firebase_id : str
        supplier_product_id : UUID

        Returns
        -------
        SupplierProductDetailsGQL
        """
        # get supplier business
        _, supplier_business = await self.fetch_supplier_business(firebase_id)
        # get all products with last price and stock
        qry = """
            WITH last_stock AS (
                WITH rcos AS (
                    SELECT id, supplier_product_id, supplier_unit_id, stock, stock_unit, created_by,
                        created_at, active, keep_selling_without_stock,
                        ROW_NUMBER() OVER (PARTITION BY supplier_product_id, supplier_unit_id ORDER BY created_at DESC) row_num
                    FROM supplier_product_stock
                )
                SELECT * FROM rcos WHERE row_num = 1
            )
            SELECT
                sp.*,
                lssp.id as lssp_id,
                lssp.supplier_product_id as lssp_supplier_product_id,
                lssp.supplier_unit_id as lssp_supplier_unit_id,
                lssp.stock as lssp_stock,
                lssp.stock_unit as lssp_stock_unit,
                lssp.created_by as lssp_created_by,
                lssp.created_at as lssp_created_at,
                lssp.active as lssp_active,
                lssp.keep_selling_without_stock as lssp_keep_selling_without_stock
            FROM supplier_product sp
            LEFT JOIN last_stock lssp ON sp.id = lssp.supplier_product_id
            WHERE sp.supplier_business_id = :supplier_business_id
            AND sp.id = :supplier_product_id
        """
        # fetch products
        supplier_products = await self.supplier_product_repo.raw_query(
            qry,
            {
                "supplier_business_id": supplier_business["id"],
                "supplier_product_id": supplier_product_id,
            },
        )
        if not supplier_products:
            raise GQLApiException(
                msg="Could not find product with given supplier: {}".format(
                    supplier_product_id
                ),
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sp_dict = dict(supplier_products[0])
        # fetch default price
        pqry = """
            WITH expanded_def_price AS (
                WITH expanded_price_list AS (
                    WITH last_price_list AS (
                        WITH rcos AS (
                            SELECT id, supplier_unit_id, supplier_restaurant_relation_ids, supplier_product_price_ids,
                                name, is_default, valid_from, valid_upto, created_by, created_at, last_updated,
                                ROW_NUMBER() OVER (PARTITION BY name, supplier_unit_id ORDER BY last_updated DESC) row_num
                            FROM supplier_price_list
                        )
                        SELECT * FROM rcos WHERE row_num = 1
                    )

                    SELECT lpl.id, lpl.supplier_unit_id, json_array_elements(lpl.supplier_product_price_ids) spp_id
                    FROM last_price_list lpl
                    WHERE is_default = 't'
                )
                SELECT edp.id as plist_id,
                        edp.supplier_unit_id,
                        REPLACE(edp.spp_id::varchar, '"', '') as spp_id
                FROM expanded_price_list edp
            )
            SELECT spp.* FROM expanded_def_price edp
            JOIN supplier_product_price spp ON spp.id::varchar = edp.spp_id
            WHERE spp.supplier_product_id = :supplier_product_id
            AND spp.valid_upto::date >= CURRENT_DATE
            ORDER BY valid_upto DESC
        """
        prices = await self.supplier_product_repo.raw_query(
            pqry, {"supplier_product_id": supplier_product_id}
        )
        # fetch images
        img_qry = """
            SELECT *
            FROM supplier_product_image
            WHERE supplier_product_id = :sp_id
            AND deleted = 'f' ORDER BY priority ASC
            """
        sp_imgs = await self.supplier_product_repo.raw_query(
            img_qry, {"sp_id": supplier_product_id}
        )
        # format response
        if prices:
            _spp = SupplierProductPrice(**dict(prices[0]))
        else:
            _spp = None
        if sp_imgs:
            _spimgs = [
                SupplierProductImage(**sql_to_domain(sp_img, SupplierProductImage))
                for sp_img in sp_imgs
            ]
        else:
            _spimgs = []
        # format special data types - supplier product
        sp_dict["sell_unit"] = UOMType(sp_dict["sell_unit"])
        sp_dict["buy_unit"] = UOMType(sp_dict["buy_unit"])
        _sp = SupplierProduct(
            **{k: v for k, v in sp_dict.items() if (not k.startswith("lssp"))}
        )
        # format special data types - supplier product price
        if sp_dict["lssp_stock"] is not None:
            # format special data types - supplier product stock
            sp_dict["lssp_stock_unit"] = UOMType(sp_dict["lssp_stock_unit"])
            _sps = SupplierProductStockWithAvailability(
                **{
                    k.replace("lssp_", ""): v
                    for k, v in sp_dict.items()
                    if k.startswith("lssp")
                }
            )
        else:
            _sps = None
        # fetch tags
        sp_tags = await self.supplier_product_repo.fetch_tags(supplier_product_id)
        # return data
        return SupplierProductDetailsGQL(
            last_price=_spp, stock=_sps, tags=sp_tags, images=_spimgs, **_sp.__dict__
        )

    async def add_supplier_product(
        self,
        firebase_id: str,
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
        default_price: Optional[float] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
        long_description: Optional[str] = None,
        mx_ieps: Optional[float] = None,
    ) -> SupplierProductDetailsGQL:
        # get supplier user
        core_user, supplier_business = await self.fetch_supplier_business(firebase_id)
        # verify tax id is within sat codes
        tax_codes = await self.get_sat_codes()
        if tax_id not in tax_codes:
            raise GQLApiException(
                msg="Tax Code is not Valid",
                error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        tax_uom = DataTypeDecoder.get_sat_unit_code(sell_unit.value)
        # verify that the product does not exist - by supplier business & sku
        prev_sps = await self.supplier_product_repo.find(
            supplier_business_id=supplier_business_id, sku=sku
        )
        if len(prev_sps) > 0:
            raise GQLApiException(
                msg="Product already exists",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        # create supplier product
        s_prod = SupplierProduct(
            id=uuid4(),
            supplier_business_id=supplier_business_id,
            sku=sku,
            description=description,
            tax_id=tax_id,
            sell_unit=sell_unit,
            tax=tax,
            tax_unit=tax_uom,
            conversion_factor=conversion_factor,
            buy_unit=buy_unit,
            unit_multiple=unit_multiple,
            min_quantity=min_quantity,
            product_id=product_id,
            upc=upc,
            estimated_weight=estimated_weight,
            is_active=True,
            created_by=core_user.id,  # type: ignore (safe)
            long_description=long_description,
            mx_ieps=mx_ieps,
        )
        await self.supplier_product_repo.add(s_prod)
        # if price exists - add price to default price lists of all supplier units
        if default_price is not None:
            await self.supplier_price_list_handler.add_price_to_default_price_lists(
                firebase_id=firebase_id,
                supplier_business_id=supplier_business_id,
                supplier_product_id=s_prod.id,
                price=default_price,
            )
        # if tags insert them
        if tags is not None and (isinstance(tags, list) and len(tags) > 0):
            _tgs = [
                SupplierProductTag(
                    id=uuid4(),
                    supplier_product_id=s_prod.id,
                    tag_key=tag["tag_key"],
                    tag_value=tag["tag_value"],
                )
                for tag in tags
            ]
            if not await self.supplier_product_repo.add_tags(s_prod.id, _tgs):
                logger.warning("Could not add tags to supplier product")
        return SupplierProductDetailsGQL(**s_prod.__dict__)

    async def edit_supplier_product(
        self,
        firebase_id: str,
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
        tags: Optional[List[Dict[str, Any]]] = None,
        long_description: Optional[str] = None,
        mx_ieps: Optional[float] = None,
    ) -> SupplierProductDetailsGQL:
        # fetch supplier product
        _sprod = await self.supplier_product_repo.fetch(supplier_product_id)
        if not _sprod:
            raise GQLApiException(
                msg="Product does not exist",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        sup_prod = SupplierProduct(**_sprod)
        prev_sps = await self.supplier_product_repo.find(
            supplier_business_id=sup_prod.supplier_business_id, sku=sku
        )
        if len(prev_sps) > 0:
            if prev_sps[0]["id"] != supplier_product_id:
                raise GQLApiException(
                    msg="Product already exists",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
                )
        # data updates
        if sku is not None:
            sup_prod.sku = sku
        if description is not None:
            sup_prod.description = description
        if tax is not None:
            sup_prod.tax = tax
        if mx_ieps is not None:
            sup_prod.mx_ieps = mx_ieps
        else:
            sup_prod.mx_ieps = None
        if conversion_factor is not None:
            sup_prod.conversion_factor = conversion_factor
        if sell_unit is not None:
            sup_prod.sell_unit = sell_unit
            sup_prod.tax_unit = DataTypeDecoder.get_sat_unit_code(sell_unit.value)
        if buy_unit is not None:
            sup_prod.buy_unit = buy_unit
        if unit_multiple is not None:
            if sup_prod.sell_unit in INTEGER_UOMS:
                # validate if unit_multiple is integer and greater equal than 1
                if not unit_multiple.is_integer() or unit_multiple < 1:
                    raise GQLApiException(
                        msg="Unit Multiple must be an integer greater equal than 1",
                        error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            sup_prod.unit_multiple = unit_multiple
        if min_quantity is not None:
            if sup_prod.sell_unit in INTEGER_UOMS:
                # validate if min_quantity is integer and greater equal than 1
                if not min_quantity.is_integer() or min_quantity < 1:
                    raise GQLApiException(
                        msg="Min Quantity must be an integer greater equal than 1",
                        error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                    )
            sup_prod.min_quantity = min_quantity
        if product_id is not None:
            # verify if product id exists
            _prod = await self.product_repo.fetch(product_id)
            if not _prod:
                raise GQLApiException(
                    msg="Product does not exist",
                    error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
                )
            sup_prod.product_id = product_id
        if tax_id is not None:
            # verify tax id is within sat codes
            tax_codes = await self.get_sat_codes()
            if tax_id not in tax_codes:
                raise GQLApiException(
                    msg="Tax Code is not Valid",
                    error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
                )
            sup_prod.tax_id = tax_id
        if upc is not None:
            sup_prod.upc = upc
        else:
            sup_prod.upc = None
        if estimated_weight is not None:
            sup_prod.estimated_weight = estimated_weight
        else:
            sup_prod.estimated_weight = None
        if long_description is not None:
            sup_prod.long_description = long_description
        # update supplier product
        await self.supplier_product_repo.edit(sup_prod)
        # if price exists - add price to default price lists of all supplier units
        if default_price is not None:
            await self.supplier_price_list_handler.add_price_to_default_price_lists(
                firebase_id=firebase_id,
                supplier_business_id=sup_prod.supplier_business_id,
                supplier_product_id=sup_prod.id,
                price=default_price,
            )
        # if tags insert them
        if tags is not None and (isinstance(tags, list)):
            if not await self.supplier_product_repo.add_tags(
                sup_prod.id,
                [
                    SupplierProductTag(
                        id=uuid4(),
                        supplier_product_id=sup_prod.id,
                        tag_key=tag["tag_key"],
                        tag_value=tag["tag_value"],
                    )
                    for tag in tags
                ],
            ):
                logger.warning("Could not add tags to supplier product")
        return SupplierProductDetailsGQL(**sup_prod.__dict__)

    async def get_customer_products_to_export(
        self,
        firebase_id: str,
        receiver: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        # get supplier business
        _, supplier_business = await self.fetch_supplier_business(firebase_id)
        if not supplier_business:
            raise GQLApiException(
                msg="Issues to find supplier business",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        supp_bus_obd = SupplierBusiness(**supplier_business)
        # fetch invoices, suppliers and branches
        _prods = await self.supplier_product_repo.fetch_products_to_export(
            supplier_business_id=supp_bus_obd.id,
            receiver=receiver,
        )
        if not _prods:
            logger.warning("No products found")
            return []
        return _prods

    async def get_customer_products_stock_to_export(
        self, supplier_unit_id: UUID
    ) -> List[Dict[Any, Any]]:
        # fetch invoices, suppliers and branches
        supp_unit = await self.supplier_unit_repo.fetch(supplier_unit_id)
        if not supp_unit:
            raise GQLApiException(
                msg="Issues to find supplier unit",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        supp_unit_obj = SupplierUnit(**supp_unit)
        prods = await self.supplier_product_repo.find(
            supplier_business_id=supp_unit_obj.supplier_business_id
        )
        if not prods:
            logger.warning("No products found")
            return []
        prods_idx = {p["id"]: p for p in prods}
        _prods_stock = await self.supplier_product_stock_repo.fetch_latest_by_unit(
            supplier_unit_id=supplier_unit_id,
        )
        if not _prods_stock:
            logger.warning("No products stock found")
            return []
        stock_dict_list = []
        for stock in _prods_stock:
            stock_dict = {}
            stock_dict["sku"] = prods_idx[stock.supplier_product_id].get("sku", None)
            stock_dict["description"] = prods_idx[stock.supplier_product_id].get(
                "description", None
            )
            stock_dict["sell_unit"] = DataTypeTraslate.get_uomtype_encode(
                str(stock.stock_unit)
            )
            stock_dict["stock"] = stock.stock if stock.active else None
            stock_dict["keep_selling_without_stock"] = stock.keep_selling_without_stock
            stock_dict_list.append(stock_dict)
        return stock_dict_list
