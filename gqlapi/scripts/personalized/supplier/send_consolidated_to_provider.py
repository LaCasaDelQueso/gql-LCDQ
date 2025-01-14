"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.personalized.supplier.send_consolidated_to_provider"""

import argparse
import asyncio
import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO
import logging
from typing import Any, Dict, List
from uuid import UUID
from gqlapi.lib.clients.clients.email_api.mails import send_email, send_email_with_attachments_syncronous
from databases import Database
from gqlapi.config import RETOOL_SECRET_BYPASS
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.handlers.supplier.supplier_business import SupplierBusinessHandler
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.mongo import mongo_db as MongoDatabase
from gqlapi.config import SENDGRID_SINGLE_SENDER

import pandas as pd

pd.options.mode.chained_assignment = None  # type: ignore

query = """with category_tag as (
    SELECT
        supplier_product_id,
        tag_key,
        tag_value
    FROM supplier_product_tag
    WHERE tag_key = 'Proveedor' or tag_key = 'Correo'
),
orden_details_view as (
    -- get last status from orden
    WITH last_orden_status AS (
        WITH rcos AS (
            SELECT
                orden_id,
                status,
                ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
            FROM orden_status
    )
        SELECT * FROM rcos WHERE row_num = 1
    ),
    -- get last pay status from orden
    last_pay_status AS (
        WITH rcos AS (
            SELECT
                orden_id,
                status as paystatus,
                ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) as row_num
            FROM orden_paystatus
    )
        SELECT * FROM rcos WHERE row_num = 1
    ),
    -- get last version of orden
    last_orden_version AS (
        WITH last_upd AS (
            SELECT
                orden_id,
                id as orden_details_id,
                ROW_NUMBER() OVER (PARTITION BY orden_id ORDER BY created_at DESC) row_num
            FROM orden_details
        )
        SELECT * FROM last_upd WHERE row_num = 1
    )
    SELECT
        orden_details.*,
        los.status,
        lps.paystatus
    FROM last_orden_version lov
    JOIN orden_details ON orden_details.id = lov.orden_details_id
    JOIN last_orden_status los ON los.orden_id = lov.orden_id
    LEFT JOIN last_pay_status lps ON lps.orden_id = lov.orden_id
), exploted_cart as (
SELECT
        sp.sku "sku",
        sp.id "supplier_product_id",
        min(sp.description) "Producto",
        string_agg((round(cp.quantity * 100)::double precision / 100)::varchar, ', ') "Cantidades",
        sum(round(cp.quantity * 100)::double precision / 100) "Suma Cantidad",
        min(sp.sell_unit) "Presentación",
        max(cp.unit_price) "Precio",
        sum(cp.subtotal) "Total"
    FROM cart_product cp
    JOIN supplier_product sp on sp.id = cp.supplier_product_id
    LEFT JOIN (
    SELECT
        supplier_product_id,
        MAX(CASE WHEN tag_key = 'Proveedor' THEN tag_value END) AS provider,
        MAX(CASE WHEN tag_key = 'Correo' THEN tag_value END) AS email
    FROM
        category_tag
    GROUP BY
    supplier_product_id
) ct ON sp.id = ct.supplier_product_id
    WHERE cp.cart_id in (
        SELECT cart_id FROM orden_details_view odv
        join supplier_unit su ON su.id = odv.supplier_unit_id
        WHERE su.supplier_business_id = :supplier_business_id
        AND odv.status <> 'canceled'
        AND odv.delivery_date = :delivery_date
    )
    AND cp.quantity > 0
    GROUP BY 2
    ORDER BY 3
)
SELECT
    ec.*,
    ct.provider,
    ct.email
FROM
    exploted_cart ec
LEFT JOIN (
    SELECT
        supplier_product_id,
        MAX(CASE WHEN tag_key = 'Proveedor' THEN tag_value END) AS provider,
        MAX(CASE WHEN tag_key = 'Correo' THEN tag_value END) AS email
    FROM
        category_tag
    GROUP BY
    supplier_product_id
) ct ON ec.supplier_product_id = ct.supplier_product_id;
"""


async def get_consolidated_by_provider(
    db: Database,
    delivery_date: datetime.date,  # type: ignore
    supplier_business_id: UUID,
) -> List[Dict[str, Any]]:
    values = {
        "supplier_business_id": supplier_business_id,
        "delivery_date": delivery_date,
    }
    consolidated = await db.fetch_all(query, values)
    if not consolidated:
        return []
    consolidated_list = []
    for row in consolidated:
        consolidated_list.append(dict(row))
    return consolidated_list


async def send_supplier_consolidated_to_provider(
    info: InjectedStrawberryInfo, supplier_business_id: str, password: str
) -> bool:
    if password != RETOOL_SECRET_BYPASS:
        return False
    logging.info("Starting send supplier consolidated...")
    try:
        _supplier_business_id = UUID(supplier_business_id)
        db = info.context["db"].sql
        supplier_business_handler = SupplierBusinessHandler(
            supplier_business_repo=SupplierBusinessRepository(info),  # type: ignore
            supplier_business_account_repo=SupplierBusinessAccountRepository(info),  # type: ignore
        )
        supp_info = await supplier_business_handler.fetch_supplier_business(
            supplier_business_id=UUID(supplier_business_id)
        )
        if not supp_info or not supp_info.account or not supp_info.account.email:
            raise Exception("No supplier business info")
        if not db:
            raise Exception("No db connection")
        delivery_date = datetime.now(timezone.utc) + timedelta(minutes=1)
        consolidated_list = await get_consolidated_by_provider(
            db, delivery_date.date(), _supplier_business_id
        )
        if len(consolidated_list) == 0:
            return False
        condolidated_df = pd.DataFrame(consolidated_list)
        # Group by provider and create separate DataFrames
        provider_groups = condolidated_df.groupby("email")
        # Iterate over unique provider values
        for email, group_df in provider_groups:
            # Create a new DataFrame for each provider
            email_df = group_df.copy()
            provider = email_df["provider"].iloc[0]
            email_df = email_df.drop(columns=["provider", "email"])
            excel_output = BytesIO()
            email_df.to_excel(excel_output, index=False)
            excel_output.seek(0)  # Reset file pointer to the beginning
            excel_data = excel_output.read()
            excel_base64 = base64.b64encode(excel_data).decode()
            excel_base64 = base64.b64encode(excel_data).decode()

            # Create attachment dictionary
            attchs = [
                {
                    "content": excel_base64,
                    "filename": f"Orden_{delivery_date}.xlsx",
                    "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                }
            ]

            # send mail with html
            # Comment
            # NEED UPDATE ATTCH TO SEND EMAILS BY RESEND APP
            if not send_email_with_attachments_syncronous(
                email_to=str(email),
                sender_name=supp_info.name,
                subject=f"""{provider}, tienes una orden de Compra de {supp_info.name}
                    para entregar {delivery_date.strftime('%Y-%m-%d')}""",
                content="Orden de Compra",
                attchs=attchs,
            ):
                # Send email to supplier
                await send_email(
                    email_to=supp_info.account.email,
                    subject=f"Error al mandar orden de compra a proveedor a {provider}",
                    content="Error al mandar email a proveedor",
                    from_email={"email": SENDGRID_SINGLE_SENDER, "name": supp_info.name},
                )
    except Exception as e:
        logging.error(e)
    return True


async def send_supplier_consolidated_to_provider_wrapper(
    supplier_business_id: str, password: str
) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await send_supplier_consolidated_to_provider(
        info, supplier_business_id=supplier_business_id, password=password
    )


def parse_args() -> argparse.Namespace:
    """Parse the command line arguments."""
    parser = argparse.ArgumentParser(description="Reset user account.")
    parser.add_argument(
        "--supplier_business_id",
        type=str,
        default=None,
        required=True,
    )
    return parser.parse_args()


async def main():
    try:
        # Permite conectar a la db
        args = parse_args()
        await db_startup()
        logging.info("Starting routine to send supplier consolidated to providers ...")
        password = RETOOL_SECRET_BYPASS
        resp = await send_supplier_consolidated_to_provider_wrapper(
            args.supplier_business_id, password
        )
        if resp:
            logging.info("Finished routine to send supplier consolidated to providers")
        else:
            logging.info("Error to send supplier consolidated to providers")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
