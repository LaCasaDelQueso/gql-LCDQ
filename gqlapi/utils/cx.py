import logging
from uuid import UUID
from bson import Binary
from gqlapi.lib.clients.clients.email_api.mails import send_email_with_attachments_syncronous
from gqlapi.utils.helpers import deserialize_encoded_file
from motor.motor_asyncio import AsyncIOMotorClient


async def send_business_docs(
    mongo_db: AsyncIOMotorClient,  # type: ignore
    email: str,
    business_account_type: str,
    business_id: UUID,
) -> bool:
    """Send Email with business documents

    Parameters
    ----------
    mongo_db : AsyncIOMotorClient
    email : str
    business_account_type : str
    business_id : UUID
    """
    # validate account type
    if business_account_type == "restaurant":
        collection = mongo_db.restaurant_business_account
        key = "restaurant_business_id"
    elif business_account_type == "supplier":
        collection = mongo_db.supplier_business_account
        key = "supplier_business_id"
    else:
        logging.error("Invalid business account type (restaurant or supplier)")
        return False
    # fetch mongo info
    business_info = await collection.find_one({key: Binary.from_uuid(business_id)})
    if (
        not business_info
        or not business_info.get("legal_rep_id")
        or not business_info.get("legal_rep_name")
    ):
        logging.error("Business not found")
        return False
    if not business_info.get("legal_rep_id") or not business_info.get("legal_rep_name"):
        logging.error("Business does not have legal docs yet")
        return False
    # decode files
    files_to_send = []
    legal_id_name, incorp_file_name = "", ""
    if business_info.get("legal_rep_id"):
        files_to_send.append(
            await deserialize_encoded_file(
                business_info.get("legal_rep_id").decode("utf-8")
            )
        )
        legal_id_name = files_to_send[-1]["filename"]
    if business_info.get("incorporation_file"):
        files_to_send.append(
            await deserialize_encoded_file(
                business_info.get("incorporation_file").decode("utf-8")
            )
        )
        incorp_file_name = files_to_send[-1]["filename"]
    # build message
    msg = f"""
        <p>Hola team,</p>
        <br />
        <p>Aquí están los documentos legales de {Binary.as_uuid(business_info.get(key))}:</p>
        <ul>
            <li>Representate Legal: {business_info.get("legal_rep_name", "SIN REPRESENTANTE LEGAL TODAVIA")}</li>
            <li>Documento de identidad: {legal_id_name} (adjunto)</li>
            <li>Documento de acta constitutiva: {incorp_file_name} (adjunto)</li>
            <li>Razón Social: {business_info.get("legal_business_name", "NO SE HA SUBIDO LA RAZON SOCIAL")}</li>
        </ul>
        <br />
        <p>Saludos</p>
    """
    # send email
    # Comment
    # NEED UPDATE ATTCH TO SEND EMAILS BY RESEND APP
    return send_email_with_attachments_syncronous(
        email,
        f"Documentos legales ({business_info.get('legal_rep_name')})",
        msg,
        files_to_send,
        sender_name="Alima"
    )
