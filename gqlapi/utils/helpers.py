import json
import base64
import logging
import secrets
from typing import Any, Dict, List
from uuid import UUID
import string
import unicodedata

from gqlapi.domain.models.v2.utils import UOMType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


async def serialize_encoded_file(file: Any) -> str:
    """Serialize a file to a base64 encoded string

    Parameters
    ----------
    file : Any
        strawberry.Upload or starlette.datastructures.UploadFile

    Returns
    -------
    str
        JSON string with the filename, mimetype and content of the file
    """
    f_content = await file.read()
    return json.dumps(
        {
            "filename": file.filename,
            "mimetype": file.content_type,
            "content": base64.b64encode(f_content).decode(),
        }
    )


async def deserialize_encoded_file(file: str) -> Dict[str, Any]:
    """Deserialize a file from a base64 encoded string

    Parameters
    ----------
    file : str
        JSON string with the filename, mimetype and content of the file

    Returns
    -------
    Dict[str, Any]
        Dictionary with the filename, mimetype and content of the file
    """
    f = json.loads(file)
    return f


def list_into_strtuple(lis: List[UUID] | List[str]) -> str:
    """Converts a list into a tuple of strings

    Parameters
    ----------
    lis : list
        List of strings

    Returns
    -------
    str
        Tuple formated as string
    """
    _t = tuple([str(i) for i in lis])
    if len(_t) == 1:
        return f"('{_t[0]}')"
    return str(_t)


def phone_format(phone_number: str) -> str:
    """Formats a phone number to a 10 digit string

    Parameters
    ----------
    phone_number : str

    Returns
    -------
    str
    """
    phone_number = str(phone_number).replace(" ", "")
    if len(phone_number) == 10:
        return phone_number
    if phone_number.startswith("52"):
        phone_number = phone_number[2:]
    return phone_number


def price_format(price: str | int | float) -> float:
    """Formats a price to a float with 2 decimals

    Parameters
    ----------
    price : str | int | float

    Returns
    -------
    float

    Raises
    ------
    GQLApiException
    """
    try:
        if isinstance(price, str):
            if price.startswith("$"):
                price = price[1:]
            price = price.replace(" ", "")
            if "," in price:
                price = price.replace(",", "")
            price = float(price)  # type: ignore
        price = round(price, 2)  # type: ignore
        return price  # type: ignore
    except Exception as e:
        logging.error(e)
        raise GQLApiException(
            error_code=GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            msg="Formato incorrecto de precio",
        )


def format_price_to_float(price: str | int | float) -> float:
    """Formats a price to a float with 2 decimals

    Parameters
    ----------
    price : str | int | float

    Returns
    -------
    float

    Raises
    ------
    GQLApiException
    """
    try:
        if isinstance(price, str):
            if price.startswith("$"):
                price = price[1:]
            price = price.replace(" ", "")
            if "," in price:
                price = price.replace(",", "")
            price = float(price)  # type: ignore
        price = round(price, 2)  # type: ignore
        return price  # type: ignore
    except Exception:
        raise ValueError


def get_min_quantity(sell_unit: UOMType) -> float:
    """Returns the minimum quantity for a product

    Parameters
    ----------
    sell_unit : UOMType

    Returns
    -------
    float
    """
    if sell_unit == UOMType.KG:
        return 0.1
    else:
        return 1


def serialize_product_description(description: str, unit: UOMType) -> str:
    """Serializes a product description with unit of measure
        - For description:
            - set everything to lowercase
            - convert spaces to underscores
            - remove accents
            - remove special characters
            - remove parenthesis
        - For unit of measure:
            - convert to lowercase
        - Concat both with underscore

    Parameters
    ----------
    description : str
    unit : UOMType

    Returns
    -------
    str
    """
    # description transform, remove parenthesis and spaces
    _des = description.lower().replace(" ", "_").replace("(", "").replace(")", "")
    # use string or unicode module to remove accents
    all_chars = string.ascii_letters + string.digits + "_"
    f_des = "".join(c for c in unicodedata.normalize("NFD", _des) if c in all_chars)
    # unit transform
    _unit = unit.value.lower()
    # return
    return f"{f_des}_{_unit}"


def generate_random_password(pwd_length: int = 10) -> str:
    """Generates a random password

    Parameters
    ----------
    pwd_length : int, optional
        Length of the password, by default 10

    Returns
    -------
    str
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    pwd_length = 10
    pwd: str = ""
    for i in range(pwd_length):
        pwd += "".join(secrets.choice(alphabet))
    return pwd


def generate_secret_key() -> str:
    # create a truly random string of 8 characters
    return secrets.token_urlsafe(8).replace("-", "").lower()
