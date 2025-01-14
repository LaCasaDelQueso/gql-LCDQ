import logging
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID

from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from gqlapi.domain.models.v2.utils import NotificationChannelType
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


class MockSupplierBusinessRepository(SupplierBusinessRepositoryInterface):
    def new(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> SupplierBusiness:
        """post new supplier business

        Parameters
        ----------
        name : str,
            name of supplier bussines
        country : str,
            country of supplier business
        notification_preference : NotificationChannelType
            email, whatsapp or sms

        Raises
        -------
        GQLApiException

        Returns
        -------
        SupplierBusiness
        """

        if name == "error":
            raise GQLApiException(
                msg="Error creating supplier business",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR,
            )
        try:
            return SupplierBusiness(
                id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
                name=name,
                country=country,
                active=True,
                notification_preference=notification_preference,
            )
        except Exception as e:
            logging.error(e)
            logging.warning("Issues creating new supplier business")
            raise GQLApiException(
                msg="Error creating supplier business",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR,
            )

    def update(
        self,
        id: UUID,
        name: Optional[str] = "",
        country: Optional[str] = "",
        notification_preference: Optional[
            NotificationChannelType
        ] = NotificationChannelType.SMS,
    ) -> bool:
        """update existing supplier business

        Parameters
        ----------
        info : StrawberryInfo
            _description_
        name : str, optional
            name of supplier bussines
        country : str, optional
            country of supplier business
        notification_preference : NotificationChannelType, optional
            email, whatsapp or sms

        Returns
        -------
        bool
        """
        if name != "error":
            return True
        if name == "false":
            return False
        else:
            raise GQLApiException(
                msg="Error updating supplier business",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR,
            )

    def get(self, id: UUID) -> SupplierBusiness:  # type: ignore
        """get supplier business

        Parameters
        ----------
        info : StrawberryInfo
            _description_
        id : uuid,
            primary key of supplier bussines
        Returns
        -------
        SupplierBusiness
        """

        try:
            resp = {
                "id": UUID("ca949b23-a0dd-4797-a389-ca239618ad5c"),
                "name": "Jordan",
                "country": "EUA",
                "active": True,
                "notification_preference": "sms",
            }
        except Exception as e:
            logging.error(e)
            logging.warning("Issues fetch supplier business")
            raise GQLApiException(
                msg="Get Supplier business account",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_ERROR,
            )
        if id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da167e"):
            logging.warning("Issues fetch supplier business (empty)")
            raise GQLApiException(
                msg="Get Supplier business account null",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD,
            )

        return SupplierBusiness(**resp)

    async def exists(self, id: UUID) -> NoneType:
        raise NotImplementedError

    async def exist(self, id: UUID) -> NoneType:
        raise NotImplementedError

    async def search(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[SupplierBusiness]:
        raise NotImplementedError

    async def add(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> UUID:
        raise NotImplementedError

    async def edit(
        self,
        id: UUID,
        name: Optional[str] = "",
        country: Optional[str] = "",
        notification_preference: Optional[
            NotificationChannelType
        ] = NotificationChannelType.SMS,
    ) -> bool:
        raise NotImplementedError

    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    async def find(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


# class MockSupplierBusinessAccountRepository(SupplierBusinessAccountRepositoryInterface):
#     def __init__(self) -> None:
#         pass

#     async def upload_new_supplier_business_account(
#         self,
#         supplier_business_id: UUID,
#         legal_rep_name: str,
#         legal_rep_id: str,
#         legal_address: str,
#         business_type: Optional[BusinessType] = None,
#         incorporation_file: Optional[Upload] = None,
#         phone_number: Optional[str] = None,
#         email: Optional[str] = None,
#         website: Optional[str] = None,
#         mx_sat_regimen: Optional[str] = None,
#         mx_sat_rfc: Optional[str] = None,
#         mx_sat_csf: Optional[Upload] = None,
#         default_commercial_conditions: Optional[SupplierBusinessMongoCommertialConditions] = None,
#         displays_in_marketplace: Optional[bool] = None,
#         employee_directory: Optional[List[EmployeeInfo]] = None
#     ) -> SupplierBusinessAccount:  # type: ignore
#         """post new supplier business account legal info in mongo db

#         Parameters
#         ----------
#         info : StrawberryInfo
#             _description_
#         supplier_business_id : UUID,
#             id of supplier business in postgresql db
#         legal_rep_name : str,
#             name of the legal representative
#         legal_rep_id : str
#             id of the legal representative (CURP in México)
#         legal_address : str
#             address of the legal representative (CURP in México)

#         Raises
#         -------
#         GQLApiException

#         Returns
#         -------
#         SupplierBusinessAccount
#         """

#         if legal_rep_name == "Error":
#             raise GQLApiException(
#                 msg="Error creating supplier business account",
#                 error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
#             )
#         try:
#             internal_values = {
#                 "supplier_business_id": supplier_business_id,
#                 "legal_rep_name": legal_rep_name,
#                 "legal_rep_id": legal_rep_id,
#                 "legal_address": legal_address,
#             }
#             return SupplierBusinessAccount(**internal_values)

#         except Exception as e:
#             logging.error(e)
#             logging.warning("Issues creating new supplier business account legal info")
#             raise GQLApiException(
#                 msg="Error creating supplier business account legal info",
#                 error_code=GQLApiErrorCodeType.INSERT_MONGO_DB_ERROR.value,
#             )

#     async def update_supplier_business_account(
#         self,
#         supplier_business_id: UUID,
#         legal_rep_name: Optional[str] = None,
#         legal_rep_id: Optional[Upload] = None,
#         legal_address: Optional[str] = None,
#         business_type: Optional[BusinessType] = None,
#         incorporation_file: Optional[Upload] = None,
#         phone_number: Optional[str] = None,
#         email: Optional[str] = None,
#         website: Optional[str] = None,
#         mx_sat_regimen: Optional[str] = None,
#         mx_sat_rfc: Optional[str] = None,
#         mx_sat_csf: Optional[Upload] = None,
#         default_commercial_conditions: Optional[SupplierBusinessMongoCommertialConditions] = None,
#         displays_in_marketplace: Optional[bool] = None,
#         employee_directory: Optional[List[EmployeeInfo]] = None
#     ) -> bool:
#         """edit supplier business account legal info in mongo db

#         Parameters
#         ----------
#         info : StrawberryInfo
#             _description_
#         supplier_business_id : UUID,
#             id of supplier business in postgresql db
#         legal_rep_name : str, optional
#             name of the legal representative
#         legal_rep_id : str, Optional
#             id of the legal representative (CURP in México)
#         legal_address : str, Optiona
#             address of the legal representative (CURP in México)

#         Raises
#         -------
#         GQLApiException

#         Returns
#         -------
#         bool
#         """

#         internal_values: Dict[str, Any] = {"supplier_business_id": supplier_business_id}
#         if legal_rep_name == "Error":
#             raise GQLApiException(
#                 msg="Error updating supplier business account legal info",
#                 error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
#             )
#         try:
#             if legal_rep_name:
#                 internal_values["legal_rep_name"] = legal_rep_name
#             if legal_address:
#                 internal_values["legal_address"] = legal_address
#             if legal_rep_id:
#                 internal_values["legal_rep_id"] = legal_rep_id
#             if business_type:
#                 internal_values["business_type"] = business_type.value
#             if incorporation_file:
#                 internal_values["incorporation_file"] = incorporation_file
#             if mx_sat_regimen:
#                 internal_values["mx_sat_regimen"] = mx_sat_regimen
#             if mx_sat_rfc:
#                 internal_values["mx_sat_rfc"] = mx_sat_rfc
#             if mx_sat_csf:
#                 internal_values["mx_sat_csf"] = mx_sat_csf
#             if phone_number:
#                 internal_values["phone_number"] = phone_number
#             if email:
#                 internal_values["email"] = email
#             if website:
#                 internal_values["website"] = website
#             if displays_in_marketplace:
#                 internal_values[
#                     "displays_in_marketplace"
#                 ] = displays_in_marketplace
#             if mx_sat_regimen:
#                 internal_values["mx_sat_regimen"] = mx_sat_regimen

#             if internal_values:
#                 internal_values["last_updated"] = datetime.utcnow()
#             else:
#                 return False

#         except Exception as e:
#             logging.error(e)
#             logging.warning("Issues updating supplier business account legal info")
#             raise GQLApiException(
#                 msg="Error updating supplier business account legal info",
#                 error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
#             )
#         return True

#     async def get_supplier_business_account(
#         self, supplier_business_id: UUID
#     ) -> SupplierBusinessAccount:  # type: ignore
#         """get supplier business account legal info of mongo DB

#         Parameters
#         ----------
#         info : StrawberryInfo
#             _description_
#         supplier_business_id : uuid,
#             primary key of supplier bussines
#         Returns
#         -------
#         SupplierBusinessAccount
#         """

#         try:
#             result = [
#                 {
#                     "supplier_business_id": supplier_business_id,
#                     "legal_rep_name": "Error",
#                     "legal_rep_id": "123456789",
#                     "legal_address": "Calle San Mateo",
#                     "business_type": BusinessType.MORAL_PERSON,
#                     "incorporation_file": None,
#                     "phone_number": "554440000",
#                     "email": "fer@alima.la",
#                     "website": "fer.com",
#                     "mx_sat_regimen": "Regimen",
#                     "mx_sat_rfc": "ERFSDSDGSGSDG",
#                     "mx_sat_csf": None,
#                     # default_commercial_conditions: Optional[SupplierBusinessMongoCommercialConditions] = None
#                     "displays_in_marketplace": False,
#                     "employee_directory": [],
#                 }
#             ]
#         except Exception as e:
#             logging.error(e)
#             logging.warning("Issues fetch supplier business account legal info")
#             raise GQLApiException(
#                 msg="Get Supplier business account legal info",
#                 error_code=GQLApiErrorCodeType.FETCH_MONGO_DB_ERROR.value,
#             )
#         if id == UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"):
#             logging.warning("Issues fetch supplier business (empty)")
#             raise GQLApiException(
#                 msg="Get Supplier business null",
#                 error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD,
#             )

#         return SupplierBusinessAccount(**result[0])
