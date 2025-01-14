from datetime import datetime
import json
import logging
from types import NoneType
from typing import Optional, List, Dict, Any, Type
from uuid import UUID
import uuid

from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchGQL,
    RestaurantBranchInvoicingOptionsRepositoryInterface,
    RestaurantBranchRepositoryInterface,
)
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranch,
    RestaurantBranchCategory,
    RestaurantBranchMxInvoiceInfo,
    RestaurantBranchTag,
)
from gqlapi.domain.models.v2.supplier import (
    InvoicingOptions,
    SupplierRestaurantRelationMxInvoicingOptions,
)
from gqlapi.domain.models.v2.utils import (
    CFDIUse,
    InvoiceConsolidation,
    InvoiceTriggerTime,
    InvoiceType,
    RegimenSat,
)
from gqlapi.lib.future.future.deprecation import deprecated
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException
from gqlapi.repository import CoreRepository
from gqlapi.utils.datetime import from_iso_format
from gqlapi.utils.domain_mapper import SQLDomainMapping, domain_to_dict, sql_to_domain
from gqlapi.utils.helpers import list_into_strtuple


class RestaurantBranchRepository(CoreRepository, RestaurantBranchRepositoryInterface):
    @deprecated("Use add() instead", "gqlapi.repository")
    async def new(
        self,
        restaurant_business_id: UUID,
        branch_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
    ) -> UUID:
        """Create Restauran Branch

        Args:
            restaurant_business_id (UUID): unique restaurant business id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch

        Returns:
            UUID: unique restaurant branch id
        """
        # Contruct values
        internal_values_restaurant_user = {
            "id": uuid.uuid4(),
            "restaurant_business_id": restaurant_business_id,
            "branch_name": branch_name,
            "full_address": full_address,
            "street": street,
            "external_num": external_num,
            "internal_num": internal_num,
            "neighborhood": neighborhood,
            "city": city,
            "state": state,
            "country": country,
            "zip_code": zip_code,
        }

        # call super method from new
        await super().new(
            core_element_tablename="restaurant_branch",
            core_element_name="Restaurant_Branch",
            core_query="""INSERT INTO restaurant_branch
                (id,
                restaurant_business_id,
                branch_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                country,
                zip_code)
                    VALUES
                    (:id,
                    :restaurant_business_id,
                    :branch_name,
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
            core_values=internal_values_restaurant_user,
        )
        return internal_values_restaurant_user["id"]

    async def add(
        self,
        restaurant_branch: RestaurantBranch,
    ) -> UUID | NoneType:
        """Create Restauran Branch

        Args:
            restaurant_branch: RestaurantBranch

        Returns:
            UUID: unique restaurant branch id
        """
        # Contruct values
        vals = {}
        for k, v in restaurant_branch.__dict__.items():
            if k not in ["created_at", "last_updated"] and v is not None:
                vals[k] = v

        # call super method from add
        _id = await super().add(
            core_element_tablename="restaurant_branch",
            core_element_name="Restaurant_Branch",
            core_query="""INSERT INTO restaurant_branch
                (id,
                restaurant_business_id,
                branch_name,
                full_address,
                street,
                external_num,
                internal_num,
                neighborhood,
                city,
                state,
                country,
                zip_code,
                deleted
                )
                    VALUES
                    (:id,
                    :restaurant_business_id,
                    :branch_name,
                    :full_address,
                    :street,
                    :external_num,
                    :internal_num,
                    :neighborhood,
                    :city,
                    :state,
                    :country,
                    :zip_code,
                    :deleted
                    )
                """,
            core_values=vals,
        )
        if _id and isinstance(_id, UUID):
            return _id
        return None

    @deprecated("Use edit() instead", "gqlapi.repository")
    async def update(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
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
    ) -> bool:
        """Update restaurant branch

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch

        Raises:
            GQLApiException: _description_

        Returns:
            bool: _description_
        """

        branch_atributes = []
        branch_values_view: Dict[str, Any] = {"id": restaurant_branch_id}

        if branch_name:
            branch_atributes.append(" branch_name=:branch_name")
            branch_values_view["branch_name"] = branch_name
        if full_address:
            branch_atributes.append(" full_address=:full_address")
            branch_values_view["full_address"] = full_address
        if street:
            branch_atributes.append(" street=:street")
            branch_values_view["street"] = street
        if external_num:
            branch_atributes.append(" external_num=:external_num")
            branch_values_view["external_num"] = external_num
        if internal_num:
            branch_atributes.append(" internal_num=:internal_num")
            branch_values_view["internal_num"] = internal_num
        if neighborhood:
            branch_atributes.append(" neighborhood=:neighborhood")
            branch_values_view["neighborhood"] = neighborhood
        if city:
            branch_atributes.append(" city=:city")
            branch_values_view["city"] = city
        if state:
            branch_atributes.append(" state=:state")
            branch_values_view["state"] = state
        if country:
            branch_atributes.append(" country=:country")
            branch_values_view["country"] = country
        if zip_code:
            branch_atributes.append(" zip_code=:zip_code")
            branch_values_view["zip_code"] = zip_code
        if deleted:
            branch_atributes.append(" deleted=:deleted")
            branch_values_view["deleted"] = deleted

        if len(branch_atributes) == 0:
            raise GQLApiException(
                msg="Issues no data to update in sql",
                error_code=GQLApiErrorCodeType.CONNECTION_MONGO_DB_ERROR.value,
            )

        branch_atributes.append(" last_updated=:last_updated")
        branch_values_view["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE restaurant_branch
                            SET {','.join(branch_atributes)}
                            WHERE id=:id;
                """

        await super().update(
            core_element_name="Restaurant Branch",
            core_query=branch_query,
            core_values=branch_values_view,
        )
        return True

    async def edit(
        self,
        restaurant_branch_id: UUID,
        branch_name: Optional[str] = None,
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
    ) -> bool:
        """Update restaurant branch

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            branch_name (str): Name of branch
            full_address (str): address of branch
            street (str): street of branch
            external_num (str): external num of branch
            internal_num (str): internal num of branch
            neighborhood (str): neighborhood of branch
            city (str): city of branch
            state (str): state of branch
            country (str): country of branch
            zip_code (str): zip_code of branch

        Raises:
            GQLApiException: _description_

        Returns:
            bool: _description_
        """

        b_attrs = []
        b_values: Dict[str, Any] = {"id": restaurant_branch_id}

        if branch_name:
            b_attrs.append(" branch_name=:branch_name")
            b_values["branch_name"] = branch_name
        if full_address:
            b_attrs.append(" full_address=:full_address")
            b_values["full_address"] = full_address
        if street:
            b_attrs.append(" street=:street")
            b_values["street"] = street
        if external_num:
            b_attrs.append(" external_num=:external_num")
            b_values["external_num"] = external_num
        if internal_num:
            b_attrs.append(" internal_num=:internal_num")
            b_values["internal_num"] = internal_num
        if neighborhood:
            b_attrs.append(" neighborhood=:neighborhood")
            b_values["neighborhood"] = neighborhood
        if city:
            b_attrs.append(" city=:city")
            b_values["city"] = city
        if state:
            b_attrs.append(" state=:state")
            b_values["state"] = state
        if country:
            b_attrs.append(" country=:country")
            b_values["country"] = country
        if zip_code:
            b_attrs.append(" zip_code=:zip_code")
            b_values["zip_code"] = zip_code
        if deleted:
            b_attrs.append(" deleted=:deleted")
            b_values["deleted"] = deleted

        if len(b_attrs) == 0:
            logging.warning("No data to update Restaurant Branch")
            return True

        b_attrs.append(" last_updated=:last_updated")
        b_values["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE restaurant_branch
                            SET {','.join(b_attrs)}
                            WHERE id=:id;
                        """
        return await super().edit(
            core_element_name="Restaurant Branch",
            core_query=branch_query,
            core_values=b_values,
        )

    @deprecated("Use fetch() instead", "gqlapi.repository")
    async def get(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:  # type: ignore
        """Get restaurant branch

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id

        Returns:
            Dict[Any, Any]: Restaurant Branch model dict
        """
        _data = await super().get(
            id=restaurant_branch_id,
            core_element_tablename="restaurant_branch",
            core_element_name="Restaurant Branch",
            core_columns="*",
        )

        return sql_to_domain(_data, RestaurantBranch)

    async def fetch(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:  # type: ignore
        """Fetch restaurant branch

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id

        Returns:
            Dict[Any, Any]: Restaurant Branch model dict
        """
        _data = await super().fetch(
            id=restaurant_branch_id,
            core_element_tablename="restaurant_branch",
            core_element_name="Restaurant Branch",
            core_columns="*",
        )
        if not _data:
            return {}
        return sql_to_domain(_data, RestaurantBranch)

    async def new_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: str,
        email: str,
        legal_name: str,
        full_address: str,
        zip_code: str,
        sat_regime: RegimenSat,
        cfdi_use: CFDIUse,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        """Create restaurant branch tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            mx_sat_id (str): unique alphanumeric key
            email (str):  email to contact the branch
            legal_name (str): Legal NAme of branch
            full_address (str): address of branch
            zip_code (str): code of branch zone
            sat_regime (RegimenSat): code of Sat Regime
            cfdi_use (CFDIUse): code od cfdi use

        Returns:
            bool: validate creation
        """
        internal_values_rest_branch_tax_info = {
            "branch_id": restaurant_branch_id,
            "mx_sat_id": mx_sat_id,
            "email": email,
            "legal_name": legal_name,
            "full_address": full_address,
            "zip_code": zip_code,
            "cfdi_use": str(cfdi_use.value),
            "sat_regime": str(sat_regime.value),
            "invoicing_provider_id": invoicing_provider_id,
        }

        await super().new(
            core_element_tablename="restaurant_branch_mx_invoice_info",
            core_element_name="Restaurant Branch Mx Invoice Info",
            # validate_by="branch_id",
            # validate_against=restaurant_branch_id,
            core_query="""INSERT INTO restaurant_branch_mx_invoice_info
                (branch_id,
                mx_sat_id,
                email,
                legal_name,
                full_address,
                zip_code,
                cfdi_use,
                sat_regime,
                invoicing_provider_id
                )
                    VALUES
                    (:branch_id,
                    :mx_sat_id,
                    :email,
                    :legal_name,
                    :full_address,
                    :zip_code,
                    :cfdi_use,
                    :sat_regime,
                    :invoicing_provider_id)
                """,
            core_values=internal_values_rest_branch_tax_info,
        )

        return True

    async def update_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        """update restaurant branch tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            mx_sat_id (str): unique alphanumeric key
            email (str):  email to contact the branch
            legal_name (str): Legal NAme of branch
            full_address (str): address of branch
            zip_code (str): code of branch zone
            sat_regime (RegimenSat): code of Sat Regime
            cfdi_use (CFDIUse): code od cfdi use
            invoicing_provider_id (str): _description_

        Raises:
            GQLApiException

        Returns:
            bool: validate update
        """
        try:
            branch_atributes = []
            branch_values_view: Dict[str, Any] = {"id": restaurant_branch_id}

            if mx_sat_id:
                branch_atributes.append(" mx_sat_id=:mx_sat_id")
                branch_values_view["mx_sat_id"] = mx_sat_id
            if full_address:
                branch_atributes.append(" full_address=:full_address")
                branch_values_view["full_address"] = full_address
            if email:
                branch_atributes.append(" email=:email")
                branch_values_view["email"] = email
            if legal_name:
                branch_atributes.append(" legal_name=:legal_name")
                branch_values_view["legal_name"] = legal_name
            if sat_regime:
                branch_atributes.append(" sat_regime=:sat_regime")
                branch_values_view["sat_regime"] = str(sat_regime.value)
            if cfdi_use:
                branch_atributes.append(" cfdi_use=:cfdi_use")
                branch_values_view["cfdi_use"] = str(cfdi_use.value)
            if zip_code:
                branch_atributes.append(" zip_code=:zip_code")
                branch_values_view["zip_code"] = zip_code
            if invoicing_provider_id:
                branch_atributes.append(" invoicing_provider_id=:invoicing_provider_id")
                branch_values_view["invoicing_provider_id"] = invoicing_provider_id

            if len(branch_atributes) == 0:
                raise GQLApiException(
                    msg="Issues no data to update in sql",
                    error_code=GQLApiErrorCodeType.CONNECTION_MONGO_DB_ERROR.value,
                )

            branch_atributes.append(" last_updated=:last_updated")
            branch_values_view["last_updated"] = datetime.utcnow()

            branch_query = f"""UPDATE restaurant_branch_mx_invoice_info
                                SET {','.join(branch_atributes)}
                                WHERE branch_id=:id;
                    """
            await super().update(
                core_element_name="Restaurant Branch Mx Invoice Info",
                core_query=branch_query,
                core_values=branch_values_view,
            )

        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating restaurant branch tax info")
            raise GQLApiException(
                msg="Error updating restaurant branch tax info",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return True

    async def edit_tax_info(
        self,
        restaurant_branch_id: UUID,
        mx_sat_id: Optional[str] = None,
        email: Optional[str] = None,
        legal_name: Optional[str] = None,
        full_address: Optional[str] = None,
        zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
        invoicing_provider_id: Optional[str] = None,
    ) -> bool:
        """edit restaurant branch tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id
            mx_sat_id (str): unique alphanumeric key
            email (str):  email to contact the branch
            legal_name (str): Legal NAme of branch
            full_address (str): address of branch
            zip_code (str): code of branch zone
            sat_regime (RegimenSat): code of Sat Regime
            cfdi_use (CFDIUse): code od cfdi use
            invoicing_provider_id (str): _description_

        Raises:
            GQLApiException

        Returns:
            bool: validate update
        """
        try:
            branch_atributes = []
            branch_values_view: Dict[str, Any] = {"id": restaurant_branch_id}

            if mx_sat_id:
                branch_atributes.append(" mx_sat_id=:mx_sat_id")
                branch_values_view["mx_sat_id"] = mx_sat_id
            if full_address:
                branch_atributes.append(" full_address=:full_address")
                branch_values_view["full_address"] = full_address
            if email:
                branch_atributes.append(" email=:email")
                branch_values_view["email"] = email
            if legal_name:
                branch_atributes.append(" legal_name=:legal_name")
                branch_values_view["legal_name"] = legal_name
            if sat_regime:
                branch_atributes.append(" sat_regime=:sat_regime")
                branch_values_view["sat_regime"] = str(sat_regime.value)
            if cfdi_use:
                branch_atributes.append(" cfdi_use=:cfdi_use")
                branch_values_view["cfdi_use"] = str(cfdi_use.value)
            if zip_code:
                branch_atributes.append(" zip_code=:zip_code")
                branch_values_view["zip_code"] = zip_code
            if invoicing_provider_id:
                branch_atributes.append(" invoicing_provider_id=:invoicing_provider_id")
                branch_values_view["invoicing_provider_id"] = invoicing_provider_id

            if len(branch_atributes) == 0:
                logging.warning("No attributes to update in supplier business")
                return False

            branch_atributes.append(" last_updated=:last_updated")
            branch_values_view["last_updated"] = datetime.utcnow()

            branch_query = f"""UPDATE restaurant_branch_mx_invoice_info
                                SET {','.join(branch_atributes)}
                                WHERE branch_id=:id;
                    """
            return await super().edit(
                core_element_name="Restaurant Branch Mx Invoice Info",
                core_query=branch_query,
                core_values=branch_values_view,
            )

        except Exception as e:
            logging.error(e)
            logging.warning("Issues updating restaurant branch tax info")
            raise GQLApiException(
                msg="Error updating restaurant branch tax info",
                error_code=GQLApiErrorCodeType.UPDATE_SQL_DB_ERROR.value,
            )
        return True

    async def get_tax_info(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:
        """Get restaurant branch Tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id

        Returns:
            Dict[Any, Any]: restaurant branch legal info model dict
        """
        _data = await super().fetch(
            id=restaurant_branch_id,
            id_key="branch_id",
            core_element_tablename="restaurant_branch_mx_invoice_info",
            core_element_name="Restaurant Branch Mx Invoice Info(",
            core_columns="*",
        )
        if not _data:
            return {}
        return sql_to_domain(
            _data,
            RestaurantBranchMxInvoiceInfo,
            special_casts={
                "sat_regime": SQLDomainMapping(
                    "sat_regime",
                    "sat_regime",
                    lambda s: RegimenSat(int(s)),
                ),
                "cfdi_use": SQLDomainMapping(
                    "cfdi_use",
                    "cfdi_use",
                    lambda s: CFDIUse(int(s)),
                ),
            },
        )

    async def fetch_tax_info_from_many(
        self, restaurant_branch_id_list: List[UUID]
    ) -> List[RestaurantBranchMxInvoiceInfo]:
        """Fetch Restaurant Tax Info From Many

        Args:
            restaurant_branch_id_list (List[UUID]): restaurant_branch_id_list

        Returns:
            Dict[Any, Any]: UUID: RestaurantBranchMxInvoiceInfo
        """
        db_mx_info = await self.find_many(
            cols=["*"],
            filter_values=[
                {
                    "column": "branch_id",
                    "operator": "in",
                    "value": list_into_strtuple(restaurant_branch_id_list),
                }
            ],
            tablename="restaurant_branch_mx_invoice_info",
            cast_type=RestaurantBranchMxInvoiceInfo,
        )
        if not db_mx_info:
            return []
        return [
            RestaurantBranchMxInvoiceInfo(
                **sql_to_domain(
                    mx_inf,
                    RestaurantBranchMxInvoiceInfo,
                    special_casts={
                        "sat_regime": SQLDomainMapping(
                            "sat_regime",
                            "sat_regime",
                            lambda s: RegimenSat(int(s)),
                        ),
                        "cfdi_use": SQLDomainMapping(
                            "cfdi_use",
                            "cfdi_use",
                            lambda s: CFDIUse(int(s)),
                        ),
                    },
                )
            )
            for mx_inf in db_mx_info
        ]

    async def fetch_tax_info(self, restaurant_branch_id: UUID) -> Dict[Any, Any]:
        """Fetch restaurant branch Tax info

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id

        Returns:
            Dict[Any, Any]: restaurant branch legal info model dict
        """
        _data = await super().fetch(
            id=restaurant_branch_id,
            id_key="branch_id",
            core_element_tablename="restaurant_branch_mx_invoice_info",
            core_element_name="Restaurant Branch Mx Invoice Info(",
            core_columns="*",
        )

        if not _data:
            return {}
        return sql_to_domain(
            _data,
            RestaurantBranchMxInvoiceInfo,
            special_casts={
                "sat_regime": SQLDomainMapping(
                    "sat_regime",
                    "sat_regime",
                    lambda s: RegimenSat(int(s)),
                ),
                "cfdi_use": SQLDomainMapping(
                    "cfdi_use",
                    "cfdi_use",
                    lambda s: CFDIUse(int(s)),
                ),
            },
        )

    async def get_restaurant_branches(
        self,
        restaurant_business_id: Optional[UUID] = None,
        restaurant_branch_id: Optional[UUID] = None,
        branch_name: Optional[str] = None,
        search: Optional[str] = None,
        restaurant_category: Optional[str] = None,
    ) -> List[RestaurantBranchGQL]:  # type: ignore
        """Get Restaurant Branches

        Args:
            restaurant_business_id (Optional[UUID], optional): unique rest business id. Defaults to None.
            branch_name (Optional[str], optional): Name od branch. Defaults to None.
            search (Optional[str], optional): code to query filter. Defaults to None.
            restaurant_category (Optional[str], optional): restaurant category. Defaults to None.

        Returns:
            List[RestaurantBranchGQL]
        """
        rest_business_atributes = []
        rest_business_values_view = {}
        if search:
            rest_business_atributes.append(
                " Lower(regexp_replace(rb.branch_name, '[^\\w]','','g')) ilike :search and"
            )
            rest_business_values_view["search"] = (
                "%" + "".join(filter(str.isalnum, search.lower())) + "%"
            )
        if restaurant_business_id:
            rest_business_atributes.append(
                " rb.restaurant_business_id=:restaurant_business_id and"
            )
            rest_business_values_view["restaurant_business_id"] = restaurant_business_id
        if branch_name:
            rest_business_atributes.append(" rb.branch_name=:branch_name and")
            rest_business_values_view["branch_name"] = branch_name

        if restaurant_category:
            rest_business_values_view["restaurant_category"] = restaurant_category
            rest_business_atributes.append(
                " rbc.restaurant_category_id=:restaurant_category and"
            )
        if restaurant_branch_id:
            rest_business_atributes.append(" rb.id = :restaurant_branch_id and")
            rest_business_values_view["restaurant_branch_id"] = restaurant_branch_id

        if len(rest_business_atributes) == 0:
            filter_values = None
        else:
            filter_values = " ".join(rest_business_atributes).split()
            filter_values = " ".join(filter_values[:-1])

        _resp = await super().search(
            core_element_name="Restaurant Branch",
            core_element_tablename="""
                restaurant_branch rb
                    JOIN restaurant_branch_category rbc ON rb.id = rbc.restaurant_branch_id""",
            filter_values=filter_values,
            core_columns=["rb.*", "row_to_json(rbc.*) AS category_json"],
            values=rest_business_values_view,
        )
        restaurant_branch_dir = []
        for r in _resp:
            d_branch = dict(r)
            rest_branch = RestaurantBranchGQL(**sql_to_domain(r, RestaurantBranch))
            rest_branch.branch_category = RestaurantBranchCategory(
                **json.loads(d_branch["category_json"])
            )
            if rest_branch.branch_category.created_at:
                rest_branch.branch_category.created_at = from_iso_format(
                    rest_branch.branch_category.created_at  # type: ignore
                )
            if rest_branch.branch_category.last_updated:
                rest_branch.branch_category.last_updated = from_iso_format(
                    rest_branch.branch_category.last_updated  # type: ignore
                )
            restaurant_branch_dir.append(rest_branch)
        return restaurant_branch_dir

    async def exist(
        self,
        rest_branch_id: UUID,
    ) -> NoneType:
        """Validate restaurant branch exists

        Args:
            rest_branch_id (UUID): unique restaurant branch id

        Returns:
            NoneType: None
        """
        await super().exist(
            id=rest_branch_id,
            core_columns="id",
            core_element_tablename="restaurant_branch",
            id_key="id",
            core_element_name="Restaurant Branch",
        )

    async def exists(
        self,
        restaurant_branch_id: UUID,
    ) -> bool:
        """Validate restaurant branch exists

        Args:
            restaurant_branch_id (UUID): unique restaurant branch id

        Returns:
            NoneType: None
        """
        return await super().exists(
            id=restaurant_branch_id,
            core_columns="id",
            core_element_tablename="restaurant_branch",
            id_key="id",
            core_element_name="Restaurant Branch",
        )

    async def exist_relation_rest_supp(
        self, restaurant_branch_id: UUID, supplier_business_id: UUID
    ) -> NoneType:
        """Validate relation exists

        Args:
            restaurant_branch_id (UUID): unique rest branch id
            supplier_business_id (UUID): unique supp business id

        Returns:
            NoneType: None
        """
        rest_supp_values_view = {}
        rest_supp_atributes = " restaurant_branch_id=:restaurant_branch_id and supplier_business_id =:supplier_business_id"
        rest_supp_values_view["restaurant_branch_id"] = restaurant_branch_id
        rest_supp_values_view["supplier_business_id"] = supplier_business_id
        _resp = await super().exists_relation(
            core_element_name="Restaurant Supplier Relation",
            core_element_tablename="restaurant_supplier_relation",
            filter_values=rest_supp_atributes,
            core_columns=["id"],
            values=rest_supp_values_view,
        )
        if _resp:
            logging.info(
                f"realation - {restaurant_branch_id} - {supplier_business_id} exists"
            )

    async def find_many(
        self,
        cols: List[str],
        filter_values: List[Dict[str, str]],
        tablename: str = "restaurant_branch",
        filter_type: str = "AND",
        cast_type: Type = RestaurantBranch,
    ) -> List[Dict[str, Any]]:
        """Search Restaurant Branch by multiple filter values

        Parameters
        ----------
        cols : List[str]
        filter_values : List[Dict[str, Any]]
        tablename : str, optional (default: "restaurant_branch")

        Returns
        -------
        List[Dict[str, Any]]
        """
        # format query
        qry = tablename
        if filter_values:
            _filt = " WHERE "
            for filter_value in filter_values:
                if len(_filt) > 7:  # 7 is len(" WHERE ")
                    _filt += f" {filter_type} "
                _filt += f"{filter_value['column']} {filter_value['operator']} {filter_value['value']}"
            qry += _filt
        prods = await super().find(
            core_element_name="Supplier Product",
            core_element_tablename=qry,
            core_columns=cols,
            values={},
        )
        return [sql_to_domain(prod, cast_type) for prod in prods]

    async def add_tags(
        self,
        restaurant_branch_id: UUID,
        tags: List[RestaurantBranchTag],
    ) -> bool:
        # verify which tags are already in the db
        db_tags = await self.fetch_tags(restaurant_branch_id=restaurant_branch_id)
        # if db tags delete them
        if db_tags:
            try:
                await self.db.execute_many(
                    query="""
                        DELETE FROM restaurant_branch_tag
                        WHERE id = :id
                    """,
                    values=[{"id": tag.id} for tag in db_tags],
                )
            except Exception as e:
                logging.warning("Error deleting restaurant branch tags")
                logging.error(e)
                return False
        # insert new tags
        try:
            if len(tags) == 0:
                return True
            await self.db.execute_many(
                query="""
                    INSERT INTO restaurant_branch_tag
                    (id, restaurant_branch_id, tag_key, tag_value)
                    VALUES
                    (:id, :restaurant_branch_id, :tag_key, :tag_value)
                """,
                values=[domain_to_dict(tag, skip=["created_at"]) for tag in tags],
            )
            return True
        except Exception as e:
            logging.warning("Error inserting restaurant branch tags")
            logging.error(e)
        return False

    async def fetch_tags(
        self,
        restaurant_branch_id: UUID,
    ) -> List[RestaurantBranchTag]:
        """Fetch Restaurant Branch Tags

        Args:
            restaurant_branch_id (UUID): restaurant branch id

        Returns:
            List[RestaurantBranchTag]: list of RestaurantBranchTag objects
        """
        db_tags = await self.find_many(
            cols=["id", "restaurant_branch_id", "tag_key", "tag_value", "created_at"],
            filter_values=[
                {
                    "column": "restaurant_branch_id",
                    "operator": "=",
                    "value": f"'{str(restaurant_branch_id)}'",
                }
            ],
            tablename="restaurant_branch_tag",
            cast_type=RestaurantBranchTag,
        )
        if not db_tags:
            return []
        return [
            RestaurantBranchTag(**sql_to_domain(tag, RestaurantBranchTag))
            for tag in db_tags
        ]

    async def fetch_tags_from_many(
        self,
        restaurant_branch_ids: List[UUID],
    ) -> List[RestaurantBranchTag]:
        """Fetch Restaurant Branch Tags

        Args:
            restaurant branch_ids (List[UUID]): restaurant branch ids

        Returns:
            List[RestaurantBranchTag]: list of RestaurantBranchTag objects
        """
        db_tags = await self.find_many(
            cols=["id", "restaurant_branch_id", "tag_key", "tag_value", "created_at"],
            filter_values=[
                {
                    "column": "restaurant_branch_id",
                    "operator": "in",
                    "value": list_into_strtuple(restaurant_branch_ids),
                }
            ],
            tablename="restaurant_branch_tag",
            cast_type=RestaurantBranchTag,
        )
        if not db_tags:
            return []
        return [
            RestaurantBranchTag(**sql_to_domain(tag, RestaurantBranchTag))
            for tag in db_tags
        ]


class RestaurantBranchInvoicingOptionsRepository(
    CoreRepository, RestaurantBranchInvoicingOptionsRepositoryInterface
):
    async def add(
        self,
        branch_invoicing_options: SupplierRestaurantRelationMxInvoicingOptions,
    ) -> UUID | NoneType:
        branch_io = domain_to_dict(branch_invoicing_options)
        if branch_io["triggered_at"]:
            branch_io["triggered_at"] = branch_io["triggered_at"].value
        if branch_io["consolidation"]:
            branch_io["consolidation"] = branch_io["consolidation"].value
        if branch_io["invoice_type"]:
            branch_io["invoice_type"] = branch_io["invoice_type"].value
        branch_io.pop("created_at")
        branch_io.pop("last_updated")
        _id = await super().add(
            core_element_tablename="supplier_restaurant_relation_mx_invoice_options",
            core_element_name="supplier_restaurant_relation_mx_invoice_options",
            core_query="""INSERT INTO supplier_restaurant_relation_mx_invoice_options
                (
                supplier_restaurant_relation_id,
                triggered_at,
                consolidation,
                invoice_type,
                automated_invoicing
                )
                    VALUES
                    (:supplier_restaurant_relation_id,
                    :triggered_at,
                    :consolidation,
                    :invoice_type,
                    :automated_invoicing
                    )
                """,
            core_values=branch_io,
        )
        if _id and isinstance(_id, UUID):
            return _id
        return None

    async def edit(
        self,
        supplier_restaurant_relation_id: UUID,
        automated_invoicing: Optional[bool] = None,
        triggered_at: Optional[InvoiceTriggerTime] = None,
        consolidation: Optional[InvoiceConsolidation] = None,
        invoice_type: Optional[InvoiceType] = None,
    ) -> bool:
        b_attrs = []
        b_values: Dict[str, Any] = {
            "supplier_restaurant_relation_id": supplier_restaurant_relation_id
        }
        if isinstance(automated_invoicing, bool):
            b_attrs.append(" automated_invoicing=:automated_invoicing")
            b_values["automated_invoicing"] = automated_invoicing
        if triggered_at:
            b_attrs.append(" triggered_at=:triggered_at")
            b_values["triggered_at"] = triggered_at.value
        if consolidation:
            b_attrs.append(" consolidation=:consolidation")
            b_values["consolidation"] = consolidation.value
        if invoice_type:
            b_attrs.append(" invoice_type=:invoice_type")
            b_values["invoice_type"] = invoice_type.value

        if len(b_attrs) == 0:
            logging.warning("No data to update Restaurant Branch")
            return True

        b_attrs.append(" last_updated=:last_updated")
        b_values["last_updated"] = datetime.utcnow()

        branch_query = f"""UPDATE supplier_restaurant_relation_mx_invoice_options
                            SET {','.join(b_attrs)}
                            WHERE supplier_restaurant_relation_id=:supplier_restaurant_relation_id;
                        """
        return await super().edit(
            core_element_name="supplier_restaurant_relation_mx_invoice_options",
            core_query=branch_query,
            core_values=b_values,
        )

    async def fetch(
        self, supplier_restaurant_relation_id: UUID
    ) -> SupplierRestaurantRelationMxInvoicingOptions | NoneType:
        _data = await super().fetch(
            id=supplier_restaurant_relation_id,
            core_element_tablename="supplier_restaurant_relation_mx_invoice_options",
            core_element_name="Restaurant Branch Invoicing Options",
            core_columns="*",
            id_key="supplier_restaurant_relation_id",
        )
        if _data:
            srrmio = sql_to_domain(_data, SupplierRestaurantRelationMxInvoicingOptions)
            io = sql_to_domain(_data, InvoicingOptions)
            io["triggered_at"] = InvoiceTriggerTime(io["triggered_at"])
            io["invoice_type"] = InvoiceType(io["invoice_type"])
            srrmio.update(io)
            return SupplierRestaurantRelationMxInvoicingOptions(**srrmio)

        return None

    async def exists(
        self,
        restaurant_branch_id: UUID,
        supplier_unit_id: Optional[UUID] = None,
    ) -> NoneType:
        raise NotImplementedError
