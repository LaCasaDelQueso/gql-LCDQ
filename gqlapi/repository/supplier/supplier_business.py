from types import NoneType
from typing import Any, Dict, List, Optional
from datetime import datetime
import uuid
from uuid import UUID
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from strawberry.file_uploads import Upload
from bson.binary import Binary

from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.domain.models.v2.core import SupplierEmployeeInfo
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessRepositoryInterface,
    SupplierBusinessAccountRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import (
    MinimumOrderValue,
    SupplierBusiness,
    SupplierBusinessAccount,
    SupplierBusinessCommertialConditions,
)
from gqlapi.domain.models.v2.utils import (
    BusinessType,
    NotificationChannelType,
    OrderSize,
    PayMethodType,
    SupplierBusinessType,
)
from gqlapi.repository import CoreMongoRepository, CoreRepository
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain

logger = get_logger(get_app())


class SupplierBusinessRepository(CoreRepository, SupplierBusinessRepositoryInterface):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> UUID:
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

        internal_values = {
            "id": uuid.uuid4(),
            "name": name,
            "country": country,
            "active": False,  # with an onboarded & active account in Alima
            "notification_preference": notification_preference.value,
        }

        await super().new(
            core_element_tablename="supplier_business",
            core_element_name="Supplier Business",
            core_query="""INSERT INTO
            supplier_business (
                id,
                name,
                country,
                active,
                notification_preference)
                VALUES (
                    :id,
                    :name,
                    :country,
                    :active,
                    :notification_preference)
            """,
            # validate_by="name",
            # validate_against=name,
            core_values=internal_values,
        )
        return internal_values["id"]

    async def add(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> UUID:
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

        internal_values = {
            "id": uuid.uuid4(),
            "name": name,
            "country": country,
            "active": False,  # with an onboarded & active account in Alima
            "notification_preference": notification_preference.value,
        }

        await super().add(
            core_element_tablename="supplier_business",
            core_element_name="Supplier Business",
            core_query="""INSERT INTO
            supplier_business (
                id,
                name,
                country,
                active,
                notification_preference)
                VALUES (
                    :id,
                    :name,
                    :country,
                    :active,
                    :notification_preference)
            """,
            core_values=internal_values,
        )
        return internal_values["id"]

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
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

        atributes = []
        values_view: Dict[str, Any] = {"id": id}

        if name:
            atributes.append(" name=:name")
            values_view["name"] = name
        if country:
            atributes.append(" country = :country")
            values_view["country"] = country
        if notification_preference:
            values_view["notification_preference"] = notification_preference.value
            atributes.append(" notification_preference= :notification_preference")

        if len(atributes) == 0:
            logger.warning("No attributes to update in supplier business")
            return False
        else:
            atributes.append(" last_updated=:last_updated")
            values_view["last_updated"] = datetime.utcnow()

        query = f"""UPDATE supplier_business
                            SET {','.join(atributes)}
                            WHERE id=:id;
                        """
        await super().update(
            core_element_name="Supplier Business",
            core_query=query,
            core_values=values_view,
        )
        return True

    async def edit(
        self,
        id: UUID,
        name: Optional[str] = "",
        country: Optional[str] = "",
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        logo_url: Optional[str] = None,
    ) -> bool:
        """update existing supplier business

        Parameters
        ----------
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

        atributes = []
        values_view: Dict[str, Any] = {"id": id}
        if name:
            atributes.append(" name=:name")
            values_view["name"] = name
        if isinstance(active, bool):
            atributes.append(" active=:active")
            values_view["active"] = active
        if country:
            atributes.append(" country = :country")
            values_view["country"] = country
        if notification_preference:
            values_view["notification_preference"] = notification_preference.value
            atributes.append(" notification_preference= :notification_preference")
        if logo_url:
            values_view["logo_url"] = logo_url
            atributes.append(" logo_url= :logo_url")

        if len(atributes) == 0:
            logger.warning("No attributes to update in supplier business")
            return False
        else:
            atributes.append(" last_updated=:last_updated")
            values_view["last_updated"] = datetime.utcnow()

        query = f"""UPDATE supplier_business
                    SET {','.join(atributes)}
                    WHERE id=:id;
                """
        return await super().edit(
            core_element_name="Supplier Business",
            core_query=query,
            core_values=values_view,
        )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(self, id: UUID) -> Dict[Any, Any]:  # type: ignore
        """get supplier business

        Parameters
        ----------
        id : uuid,
            primary key of supplier bussines
        Returns
        -------
        SupplierBusiness
        """

        _data = await super().get(
            id=id,
            core_element_tablename="supplier_business",
            core_element_name="Supplier Business",
            core_columns="*",
        )

        return sql_to_domain(_data, SupplierBusiness)

    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        """Fetch supplier business

        Parameters
        ----------
        id : uuid,
            primary key of supplier bussines
        Returns
        -------
        SupplierBusiness
        """

        _data = await super().fetch(
            id=id,
            core_element_tablename="supplier_business",
            core_element_name="Supplier Business",
            core_columns="*",
        )
        if not _data:
            return {}
        return sql_to_domain(_data, SupplierBusiness)

    @deprecated("Use exists() instead", "gqlapi.repository")
    async def exist(self, id: UUID) -> NoneType:  # type: ignore
        """Validate supplier business exists

        Args:
            id (UUID): unique supplier business id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=id,
            core_element_tablename="supplier_business",
            core_element_name="Supplier Business",
            id_key="id",
            core_columns="id",
        )

    async def exists(self, id: UUID) -> bool:
        """Validate supplier business exists

        Args:
            id (UUID): unique supplier business id

        Returns:
            NoneType: None
        """
        return await super().exists(
            id=id,
            core_element_tablename="supplier_business",
            core_element_name="Supplier Business",
            id_key="id",
            core_columns="id",
        )

    @deprecated("Use find() instead", "domain")
    async def search(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[SupplierBusiness]:
        supp_bus_atributes = []
        supp_bus_values_view = {}
        if search:
            supp_bus_atributes.append(
                " exists (select 1 from unnest(keywords) keys where keys ILIKE :search ) and"
            )
            supp_bus_values_view["search"] = (
                "%" + "".join(filter(str.isalnum, search.lower())) + "%"
            )
        if name:
            supp_bus_atributes.append(" name=:name and")
            supp_bus_values_view["name"] = name
        if country:
            supp_bus_atributes.append(" country=:country and")
            supp_bus_values_view["country"] = country
        if notification_preference:
            supp_bus_atributes.append(
                " notification_preference_type=:notification_preference and"
            )
            supp_bus_values_view["notification_preference"] = (
                notification_preference.value
            )
        if id:
            supp_bus_values_view["id"] = id
            supp_bus_atributes.append(" id=:id and")
        if isinstance(active, bool):
            supp_bus_values_view["active"] = active
            supp_bus_atributes.append(" active=:active and")

        if len(supp_bus_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(supp_bus_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await super().search(
            core_element_name="Supplier Business",
            core_element_tablename="""supplier_business""",
            filter_values=filter_values,
            core_columns=["*"],
            values=supp_bus_values_view,
        )
        category_dir = []
        for r in _resp:
            rest_branch = SupplierBusiness(**sql_to_domain(r, SupplierBusiness))
            category_dir.append(rest_branch)
        return category_dir

    async def find(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        #
        supp_bus_atributes = []
        supp_bus_values_view = {}
        for k in [
            "id",
            "name",
            "country",
            "notification_preference",
            "active",
            "search",
        ]:
            v = locals()[k]
            if not v:
                continue
            # format filters
            _attrs = f" {k}=:{k} "
            if k == "notification_preference":
                _val = v.value
            elif k == "search":
                _attrs = " exists (select 1 from unnest(keywords) keys where keys ILIKE :search ) "
                _val = "%" + "".join(filter(str.isalnum, v.lower())) + "%"
            else:
                _val = v
            # filters accumed
            supp_bus_atributes.append(_attrs)
            supp_bus_values_view[k] = _val

        if len(supp_bus_atributes) == 0:
            filter_values = None
        else:
            filter_values = " AND ".join(supp_bus_atributes)
        # fetch from db
        _resp = await super().find(
            core_element_name="Supplier Business",
            core_element_tablename="supplier_business",
            filter_values=filter_values,
            core_columns=["*"],
            values=supp_bus_values_view,
        )
        return [dict(r) for r in _resp]

    async def delete_image(self, supplier_business_id: UUID) -> bool:
        """update existing supplier business

        Parameters
        ----------
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

        atributes = []
        values_view: Dict[str, Any] = {"id": supplier_business_id}

        atributes.append(" logo_url = NULL")

        if len(atributes) == 0:
            logger.warning("No attributes to update in supplier business")
            return False
        else:
            atributes.append(" last_updated=:last_updated")
            values_view["last_updated"] = datetime.utcnow()

        query = f"""UPDATE supplier_business
                    SET {','.join(atributes)}
                    WHERE id=:id;
                """
        return await super().edit(
            core_element_name="Supplier Business",
            core_query=query,
            core_values=values_view,
        )


class SupplierBusinessAccountRepository(
    CoreMongoRepository, SupplierBusinessAccountRepositoryInterface
):
    @staticmethod
    def deserialize_account(result: Dict[str, Any]) -> SupplierBusinessAccount:
        # decoding bytes to string of stored files
        result["supplier_business_id"] = Binary.as_uuid(result["supplier_business_id"])
        if "legal_rep_id" in result and result["legal_rep_id"]:
            result["legal_rep_id"] = result["legal_rep_id"].decode("utf-8")
        if "incorporation_file" in result and result["incorporation_file"]:
            result["incorporation_file"] = result["incorporation_file"].decode("utf-8")
        if "mx_sat_csf" in result and result["mx_sat_csf"]:
            result["mx_sat_csf"] = result["mx_sat_csf"].decode("utf-8")
        if "business_type" in result and result["business_type"]:
            result["business_type"] = SupplierBusinessType(result["business_type"])
        if (
            "default_commertial_conditions" in result
            and result["default_commertial_conditions"]
        ):
            dconds = result["default_commertial_conditions"]
            try:
                result["default_commertial_conditions"] = (
                    SupplierBusinessCommertialConditions(
                        minimum_order_value=MinimumOrderValue(
                            measure=OrderSize(dconds["minimum_order"]["measure"]),
                            amount=dconds["minimum_order"]["amount"],
                        ),
                        allowed_payment_methods=[
                            PayMethodType(apm)
                            for apm in dconds["allowed_payment_methods"]
                        ],
                        policy_terms=dconds["policy_terms"],
                        account_number=dconds["account_number"],
                    )
                )
            except Exception as e:
                logger.warning(e)
                result["default_commertial_conditions"] = None
        return SupplierBusinessAccount(**result)

    def _serialize_account(self, account: SupplierBusinessAccount) -> Dict[str, Any]:
        # values
        _values = {}
        # data validation
        for k, v in domain_to_dict(
            account, skip=["supplier_business_id", "displays_in_marketplace"]
        ).items():
            # skips None values
            if not v:
                continue
            # binary files
            if k in ["legal_rep_id", "incorporation_file", "mx_sat_csf"]:
                _values[k] = Binary(v.encode("utf-8"))
            # enums
            elif k in ["business_type"]:
                _values[k] = v.value
            # commercial conditions
            elif k in ["default_commertial_conditions"]:
                # min order value
                tmp = {
                    "minimum_order": {
                        "measure": v.minimum_order_value.measure.value,
                        "amount": v.minimum_order_value.amount,
                    },
                    "allowed_payment_methods": [
                        apm.value for apm in v.allowed_payment_methods
                    ],
                    "policy_terms": v.policy_terms,
                    "account_number": v.account_number if v.account_number else "",
                }
                _values[k] = tmp
            else:
                _values[k] = v
        return _values

    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        supplier_business_id: UUID,
        legal_rep_name: Optional[str] = None,
        legal_rep_id: Optional[Upload] = None,
        legal_address: Optional[str] = None,
        business_type: Optional[BusinessType] = None,
        legal_business_name: Optional[str] = None,
        incorporation_file: Optional[Upload] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        mx_sat_regimen: Optional[str] = None,
        mx_sat_rfc: Optional[str] = None,
        mx_sat_csf: Optional[Upload] = None,
        default_commertial_conditions: Optional[
            SupplierBusinessCommertialConditions
        ] = None,
        displays_in_marketplace: Optional[bool] = None,
        employee_directory: Optional[List[SupplierEmployeeInfo]] = None,
    ) -> bool:  # type: ignore
        """upload new supplier business account

        Args:
            supplier_business_id (UUID): unique supplier business id
            legal_rep_name (Optional[str], optional): Name of legal representive. Defaults to "".
            legal_rep_id (Optional[str], optional): ID od legal representive. Defaults to "".
            legal_address (Optional[str], optional): address of Company. Defaults to "".
            business_type (Optional[BusinessType], optional): Relation with Alima. Defaults to BusinessType.PHYSICAL_PERSON.
            legal_business_name: Optional[str] = None
            incorporation_file (Optional[Upload], optional): documents filed with a government body to
                    legally document the creation of a corporation.
            phone_number (Optional[str]), optional): number to contact the supplier
            email (Optional[str], optional): email to contact the supplier
            website: (Optional[str], optional): restaurant website
            mx_sat_regimen: (Optional[str], optional): set of laws governing an activity within a region (mx)
            mx_sat_rfc: (Optional[str], optional): unique alphanumeric key
            mx_sat_csf: (Optional[Upload], optional): document that allows you to know your status as a
                taxpayer before the Tax Administration Service (SAT)
            default_commertial_conditions (Optional[ SupplierBusinessMongoCommertialConditions], optional):
                CommertialConditions model. Defaults to None.
            displays_in_marketplace (Optional[bool], optional): displays_in_marketplace. Defaults to None.
            employee_directory (Optional[EmployeesInfo], optional): employe info list model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate creation is done
        """
        # values
        internal_values = {
            "supplier_business_id": Binary.from_uuid(supplier_business_id),
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }
        # data validation
        if legal_rep_name:
            internal_values["legal_rep_name"] = legal_rep_name
        if legal_rep_id:
            internal_values["legal_rep_id"] = legal_rep_id
        if legal_address:
            internal_values["legal_address"] = legal_address
        if business_type:
            internal_values["business_type"] = business_type.value
        if legal_business_name:
            internal_values["legal_business_name"] = legal_business_name
        if incorporation_file:
            internal_values["incorporation_file"] = incorporation_file
        if mx_sat_regimen:
            internal_values["mx_sat_regimen"] = mx_sat_regimen
        if mx_sat_rfc:
            internal_values["mx_sat_rfc"] = mx_sat_rfc
        if mx_sat_csf:
            internal_values["mx_sat_csf"] = mx_sat_csf
        if phone_number:
            internal_values["phone_number"] = phone_number
        if email:
            internal_values["email"] = email
        if website:
            internal_values["website"] = website
        if displays_in_marketplace:
            internal_values["displays_in_marketplace"] = True
        else:
            internal_values["displays_in_marketplace"] = False
        if mx_sat_regimen:
            internal_values["mx_sat_regimen"] = mx_sat_regimen

        # employee directory
        # if employee_directory:
        #     self._set_employee_directory(employee_directory, internal_values)
        # default commertial conditions
        # if default_commertial_conditions:
        #     self._set_commercial_conditions(
        #         default_commertial_conditions, internal_values
        #     )

        # execute
        await super().new(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            core_values=internal_values,
            validate_by="supplier_business_id",
            validate_against=supplier_business_id,
        )

        return True

    async def add(
        self,
        supplier_business_id: UUID,
        account: SupplierBusinessAccount,
    ) -> bool:  # type: ignore
        """upload new supplier business account

        Args:
            supplier_business_id (UUID): unique supplier business id
            account (SupplierBusinessAccount): SupplierBusinessAccount model

        Raises:
            GQLApiException

        Returns:
            bool: validate creation is done
        """
        values = self._serialize_account(account)
        # default values
        values.update(
            {
                "supplier_business_id": Binary.from_uuid(supplier_business_id),
                "created_at": datetime.utcnow(),
                "last_updated": datetime.utcnow(),
            }
        )
        # execute
        flag = await super().add(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            core_values=values,
            validate_by="supplier_business_id",
            validate_against=supplier_business_id,
        )

        return True if flag is not None else False

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        supplier_business_id: UUID,
        legal_rep_name: Optional[str] = None,
        legal_rep_id: Optional[Upload] = None,
        legal_address: Optional[str] = None,
        business_type: Optional[BusinessType] = None,
        legal_business_name: Optional[str] = None,
        incorporation_file: Optional[Upload] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        website: Optional[str] = None,
        mx_sat_regimen: Optional[str] = None,
        mx_sat_rfc: Optional[str] = None,
        mx_sat_csf: Optional[Upload] = None,
        default_commertial_conditions: Optional[
            SupplierBusinessCommertialConditions
        ] = None,
        displays_in_marketplace: Optional[bool] = None,
        employee_directory: Optional[List[SupplierEmployeeInfo]] = None,
    ) -> bool:
        """update supplier business account legal info

        Args:
            supplier_business_id (UUID): unique supplier business id
            llegal_rep_name (Optional[str], optional): Name of legal representive. Defaults to "".
            legal_rep_id (Optional[str], optional): ID od legal representive. Defaults to "".
            legal_address (Optional[str], optional): address of Company. Defaults to "".
            business_type (Optional[BusinessType], optional): Relation with Alima. Defaults to BusinessType.PHYSICAL_PERSON.
            legal_business_name: Optional[str] = None
            incorporation_file (Optional[Upload], optional): documents filed with a government body to
                    legally document the creation of a corporation.
            phone_number (Optional[str]), optional): number to contact the supplier
            email (Optional[str], optional): email to contact the supplier
            website: (Optional[str], optional): restaurant website
            mx_sat_regimen: (Optional[str], optional): set of laws governing an activity within a region (mx)
            mx_sat_rfc: (Optional[str], optional): unique alphanumeric key
            mx_sat_csf: (Optional[Upload], optional): document that allows you to know your status as a
                taxpayer before the Tax Administration Service (SAT)
            default_commertial_conditions (Optional[ SupplierBusinessMongoCommertialConditions], optional):
                CommertialConditions model. Defaults to None.
            displays_in_marketplace (Optional[bool], optional): displays_in_marketplace. Defaults to None.
            employee_directory (Optional[EmployeesInfo], optional): employe info list model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        try:
            collection = self.db["supplier_business_account"]
            query = {"supplier_business_id": Binary.from_uuid(supplier_business_id)}
            internal_values = {}
            # data validation
            if legal_rep_name:
                internal_values["legal_rep_name"] = legal_rep_name
            if legal_address:
                internal_values["legal_address"] = legal_address
            if legal_rep_id:
                internal_values["legal_rep_id"] = legal_rep_id
            if business_type:
                internal_values["business_type"] = business_type.value
            if legal_business_name:
                internal_values["legal_business_name"] = legal_business_name
            if incorporation_file:
                internal_values["incorporation_file"] = incorporation_file
            if mx_sat_regimen:
                internal_values["mx_sat_regimen"] = mx_sat_regimen
            if mx_sat_rfc:
                internal_values["mx_sat_rfc"] = mx_sat_rfc
            if mx_sat_csf:
                internal_values["mx_sat_csf"] = mx_sat_csf
            if phone_number:
                internal_values["phone_number"] = phone_number
            if email:
                internal_values["email"] = email
            if website:
                internal_values["website"] = website
            if displays_in_marketplace:
                internal_values["displays_in_marketplace"] = displays_in_marketplace
            if mx_sat_regimen:
                internal_values["mx_sat_regimen"] = mx_sat_regimen
            if internal_values:
                internal_values["last_updated"] = datetime.utcnow()
                new_values = {"$set": internal_values}
                await collection.update_one(query, new_values)
            else:
                logger.warning("No data to update in supplier business account")
        except GQLApiException as ge:
            logger.error(ge)
            logger.warning("Issues updating supplier business account legal info")
            raise GQLApiException(
                msg=ge.msg,
                error_code=ge.error_code,
            )
        except Exception as e:
            logger.error(e)
            logger.warning("Issues updating supplier business account legal info")
            raise GQLApiException(
                msg="Error updating supplier business account legal info",
                error_code=GQLApiErrorCodeType.UPDATE_MONGO_DB_ERROR.value,
            )
        return True

    async def edit(
        self,
        supplier_business_id: UUID,
        account: SupplierBusinessAccount,
    ) -> bool:  # type: ignore
        """update supplier business account

        Args:
            supplier_business_id (UUID): unique supplier business id
            account (SupplierBusinessAccount): SupplierBusinessAccount model

        Raises:
            GQLApiException

        Returns:
            bool: validate update is done
        """
        values = self._serialize_account(account)
        if account.displays_in_marketplace is not None:
            values["displays_in_marketplace"] = account.displays_in_marketplace
        # if no values:
        if not values:
            logger.warning("No data to update in supplier business account")
            return True
        # default values
        values.update(
            {
                "supplier_business_id": Binary.from_uuid(supplier_business_id),
                "last_updated": datetime.utcnow(),
            }
        )
        # do not allow to update created_at
        if "created_at" in values:
            del values["created_at"]
        # execute
        return await super().edit(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            core_values={"$set": values},
            core_query={"supplier_business_id": values["supplier_business_id"]},
        )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(self, supplier_business_id: UUID) -> Dict[Any, Any]:
        """Get supplier business account

        Args:
            supplier_business_id (UUID): unique supplier business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: Supplier Business model dict
        """
        query = {"supplier_business_id": Binary.from_uuid(supplier_business_id)}
        result = await super().get(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            query=query,
        )
        return result

    async def fetch(self, supplier_business_id: UUID) -> Dict[Any, Any] | NoneType:
        """Get supplier business account

        Args:
            supplier_business_id (UUID): unique supplier business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: Supplier Business model dict
        """
        query = {"supplier_business_id": Binary.from_uuid(supplier_business_id)}
        result = await super().fetch(
            core_element_collection="supplier_business_account",
            core_element_name="Supplier Business Account",
            query=query,
        )
        if not result:
            return None
        # decoding bytes to string of stored files
        result["supplier_business_id"] = Binary.as_uuid(result["supplier_business_id"])
        if "legal_rep_id" in result and result["legal_rep_id"]:
            result["legal_rep_id"] = result["legal_rep_id"].decode("utf-8")
        if "incorporation_file" in result and result["incorporation_file"]:
            result["incorporation_file"] = result["incorporation_file"].decode("utf-8")
        if "mx_sat_csf" in result and result["mx_sat_csf"]:
            result["mx_sat_csf"] = result["mx_sat_csf"].decode("utf-8")
        if (
            "default_commertial_conditions" in result
            and result["default_commertial_conditions"]
        ):
            dconds = result["default_commertial_conditions"]
            try:
                result["default_commertial_conditions"] = (
                    SupplierBusinessCommertialConditions(
                        minimum_order_value=MinimumOrderValue(
                            measure=OrderSize(dconds["minimum_order"]["measure"]),
                            amount=dconds["minimum_order"]["amount"],
                        ),
                        allowed_payment_methods=[
                            PayMethodType(apm)
                            for apm in dconds["allowed_payment_methods"]
                        ],
                        policy_terms=dconds["policy_terms"],
                        account_number=dconds["account_number"],
                    )
                )
            except Exception as e:
                logger.warning(e)
                result["default_commertial_conditions"] = None
        return result

    def _set_employee_directory(
        self, employee_directory: List[Any], passed_memdict: Dict[str, Any]
    ):
        """Set employee directory

        Args:
            employee_directory (List[EmployeeDirectory]):
                Employee directory
            passed_memdict (Dict[str, Any]):
                Dict passed by reference to set employee directory in place
        """
        employee_directory_dir = []
        for employee in employee_directory:
            employee_dict = {}
            employee_dict["id"] = Binary.from_uuid(uuid.uuid4())
            if employee.department:
                employee_dict["department"] = employee.department
            if employee.email:
                employee_dict["email"] = employee.email
            if employee.last_name:
                employee_dict["last_name"] = employee.last_name
            if employee.name:
                employee_dict["name"] = employee.name
            if employee.phone_number:
                employee_dict["phone_number"] = employee.phone_number
            if employee.position:
                employee_dict["position"] = employee.position
            employee_directory_dir.append(employee_dict)
        passed_memdict["employee_directory"] = employee_directory_dir

    def _set_commercial_conditions(
        self, comm_conditions: Any, passed_memdict: Dict[str, Any]
    ):
        """Set commercial conditions

        Args:
            comm_conditions (Any):
                Commercial Conditions
            passed_memdict (Dict[str, Any]):
                Dict passed as ref to be updated in place
        """
        default_commertialconditions_dict = {}
        if comm_conditions.selling_options:
            _so_dir = []
            for so in comm_conditions.selling_options:
                _so_dict = {}
                _so_dict["selling_option_id"] = Binary.from_uuid(uuid.uuid4())
                if so.cutoff_time:
                    _so_dict["cutoff_time"] = so.cutoff_time
                if so.delivery_time_windows:
                    _so_dtw_dir = []
                    for so_dtw in so.delivery_time_windows:
                        _so_dtw_dir.append(so_dtw.value)
                    _so_dict["delivery_time_windows"] = _so_dtw_dir
                if so.selling_option:
                    _so_dict["selling_option"] = so.selling_option.value
                if so.service_hours:
                    _so_dict["service_hours"] = so.service_hours.value
                _so_dir.append(_so_dict)
            default_commertialconditions_dict["selling_options"] = _so_dir

        if comm_conditions.allowed_payment_methods:
            _apm_dir = []
            for apm in comm_conditions.allowed_payment_methods:
                _apm_dir.append(apm.value)
            default_commertialconditions_dict["allowed_payment_methods"] = _apm_dir

        if comm_conditions.invoicing:
            _inv_dict = {}
            if comm_conditions.invoicing.triggered_at:
                _inv_dict["triggered_at"] = comm_conditions.invoicing.triggered_at.value

            if comm_conditions.invoicing.automated_invoicing:
                _inv_dict["automated_invoicing"] = True
            else:
                _inv_dict["automated_invoicing"] = False

            if comm_conditions.invoicing.consolidation:
                _inv_dict["consolidation"] = (
                    comm_conditions.invoicing.consolidation.value
                )

            if comm_conditions.invoicing.invoice_type:
                _inv_dict["invoice_type"] = comm_conditions.invoicing.invoice_type.value

            if comm_conditions.invoicing.invoice_use:
                _inv_dict["invoice_use"] = comm_conditions.invoicing.invoice_use.value
            default_commertialconditions_dict["invoicing"] = _inv_dict

        if comm_conditions.minimum_order_value:
            _mov_dict = {}
            if comm_conditions.minimum_order_value.amount:
                _mov_dict["amount"] = comm_conditions.minimum_order_value.amount
            if comm_conditions.minimum_order_value.measure:
                _mov_dict["measure"] = comm_conditions.minimum_order_value.measure.value
            default_commertialconditions_dict["minimum_order_value"] = _mov_dict

        passed_memdict["default_commertial_conditions"] = (
            default_commertialconditions_dict
        )
