from enum import Enum
from typing import Any

import strawberry


@strawberry.enum
class GQLApiErrorCodeType(Enum):
    # SQL
    INSERT_SQL_DB_ERROR = 1001  # Error inserting data record in SQL DB
    DELETE_SQL_DB_ERROR = 1002  # Error deleting record in SQL DB
    UPDATE_SQL_DB_ERROR = 1003  # Error updating record in SQL DB
    FETCH_SQL_DB_ERROR = 1004  # Error fetch record in SQL DB
    FETCH_SQL_DB_NOT_FOUND = 1005  # Fetched record not found
    FETCH_SQL_DB_EMPTY_RECORD = 1006  # Fetched empty record
    FETCH_SQL_DB_EXISTING_RECORD = 1007  # Fetched existing record
    EXECUTE_SQL_DB_ERROR = 1008  # Error executing SQL DB
    CONNECTION_SQL_DB_ERROR = 1010  # Error to connect SQL DB
    INVALID_SQL_DB_OPERATION = 1011  # Invalid SQL DB operation
    # Data Validation
    DATAVAL_WRONG_DATATYPE = (
        2001  # Sent Argument does not correspond to correct data type
    )
    DATAVAL_NO_DATA = 2002  # Sent Empty arguments
    DATAVAL_DUPLICATED = 2003  # Sent duplicated arguments
    DATAVAL_NO_MATCH = 2004
    # mongoDB
    INSERT_MONGO_DB_ERROR = 3001  # Error inserting data record in Mongo DB
    DELETE_MONGO_DB_ERROR = 3002  # Error deleting record in Mongo DB
    UPDATE_MONGO_DB_ERROR = 3003  # Error updating record in Mongo DB
    FETCH_MONGO_DB_ERROR = 3004  # Error fetch record in Mongo DB
    FETCH_MONGO_DB_EMPTY_RECORD = 3005  # Fetched empty record
    RECORD_ALREADY_EXIST = 2006  # Error record already exist
    CONNECTION_MONGO_DB_ERROR = 2010  # Error to connect mongo DB
    # xlsx
    WRONG_COLS_FORMAT = 4001  # Error in columns format
    EMPTY_DATA = 4002  # Error empty data
    WRONG_DATA_FORMAT = 4003  # Error in data format
    # xml and pdf
    WRONG_XML_FORMAT = 5001  # Error in xml format
    # Firebase
    INSERT_FIREBASE_DB_ERROR = 6001  # Error inserting data record in Firebase Service
    # GENERIC
    UNEXPECTED_ERROR = 9999  # Unexpected error
    # Facturama
    FACTURAMA_NO_VALID_DATA = 7001
    FACTURAMA_ERROR_BUILD = 7002  # Error to build info for facturama
    FACTURAMA_FETCH_ERROR = 7003  # Error to fetch info from facturama
    FACTURAMA_NEW_CUSTOMER_ERROR = 7004  # Error to create new customer in facturama
    FACTURAMA_DELETE_ERROR = 7005  # Error to fetch info from facturama
    FACTURAMA_WRONG_INVOICE_TAX = 7006  # Error to fetch info from facturama
    FACTURAMA_NO_TAX_INVOICE_DATA = 7007  # Error to fetch info from facturama
    FACTURAMA_TAX_NO_MATCH_WITH_ORDEN = 7008  # Error to fetch info from facturama
    # Business Logic
    SUPPLIER_NOT_ACTIVE = 8001  # Supplier not active in Alima Seller
    SUPPLIER_BUSINESS_NO_PERMISSIONS = 8002  # Supplier Business has no permissions
    # Cloudinary
    INSERT_CLOUDINARY_DB_ERROR = 10001
    # Authos
    AUTHOS_ERROR_CREATING_SESSION = 11001
    AUTHOS_ERROR_UPDATING_SESSION = 11002
    AUTHOS_ERROR_DECODE_JWT = 11003
    AUTHOS_ERROR_TABLE_NOT_FOUND = 11004
    AUTHOS_ERROR_INVALID_SESSION = 11005
    AUTHOS_ERROR_EMAIL_ALREADY_REGISTERED = 11006
    AUTHOS_ERROR_CREATING_ECOMM_USER = 11007
    AUTHOS_ERROR_ELEMENT_NOT_FOUND = 11008
    AUTHOS_ERROR_WRONG_PASSWORD = 11009
    AUTHOS_ERROR_CREATING_RESTORE = 11010
    AUTHOS_ERROR_INVALID_RESTORE = 11011
    AUTHOS_ERROR_USER_ALREADY_LOGGED = 11012
    # SCORPION
    SCORPION_TOKEN_ERROR = 12001
    SCORPION_INSERT_ORDEN_ERROR = 12002
    # STRIPE
    STRIPE_ERROR_SETUP_INTENT = 13001
    STRIPE_ERROR_CREATE_USER = 13002


class GQLApiException(Exception):
    msg: str
    error_code: Any  # GQLApiErrorCode

    def __init__(self, msg: str, error_code: Any, *args: object) -> None:
        super().__init__(*args)
        self.msg = msg
        self.error_code = error_code

    def __str__(self) -> str:
        return f"{self.msg} ({self.error_code})"


def error_code_decode(value: int, lang: str = "es") -> str:
    return {
        5001: "Error en el formato del XML",
        4003: "Error de formato de datos",
        4002: "Error no se encontraron datos",
        4001: "Error, el formato de columnas esta mal",
        1001: "Error al insertar los datos",
        1002: "Error al borrar los datos ",
        1003: "Error al actualizar los datos",
        1004: "Error al buscar los datos",
        1005: "Error, no se encontraron los datos solicitados",
        1006: "Error, datos nulos",
        1007: "Error ya existe ese dato registrado",
        1010: "Error al conectar a la base de datos",
        2001: "Error, argumentos no corresponden con el tipo de dato",
        2002: "Error, hacen falta datos necesarios",
        3001: "Error al insertar los datos",
        3002: "Error al borrar los datos ",
        3003: "Error al actualizar los datos",
        3004: "Error al buscar los datos",
        3005: "Error, no se encontraron los datos solicitados",
        3006: "Error ya existe ese dato registrado",
        3010: "Error al conectar a la base de datos",
    }.get(value, "Error")
