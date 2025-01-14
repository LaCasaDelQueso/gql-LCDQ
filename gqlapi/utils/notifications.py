from types import NoneType
from typing import Any, Dict, List, Optional
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from uuid import UUID
from gqlapi.lib.clients.clients.email_api.mails import send_email
from gqlapi.lib.clients.clients.whatsapp.hilos import HilosSender
from gqlapi.domain.interfaces.v2.orden.cart import CartProductGQL
from gqlapi.domain.models.v2.core import OrdenDetails
from gqlapi.domain.models.v2.utils import DataTypeTraslate, OrdenStatusType
from gqlapi.config import (
    ALIMA_EXTERNAL_RESTO_REVIEW,
    ALIMA_EXTERNAL_SUPPLIER_REVIEW,
    app_path,
    HILOS_API_KEY,
    SENDGRID_SINGLE_SENDER
)


logger = get_logger(get_app())

# WhatsApp api
wa_sender = HilosSender(HILOS_API_KEY)


####################
# Formatters
####################
def format_email_table(html_table: str) -> str:
    """Format HTML Table for email

    Parameters
    ----------
    html_table : str
        HTML Table

    Returns
    -------
    str
        Formatted HTML Table
    """
    msg_file = app_path / "views" / "mails" / "striped_email_table.html"
    msg_content = msg_file.open().read().replace("HTMLTABLE", html_table)
    return msg_content


####################
# User Notifications
####################


async def send_new_resto_user_welcome_msg(
    subject: str,
    to_email: Dict[str, str],
) -> bool:
    """Send email to new restaurant user with welcome message

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    msg_file = app_path / "views" / "mails" / "welcome_new_restaurant_user.html"
    msg_content = (
        msg_file.open().read().replace("DISPLAYNAME", to_email.get("name", ""))
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
    )


async def send_new_sup_user_welcome_msg(
    subject: str,
    to_email: Dict[str, str],
) -> bool:
    """Send email to new supplier user with welcome message

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    # [TODO] - update supplier template
    msg_file = app_path / "views" / "mails" / "welcome_new_supplier_user.html"
    msg_content = (
        msg_file.open().read().replace("DISPLAYNAME", to_email.get("name", ""))
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
    )


async def send_employee_welcome_msg(
    subject: str,
    to_email: Dict[str, str],
    business_name: str,
    tmp_pswd: str,
    template: str = "welcome_employee.html",
) -> bool:
    """Send email to employee with welcome message

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    business_name : str
        Business name
    tmp_pswd : str
        Temporary password

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    msg_file = app_path / "views" / "mails" / template
    msg_content = (
        msg_file.open()
        .read()
        .replace("DISPLAYNAME", to_email.get("name", ""))
        .replace("ALIMAEMAIL", to_email.get("email", ""))
        .replace("BUSINESSACCOUNT", business_name)
        .replace("ALIMAPASSWORD", tmp_pswd)
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
    )


####################
# Orden Notifications
####################


async def send_supplier_changed_status(
    to_email: Dict[str, str],
    status: OrdenStatusType,
    orden_id: UUID,
) -> bool:
    """Send email to notify restaurant of status change

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    status : OrdenStatusType

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    status_msg = get_status_message(status, orden_id, ALIMA_EXTERNAL_SUPPLIER_REVIEW)
    msg_file = app_path / "views" / "mails" / "orden_status_update.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("DISPLAYNAME", to_email.get("name", ""))
        .replace("CHANGESTATUSMSG", status_msg)
        .replace("APPLINKREF", "https://seller.alima.la/app")
    )
    return await send_email(
        email_to=to_email["email"],
        subject=f"Pedido ({str(orden_id)[:10]}) ha sido {DataTypeTraslate.get_orden_status_encode(status.value)}",
        content=msg_content,
    )


@deprecated("Use send_restaurant_changed_status_v2 instead", "utils")
async def send_restaurant_changed_status(
    to_email: Dict[str, str],
    status: OrdenStatusType,
    orden_id: UUID,
) -> bool:
    """Send email to notify restaurant of status change

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    status : OrdenStatusType

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    status_msg = get_status_message(status, orden_id, ALIMA_EXTERNAL_RESTO_REVIEW)
    msg_file = app_path / "views" / "mails" / "orden_status_update.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("DISPLAYNAME", to_email.get("name", ""))
        .replace("CHANGESTATUSMSG", status_msg)
        .replace("APPLINKREF", "https://app.alima.la/app")
    )
    return await send_email(
        email_to=to_email["email"],
        subject=f"Tu pedido ({str(orden_id)[:10]}) ha sido {DataTypeTraslate.get_orden_status_encode(status.value)}",
        content=msg_content,
    )


async def send_restaurant_changed_status_v2(
    to_email: Dict[str, str],
    from_email: Dict[str, str],
    status: OrdenStatusType,
    orden_details: OrdenDetails,
    rest_branch_name: str,
    orden_number: int,
    cel_contact: str,
) -> bool:
    """Send email to notify restaurant of status change

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    status : OrdenStatusType

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    status_msg = get_status_message_v2(
        status,
        str(orden_number),
        delivery_date=(
            orden_details.delivery_date.isoformat()
            if orden_details.delivery_date
            else ""
        ),
        restaurant_branch_name=rest_branch_name,
    )
    # ORDEN FECHA DE ENTREGA
    msg_file = app_path / "views" / "mails" / "orden_status_update_v2.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("SUPPLIER_BUSINESS_NAME", to_email.get("name", ""))
        .replace("CHANGESTATUSMSG", status_msg)
        .replace(
            "APPLINKREF",
            f"https://app.alima.la/ext/supplier/purchase-order?ordenId={str(orden_details.orden_id)}",
        )
        .replace("RESTAURANT_BRANCH_NAME", rest_branch_name)
        .replace("CONTACT_CEL", cel_contact)
    )
    return await send_email(
        email_to=to_email["email"],
        from_email=from_email,
        subject=f"""Tu pedido ({str(orden_details.orden_id)[:10]})
            ha sido {DataTypeTraslate.get_orden_status_encode(status.value)}""",
        content=msg_content,
    )


async def send_supplier_changed_status_v2(
    to_email: Dict[str, str],
    from_email: Dict[str, str],
    status: OrdenStatusType,
    orden_details: OrdenDetails,
    rest_branch_name: str,
    orden_number: int,
    cel_contact: str,
) -> bool:
    """Send email to notify restaurant of status change

    Parameters
    ----------
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    status : OrdenStatusType

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    status_msg = get_status_message_v2(
        status,
        str(orden_number),
        delivery_date=(
            orden_details.delivery_date.isoformat()
            if orden_details.delivery_date
            else ""
        ),
        restaurant_branch_name=rest_branch_name,
    )
    # ORDEN FECHA DE ENTREGA
    msg_file = app_path / "views" / "mails" / "orden_status_update_v2.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("SUPPLIER_BUSINESS_NAME", to_email.get("name", ""))
        .replace("CHANGESTATUSMSG", status_msg)
        .replace(
            "APPLINKREF",
            f"https://app.alima.la/ext/supplier/purchase-order?ordenId={str(orden_details.orden_id)}",
        )
        .replace("RESTAURANT_BRANCH_NAME", rest_branch_name)
        .replace("CONTACT_CEL", cel_contact)
    )

    return await send_email(
        email_to=to_email["email"],
        from_email=from_email,
        subject=f"""Tu pedido ({str(orden_details.orden_id)[:10]})
            ha sido {DataTypeTraslate.get_orden_status_encode(status.value)}""",
        content=msg_content,
    )


@deprecated("Use get_status_message_v2 instead", "utils")
def get_status_message(
    status: OrdenStatusType, orden_id: UUID, review_link: str
) -> str:
    """Get Status message

    Parameters
    ----------
    status : OrdenStatusType

    Returns
    -------
    str
    """
    if status == OrdenStatusType.ACCEPTED:
        return "Tu pedido ha sido confirmado por el proveedor. Entra a tu cuenta para revisar el éstatus de tu pedido."
    if status == OrdenStatusType.DELIVERED:
        return """Tu pedido ha sido entregado por el proveedor.
                 <br/> <br/>
                Te invitamos a calificar a tu proveedor en esta liga:
                <br/>
                <a href='{}'>Calificar proveedor</a>""".format(
            review_link + str(orden_id)
        )
    if status == OrdenStatusType.CANCELED:
        return "Tu pedido ha sido cancelado por el proveedor."
    return "Tu pedido ha sido actualizado."


def get_status_message_v2(
    status: OrdenStatusType,
    orden_number: str,
    delivery_date: str,
    restaurant_branch_name: str,
) -> str:
    """Get Status message

    Parameters
    ----------
    status : OrdenStatusType

    Returns
    -------
    str
    """
    if status == OrdenStatusType.ACCEPTED:
        return f"""Te confirmamos que la orden de compra
        {orden_number} ha sido confirmada para
        {restaurant_branch_name} hace un momento.
        Tu fecha programada de entrega es el {delivery_date}
    """
    if status == OrdenStatusType.DELIVERED:
        return f"""Te confirmamos que la orden de compra
        {orden_number} ha sido entregada para
        {restaurant_branch_name} hace un momento.
    """

    if status == OrdenStatusType.CANCELED:
        return f"""Te confirmamos que la orden de compra
        {orden_number} ha sido cancelada para
        {restaurant_branch_name} hace un momento.
    """
    return "Tu pedido ha sido actualizado."


@deprecated("Use send_supplier_changed_status_v2 instead", "utils")
async def send_supplier_email_confirmation(
    subject: str,
    from_email: Dict[str, str],
    to_email: Dict[str, str],
    orden_details: OrdenDetails,
    branch_name: str,
    contact_number: str,
    delivery_address: str,
    cart_products: List[CartProductGQL],
) -> bool:
    """Send email confirmation to customer / supplier

    Parameters
    ----------
    from_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    orden_details : OrdenDetails
    cart_products : List[CartProductGQL]

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    prod_table = await cart_to_html_table(
        cart_products,
        orden_details.subtotal,
        orden_details.tax,
        orden_details.subtotal_without_tax,
        orden_details.total,
        orden_details.shipping_cost,
        orden_details.packaging_cost,
        orden_details.service_fee,
        orden_details.discount,
    )
    msg_file = app_path / "views" / "mails" / "supplier_order_confirmation.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("DISPLAYNAME", to_email.get("name", ""))
        .replace("REMITANT", from_email.get("name", ""))
        .replace("BRANCHNAME", branch_name)
        .replace("PHONENUMBER", contact_number)
        .replace("DELIVERYADDRESS", delivery_address)
        .replace(
            "FECHADEENTREGA",
            (
                (
                    orden_details.delivery_date.isoformat()
                    + f" (entre {str(orden_details.delivery_time)}hrs)"
                )
                if orden_details.delivery_date
                else ""
            ),
        )
        .replace("TABLADEPRODUCTOS", prod_table)
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
        from_email=from_email,
    )


async def cart_to_html_table(
    cart: List[CartProductGQL],
    subtotal: float | NoneType,
    tax: float | NoneType,
    subtotal_without_tax: float | NoneType,
    total: float | NoneType,
    shipping: float | NoneType = None,
    packaging: float | NoneType = None,
    service_fee: float | NoneType = None,
    discounts: float | NoneType = None,
) -> str:
    """Convert List of prodcuts into HTML Table

    Parameters
    ----------
    cart : List
        List of products
    subtotal: float
    total : float

    Returns
    -------
    str
        HTML Table from Cart
    """
    table_p = """
    <div style="font-size: 5px; ">
        <table class="table" id="cartfyv" style="font-size: 12px; margin: 0 auto 0 auto;">
            <tr>
                <th>Producto</th>
                <th>Precio por Unidad</th>
                <th>Cantidad</th>
                <th>Precio</th>
            </tr>
    """
    row_temp = """<tr>
            <td>{product}</td>
            <td>{unit_price} por {sale_unit}</td>
            <td>{quantity}</td>
            <td>{price}</td>
        </tr>
        """
    for p in cart:
        table_p += row_temp.format(
            product=(
                p.supp_prod.description if p.supp_prod else "Producto no encontrado"
            ),
            unit_price=round(p.unit_price, 2) if p.unit_price else "-",
            sale_unit=DataTypeTraslate.get_uomtype_encode(
                p.sell_unit  # type: ignore
            ).capitalize(),
            quantity=str(round(p.quantity, 2)),
            price=round(p.subtotal, 2) if p.subtotal else "-",
        )
    table_p += f"""
        <tr><td></td><td></td>
            <td><b>Subtotal (Sin impuestos)</b></td>
            <td><b>${round(subtotal_without_tax, 2) if subtotal_without_tax else '-'} MXN</b></td>
        </tr>
        <tr><td></td><td></td>
            <td><b>Impuestos</b></td>
            <td><b>${round(tax, 2) if tax else '-'} MXN</b></td>
        </tr>
        <tr><td></td><td></td>
            <td><b>Subtotal</b></td>
            <td><b>${round(subtotal, 2) if subtotal else '-'} MXN</b></td>
        </tr>
    """
    for cost in [
        (shipping, "Envío"),
        (packaging, "Empaque"),
        (service_fee, "Servicio"),
    ]:
        if cost[0]:
            table_p += f"""
            <tr><td></td><td></td>
                <td><b>{cost[1]}</b></td>
                <td><b>${round(cost[0], 2)} MXN</b></td>
            </tr>
            """
    for disc in [(discounts, "Descuentos")]:
        if disc[0]:
            table_p += f"""
            <tr><td></td><td></td>
                <td><b>{disc[1]}</b></td>
                <td><b>-${round(disc[0], 2)} MXN</b></td>
            </tr>
            """
    table_p += f"""
        <tr><td></td><td></td>
            <td><b>Total</b></td>
            <td><b>${round(total, 2) if total else '-'} MXN</b></td>
        </tr>
        </table></div>
    """
    return table_p


def cart_to_whatsapp_format(
    cart: List[CartProductGQL],
    subtotal: float | NoneType,
    tax: float | NoneType,
    subtotal_without_tax: float | NoneType,
    total: float | NoneType,
    shipping: float | NoneType = None,
    packaging: float | NoneType = None,
    service_fee: float | NoneType = None,
    discounts: float | NoneType = None,
) -> Dict[str, Any]:
    """Convert List of prodcuts into WhatsApp readable

    Parameters
    ----------
    cart : List
        List of products
    subtotal: float
    total : float

    Returns
    -------
    str
        Whatsapp readable from Cart
    """
    table_p = ""
    row_temp = "{product} {sale_unit}: {quantity} x ${unit_price} = ${price}"
    for p in cart:
        table_p += row_temp.format(
            product=(
                p.supp_prod.description if p.supp_prod else "Producto no encontrado"
            ),
            unit_price=round(p.unit_price, 2) if p.unit_price else "-",
            sale_unit=DataTypeTraslate.get_uomtype_encode(
                p.sell_unit  # type: ignore
            ).capitalize(),
            quantity=str(round(p.quantity, 2)),
            price=round(p.subtotal, 2) if p.subtotal else "-",
        )
        table_p += ",\n"
    summary_p = (
        f"Subtotal (S/ IVA): ${round(subtotal_without_tax, 2) if subtotal_without_tax else '-'}\n"
        + f"Impuestos: ${round(tax, 2) if tax else '-'}\n"
        + f"Subtotal: ${round(subtotal, 2) if subtotal else '-'}\n"
    )
    for cost in [
        (shipping, "Envío"),
        (packaging, "Empaque"),
        (service_fee, "Servicio"),
    ]:
        if cost[0]:
            summary_p += f"{cost[1]}: ${round(cost[0], 2)}\n"
    for disc in [(discounts, "Descuentos")]:
        if disc[0]:
            summary_p += f"{disc[1]}: -${round(disc[0], 2)}\n"
    summary_p += f"*Total: ${round(total, 2) if total else '-'}*\n"
    return {
        "summary": summary_p,
        "products": table_p,
    }


def send_supplier_whatsapp_confirmation(
    to_wa: Dict[str, str],
    orden_details: OrdenDetails,
    branch_name: str,
    contact_number: str,
    delivery_address: str,
    cart_products: List[CartProductGQL],
    notification_type: str = "new_orden",
) -> bool:
    """Send email confirmation to customer / supplier

    Parameters
    ----------
    to_wa : Dict[str,str]
        ie {"phone": "5215555555555", "name": "Alima"}
    orden_details : OrdenDetails
    branch_name : str
    contact_number : str
    delivery_address : str
    cart_products : List[CartProductGQL]

    Returns
    -------
    bool
        True if whatsapp was sent, False otherwise
    """
    # WA template new: alima_compras_notif_proveedor_new_orden_link
    # WA template update: alima_compras_notif_proveedor_update_orden_link
    template_id = (
        "8a6d0a79-8502-4466-ac24-e06ac75ed555"
        if notification_type == "new_orden"
        else "3de99044-1629-43f5-a8cc-e2c0985292f3"
    )
    if notification_type == "new_orden":
        template_vars = [
            f"nuevo ({str(orden_details.orden_id)[:10]})",
            branch_name,
            f"{orden_details.delivery_date.isoformat()}",  # type: ignore
            f"{str(orden_details.delivery_time)}hrs",
            contact_number,
            f"{str(orden_details.orden_id)}",
        ]
    else:
        template_vars = [
            f"({str(orden_details.orden_id)[:10]})",
            branch_name,
            f"{orden_details.delivery_date.isoformat()}",  # type: ignore
            f"{str(orden_details.delivery_time)}hrs",
            f"={str(orden_details.orden_id)}",
        ]
    # call api
    resp = wa_sender.send_message(
        to_wa["phone"],
        template_id,
        template_vars,
    )
    if not resp:
        return False
    return "id" in resp and "conversation" in resp


async def send_restaurant_email_confirmation(
    subject: str,
    from_email: Dict[str, str],
    to_email: Dict[str, str],
    orden_details: OrdenDetails,
    cart_products: List[CartProductGQL],
) -> bool:
    """Send email confirmation to customer / supplier

    Parameters
    ----------
    from_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    orden_details : OrdenDetails
    cart_products : List[CartProductGQL]

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    prod_table = await cart_to_html_table(
        cart_products,
        orden_details.subtotal,
        orden_details.tax,
        orden_details.subtotal_without_tax,
        orden_details.total,
        orden_details.shipping_cost,
        orden_details.packaging_cost,
        orden_details.service_fee,
        orden_details.discount,
    )
    msg_file = app_path / "views" / "mails" / "customer_order_confirmation.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("DISPLAYNAME", to_email.get("name", ""))
        .replace(
            "FECHADEENTREGA",
            (
                orden_details.delivery_date.isoformat()
                if orden_details.delivery_date
                else ""
            ),
        )
        .replace("TABLADEPRODUCTOS", prod_table)
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
        from_email=from_email,
    )


async def send_unformat_restaurant_email_confirmation(
    subject: str,
    from_email: Dict[str, str],
    to_email: Dict[str, str],
    orden_details: OrdenDetails,
    cart_products: List[CartProductGQL],
    orden_number: int,
    rest_branch_name: str,
    cel_contact: str,
) -> bool:
    """Send email confirmation to customer / supplier

    Parameters
    ----------
    from_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    orden_details : OrdenDetails
    cart_products : List[CartProductGQL]

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    prod_table = await cart_to_html_table(
        cart_products,
        orden_details.subtotal,
        orden_details.tax,
        orden_details.subtotal_without_tax,
        orden_details.total,
        orden_details.shipping_cost,
        orden_details.packaging_cost,
        orden_details.service_fee,
        orden_details.discount,
    )
    msg_file = (
        app_path / "views" / "mails" / "restaurant_order_creation_confirmation.html"
    )
    msg_content = (
        msg_file.open()
        .read()
        .replace("SUPPLIER_BUSINESS_NAME", from_email.get("name", ""))
        .replace(
            "APPLINKREF",
            f"https://app.alima.la/ext/supplier/purchase-order?ordenId={str(orden_details.orden_id)}",
        )
        .replace("RESTAURANT_BRANCH_NAME", rest_branch_name)
        .replace("ORDEN_NUMBER", str(orden_number))
        .replace(
            "FECHADEENTREGA",
            (
                orden_details.delivery_date.isoformat()
                if orden_details.delivery_date
                else ""
            ),
        )
        .replace("HTML_TABLE", prod_table)
        .replace("CONTACT_CEL", cel_contact)
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
        from_email=from_email,
    )


async def send_ecommerce_restaurant_email_confirmation(
    seller_name: str,
    subject: str,
    from_email: Dict[str, str],
    to_email: Dict[str, str],
    orden_details: OrdenDetails,
    cart_products: List[CartProductGQL],
) -> bool:
    """Send email confirmation to customer / supplier

    Parameters
    ----------
    from_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    to_email : Dict[str,str]
        ie {"email": SENDGRID_SINGLE_SENDER, "name": "Alima"}
    orden_details : OrdenDetails
    cart_products : List[CartProductGQL]

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    prod_table = await cart_to_html_table(
        cart_products,
        orden_details.subtotal,
        orden_details.tax,
        orden_details.subtotal_without_tax,
        orden_details.total,
        orden_details.shipping_cost,
        orden_details.packaging_cost,
        orden_details.service_fee,
        orden_details.discount,
    )
    msg_file = app_path / "views" / "mails" / "ecommerce_order_confirmation.html"
    msg_content = (
        msg_file.open()
        .read()
        .replace("DISPLAYNAME", to_email.get("name", ""))
        .replace(
            "FECHADEENTREGA",
            (
                orden_details.delivery_date.isoformat()
                if orden_details.delivery_date
                else ""
            ),
        )
        .replace("SELLERNAME", seller_name)
        .replace("TABLADEPRODUCTOS", prod_table)
    )
    return await send_email(
        email_to=to_email["email"],
        subject=subject,
        content=msg_content,
        from_email=from_email,
    )


def send_supplier_whatsapp_invoice_reminder(
    to_wa: Dict[str, str],
    orden_details: OrdenDetails,
    branch_name: str,
) -> bool:
    """Send whatsapp reminder to supplier

    Parameters
    ----------
    to_wa : Dict[str,str]
        ie {"phone": "5215555555555", "name": "Alima"}
    orden_details : OrdenDetails
    branch_name : str

    Returns
    -------
    bool
        True if whatsapp was sent, False otherwise
    """
    try:
        # WA template new: alima_compras_notif_proveedor_upload_invoice_link
        template_id = "f5f3e7e6-be13-4601-9177-fd1affbd1473"
        template_vars = [
            f"({str(orden_details.orden_id)[:10]})",
            branch_name,
            f"{orden_details.delivery_date.isoformat()}",  # type: ignore
            f"{str(orden_details.delivery_time)}hrs",
            f"={str(orden_details.orden_id)}",
        ]
        # call api
        resp = wa_sender.send_message(
            to_wa["phone"],
            template_id,
            template_vars,
        )
        if not resp:
            return False
        return "id" in resp and "conversation" in resp
    except Exception as e:
        logger.warning("Error sending whatsapp invoice reminder")
        logger.error(e)
        return False


####################
# Authos Notifications
####################


async def send_authos_email_restore_password_token(
    seller_name: str,
    to_email: str,
    restore_token: str,
    url: str,
    email_template: Optional[str] = None,
) -> bool:
    """Send email with link and temporal token to restore password

    Parameters
    ----------
    seller_name : str
        Seller Business name
    to_email : str
        email to send
    restore_token : str
        temporal token
    url : str
        url to redirect
    email_template : str
        email template to use

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    try:
        if email_template is None:
            email_template = "authos_generic_password_restore.html"
        msg_file = app_path / "views" / "mails" / email_template
        msg_content = (
            msg_file.open()
            .read()
            .replace("ECOMM_SELLER_RESTORE_URL", f"{url}?restore_token={restore_token}")
            .replace(
                "ECOMM_SELLER_NAME",
                seller_name,
            )
        )
        return await send_email(
            email_to=to_email,
            subject=f"{seller_name} - Restaurar contraseña",
            content=msg_content,
            from_email={
                "email": SENDGRID_SINGLE_SENDER,
                "name": seller_name,
            },
        )
    except Exception as e:
        logger.warning("Error sending authos email restore password")
        logger.error(e)
        return False


async def send_authos_email_welcome(
    seller_name: str,
    to_email: Dict[str, str],
    ref_url: str,
    email_template: Optional[str] = None,
) -> bool:
    """Send email with a welcome message

    Parameters
    ----------
    seller_name : str
        Seller Business name
    to_email : Dict[str,str]
        email to send  - {email:'', 'name', ''}
    email_template : str
        email template to use

    Returns
    -------
    bool
        True if email was sent, False otherwise
    """
    try:
        if email_template is None:
            email_template = "authos_generic_welcome_message.html"
        msg_file = app_path / "views" / "mails" / email_template
        msg_content = (
            msg_file.open()
            .read()
            .replace(
                "ECOMM_SELLER_NAME",
                seller_name,
            )
            .replace(
                "ECOMM_BUYER_NAME",
                to_email.get("name", ""),
            )
            .replace(
                "ECOMM_REDIRECT_URL",
                ref_url,
            )
        )
        return await send_email(
            email_to=to_email["email"],
            subject=f"¡Bienvenido a {seller_name}!",
            content=msg_content,
            from_email={
                "email": SENDGRID_SINGLE_SENDER,
                "name": seller_name,
            },
        )
    except Exception as e:
        logger.warning("Error sending authos email welcome")
        logger.error(e)
        return False
