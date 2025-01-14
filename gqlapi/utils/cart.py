from typing import Any, Dict, List
from gqlapi.domain.interfaces.v2.orden.cart import CartProductGQL


def calculate_subtotal_without_tax(
    cart_products: List[CartProductGQL],
) -> Dict[Any, Any]:
    """Calculate subtotal without tax

    Parameters
    ----------
    cart_products : List[CartProductGQL]

    Returns
    -------
    Dict[Any, Any]
        {
            "tax": float,
            "subtotal": float,
            "subtotal_without_tax": float,
        }
    """
    tax = 0
    subtotal = 0
    for cart_product in cart_products:
        if cart_product.subtotal and cart_product.supp_prod:
            tax += cart_product.subtotal * cart_product.supp_prod.tax
            subtotal += cart_product.subtotal
            if cart_product.supp_prod.mx_ieps:
                tax += cart_product.subtotal * cart_product.supp_prod.mx_ieps
    subtotal_without_tax = subtotal - tax

    return {
        "tax": tax,
        "subtotal": subtotal,
        "subtotal_without_tax": subtotal_without_tax,
    }
