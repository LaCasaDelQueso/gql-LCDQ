from abc import ABC, abstractmethod
from urllib.parse import urlencode
from enum import Enum
import json
import re
from types import NoneType
from uuid import UUID
from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL
from gqlapi.domain.models.v2.utils import PayMethodType
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.config import APP_TZ
from gqlapi.lib.logger.logger.basic_logger import get_logger
from typing import Any, Dict, Optional
import requests
from datetime import datetime
from strawberry import type as strawberry_type
import unicodedata
from gqlapi.config import ENV


logger = get_logger(get_app())


supplier_unit_code = {
    "STG": {
        "cd8586c4-8a2a-470f-b3ed-84a6fe2c16f2": "091",
        "7b35e25f-50f6-4aac-a333-ff8f37670608": "140",
        "aa48700c-2ad0-4963-9901-b8c572e74a37": "079",
    },
    "PROD": {
        "59b8846f-bdfc-4031-86d7-3eb4a11c17be": "091",
        "b8d5fa2e-c624-4e1c-a5a9-4b3912712d44": "140",
        "d3c261e5-7fec-4181-8e2c-8d168f533b94": "079",
    },
}


@strawberry_type
class ScorpionToken(ABC):
    user: str
    password: str


@strawberry_type
class ScorpionResponse(ABC):
    status: str
    msg: str
    result: Optional[str] = None
    value: Optional[str] = None


class ScorpionEndpoints(Enum):
    TOKEN = "service/getToken"
    SAVE_ORDEN = "orders/saveOrder"
    GET_ORDENES = "orders/order_merksyst"
    GET_STATUS = "orders/notification_status"


SCORPION_PACKAGE_MAP = {
    "kg": "KG",
    "unit": "PZ",
    "pack": "PAQ",
}


class ScorpionHandlerInterface(ABC):
    @abstractmethod
    async def new_orden(
        self, integrations_partner_id: UUID, orden_id: str, status: str
    ) -> UUID | NoneType:
        raise NotImplementedError

    @abstractmethod
    async def edit_orden(
        self,
        id: UUID,
        integrations_partner_id: UUID,
        orden_id: UUID,
        integrations_orden_id: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[str] = None,
    ) -> UUID | NoneType:
        raise NotImplementedError


def build_url_string(object: Dict[Any, Any]) -> str:
    return urlencode(object)


def build_token_string(token: ScorpionToken) -> str:
    token_json = {"user": token.user, "password": token.password}
    return urlencode(token_json)


def build_get_orden_string(token: str, number_order: str) -> str:
    json_data = {
        "token_session": token,
        "Number_Orden": number_order,
        # "Platform_Origin_Id": "5",
    }
    return build_url_string(json_data)


def build_get_orden_status_string(token: str, number_order) -> str:
    json_data = {
        "token_session": token,
        "Number_Orden": number_order,
        # "Platform_Origin_Id": "5",
    }
    return build_url_string(json_data)


def remove_special_characters(input_string) -> str:
    # Normalize the string to NFKD form to decompose characters into their base and combining forms
    normalized_string = unicodedata.normalize("NFKD", input_string)
    result_string = "".join(
        [char for char in normalized_string if not unicodedata.combining(char)]
    )
    # Replace string " with empty string
    return (
        re.sub(r"\\.", lambda x: x.group(0)[1], result_string)
        .replace("'", "")
        .replace('"', "")
    )


def build_save_orden_string(
    token: str,
    orden: OrdenGQL,
    consecutive: int,
    zone_info: Optional[Dict[Any, Any]] = None,
) -> str:
    # urllib.parse.quote(data)
    if not orden.details:
        raise Exception("No se encontraron los detalles de la orden")

    branch_key = supplier_unit_code.get(ENV, {}).get(
        str(orden.details.supplier_unit_id), "091"
    )

    number_orden = "C" + str(orden.orden_number).zfill(8)
    number_order = number_orden[:-2]

    if not orden.details.delivery_date or not orden.details.delivery_time:
        raise Exception("Error al encontrar fecha de entrega")
    # Date Orden
    # date_order = orden.details.delivery_date.strftime("%Y%m%d")
    if orden.details.payment_method == PayMethodType.CASH:
        payment_method = "POSPAG"
        conditions_payment = "CTDO"
    elif orden.details.payment_method == PayMethodType.TRANSFER:
        payment_method = "TRAN"
        conditions_payment = "CTDO"

    # Branch Data
    if not orden.branch:
        raise Exception("Error al encontrar branch de restaurante")
    branch = orden.branch
    if not branch.contact_info:
        raise Exception("Error al encontrar contact info")
    city = None
    state = None
    country = None
    zip_code = None
    if zone_info:
        city = zone_info.get("city", None)
        state = zone_info.get("state", None)
        country = zone_info.get("country", None)
        zip_code = zone_info.get("zip_code", None)
        neighborhood = zone_info.get("neighborhood", None)
        street = remove_special_characters(branch.street) + ", "
        ext_num = (
            remove_special_characters(branch.external_num) + ", "
            if branch.external_num
            else ""
        )
        int_num = (
            remove_special_characters(branch.internal_num) + ", "
            if branch.internal_num
            else ""
        )
        address_send = street + ext_num + int_num + neighborhood
    else:
        city = remove_special_characters(branch.city)
        state = remove_special_characters(branch.state)
        country = "MEX"
        zip_code = remove_special_characters(branch.zip_code)
        neighborhood = remove_special_characters("neighborhood")
        address_send = remove_special_characters(branch.full_address)
    # Branch Data
    if not orden.supplier:
        raise Exception("Error al encontrar supplier")
    if not orden.supplier.supplier_unit:
        raise Exception("Error al encontrar unit")
    unit = orden.supplier.supplier_unit
    if branch.contact_info.phone_number:
        phone_number = str(branch.contact_info.phone_number).replace(" ", "")
        if len(phone_number) >= 12:
            phone_number = phone_number[-10:]

    # Hour_Order
    if not orden.details.created_at:
        raise Exception("Error al encontrar fecha de creación de orden")
    date_orden = orden.details.created_at.strftime("%Y%m%d")
    date_hour_orden = orden.details.created_at.strftime("%H%M%S")
    # date_hour_orden = f"{str(orden.details.delivery_time.start).zfill(2)}0000"
    subtotal_without_tax = (
        round(orden.details.subtotal_without_tax, 4)
        if orden.details.subtotal_without_tax
        else 0
    )
    subtotal = round(orden.details.subtotal, 4) if orden.details.subtotal else 0
    shipping_cost = (
        round(orden.details.shipping_cost, 4) if orden.details.shipping_cost else 0
    )

    if not orden.cart:
        raise Exception("Error al encontrar productos de la orden")
    tax = 0
    ieps = 0
    for prods in orden.cart:
        if not prods.supp_prod or not prods.unit_price:
            raise Exception("Error al encontrar detalles del producto")
        if prods.supp_prod.tax:
            tax += prods.supp_prod.tax * prods.quantity * prods.unit_price
        if prods.supp_prod.mx_ieps:
            ieps += prods.supp_prod.mx_ieps * prods.quantity * prods.unit_price

    data_json = {
        "token_session": token,
        "Branch_Key": branch_key,
        "Number_Order": number_order,
        "Number_Orden": number_orden,
        "Divided_In": "1",
        "Order_Status": "PX",
        "Zone_Prices_Key": branch_key,
        "Company_Key": "GSC",
        "Market_Segment": "MAY",
        "Payment_Method": payment_method,
        "Conditions_Payment": conditions_payment,
        "Accept_Substitutes": "N",
        "Accept_Missing": "N",
        "Accept_Change_Price": "N",
        "Currency_Order": "NAL",
        # "Vendor_Key":,
        "Sales_Order_Num": "ECOMMERCE",
        "Order_Type": "NORMAL",
        # "Invoice_Number":,
        # "Return_Invoice_Number":,
        "Supply_Department_Order": branch_key + "E01",
        # "Authorization_Key":,
        # "Amount_Authorized":,
        "Client_Key": "001263656",
        "Contact": "CF:9999013040961",
        "Name_Customer": remove_special_characters(branch.branch_name),
        "Name_Send": remove_special_characters(unit.unit_name),
        # f”{street} {ext_num}, {int_num}, {colonia_select}”.upper()
        "Address_Send1": address_send,
        "City_Send": city if city else "",
        "State_Send": state if state else "",
        "Country_Send": country if country else "",
        "Zip_Code": zip_code if zip_code else "",
        "Phone_Send": remove_special_characters(str(phone_number)),
        "RFC_Client": (
            remove_special_characters(branch.tax_info.mx_sat_id)
            if branch.tax_info
            else ""
        ),
        # "Collection_Date":,
        # "Delivery_Date_Buy":,
        "Date_Order": date_orden,
        "Hour_Order": date_hour_orden,
        "User_Order_Key": "A02",
        # "Credit_Authorization_Date":,
        # "Credit_Authorization_Hour":,
        # "User_Authorize_Order_Key":,
        # "Date_Supplied":,
        # "Hour_Supplied":,
        # "User_Supplied_Key":,
        # "Last_Invoicing_Date":,
        # "Last_Invoicing_Hour":,
        # "Last_Invoicing_User_Key":,
        # "Cancellation_Date":,
        # "Cancellation_Hour":,
        # "Cancel_User_Key":,
        # "Code_Cancellation":,
        # "Last_Change_Date":,
        # "Hour_Last_Change":,
        # "Last_Change_User_Key":,
        "Tax_Type": "1",
        "Num_Invoices_Printed": "0",
        "Num_Orders_Printed": "0",
        "Num_Contribution_Printed": "0",
        "Discount": "0",
        "Discount_Standard": "0",
        "Percentage_Discount": "0",
        "Condition_Discount": "0",
        "Discount_Operation0": "0",
        "Discount_Operation1": "0",
        "Discount_Operation2": "0",
        "Discount_Operation3": "0",
        "Subtotal": str(subtotal_without_tax),
        "Discount_Total": "0",
        "Tax_Total": str(tax),
        "Tax_Total_Special1": str(ieps),
        # "Tax_Total_Special2":,
        "Total_Sale_Cost": str(subtotal),
        # "Transfer":,
        # "Status_Ticket":,
        "Total_Freight": str(shipping_cost),
        "Iva_Freight": "1",
        "Other_Charges": "0",
        "Change_Type": "1",
        # "Discount_Soon_Payment":"0",
        # "Days_Soon_Payment":,
        # "Period_Payment":,
        # "Address_Send":,
        # "Percentage_Charge_Supplied":,
        # "Separated":,
        "Platform_Origin_Id": "5",  # ALIMA
    }
    date = datetime.now(APP_TZ)
    movement_date = date.strftime("%Y%m%d")
    movement_hour = date.strftime("%H%M%S")
    for index, prods in enumerate(orden.cart):
        if not prods.supp_prod:
            raise Exception("Error al encontrar detalles del producto")
        package = SCORPION_PACKAGE_MAP.get(prods.sell_unit.value, "PZ")
        if prods.supp_prod.tax and prods.unit_price:
            amount_tax = str(prods.unit_price * prods.quantity * prods.supp_prod.tax)
        else:
            amount_tax = "0"
        if prods.supp_prod.mx_ieps and prods.unit_price:
            amount_ieps = str(
                prods.unit_price * prods.quantity * prods.supp_prod.mx_ieps
            )
        else:
            amount_ieps = "0"

        prod_det = prods.supp_prod
        prods = {
            f"products[{str(index)}][Branch_Key]": branch_key,
            f"products[{str(index)}][Number_Order]": number_order,
            f"products[{str(index)}][Number_Orden]": number_orden,
            f"products[{str(index)}][Divided_In]": "1",
            f"products[{str(index)}][Date_Order]": date_orden,
            f"products[{str(index)}][Company_Key]": "GSC",
            f"products[{str(index)}][Zone_Prices_Key]": branch_key,
            f"products[{str(index)}][Warehouse_Key]": "091M",
            f"products[{str(index)}][Product_Key]": prod_det.sku,
            f"products[{str(index)}][Product_Description]": remove_special_characters(
                prod_det.description
            ),
            f"products[{str(index)}][Type_Service]": "0",
            f"products[{str(index)}][Unit_Output]": "U",
            f"products[{str(index)}][Quantity]": str(prods.quantity),
            f"products[{str(index)}][Unitary_Price]": str(prods.unit_price),
            f"products[{str(index)}][Total_Order]": str(orden.details.total),
            f"products[{str(index)}][Modify_Price]": "M",
            f"products[{str(index)}][Promotion_Match]": "0",
            f"products[{str(index)}][Tax_Free]": "S",
            f"products[{str(index)}][Currency_Order_Key]": "NAL",
            f"products[{str(index)}][Currency_Original_Key]": "NAL",
            f"products[{str(index)}][Status_Article]": "M",
            f"products[{str(index)}][Tax_Key]": "A",
            f"products[{str(index)}][Options]": "N",
            f"products[{str(index)}][Packaging]": package,
            f"products[{str(index)}][Row_Match]": str(index),
            f"products[{str(index)}][Supplied_Units]": "0",
            f"products[{str(index)}][Refund_Amount]": "0",
            f"products[{str(index)}][Cost_Purchase]": "0",
            f"products[{str(index)}][Total_Order]": subtotal,
            f"products[{str(index)}][Change_Type]": "1",
            f"products[{str(index)}][Price_Unit_Currency]": str(prods.unit_price),
            # f"products[{str(index)}][Price_Tax]": str(prods.unit_price),
            f"products[{str(index)}][Discount_Order]": "0",
            f"products[{str(index)}][Discount_Client]": "0",
            f"products[{str(index)}][Discount_Promotion]": "0",
            f"products[{str(index)}][Discount_Accumulated]": "0",
            f"products[{str(index)}][Discount_Condition]": "0",
            f"products[{str(index)}][Percentage_Discount_0]": "0",
            f"products[{str(index)}][Percentage_Discount_1]": "0",
            f"products[{str(index)}][Percentage_Discount_2]": "0",
            f"products[{str(index)}][Amount_Tax]": amount_tax,
            f"products[{str(index)}][Special_Tax_Amount]": amount_ieps,
            f"products[{str(index)}][Special_Tax_Amount2]": "0",
            f"products[{str(index)}][Wholesale_Type]": "0",
            f"products[{str(index)}][Average_Type]": "0",
            f"products[{str(index)}][Subtotal_Taxes]": "0",
            f"products[{str(index)}][Department_Key]": branch_key + "E01",
            f"movements[{str(index)}][Branch_Key]": branch_key,
            f"movements[{str(index)}][Company_Key]": "GSC",
            f"movements[{str(index)}][Movement_Branch_Key]": branch_key,
            f"movements[{str(index)}][Number_Orden]": number_orden,
            f"movements[{str(index)}][Number_Movement]": orden.orden_number,
            f"movements[{str(index)}][Payment_Method_Key]": payment_method,
            f"movements[{str(index)}][Transaction_Bank]": "",
            f"movements[{str(index)}][Transaction_Amount]": str(orden.details.total),
            f"movements[{str(index)}][Movement_Date]": movement_date,
            f"movements[{str(index)}][Movement_Hour]": movement_hour,
            f"movements[{str(index)}][Consecutive]": str(consecutive),
            f"movements[{str(index)}][Client_Key]": "001263656",
            f"movements[{str(index)}][Division_Key]": "1",
            f"movements[{str(index)}][Currency_Key]": "NAL",
            f"movements[{str(index)}][Change_Movement_Type]": "1",
            f"movements[{str(index)}][Department_Key]": branch_key + "E01",
            f"movements[{str(index)}][Row_Match]": str(index),
            f"movements[{str(index)}][Shipment_Movement]": "1",
        }
        data_json.update(prods)
    data_str = build_url_string(data_json)
    return data_str


class ScorpionClientApi:
    def __init__(self, env) -> None:
        self.headers = {"Content-Type": "application/x-www-form-urlencoded"}
        self.url_base = (
            "http://20.97.8.26/dev_scorpion_bdu_services/{endpoint}"
            if env.lower() == "prod"
            else "http://20.97.8.26/dev_scorpion_bdu_services/{endpoint}"
        )

    async def get_token(self, token: ScorpionToken) -> ScorpionResponse:
        try:
            url = self.url_base.format(endpoint=ScorpionEndpoints.TOKEN.value)
            payload = build_token_string(token=token)
            scrp_resp = requests.request(
                "POST", url, headers=self.headers, data=payload
            )
            logger.debug(scrp_resp.status_code)
            logger.debug(scrp_resp.content)
            if scrp_resp.status_code == 200:
                scrp_resp = scrp_resp.json()
                if scrp_resp["msg"] == "Ok":
                    return ScorpionResponse(
                        msg="ok",
                        status="ok",
                        result=json.dumps(scrp_resp),
                        value=scrp_resp["token"],
                    )
                else:
                    logger.warning("SCORPION GET TOKEN LOG")
                    logger.error(scrp_resp.content)
                    return ScorpionResponse(
                        msg="Scorpion Response error",
                        status="error",
                    )
            else:
                logger.warning("SCORPION GET TOKEN LOG")
                logger.error(scrp_resp.content)
                return ScorpionResponse(
                    msg="Scorpion Error connection",
                    status="error",
                )
        except Exception as e:
            logger.warning("SCORPION GET TOKEN LOG")
            logger.error(e)
            return ScorpionResponse(
                msg="Scorpion Error request",
                status="error",
            )

    async def save_orden(
        self,
        token: str,
        orden: OrdenGQL,
        consecutive: int,
        zone_info: Optional[Dict[str, Any]] = None,
    ) -> ScorpionResponse:
        try:
            url = self.url_base.format(endpoint=ScorpionEndpoints.SAVE_ORDEN.value)
            payload = build_save_orden_string(
                token, orden=orden, consecutive=consecutive, zone_info=zone_info
            )
            scrp_resp = requests.request("PUT", url, headers=self.headers, data=payload)
            logger.info(scrp_resp.status_code)
            logger.info(scrp_resp.content)
            if scrp_resp.status_code == 200:
                scrp_resp = scrp_resp.json()
                if scrp_resp["msg"] == "Record saved.":
                    return ScorpionResponse(
                        msg="ok",
                        status="ok",
                        result=json.dumps(scrp_resp),
                        value="C" + str(orden.orden_number).zfill(8),
                    )
                else:
                    logger.warning("SCORPION SAVE ORDEN LOG")
                    logger.error(scrp_resp.content)
                    return ScorpionResponse(
                        msg="Scorpion Response error",
                        status="error",
                    )
            else:
                logger.warning("SCORPION SAVE ORDEN LOG")
                logger.error(scrp_resp.content)
                return ScorpionResponse(
                    msg="Scorpion Error connection",
                    status="error",
                )
        except Exception as e:
            logger.warning("SCORPION SAVE ORDEN LOG")
            logger.error(e)
            return ScorpionResponse(
                msg="Scorpion Error request",
                status="error",
            )

    async def get_orden(self, token: str, number_orden: str) -> ScorpionResponse:
        try:
            url = self.url_base.format(endpoint=ScorpionEndpoints.GET_ORDENES.value)
            payload = build_get_orden_string(token, number_orden)
            scrp_resp = requests.request(
                "POST", url, headers=self.headers, data=payload
            )
            logger.info(scrp_resp.status_code)
            logger.info(scrp_resp.content)
            if scrp_resp.status_code == 200:
                scrp_resp = scrp_resp.json()
                if scrp_resp["msg"] == "ok":
                    if len(scrp_resp["data"]) == 0:
                        return ScorpionResponse(
                            msg="empty",
                            status="ok",
                            result=json.dumps(scrp_resp),
                            value="0",
                        )
                    else:
                        return ScorpionResponse(
                            msg="ok",
                            status="ok",
                            result=json.dumps(scrp_resp),
                            value=str(len(scrp_resp["data"][0]["detalle_venta"])),
                        )
                logger.warning("SCORPION GET ORDEN LOG")
                logger.error(scrp_resp.content)
                return ScorpionResponse(
                    msg="Scorpion Response error",
                    status="error",
                )
            else:
                logger.warning("SCORPION GET ORDEN LOG")
                logger.error(scrp_resp.content)
                return ScorpionResponse(
                    msg="Scorpion Error connection",
                    status="error",
                )
        except Exception as e:
            logger.warning("SCORPION GET ORDEN LOG")
            logger.error(e)
            return ScorpionResponse(
                msg="Scorpion Error request",
                status="error",
            )

    async def get_ordenes(self, token: str, orden_number: str) -> ScorpionResponse:
        try:
            url = self.url_base.format(endpoint=ScorpionEndpoints.GET_STATUS.value)
            payload = build_get_orden_status_string(token, orden_number)
            scrp_resp = requests.request(
                "POST", url, headers=self.headers, data=payload
            )
            logger.info(scrp_resp.status_code)
            logger.info(scrp_resp.content)
            if scrp_resp.status_code == 200:
                scrp_resp_json = scrp_resp.json()
                if scrp_resp_json["msg"] == "OK" and len(scrp_resp_json["data"]) > 0:
                    return ScorpionResponse(
                        msg="ok",
                        status="ok",
                        result=json.dumps(scrp_resp),
                        value=str(len(scrp_resp_json["numero de productos"])),
                    )
                logger.warning("SCORPION GET ORDENES LOG")
                logger.error(scrp_resp.content)
                return ScorpionResponse(
                    msg="Scorpion Response error",
                    status="error",
                )
            else:
                logger.warning("SCORPION GET ORDENES LOG")
                logger.error(scrp_resp.content)
                return ScorpionResponse(
                    msg="Scorpion Error connection",
                    status="error",
                )
        except Exception as e:
            logger.warning("SCORPION GET ORDENES LOG")
            logger.error(e)
            return ScorpionResponse(
                msg="Scorpion Error request",
                status="error",
            )
