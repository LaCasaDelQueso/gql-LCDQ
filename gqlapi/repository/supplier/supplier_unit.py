from datetime import datetime
from enum import Enum
import logging
from types import NoneType
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from bson import Binary

from gqlapi.domain.interfaces.v2.supplier.supplier_unit import (
    SupplierUnitDeliveryRepositoryInterface,
    SupplierUnitRepositoryInterface,
)
from gqlapi.domain.models.v2.supplier import (
    DeliveryOptions,
    SupplierUnit,
)
from gqlapi.domain.models.v2.utils import PayMethodType, ServiceDay
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.repository import CoreMongoRepository, CoreRepository
from gqlapi.utils.domain_mapper import domain_to_dict, sql_to_domain


class SupplierUnitRepository(CoreRepository, SupplierUnitRepositoryInterface):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        supplier_business_id: UUID,
        unit_name: str,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
    ) -> UUID:
        internal_values = {
            "id": uuid.uuid4(),
            "supplier_business_id": supplier_business_id,
            "unit_name": unit_name,
            "full_address": "",
            "street": "",
            "external_num": "",
            "internal_num": "",
            "neighborhood": "",
            "city": "",
            "state": "",
            "country": "",
            "zip_code": "",
        }

        if full_address:
            internal_values["full_address"] = full_address
        if street:
            internal_values["street"] = street
        if external_num:
            internal_values["external_num"] = external_num
        if internal_num:
            internal_values["internal_num"] = internal_num
        if neighborhood:
            internal_values["neighborhood"] = neighborhood
        if city:
            internal_values["city"] = city
        if state:
            internal_values["state"] = state
        if country:
            internal_values["country"] = country
        if zip_code:
            internal_values["zip_code"] = zip_code

        await super().new(
            core_element_tablename="supplier_unit",
            core_element_name="Supplier Unit",
            core_query="""INSERT INTO
            supplier_unit(
                id,
                supplier_business_id,
                unit_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                country,
                zip_code)
                VALUES (
                    :id,
                    :supplier_business_id,
                    :unit_name,
                    :full_address,
                    :street,
                    :external_num,
                    :internal_num,
                    :neighborhood,
                    :city,
                    :state,
                    :country,
                    :zip_code)
            """,
            core_values=internal_values,
        )
        return internal_values["id"]

    async def add(
        self,
        supplier_business_id: UUID,
        unit_name: str,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        allowed_payment_methods: Optional[List[PayMethodType]] = None,
        account_number: Optional[str] = None,
    ) -> UUID:
        internal_values = {
            "id": uuid.uuid4(),
            "supplier_business_id": supplier_business_id,
            "unit_name": unit_name,
            "full_address": "",
            "street": "",
            "external_num": "",
            "internal_num": "",
            "neighborhood": "",
            "city": "",
            "state": "",
            "country": "",
            "zip_code": "",
            "allowed_payment_methods": [],
            "account_number": "",
        }

        if full_address:
            internal_values["full_address"] = full_address
        if street:
            internal_values["street"] = street
        if external_num:
            internal_values["external_num"] = external_num
        if internal_num:
            internal_values["internal_num"] = internal_num
        if neighborhood:
            internal_values["neighborhood"] = neighborhood
        if city:
            internal_values["city"] = city
        if state:
            internal_values["state"] = state
        if country:
            internal_values["country"] = country
        if zip_code:
            internal_values["zip_code"] = zip_code
        if allowed_payment_methods:
            internal_values["allowed_payment_methods"] = [
                amp.value for amp in allowed_payment_methods
            ]
        if account_number:
            internal_values["account_number"] = account_number

        await super().add(
            core_element_tablename="supplier_unit",
            core_element_name="Supplier Unit",
            core_query="""INSERT INTO
            supplier_unit(
                id,
                supplier_business_id,
                unit_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                country,
                zip_code,
                account_number,
                allowed_payment_methods
                )
                VALUES (
                    :id,
                    :supplier_business_id,
                    :unit_name,
                    :full_address,
                    :street,
                    :external_num,
                    :internal_num,
                    :neighborhood,
                    :city,
                    :state,
                    :country,
                    :zip_code,
                    :account_number,
                    :allowed_payment_methods)
            """,
            core_values=internal_values,
        )
        return internal_values["id"]

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        id: UUID,
        unit_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
    ) -> bool:
        atributes = []
        values_view: Dict[str, Any] = {"id": id}

        if unit_name:
            atributes.append(" unit_name=:unit_name")
            values_view["unit_name"] = unit_name
        if full_address:
            atributes.append(" full_address=:full_address")
            values_view["full_address"] = full_address
        if street:
            atributes.append(" street=:street")
            values_view["street"] = street
        if external_num:
            atributes.append(" external_num=:external_num")
            values_view["external_num"] = external_num
        if internal_num:
            atributes.append(" internal_num=:internal_num")
            values_view["internal_num"] = internal_num
        if neighborhood:
            atributes.append(" neighborhood=:neighborhood")
            values_view["neighborhood"] = neighborhood
        if city:
            atributes.append(" city=:city")
            values_view["city"] = city
        if state:
            atributes.append(" state=:state")
            values_view["state"] = state
        if country:
            atributes.append(" country=:country")
            values_view["country"] = country
        if zip_code:
            atributes.append(" zip_code=:zip_code")
            values_view["zip_code"] = zip_code

        if len(atributes) == 0:
            logging.warning("No attributes to update in supplier unit")
            return False
        else:
            atributes.append(" last_updated=:last_updated")
            values_view["last_updated"] = datetime.utcnow()

        query = f"""UPDATE supplier_unit
                            SET {','.join(atributes)}
                            WHERE id=:id;
                        """
        await super().update(
            core_element_name="Supplier Unit",
            core_query=query,
            core_values=values_view,
        )
        return True

    async def edit(
        self,
        id: UUID,
        unit_name: Optional[str] = None,
        full_address: Optional[str] = None,
        street: Optional[str] = None,
        external_num: Optional[str] = None,
        internal_num: Optional[str] = None,
        neighborhood: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: Optional[str] = None,
        zip_code: Optional[str] = None,
        deleted: Optional[bool] = None,
        allowed_payment_methods: Optional[List[PayMethodType]] = None,
        account_number: Optional[str] = None,
    ) -> bool:
        attrs = []
        values_view: Dict[str, Any] = {"id": id}

        for k in SupplierUnit.__annotations__.keys():
            # skip these
            if k in ["created_at", "last_updated", "supplier_business_id"]:
                continue
            v = locals()[k]
            # skip none values
            if v is None:
                continue
            # add all values
            if k in ["allowed_payment_methods"]:
                values_view[k] = [apm.value for apm in v]
                continue
            values_view[k] = v
        # add attributes
        for k in values_view.keys():
            if k in ["id", "created_at", "last_updated"]:
                continue
            attrs.append(f" {k}= :{k}")
        if len(attrs) == 0:
            logging.warning("No attributes to update in supplier unit")
            return False
        else:
            attrs.append(" last_updated=:last_updated")
            values_view["last_updated"] = datetime.utcnow()

        query = f"""UPDATE supplier_unit
                    SET {','.join(attrs)}
                    WHERE id=:id;
                """
        return await super().edit(
            core_element_name="Supplier Unit",
            core_query=query,
            core_values=values_view,
        )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(self, id: UUID) -> Dict[Any, Any]:
        """get supplier unit

        Parameters
        ----------
        id : uuid,
            primary key of supplier unit
        Returns
        -------
        Supplier Unit Dict
        """

        _data = await super().get(
            id=id,
            core_element_tablename="supplier_unit",
            core_element_name="Supplier Unit",
            core_columns="*",
        )

        return sql_to_domain(_data, SupplierUnit)

    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        """get supplier unit

        Parameters
        ----------
        id : uuid,
            primary key of supplier unit
        Returns
        -------
        Supplier Unit Dict
        """

        _data = await super().fetch(
            id=id,
            core_element_tablename="supplier_unit",
            core_element_name="Supplier Unit",
            core_columns="*",
        )
        if not _data:
            return {}
        return sql_to_domain(_data, SupplierUnit)

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def exist(self, id: UUID) -> NoneType:  # type: ignore
        """Validate supplier unit exists

        Args:
            id (UUID): unique supplier unit id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=id,
            core_element_tablename="supplier_unit",
            core_element_name="Supplier Unit",
            id_key="id",
            core_columns="id",
        )

    async def exists(self, id: UUID) -> bool:  # type: ignore
        """Validate supplier unit exists

        Args:
            id (UUID): unique supplier unit id

        Returns:
            bool: True if exists, False otherwise
        """
        return await super().exists(
            id=id,
            core_element_tablename="supplier_unit",
            core_element_name="Supplier Unit",
            id_key="id",
            core_columns="id",
        )

    @deprecated("Use add() instead", "gqlapi.repository")
    async def search(
        self,
        supplier_business_id: Optional[UUID] = None,
        unit_name: Optional[str] = None,
    ) -> List[SupplierUnit]:
        """Search supplier unit

        Parameters
        ----------
        supplier_business_id : UUID, optional
            supplier business id, by default None

        Returns
        -------
        List[SupplierUnit]
        """
        sunit_values = {}
        filter_values = ""
        if supplier_business_id:
            filter_values = " supplier_business_id=:supplier_business_id"
            sunit_values["supplier_business_id"] = supplier_business_id
        if unit_name:
            if filter_values:
                filter_values += " AND"
            filter_values += " unit_name=:unit_name"
            sunit_values["unit_name"] = unit_name

        _data = await super().search(
            core_element_name="Supplier Unit",
            core_element_tablename="supplier_unit",
            core_columns="*",
            filter_values=filter_values,
            values=sunit_values,
        )
        return [SupplierUnit(**sql_to_domain(su, SupplierUnit)) for su in _data]

    async def find(
        self,
        supplier_business_id: Optional[UUID] = None,
        unit_name: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        """Search supplier unit

        Parameters
        ----------
        supplier_business_id : UUID, optional
            supplier business id, by default None

        Returns
        -------
        List[SupplierUnit]
        """
        sunit_values = {}
        filter_values = ""
        if supplier_business_id:
            filter_values = " supplier_business_id=:supplier_business_id"
            sunit_values["supplier_business_id"] = supplier_business_id
        if unit_name:
            if filter_values:
                filter_values += " AND"
            filter_values += " unit_name=:unit_name"
            sunit_values["unit_name"] = unit_name
        if unit_name or supplier_business_id:
            filter_values += " AND"
        filter_values += " deleted = 'f' ORDER BY created_at ASC"
        _data = await super().find(
            core_element_name="Supplier Unit",
            core_element_tablename="supplier_unit",
            core_columns="*",
            filter_values=filter_values,
            values=sunit_values,
        )
        return [sql_to_domain(su, SupplierUnit) for su in _data]

    async def count(
        self,
        supplier_business_id: UUID,
        deleted: bool = False,
    ) -> int:
        """Count supplier units

        Parameters
        ----------
        supplier_business_id : UUID, optional
            supplier business id, by default None
        deleted : bool, optional

        Returns
        -------
        int
        """
        del_str = "t" if deleted else "f"
        _data = await super().find(
            core_element_name="Supplier Unit",
            core_element_tablename="supplier_unit",
            core_columns="id",
            filter_values=f" supplier_business_id = :supplier_business_id and deleted='{del_str}' ",
            values={"supplier_business_id": supplier_business_id},
        )
        if not _data:
            return 0
        return len(_data)


class SupplierUnitDeliveryRepository(
    CoreMongoRepository, SupplierUnitDeliveryRepositoryInterface
):
    async def _serialize_supplier_unit_delivery(
        self, supplier_unit_id: UUID, delivery_options: DeliveryOptions
    ):
        internal_values = domain_to_dict(delivery_options)
        internal_values["supplier_unit_id"] = Binary.from_uuid(supplier_unit_id)
        for k, v in internal_values.items():
            if isinstance(v, UUID):
                internal_values[k] = Binary.from_uuid(v)
            if isinstance(v, list):
                tmp_list = []
                for j in v:
                    if isinstance(j, Enum):
                        tmp_list.append(j.value)
                    elif isinstance(j, ServiceDay):
                        tmp_list.append(j.__dict__)
                    elif k == "regions":
                        tmp_list.append(str(j).lower())
                    else:
                        tmp_list.append(j)
                internal_values[k] = tmp_list
        return internal_values

    async def add(
        self, supplier_unit_id: UUID, delivery_options: DeliveryOptions
    ) -> bool:
        # Build data
        internal_values = await self._serialize_supplier_unit_delivery(
            supplier_unit_id=supplier_unit_id,
            delivery_options=delivery_options,
        )
        # query
        _res = await super().add(
            core_element_collection="supplier_unit_delivery_info",
            core_element_name="Supplier Unit Delivery",
            core_values=internal_values,
            validate_by="supplier_unit_id",
            validate_against=supplier_unit_id,
        )
        return _res is not None

    async def find(
        self,
        supplier_unit_ids: List[UUID] = [],
        regions: List[str] = [],
    ) -> List[Dict[Any, Any]]:
        if not supplier_unit_ids and not regions:
            return []
        # build filters
        filters = {}
        if supplier_unit_ids:
            filters["supplier_unit_id"] = {
                "$in": [Binary.from_uuid(su) for su in supplier_unit_ids]
            }
        if regions:
            filters["regions"] = {"$in": [str(r).lower() for r in regions]}
        _res = await super().find(
            core_element_collection="supplier_unit_delivery_info",
            core_element_name="Supplier Unit Delivery",
            core_query=filters,
        )
        if not _res:
            return []
        # format response
        sdelivs = []
        for r in _res:
            _dlv = sql_to_domain(r, DeliveryOptions)
            _dlv["supplier_unit_id"] = Binary.as_uuid(r["supplier_unit_id"])
            sdelivs.append(_dlv)
        return sdelivs

    async def fetch(self, supplier_unit_id: UUID) -> Dict[Any, Any]:
        """Fetch supplier unit delivery

        Parameters
        ----------
        supplier_unit_id : UUID

        Returns
        -------
        Dict[Any, Any]
        """
        _res = await super().fetch(
            core_element_collection="supplier_unit_delivery_info",
            core_element_name="Supplier Unit Delivery",
            query={"supplier_unit_id": Binary.from_uuid(supplier_unit_id)},
        )
        if not _res:
            return {}
        # format response
        _dlv = sql_to_domain(_res, DeliveryOptions)
        _dlv["supplier_unit_id"] = Binary.as_uuid(_res["supplier_unit_id"])
        return _dlv

    async def edit(
        self, supplier_unit_id: UUID, delivery_options: DeliveryOptions
    ) -> bool:
        # Build data
        internal_values = await self._serialize_supplier_unit_delivery(
            supplier_unit_id=supplier_unit_id,
            delivery_options=delivery_options,
        )
        qry = {"supplier_unit_id": internal_values["supplier_unit_id"]}
        # query
        return await super().edit(
            core_element_collection="supplier_unit_delivery_info",
            core_element_name="Supplier Unit Delivery",
            core_values={"$set": internal_values},
            core_query=qry,
        )
