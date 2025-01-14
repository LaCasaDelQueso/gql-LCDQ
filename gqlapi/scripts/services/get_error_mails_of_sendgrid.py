"""How to run (file path as example):
        poetry run python -m gqlapi.scripts.services.get_error_mails_of_sendgrid"""

import argparse
import asyncio
import base64
from datetime import datetime, timedelta
import json
import logging
import time
from types import NoneType
from typing import Any, Dict, List

# from gqlapi.lib.clients.clients.sendgridapi.sendgridapi import SendgridClientApi
from gqlapi.lib.clients.clients.email_api.mails import send_email, send_email_with_attachments_syncronous
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from gqlapi.repository.supplier.supplier_business import (
    SupplierBusinessAccountRepository,
    SupplierBusinessRepository,
)
import sendgrid
from gqlapi.config import APP_TZ, RETOOL_SECRET_BYPASS
from gqlapi.db import db_shutdown, db_startup, database as SQLDatabase
from gqlapi.utils.automation import InjectedStrawberryInfo
from gqlapi.mongo import mongo_db as MongoDatabase

import pandas as pd
from gqlapi.config import SENDGRID_API_KEY

pd.options.mode.chained_assignment = None  # type: ignore

headers = {"Authorization": f"Bearer {SENDGRID_API_KEY}"}
email_to = "automations@alima.la"


def delete_bounces(sg):
    response = sg.client.suppression.bounces.delete(request_body={"delete_all": True})
    print(response.status_code)
    print(response.body)
    print(response.headers)


def delete_spam_reports(sg):
    response = sg.client.suppression.spam_reports.delete(
        request_body={"delete_all": True}
    )
    print(response.status_code)
    print(response.body)
    print(response.headers)


def delete_blocks(sg):
    response = sg.client.suppression.blocks.delete(request_body={"delete_all": True})
    print(response.status_code)
    print(response.body)
    print(response.headers)


def delete_failed_events(sg):
    delete_blocks(sg)
    delete_spam_reports(sg)
    delete_bounces(sg)


def get_unix_timestamp(date):
    return int(date.timestamp())


async def get_blocked_events(sendgrid_api) -> List[Dict[str, Any]]:
    query_params = {
        "start_time": get_unix_timestamp(datetime.now()),
        "end_time": get_unix_timestamp(datetime.now() - timedelta(weeks=1)),
        "limit": 1000,
        "offset": 0,
    }
    offset = 0
    block_events_list = []
    while True:
        query_params["offset"] = offset

        blocks = sendgrid_api.client.suppression.blocks.get(query_params)  # type: ignore
        block_events = json.loads(blocks.body)  # type: ignore
        if not block_events:
            break
        for event in block_events:
            event["type"] = "block"
            dt_object = datetime.fromtimestamp(event["created"])
            event["created"] = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            block_events_list.append(event)

        # Increment offset by the number of events fetched
        offset += len(block_events_list)
        if offset == 1000:
            await send_email(
                email_to="fernando@alima.la",
                subject="Error al obtener eventos de bloqueo de correos",
                content="Los bloqueos han excedido los 1000 eventos, por favor revisar",
            )
        else:
            break

    block_mails_set = set()
    filtered_block_events = []
    for event in block_events_list:
        if event["email"] in block_mails_set:
            continue
        block_mails_set.add(event["email"])
        filtered_block_events.append(event)
    return filtered_block_events


async def get_spam_events(sendgrid_api) -> List[Dict[str, Any]]:
    query_params = {
        "start_time": get_unix_timestamp(datetime.now()),
        "end_time": get_unix_timestamp(datetime.now() - timedelta(weeks=1)),
        "limit": 1000,
        "offset": 0,
    }
    offset = 0
    spam_events_list = []
    while True:
        query_params["offset"] = offset

        spam_reports = sendgrid_api.client.suppression.spam_reports.get(query_params)  # type: ignore
        spam_events = json.loads(spam_reports.body)  # type: ignore
        if not spam_events:
            break
        for event in spam_events:
            event["type"] = "spam_reports"
            dt_object = datetime.fromtimestamp(event["created"])
            event["created"] = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            spam_events_list.append(event)

        # Increment offset by the number of events fetched
        offset += len(spam_events_list)
        if offset == 1000:
            await send_email(
                email_to="fernando@alima.la",
                subject="Error al obtener eventos de spam de correos",
                content="Los spam han excedido los 1000 eventos, por favor revisar",
            )
        else:
            break

    spam_mails_set = set()
    filtered_spam_events = []
    for event in spam_events_list:
        if event["email"] in spam_mails_set:
            continue
        spam_mails_set.add(event["email"])
        filtered_spam_events.append(event)
    return filtered_spam_events


async def get_bounces_events(sendgrid_api) -> List[Dict[str, Any]]:
    query_params = {
        "start_time": get_unix_timestamp(datetime.now()),
        "end_time": get_unix_timestamp(datetime.now() - timedelta(weeks=1)),
        "limit": 1000,
        "offset": 0,
    }
    offset = 0
    bounces_events_list = []
    while True:
        query_params["offset"] = offset
        bounces = sendgrid_api.client.suppression.bounces.get(query_params)  # type: ignore
        bounces_events = json.loads(bounces.body)  # type: ignore
        if not bounces_events:
            break
        for event in bounces_events:
            event["type"] = "bounces"
            dt_object = datetime.fromtimestamp(event["created"])
            event["created"] = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            bounces_events_list.append(event)

        # Increment offset by the number of events fetched
        offset += len(bounces_events_list)
        if offset == 1000:
            await send_email(
                email_to="fernando@alima.la",
                subject="Error al obtener eventos de bounce de correos",
                content="Los bounce han excedido los 1000 eventos, por favor revisar",
            )
        else:
            break

    bounces_mails_set = set()
    filtered_bounces_events = []
    for event in bounces_events_list:
        if event["email"] in bounces_mails_set:
            continue
        bounces_mails_set.add(event["email"])
        filtered_bounces_events.append(event)
    return filtered_bounces_events


async def get_invalid_emails_events(sendgrid_api) -> List[Dict[str, Any]]:
    query_params = {
        "start_time": get_unix_timestamp(datetime.now()),
        "end_time": get_unix_timestamp(datetime.now() - timedelta(weeks=1)),
        "limit": 1000,
        "offset": 0,
    }
    offset = 0
    invalid_emails_events_list = []
    while True:
        query_params["offset"] = offset
        invalid_emails = sendgrid_api.client.suppression.invalid_emails.get(query_params)  # type: ignore
        invalid_emails_events = json.loads(invalid_emails.body)  # type: ignore
        if not invalid_emails_events:
            break
        for event in invalid_emails_events:
            event["type"] = "invalid_emails"
            dt_object = datetime.fromtimestamp(event["created"])
            event["created"] = dt_object.strftime("%Y-%m-%d %H:%M:%S")
            invalid_emails_events_list.append(event)

        # Increment offset by the number of events fetched
        offset += len(invalid_emails_events_list)
        if offset == 1000:
            await send_email(
                email_to=email_to,
                subject="Error al obtener eventos de correos invalidos",
                content="Los correos invalidos han excedido los 1000 eventos, por favor revisar",
            )
        else:
            break

    invalid_emails_set = set()
    filtered_invalid_emails_events = []
    for event in invalid_emails_events_list:
        if event["email"] in invalid_emails_set:
            continue
        invalid_emails_set.add(event["email"])
        filtered_invalid_emails_events.append(event)
    return filtered_invalid_emails_events


async def get_suppression_events(sendgrid_api) -> pd.DataFrame:
    error_emails_list = []
    error_emails_list.extend(await get_blocked_events(sendgrid_api))
    error_emails_list.extend(await get_spam_events(sendgrid_api))
    error_emails_list.extend(await get_bounces_events(sendgrid_api))
    error_emails_list.extend(await get_invalid_emails_events(sendgrid_api))
    error_emails_df = pd.DataFrame(error_emails_list)
    return error_emails_df


async def send_error_mails_to_automations(error_emails_df: pd.DataFrame) -> NoneType:
    # Save the error emails in a xlsx file
    with pd.ExcelWriter("output_variable.xlsx", engine="xlsxwriter") as writer:
        error_emails_df.to_excel(writer, index=False)
    with open("output_variable.xlsx", "rb") as file:
        xls_file = base64.b64encode(file.read()).decode()
    xls_file_attcht = [
        {
            "content": xls_file,
            "filename": f"Reporte Semanal - Error Mails - {datetime.now(APP_TZ).strftime('%Y-%m-%d')}",
            "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
    ]
    # Send the email with the error emails
    # Comment
    # NEED UPDATE ATTCH TO SEND EMAILS BY RESEND APP
    send_email_with_attachments_syncronous(
        email_to=email_to,
        subject=f"Reporte Semanal - Error Mails - {datetime.now(APP_TZ).strftime('%Y-%m-%d')}",
        content=f"Reporte Semanal - Error Mails - {datetime.now(APP_TZ).strftime('%Y-%m-%d')}",
        attchs=xls_file_attcht,
        sender_name="Alima",
    )


async def send_mails_to_suppliers(
    info: InjectedStrawberryInfo, failed_emails: Dict[Any, Any]
) -> NoneType:
    supplier_business_repo = SupplierBusinessRepository(info)  # type: ignore
    supplier_business_account_repo = SupplierBusinessAccountRepository(info)  # type: ignore

    for key in failed_emails:
        supplier = await supplier_business_repo.find(name=key, active=True)
        error_emails_df = pd.DataFrame(failed_emails[key])
        remove_columns = ["from_email", "status", "clicks_count", "opens_count"]
        error_emails_df = error_emails_df.drop(columns=remove_columns)
        error_emails_df.columns = ["msg_id", "asunto", "email", "fecha de envío"]
        with pd.ExcelWriter("output_variable.xlsx", engine="xlsxwriter") as writer:
            error_emails_df.to_excel(writer, index=False)
        with open("output_variable.xlsx", "rb") as file:
            xls_file = base64.b64encode(file.read()).decode()
        subject = (
            "Reporte Semanal - "
            + "Errores en envío de correos de facturas - "
            + f"{datetime.now(APP_TZ).strftime('%Y-%m-%d')}"
            ""
        )
        xls_file_attcht = [
            {
                "content": xls_file,
                "filename": subject,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        ]

        # subject = "test"
        if not supplier:
            # Comment
            # NEED UPDATE ATTCH TO SEND EMAILS BY RESEND APP
            send_email_with_attachments_syncronous(
                email_to=email_to,
                subject=subject,
                content=f"""Error al enviar correos de error mails a proveedor {key} no se encontro nombre en base de datos""",
                attchs=xls_file_attcht,
                sender_name="Alima",
            )
            continue
        # [TODO] warinig: supplier name can be duplicated
        supplier_obj = SupplierBusiness(**supplier[0])
        supplier_account = await supplier_business_account_repo.fetch(supplier_obj.id)

        if not supplier_account or "email" not in supplier_account:
            # Comment
            # NEED UPDATE ATTCH TO SEND EMAILS BY RESEND APP
            send_email_with_attachments_syncronous(
                email_to=email_to,
                subject=subject,
                content=f"""Error al enviar correos de error mails a proveedor {key} no se encontro cuenta o correo""",
                attchs=xls_file_attcht,
                sender_name="Alima",
            )
            continue
        # Comment
        # NEED UPDATE ATTCH TO SEND EMAILS BY RESEND APP
        send_email_with_attachments_syncronous(
            email_to=email_to,  # [TODO] supplier_account.email,
            subject=subject,
            content=f"""{key} - Estos son los correos que no le llegaron a tus clientes""",
            attchs=xls_file_attcht,
            sender_name="Alima",
        )


def get_failed_events(sendgrid_api) -> Dict[Any, Any]:
    query_params = {
        "limit": 1000,
        "query": "status='not_delivered'",
    }
    failed_emails = []
    offset = 0
    one_week_ago = datetime.now() - timedelta(weeks=1)
    time_validation = True
    while time_validation:
        query_params["offset"] = offset
        fail_mails = sendgrid_api.client.messages.get(query_params=query_params)  # type: ignore
        if not fail_mails:
            time_validation = False
            break
        fail_mails_dict = fail_mails.to_dict["messages"]
        for mails in fail_mails_dict:
            last_datetime = datetime.strptime(
                mails["last_event_time"], "%Y-%m-%dT%H:%M:%SZ"
            )
            if last_datetime <= one_week_ago:
                time_validation = False
            else:
                failed_emails.append(mails)
                offset += 1
        time.sleep(5)
    filtered_failed_emails = {}
    for event in failed_emails:  # type: ignore
        if "Factura de" in event["subject"]:
            part = event["subject"].split("Factura de ")[1]
            # Split the resulting part by ' - Folio ' and take the first part
            supplier = part.split(" - Folio ")[0]
            if supplier in filtered_failed_emails:
                filtered_failed_emails[supplier].append(event)
            else:
                filtered_failed_emails[supplier] = [event]
    return filtered_failed_emails


async def send_mail_of_error_when_sending_emails_from_sendgrid(
    info: InjectedStrawberryInfo, password: str
) -> bool:
    if password != RETOOL_SECRET_BYPASS:
        return False
    logging.info("Starting send supplier consolidated...")
    try:
        sendgrid_api = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        error_emails_df = await get_suppression_events(sendgrid_api)
        await send_error_mails_to_automations(error_emails_df)
        failed_emails = get_failed_events(sendgrid_api)
        await send_mails_to_suppliers(info, failed_emails)
        delete_failed_events(sendgrid_api)
    except Exception as e:
        print(e)
        return False
        # Iterate over unique provider values

    return True


async def send_mail_of_error_when_sending_emails_from_sendgrid_wrapper(
    password: str,
) -> bool:
    info = InjectedStrawberryInfo(
        db=SQLDatabase,
        mongo=MongoDatabase,
    )
    return await send_mail_of_error_when_sending_emails_from_sendgrid(
        info, password=password
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
        await db_startup()
        logging.info(
            "Starting routine to send mail of error when sending emails from sendgrid ..."
        )
        password = RETOOL_SECRET_BYPASS
        resp = await send_mail_of_error_when_sending_emails_from_sendgrid_wrapper(
            password
        )
        if resp:
            logging.info(
                "Finished routine to send error when sending emails from sendgrid"
            )
        else:
            logging.info("Error to send error when sending emails from sendgrid")
        await db_shutdown()
    except Exception as e:
        logging.error(e)


if __name__ == "__main__":
    asyncio.run(main())
