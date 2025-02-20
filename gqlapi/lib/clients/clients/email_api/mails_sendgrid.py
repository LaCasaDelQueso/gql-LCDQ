import logging
from typing import Any, Dict, List, Optional
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail.from_email import From
from sendgrid.helpers.mail import (
    Mail,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
)
from gqlapi.config import SENDGRID_API_KEY, SENDGRID_SINGLE_SENDER


async def send_email(
    email_to: str,
    subject: str,
    content: str,
    from_email: Dict[str, str] = {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"},
) -> bool:
    """Send Email

    Returns
    -------
    Bool
        True if correctly sent
    """
    #
    message = Mail(
        to_emails=email_to,
        from_email=From(email=from_email["email"], name=from_email["name"]),
        subject=subject,
        html_content=content,
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(response.status_code)
        logging.info(response.body)
        logging.info(response.headers)
        return True
    except Exception as e:
        logging.info(e)
        return False


def send_email_syncronous(email_to: str, subject: str, content: str) -> bool:
    """Send Email

    Returns
    -------
    Bool
        True if correctly sent
    """
    message = Mail(
        from_email=From(email=SENDGRID_SINGLE_SENDER, name="Alima"),
        to_emails=email_to,
        subject=subject,
        html_content=content,
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(response.status_code)
        logging.info(response.body)
        logging.info(response.headers)
        return True
    except Exception as e:
        logging.info(e)
        return False


def send_email_with_attachments_syncronous(
    email_to: str | List[str], subject: str, content: str, attchs: List[Dict[str, Any]], sender_name: Optional[str] = "Alima"
) -> bool:
    """Send Email with attachments

    Returns
    -------
    Bool
        True if correctly sent
    """
    message = Mail(
        from_email=From(email=SENDGRID_SINGLE_SENDER, name=sender_name),
        to_emails=email_to,
        subject=subject,
        html_content=content,
    )
    _attchms = []
    for atc in attchs:
        _attchms.append(
            Attachment(
                FileContent(atc["content"]),
                FileName(atc["filename"]),
                FileType(atc["mimetype"]),
                Disposition("attachment"),
            )
        )
    message.attachment = _attchms

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logging.info(response.status_code)
        logging.info(response.body)
        logging.info(response.headers)
        return True
    except Exception as e:
        logging.info(e)
        return False
