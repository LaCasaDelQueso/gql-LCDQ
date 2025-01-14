from datetime import datetime
from enum import Enum
import logging
from types import NoneType
from typing import Any, Optional, Dict, List
import uuid
from uuid import UUID

from bson import Binary

from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepositoryInterface,
    RestaurantBusinessRepositoryInterface,
)
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBusiness,
    RestaurantBusinessAccount,
)
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.repository import CoreMongoRepository, CoreRepository
from gqlapi.utils.domain_mapper import sql_to_domain


class RestaurantBusinessRepository(
    CoreRepository, RestaurantBusinessRepositoryInterface
):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(self, name: str, country: str, active: bool = True) -> UUID:
        """Create Restaurant Business

        Args:
            name (str): name of restaurant business
            country (str): country where the restaurant resides

        Raises:
            GQLApiException

        Returns:
            UUID: unique restaurant business id
        """

        # cast to dict
        internal_values_restaurant_business = {
            "id": uuid.uuid4(),
            "name": name,
            "country": country,
            "active": active,
        }
        # call super method from new
        await super().new(
            core_element_tablename="restaurant_business",
            core_element_name="Restaurant Business",
            core_query="""INSERT INTO restaurant_business (id, name, country, active)
                    VALUES (:id, :name, :country, :active)
                """,
            core_values=internal_values_restaurant_business,
        )
        return internal_values_restaurant_business["id"]

    async def add(
        self, name: str, country: str, active: bool = True
    ) -> UUID | NoneType:
        """Create Restaurant Business

        Args:
            name (str): name of restaurant business
            country (str): country where the restaurant resides

        Raises:
            GQLApiException

        Returns:
            UUID: unique restaurant business id
        """

        # cast to dict
        internal_values_restaurant_business = {
            "id": uuid.uuid4(),
            "name": name,
            "country": country,
            "active": active,
        }
        # call super method from new
        _id = await super().add(
            core_element_tablename="restaurant_business",
            core_element_name="Restaurant Business",
            core_query="""INSERT INTO restaurant_business (id, name, country, active)
                    VALUES (:id, :name, :country, :active)
                """,
            core_values=internal_values_restaurant_business,
        )
        if _id and isinstance(_id, uuid.UUID):
            return _id
        return None

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update Restaurant Business

        Args:
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """

        rest_business_atributes = []
        rest_business_values_view: Dict[str, Any] = {"id": id}

        if name:
            rest_business_atributes.append(" name=:name")
            rest_business_values_view["name"] = name
        if country:
            rest_business_atributes.append(" country =:country")
            rest_business_values_view["country"] = country
        if active:
            rest_business_values_view["active"] = active
            rest_business_atributes.append(" active=:active")

        if len(rest_business_atributes) == 0:
            logging.info("No values to update in Restaurant Business")
            return True

        rest_business_atributes.append(" last_updated=:last_updated")
        rest_business_values_view["last_updated"] = datetime.utcnow()

        core_query = f"""UPDATE restaurant_business
                            SET {','.join(rest_business_atributes)}
                            WHERE id=:id;
                """
        await super().update(
            core_element_name="Restaurant Business",
            core_query=core_query,
            core_values=rest_business_values_view,
        )
        return True

    async def edit(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update Restaurant Business

        Args:
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """
        str_attrs = []
        q_vals: Dict[str, Any] = {"id": id}

        if name:
            str_attrs.append(" name=:name")
            q_vals["name"] = name
        if country:
            str_attrs.append(" country =:country")
            q_vals["country"] = country
        if active:
            q_vals["active"] = active
            str_attrs.append(" active=:active")

        if len(str_attrs) == 0:
            logging.info("No values to update in Restaurant Business")
            return True

        str_attrs.append(" last_updated=:last_updated")
        q_vals["last_updated"] = datetime.utcnow()

        core_query = f"""UPDATE restaurant_business
                            SET {','.join(str_attrs)}
                            WHERE id=:id;
                """
        return await super().edit(
            core_element_name="Restaurant Business",
            core_query=core_query,
            core_values=q_vals,
        )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(self, id: UUID) -> Dict[Any, Any]:  # type: ignore
        """Get Restaurant Business

        Args:
            id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: restaurant business model dict
        """
        _data = await super().get(
            id=id,
            id_key="id",
            core_element_tablename="restaurant_business",
            core_element_name="Restaurant Business",
            core_columns="*",
        )
        return sql_to_domain(_data, RestaurantBusiness)

    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        """Get Restaurant Business

        Args:
            id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            Dict[Any, Any]: restaurant business model dict
        """
        _data = await super().fetch(
            id=id,
            id_key="id",
            core_element_tablename="restaurant_business",
            core_element_name="Restaurant Business",
            core_columns="*",
        )
        if not _data:
            return {}
        return sql_to_domain(_data, RestaurantBusiness)

    async def get_restaurant_businesses(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> List[RestaurantBusiness]:
        """Get Restaurant Business

        Args:
            id (UUID): unique restaurant business id
            name (Optional[str], optional): name of restaurant business. Defaults to None.
            country (Optional[str], optional): country where the restaurant resides.Defaults to None.
            active (Optional[bool], optional): restaurant business status. Defaults to None. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            List[RestaurantBusiness]: restaurant business model list
        """

        rest_business_atributes = []
        rest_business_values_view = {}
        if id:
            rest_business_atributes.append(" id=:id and")
            rest_business_values_view["id"] = id
        if name:
            rest_business_atributes.append(" name=:name and")
            rest_business_values_view["name"] = name
        if country:
            rest_business_atributes.append(" country =:country and")
            rest_business_values_view["country"] = country
        if isinstance(active, bool):
            if active:
                rest_business_values_view["active"] = True
                rest_business_atributes.append(" active=:active and")
            else:
                rest_business_values_view["active"] = False
                rest_business_atributes.append(" active=:active and")

        if len(rest_business_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(rest_business_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        resp_restaurant_business = await super().search(
            core_element_name="Restaurant Business",
            core_element_tablename="restaurant_business",
            filter_values=filter_values,
            core_columns="*",
            values=rest_business_values_view,
        )

        return [
            RestaurantBusiness(**sql_to_domain(r, RestaurantBusiness))
            for r in resp_restaurant_business
        ]

    async def exist(
        self,
        restaurant_business_id: UUID,
    ) -> NoneType:
        """Validate Restaurant Business exists

        Args:
            restaurant_business_id (UUID): unique restaurant business id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=restaurant_business_id,
            core_columns="id",
            core_element_tablename="restaurant_business",
            id_key="id",
            core_element_name="Restaurant Business",
        )


class RestaurantBusinessAccountRepository(
    CoreMongoRepository, RestaurantBusinessAccountRepositoryInterface
):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        restaurant_business_id: UUID,
        account: Optional[RestaurantBusinessAccount] = None,
    ) -> bool:
        """Create Restaurant Business Account

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            account (Optional[RestaurantBusinessAccount], optional): Restaurant business account model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the creation is done
        """
        internal_values = {
            "restaurant_business_id": Binary.from_uuid(restaurant_business_id),
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }
        if account:
            if account.business_type:
                internal_values["business_type"] = account.business_type.value
            if account.legal_business_name:
                internal_values["legal_business_name"] = account.legal_business_name
            if account.incorporation_file:
                internal_values["incorporation_file"] = account.incorporation_file
            if account.mx_sat_regimen:
                internal_values["mx_sat_regimen"] = account.mx_sat_regimen
            if account.mx_sat_rfc:
                internal_values["mx_sat_rfc"] = account.mx_sat_rfc
            if account.mx_sat_csf:
                internal_values["mx_sat_csf"] = account.mx_sat_csf
            if account.phone_number:
                internal_values["phone_number"] = account.phone_number
            if account.email:
                internal_values["email"] = account.email
            if account.website:
                internal_values["website"] = account.website
            if account.mx_sat_regimen:
                internal_values["mx_sat_regimen"] = account.mx_sat_regimen

        await super().new(
            core_element_collection="restaurant_business_account",
            core_element_name="restaurant Business Account",
            validate_by="restaurant_business_id",
            validate_against=restaurant_business_id,
            core_values=internal_values,
        )

        return True

    async def add(
        self,
        account: RestaurantBusinessAccount,
    ) -> bool:
        """Create Restaurant Business Account

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            account (Optional[RestaurantBusinessAccount], optional): Restaurant business account model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the creation is done
        """
        internal_values = {
            "restaurant_business_id": Binary.from_uuid(account.restaurant_business_id),
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow(),
        }
        for key, value in account.__dict__.items():
            if key in ["restaurant_business_id", "created_at", "last_updated"]:
                continue
            if isinstance(value, Enum):
                internal_values[key] = value.value
                continue
            if value is not None:
                internal_values[key] = value

        res_vals = await super().add(
            core_element_collection="restaurant_business_account",
            core_element_name="restaurant Business Account",
            validate_by="restaurant_business_id",
            validate_against=account.restaurant_business_id,
            core_values=internal_values,
        )
        return False if res_vals is None else True

    async def edit(
        self,
        restaurant_business_id: UUID,
        account: RestaurantBusinessAccount,
    ) -> bool:
        """Update Restaurant Business Account

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            account (Optional[RestaurantBusinessAccount], optional): Restaurant business account model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """
        q_vals = {}
        for k, v in account.__dict__.items():
            if k in ["restaurant_business_id", "created_at", "last_updated"]:
                continue
            if v is None:
                continue
            if isinstance(v, Enum):
                q_vals[k] = v.value
                continue
            if k in ["incorporation_file", "mx_sat_csf", "legal_rep_id"]:
                q_vals[k] = Binary(v.encode("utf-8"))
                continue
            q_vals[k] = v
        # add last updated timestamp
        if q_vals:
            q_vals["last_updated"] = datetime.utcnow()
        else:
            logging.info("No values to update in Restaurant Business Account")
            return False

        new_values = {"$set": q_vals}
        query = {"restaurant_business_id": Binary.from_uuid(restaurant_business_id)}
        return await super().edit(
            core_element_collection="restaurant_business_account",
            core_element_name="Restaurant Bussines",
            core_query=query,
            core_values=new_values,
        )

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        restaurant_business_id: UUID,
        account: Optional[RestaurantBusinessAccount] = None,
    ) -> bool:
        """Update Restaurant Business Account

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            account (Optional[RestaurantBusinessAccount], optional): Restaurant business account model. Defaults to None.

        Raises:
            GQLApiException

        Returns:
            bool: validate the update is done
        """

        query = {"restaurant_business_id": Binary.from_uuid(restaurant_business_id)}
        internal_values = {}
        if account:
            if account.legal_rep_name:
                internal_values["legal_rep_name"] = account.legal_rep_name
            if account.legal_address:
                internal_values["legal_address"] = account.legal_address
            if account.legal_rep_id:
                internal_values["legal_rep_id"] = Binary(
                    account.legal_rep_id.encode("utf-8")
                )
            if account.business_type:
                internal_values["business_type"] = account.business_type.value
            if account.legal_business_name:
                internal_values["legal_business_name"] = account.legal_business_name
            if account.incorporation_file:
                internal_values["incorporation_file"] = Binary(
                    account.incorporation_file.encode("utf-8")
                )
            if account.mx_sat_regimen:
                internal_values["mx_sat_regimen"] = account.mx_sat_regimen
            if account.mx_sat_rfc:
                internal_values["mx_sat_rfc"] = account.mx_sat_rfc
            if account.mx_sat_csf:
                internal_values["mx_sat_csf"] = Binary(
                    account.mx_sat_csf.encode("utf-8")
                )
            if account.phone_number:
                internal_values["phone_number"] = account.phone_number
            if account.email:
                internal_values["email"] = account.email
            if account.website:
                internal_values["website"] = account.website
            if account.mx_sat_regimen:
                internal_values["mx_sat_regimen"] = account.mx_sat_regimen

        if internal_values:
            internal_values["last_updated"] = datetime.utcnow()
        else:
            logging.info("No values to update in Restaurant Business Account")
            return False

        new_values = {"$set": internal_values}

        await super().update(
            core_element_collection="restaurant_business_account",
            core_element_name="Restaurant Bussines",
            core_query=query,
            core_values=new_values,
        )
        return True

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(
        self, restaurant_business_id: UUID
    ) -> RestaurantBusinessAccount:  # type: ignore
        """Get Restaurant Business Account

        Args:
            restaurant_business_id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            RestaurantBusinessAccount: Restaurant business account model.
        """
        _data = await super().get(
            core_element_name="Restaurant Business",
            core_element_collection="restaurant_business_account",
            query={"restaurant_business_id": Binary.from_uuid(restaurant_business_id)},
        )
        # decoding bytes to string of stored files
        if "legal_rep_id" in _data and _data["legal_rep_id"]:
            _data["legal_rep_id"] = _data["legal_rep_id"].decode("utf-8")
        if "incorporation_file" in _data and _data["incorporation_file"]:
            _data["incorporation_file"] = _data["incorporation_file"].decode("utf-8")
        if "mx_sat_csf" in _data and _data["mx_sat_csf"]:
            _data["mx_sat_csf"] = _data["mx_sat_csf"].decode("utf-8")
        return RestaurantBusinessAccount(**_data)

    async def fetch(
        self, restaurant_business_id: UUID
    ) -> RestaurantBusinessAccount | NoneType:
        """Get Restaurant Business Account

        Args:
            restaurant_business_id (UUID): unique restaurant business id

        Raises:
            GQLApiException

        Returns:
            RestaurantBusinessAccount: Restaurant business account model.
        """
        _data = await super().fetch(
            core_element_name="Restaurant Business",
            core_element_collection="restaurant_business_account",
            query={"restaurant_business_id": Binary.from_uuid(restaurant_business_id)},
        )
        if not _data:
            return None
        # decoding bytes to string of stored files
        _data["restaurant_business_id"] = Binary.as_uuid(
            _data["restaurant_business_id"]
        )
        if "legal_rep_id" in _data and _data["legal_rep_id"]:
            _data["legal_rep_id"] = _data["legal_rep_id"].decode("utf-8")
        if "incorporation_file" in _data and _data["incorporation_file"]:
            _data["incorporation_file"] = _data["incorporation_file"].decode("utf-8")
        if "mx_sat_csf" in _data and _data["mx_sat_csf"]:
            _data["mx_sat_csf"] = _data["mx_sat_csf"].decode("utf-8")
        return RestaurantBusinessAccount(**_data)

    async def exist(
        self,
        id_key: str,
        restaurant_business_id: UUID,
    ) -> NoneType:
        """Validate Restaurant Business Account exists

        Args:
            id_key (str): key of id to query filter
            restaurant_business_id (UUID): unique restaurant business_id

        Returns:
            NoneType: None
        """
        query = {id_key: Binary.from_uuid(restaurant_business_id)}
        await super().exist(
            core_element_collection="restaurant_business_Account",
            core_element_name="Restaurant Business Account",
            core_query=query,
        )

    async def delete(
        self,
        restaurant_business_id: UUID,
    ) -> bool | NoneType:
        query = {"restaurant_business_id": Binary.from_uuid(restaurant_business_id)}
        if await super().delete(
            core_element_collection="restaurant_business_account",
            core_element_name="Restaurant Business Account",
            core_query=query,
        ):
            return True

    async def find(
        self,
        query: Dict[Any, Any],
    ) -> List[Any]:
        """Find Restaurant Business Account

        Parameters
        ----------
        query : Dict[Any, Any]

        Returns
        -------
        List[Any]
        """
        return await super().find(
            core_element_name="Restaurant Business Account",
            core_element_collection="restaurant_business_account",
            core_query=query,
        )
