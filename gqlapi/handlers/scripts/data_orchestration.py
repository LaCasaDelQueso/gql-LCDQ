import datetime
import logging
from typing import Any, Dict, List, Optional
from bson import Binary
from gqlapi.utils.automation import InjectedStrawberryInfo
import pandas as pd
from strawberry.types import Info as StrawberryInfo
from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.domain.models.v2.supplier import SupplierBusiness

from gqlapi.repository import CoreMongoBypassRepository, CoreRepository
from gqlapi.repository.supplier.supplier_business import SupplierBusinessRepository
from gqlapi.mongo import mongo_db


class DataOrchestrationHandler:
    def __init__(self):
        self.info = InjectedStrawberryInfo(
            db=None, mongo=mongo_db
        )

    async def send_warning(self, date: str, tolerance: Optional[int] = 1) -> bool:  # type: ignore
        logging.info("Starting send warning ...")
        # Permite conectar a la db
        date_object = datetime.datetime.strptime(
            date, "%Y-%m-%d"
        ).date() + datetime.timedelta(
            days=tolerance  # type: ignore
        )
        _info = self.info
        logging.info("Get_expiration price list...")
        expiration_price_list = await get_price_list_expiration(date_object, _info)
        if not expiration_price_list:
            logging.info("There are no price lists that expire on that date")
            return True
        expiration_price_list_df = pd.DataFrame(expiration_price_list)

        grouped_df = (
            expiration_price_list_df.groupby("supplier_business_id")
            .agg({"name": list, "unit_name": list})
            .reset_index()
        )
        grouped_expiration_price_list = grouped_df.to_dict(orient="records")

        await send_notification(grouped_expiration_price_list, info=_info)
        return True


async def get_price_list_expiration(
    expiration_date: datetime.date, info: InjectedStrawberryInfo
) -> List[Dict[Any, Any]]:
    orden_repo = CoreRepository(info=info)  # type: ignore
    core_values = {"expiration_date": expiration_date}
    expiration_price_list = await orden_repo.find(
        core_element_name="Orden Satus",
        core_columns=[
            "spl.name as name",
            "spl.valid_upto as valid_upto",
            "spl.supplier_unit_id as supplier_unit_id",
            "su.supplier_business_id as supplier_business_id",
            "su.unit_name as unit_name",
        ],
        filter_values="spl.valid_upto = :expiration_date",
        values=core_values,
        core_element_tablename="""supplier_price_list spl JOIN supplier_unit su ON spl.supplier_unit_id = su.id""",
    )

    if not expiration_price_list:
        return []
    return [dict(r) for r in expiration_price_list]  # type: ignore


async def send_notification(
    expiration_price_list: List[Dict[Any, Any]],
    info: StrawberryInfo,
):
    supplier_business_repo = SupplierBusinessRepository(info=info)  # type: ignore
    mongo_bypass = CoreMongoBypassRepository(mongo_db=mongo_db)  # type: ignore

    for epl in expiration_price_list:
        supplier_business = SupplierBusiness(
            **await supplier_business_repo.fetch(epl["supplier_business_id"])
        )
        supplier_business_account = await mongo_bypass.fetch(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            query={"supplier_business_id": Binary.from_uuid(supplier_business.id)},
        )
        content = "Las siguientes listas de precios estan a 1 día de expirar:\n\n"
        for name, unit_name in zip(epl["name"], epl["unit_name"]):
            content = content + unit_name + " - " + name + "\n"
        bol = await send_email(
            email_to=supplier_business_account["email"],
            subject="Alima - Listas de precios estan por expirar",
            content=content,
        )
        logging.info(supplier_business.name + " - " + str(bol))
