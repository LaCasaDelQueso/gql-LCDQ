import logging
import math
from typing import Any, Dict, Set
from uuid import UUID

from gqlapi.domain.models.v2.utils import DataTypeDecoder, DataTypeTraslate, UOMType
from gqlapi.utils.helpers import format_price_to_float

SUPPLIER_PRODUCT_BATCH_FILE_COLS = [
    "description",
    "sell_unit",
    # "upc_barcode",
    "conversion_factor",
    "buy_unit",
    "unit_multiple",
    "min_quantity",
    "estimated_weight",
    "max_daily_stock",
    "product_price",
    "sat_product_code",
    "tax_iva_percent",
]

SUPPLIER_PRODUCT_STOCK_BATCH_FILE_COLS = [
    "stock",
    "sku",
    "keep_selling_without_stock"
]

SUPPLIER_PRODUCT_BATCH_FILE_COLS_OPTIONAL = [
    "id",
    "product_id",
    "sku",
    "long_description",
    "ieps_percent",
]

INTEGER_UOMS = {UOMType.DOZEN, UOMType.PACK, UOMType.UNIT, UOMType.DOME}


def verify_mins_and_increments(val: Any, sell_unit: str) -> float | None:
    """Verify Min quantity and unit multiple

    Parameters
    ----------
    val : Any
        unparsed value
    sell_unit : str
        Unparsed Sell Unit

    Returns
    -------
    float | None
    """
    try:
        fval = float(val)
        _unit = UOMType(DataTypeTraslate.get_uomtype_decode(sell_unit.lower()))
        if _unit in INTEGER_UOMS:
            if fval < 1:
                return None
        if fval < 0:
            return None
        return fval
    except ValueError:
        return None


def get_tag_info(row_dict: Dict[Any, Any]) -> bool | str:
    if ("tag_value" in row_dict and row_dict["tag_value"]) and (
        "tag_key" in row_dict and row_dict["tag_key"]
    ):
        return True
    if ("tag_value" in row_dict and not row_dict["tag_value"]) and (
        "tag_key" in row_dict and not row_dict["tag_key"]
    ):
        return False
    if ("tag_value" in row_dict and not row_dict["tag_value"]) and (
        "tag_key" in row_dict and row_dict["tag_key"]
    ):
        return "El producto no tiene tag_value"
    if ("tag_value" in row_dict and row_dict["tag_value"]) and (
        "tag_key" in row_dict and not row_dict["tag_key"]
    ):
        return "El producto no tiene tag_key"
    return False


def verify_supplier_product_row_is_complete(
    row: Dict[str, Any],
    valid_tax_ids: Set[str],
    supplier_product_idx: Dict[Any, Any],
    sku_supplier_product_idx: Dict[Any, Any],
    skip_tax_rev: bool = False,
) -> Dict[str, Any]:
    """Verify that the row has all the required fields with the right format
        - description: must be string of more than 3 characters
        - sell_unit: must be in the list of UOMType
        - upc_barcode: [TODO] validate later against DB -> now only store 12 and 13 digits
        - conversion_factor: must be float >= 1, and 1 if sell_unit == buy_unit
        - buy_unit: must be in the list of UOMType
        - unit_multiple: must be float > 0
        - min_quantity: must be float > 0
        - estimated_weight: must be float > 0 or None
        - max_daily_stock: must be float > 0 or None
        - product_price: must be float > 0 or None
        - sat_product_code: must be string of 8 character
        - tax_iva_percent: must be float >= 0 and < 1

    Parameters
    ----------
    row : Dict[str, Any]
    valid_tax_ids : Set[str]
    supplier_product_idx : Dict[Any, Any] - indexed by supplier description
    sku_supplier_product_idx : Dict[Any, Any] - indexed by supplier sku
    skip_tax_rev : bool, optional - if True, only validate the fields needed for prices

    Returns
    -------
    Dict[str, Any]
        {
            "status": bool, # True if the data is correct
            "data": Dict[str, Any], # partial Supplier Product + max_daily_stock + product_price
            "feedback": Dict[str, Any], # partial Supplier Products Batch
        }
    """
    feedback = {
        "product_id": row.get("product_id", None),
        "supplier_product_id": row.get("id", None),
        "sku": row.get("sku", None),
        "description": row["description"],
        "status": True,
    }
    _data = {}
    # iterate over all needed required cols
    for col in SUPPLIER_PRODUCT_BATCH_FILE_COLS:
        val = row.get(col, None)
        # verify empty values
        if (
            val is None
            or val == ""
            and col
            not in (
                [
                    "estimated_weight",
                    "max_daily_stock",
                    "product_price",
                    "upc_barcode",
                    "long_description",
                ]
            )
        ):
            feedback["msg"] = f"{col} está vacío"
            feedback["status"] = False
            break
        # verify description
        if col == "description":
            if len(val) < 3:
                feedback["msg"] = f"{col} debe tener al menos 3 caracteres"
                feedback["status"] = False
                break
            _data["description"] = val
        # verify sell_unit & buy unit
        if col == "sell_unit" or col == "buy_unit":
            try:
                _unit = UOMType(DataTypeTraslate.get_uomtype_decode(val.lower()))
                _data[col] = _unit
                # add correspondent tax unit
                _data["tax_unit"] = DataTypeDecoder.get_sat_unit_code(_unit.value)
            except ValueError:
                uom_opts = [
                    DataTypeTraslate.get_uomtype_encode(u).capitalize()
                    for u in UOMType.__members__.keys()
                ]
                feedback["msg"] = f"{col} debe ser uno de {uom_opts}"
                feedback["status"] = False
                break
            except Exception as e:
                logging.warning(e)
                feedback["msg"] = (
                    f"{col} debe ser uno de {list(UOMType.__members__.keys())}, y es: {val}"
                )
                feedback["status"] = False
                break
        # verify upc_barcode
        if col == "upc_barcode":
            if val is None or val == "":
                _data["upc"] = None
                continue
            if len(str(val)) not in [12, 13]:
                feedback["msg"] = f"{col} debe tener 12 o 13 dígitos"
                feedback["status"] = False
                break
            _data["upc"] = str(val)
        # verify conversion_factor, unit_multiple, min_quantity
        if col in [
            "conversion_factor",
            "unit_multiple",
            "min_quantity",
            "max_daily_stock",
            "product_price",
            "estimated_weight",
        ]:
            try:
                if val is None or val == "":
                    _data[col] = None
                    continue
                if col == "product_price":
                    _factor = format_price_to_float(val)
                else:
                    _factor = float(val)
                if _factor <= 0:
                    feedback["msg"] = f"{col} debe ser mayor a 0"
                    feedback["status"] = False
                    break
                # validation for min quantity and unit multiple
                if (
                    col in ["unit_multiple", "min_quantity"]
                    and _data["sell_unit"] in INTEGER_UOMS
                ):
                    if _factor < 1:
                        feedback["msg"] = (
                            f"{col} para piezas y unidades debe ser mayor o igual a 1"
                        )
                        feedback["status"] = False
                        break
                _data[col] = _factor
            except ValueError:
                feedback["msg"] = f"{col} debe ser un número"
                feedback["status"] = False
                break
        # verify sat_product_code
        if col == "sat_product_code":
            if not skip_tax_rev and str(val) not in valid_tax_ids:
                feedback["msg"] = f"{col} debe ser un código válido del SAT"
                feedback["status"] = False
                break
            _data["tax_id"] = str(val)
        # verify tax_iva_percent
        if col == "tax_iva_percent":
            try:
                if skip_tax_rev:
                    _data["tax"] = None
                    continue
                _tax = float(val)
                if _tax < 0 or _tax >= 1:
                    feedback["msg"] = f"{col} debe ser mayor o igual a 0 y menor a 1"
                    feedback["status"] = False
                    break
                _data["tax"] = _tax
            except ValueError:
                feedback["msg"] = f"{col} debe ser un número"
                feedback["status"] = False
                break
    _data, feedback = verify_supplier_optional_product_row_is_complete(
        row, _data, feedback
    )
    # ad match to supplier product if exists by SKU
    if _data["sku"] in sku_supplier_product_idx:
        sup_prod = sku_supplier_product_idx[_data["sku"]]
        _data["id"] = sup_prod["id"]
    # or by description and sell unit
    elif _data["description"].lower() in supplier_product_idx:
        try:
            sup_prod = supplier_product_idx[_data["description"].lower()]
            if _data["sell_unit"].value == sup_prod["sell_unit"]:
                _data["id"] = sup_prod["id"]
        except Exception as e:
            logging.warning(e)  # pass if not found

    # add status
    if feedback["status"]:
        feedback["msg"] = "OK"
    # return formated info
    return {
        "status": feedback["status"],
        "data": _data,
        "feedback": feedback,
    }


def verify_supplier_optional_product_row_is_complete(
    row: Dict[str, Any], _data, feedback: Dict[Any, Any]
):
    # iterate over all optional cols
    for col in SUPPLIER_PRODUCT_BATCH_FILE_COLS_OPTIONAL:
        val = row.get(col, None)
        if val is None or val == "":
            if col == "ieps_percent":
                _data["mx_ieps"] = None
                continue
            else:
                _data[col] = None
                continue
        if col == "id" or col == "product_id":
            try:
                _data[col] = UUID(val) if not isinstance(val, UUID) else val
            except ValueError:
                feedback["msg"] = f"{col} debe ser un UUID válido"
                feedback["status"] = False
                break
        if col == "sku":
            _data[col] = str(val)
        if col == "long_description":
            _data[col] = str(val)
        if col == "ieps_percent":
            ieps: Any = val
            try:
                if math.isnan(ieps):
                    _data["mx_ieps"] = None
                else:
                    if ieps < 0 or ieps >= 1:
                        feedback["msg"] = (
                            f"{col} debe ser mayor o igual a 0 y menor a 1"
                        )
                        feedback["status"] = False
                        break
                    else:
                        _data["mx_ieps"] = ieps
            except ValueError:
                feedback["msg"] = f"{col} debe ser un número"
                feedback["status"] = False
                break
    return _data, feedback
