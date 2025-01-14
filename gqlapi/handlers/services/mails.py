from typing import Any, Dict, List
from gqlapi.lib.clients.clients.email_api.mails import (
    send_email,
    send_email_with_attachments_syncronous,
)
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.config import app_path, ENV as DEV_ENV

# Price Lists Emails


async def send_notification_price_list_expiration(
    email_to: str, name: str, price_list: str
) -> bool:
    """Send Order cancelation

    Parameters
    ----------
    email_to : str
        Email address
    uname : str
        Name
    delivery_date : str
        Delivery date

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "expiration_price_list_warning.html"
    msg_content = msg_file.open().read().replace("LIST_TO_EXPIRE", price_list)
    return await send_email(
        email_to=email_to,
        subject=f"Listas de precios estan por expirar - {name}",
        content=msg_content,
    )


# Alima Billing Emails

# Add depricated because maybe attchs need update
@deprecated("Need update attchs for Resend", "gqlapi.handlers.services.mails")
async def send_new_alima_invoice_notification_v2(
    email_to: str | List[str], name: str, attchs: List[Dict[Any, Any]]
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    month : float
        Invoice total

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "notification_new_alima_invoice_v2.html"
    msg_content = msg_file.open().read().replace("SUPPLIER_BUSINESS_NAME", name)
    return send_email_with_attachments_syncronous(
        email_to=email_to,
        subject=("" if DEV_ENV.lower() == "prod" else "[TEST] ")
        + f"{name}, tienes una nueva factura de Alima",
        content=msg_content,
        attchs=attchs,
        sender_name="Alima",
    )

# Add depricated because maybe attchs need update
@deprecated("Need update attchs for Resend", "gqlapi.handlers.services.mails")
async def send_alima_invoice_complement_notification_v2(
    email_to: str | List[str], name: str, attchs: List[Dict[Any, Any]]
) -> bool:
    """Send Alima Invoice Complement Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name

    Returns
    -------
    bool
        validation
    """
    msg_file = (
        app_path / "views" / "mails" / "notification_alima_invoice_complement.html"
    )
    msg_content = msg_file.open().read().replace("SUPPLIER_BUSINESS_NAME", name)
    return send_email_with_attachments_syncronous(
        email_to=email_to,
        subject=("" if DEV_ENV.lower() == "prod" else "[TEST] ")
        + f"{name}, recibimos el pago de tu factura de Alima",
        content=msg_content,
        attchs=attchs,
        sender_name="Alima",
    )


async def send_card_payment_failed_notification(
    email_to: str, name: str, month: str, plan: str
) -> bool:
    """Send Card Payment Failed Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    month : str
        Invoice Month
    plan : str
        Alima Plan

    Returns
    -------
    bool
        validation
    """
    msg_file = (
        app_path / "views" / "mails" / "notification_stripe_failed_card_payment.html"
    )
    msg_content = (
        msg_file.open()
        .read()
        .replace("INVOICE_MONTH_ALIMA", month)
        .replace("SUPPLIER_BUSINESS_NAME", name)
        .replace("ALIMAPLAN", plan)
    )
    # REPLACE
    return await send_email(
        email_to=email_to,
        subject=f"{name}: Problema con tu Suscripción de Alima",
        content=msg_content,
    )


@deprecated(
    "Use send_new_alima_invoice_notification_v2 instead",
    "gqlapi.handlers.services.mails",
)
async def send_new_alima_invoice_notification(
    email_to: str, name: str, month: str, attchs: List[Dict[Any, Any]]
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    month : int
        Invoice Month
    month : float
        Invoice total

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "notification_new_alima_invoice.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("INVOICE_MONTH_ALIMA", month)
        .replace("SUPPLIER_BUSINESS_NAME", name)
    )
    return send_email_with_attachments_syncronous(
        email_to=email_to,
        subject="Tienes una nueva factura de Alima",
        content=msg_content,
        attchs=attchs,
        sender_name="Alima",
    )


# V2 Alima Billing Emails
async def send_alima_invoice_pending_notification(
    email_to: str, name: str, tolerance: int, month: str, bank_info: Dict[str, str] = {}
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    tolerance: int
        tolerance days

    Returns
    -------
    bool
        validation
    """
    max_tolerance = 8 - tolerance
    if max_tolerance <= 1:
        max_tolerance = 1
    msg_file = app_path / "views" / "mails" / "notification_alima_invoice_pending.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("INVOICE_MONTH_ALIMA", month)
        .replace("SUPPLIER_BUSINESS_NAME", name)
        .replace(
            "ACCOUNTNAME",
            bank_info.get(
                "account_name",
                '<li><p style="text-align: left;">Nombre: Servicios de Distribución de Perecederos Neutro</p></li>',
            ),
        )
        .replace("BANKNAME", bank_info.get("bank_name", "BBVA"))
        .replace("ACCOUNTNUMBER", bank_info.get("account_number", "012180001182328575"))
    )
    # REPLACE
    return await send_email(
        email_to=email_to,
        subject=f"{name}, tienes una Factura de Alima pendiente de Pago ({max_tolerance} / 8)",
        content=msg_content,
    )

# Add depricated because maybe attchs need update
@deprecated("Need update attchs for Resend", "gqlapi.handlers.services.mails")
async def send_restaurant_new_invoice_complement_notification(
    email_to: str,
    supplier_business_name: str,
    restaurant_business_name: str,
    folio: str,
    delivery_date: str,
    attchs: List[Dict[Any, Any]],
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    month : str
        Invoice Month
    month : float
        Invoice total

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "notification_restaurant_new_invoice.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("SUPPLIER_BUSINESS_NAME", supplier_business_name)
        .replace("RESTAURANT_BRANCH_NAME", restaurant_business_name)
        .replace("NUMFOLIO", str(folio))
        .replace("DELIVERY_DATE", str(delivery_date))
        # .replace("SUPPLIER_BUSINESS_NAME", name)
    )
    return send_email_with_attachments_syncronous(
        email_to=email_to,
        subject=f"Factura de {supplier_business_name} - Folio {folio}",
        content=msg_content,
        attchs=attchs,
        sender_name=supplier_business_name,
    )


# V2 Alima Billing Emails
async def send_account_inactive_notification(
    email_to: str, name: str, tolerance: int, month: str
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    tolerance: int
        tolerance days

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "notification_account_inactive.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("INVOICE_MONTH_ALIMA", month)
        .replace("SUPPLIER_BUSINESS_NAME", name)
    )
    # REPLACE
    return await send_email(
        email_to=email_to,
        subject="Tienes una factura de Alima pendiente",
        content=msg_content,
    )


async def send_account_inactive(email_to: str, name: str, month: str) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "account_inactive.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("INVOICE_MONTH_ALIMA", month)
        .replace("SUPPLIER_BUSINESS_NAME", name)
    )
    # REPLACE
    return await send_email(
        email_to=email_to,
        subject=("" if DEV_ENV.lower() == "prod" else "[TEST] ")
        + f"{name}, su cuenta Alima ha sido suspendida por falta de pago",
        content=msg_content,
    )


# Supply Invoices Emails

# Add depricated because maybe attchs need update
@deprecated("Need update attchs for Resend", "gqlapi.handlers.services.mails")
async def send_new_consolidated_invoice_notification(
    email_to: str,
    supplier_business_name: str,
    restaurant_business_name: str,
    folio: int,
    html_table: str,
    attchs: List[Dict[Any, Any]],
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    month : int
        Invoice Month
    month : float
        Invoice total

    Returns
    -------
    bool
        validation
    """
    msg_file = (
        app_path
        / "views"
        / "mails"
        / "notification_restaurant_new_consolidated_invoice.html"
    )
    msg_content = (
        msg_file.open()
        .read()
        .replace("SUPPLIER_BUSINESS_NAME", supplier_business_name)
        .replace("RESTAURANT_BRANCH_NAME", restaurant_business_name)
        .replace("NUMFOLIO", str(folio))
        .replace("HTML_TABLE", html_table)
        # .replace("SUPPLIER_BUSINESS_NAME", name)
    )
    return send_email_with_attachments_syncronous(
        email_to=email_to,
        subject=f"Factura Consolidada de {supplier_business_name} con Folio {folio}",
        content=msg_content,
        attchs=attchs,
        sender_name=supplier_business_name,
    )

# Add depricated because maybe attchs need update
@deprecated("Need update attchs for Resend", "gqlapi.handlers.services.mails")
async def send_restaurant_new_invoice_notification(
    email_to: str,
    supplier_business_name: str,
    restaurant_business_name: str,
    folio: int,
    delivery_date: str,
    attchs: List[Dict[Any, Any]],
) -> bool:
    """Send Alima Invoice Notification

    Parameters
    ----------
    email_to : str
        Email address
    name : str
        Supplier Business Name
    month : int
        Invoice Month
    month : float
        Invoice total

    Returns
    -------
    bool
        validation
    """
    msg_file = app_path / "views" / "mails" / "notification_restaurant_new_invoice.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("SUPPLIER_BUSINESS_NAME", supplier_business_name)
        .replace("RESTAURANT_BRANCH_NAME", restaurant_business_name)
        .replace("NUMFOLIO", str(folio))
        .replace("DELIVERY_DATE", str(delivery_date))
        # .replace("SUPPLIER_BUSINESS_NAME", name)
    )
    return send_email_with_attachments_syncronous(
        email_to=email_to,
        subject=f"Factura de {supplier_business_name} - Folio {folio}",
        content=msg_content,
        attchs=attchs,
        sender_name=supplier_business_name,
    )


# Internal Monitoring Emails


async def send_monitor_alert(email_to: str, subject: str, content: str) -> bool:
    return await send_email(email_to=email_to, subject=subject, content=content)


async def send_reports_alert(email_to: str, subject: str, content: str) -> bool:
    return await send_email(email_to=email_to, subject=subject, content=content)
