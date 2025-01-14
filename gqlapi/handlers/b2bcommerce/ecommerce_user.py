import asyncio
from datetime import date
import secrets
import string
from types import NoneType
from typing import Any, Dict, List, Optional
from uuid import UUID
import uuid
from bson import Binary
from gqlapi.domain.models.v2.authos import IEcommerceUser
from gqlapi.domain.models.v2.b2bcommerce import EcommerceUserRestaurantRelation
from gqlapi.domain.models.v2.supplier import SupplierUnit
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.handlers.services.authos import EcommerceJWTHandler
from gqlapi.repository.supplier.supplier_restaurants import (
    SupplierRestaurantsRepository,
)
from gqlapi.repository.supplier.supplier_unit import SupplierUnitRepository
from gqlapi.lib.logger.logger.basic_logger import get_logger
from gqlapi.domain.interfaces.v2.authos.ecommerce_user import (
    EcommerceUser,
    EcommerceUserRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.b2bcommerce.ecommerce_seller import (
    B2BEcommerceHistorialOrdenes,
    B2BEcommerceOrdenInfo,
    B2BEcommerceUserHandlerInterface,
    B2BEcommerceUserInfo,
    EcommerceSellerRepositoryInterface,
    EcommerceUserRestaurantRelationRepositoryInterface,
)
from gqlapi.domain.interfaces.v2.orden.invoice import MxInvoiceHandlerInterface
from gqlapi.domain.interfaces.v2.orden.orden import OrdenGQL, OrdenHandlerInterface
from gqlapi.domain.interfaces.v2.restaurant.restaurant_branch import (
    RestaurantBranchGQL,
    RestaurantBranchHandlerInterface,
)
from gqlapi.domain.interfaces.v2.restaurant.restaurant_business import (
    RestaurantBusinessAccountRepositoryInterface,
    RestaurantBusinessHandlerInterface,
)
from gqlapi.domain.models.v2.restaurant import (
    RestaurantBranchMxInvoiceInfo,
    RestaurantBusiness,
)
from gqlapi.domain.models.v2.utils import CFDIUse, RegimenSat
from gqlapi.errors import GQLApiErrorCodeType, GQLApiException


logger = get_logger(get_app())


class B2BEcommerceUserHandler(B2BEcommerceUserHandlerInterface):
    def __init__(
        self,
        authos_ecommerce_user_repo: EcommerceUserRepositoryInterface,
        ecommerce_user_restaurant_relation_repo: EcommerceUserRestaurantRelationRepositoryInterface,
        restaurant_business_handler: RestaurantBusinessHandlerInterface,
        restaurant_branch_handler: RestaurantBranchHandlerInterface,
        orden_handler: Optional[OrdenHandlerInterface] = None,
        mxinvoice_handler: Optional[MxInvoiceHandlerInterface] = None,
        ecomerce_seller_repo: Optional[EcommerceSellerRepositoryInterface] = None,
        restaurant_business_account_repo: Optional[
            RestaurantBusinessAccountRepositoryInterface
        ] = None,
        supplier_restaurant_repo: Optional[SupplierRestaurantsRepository] = None,
        supplier_unit_repo: Optional[SupplierUnitRepository] = None,
    ) -> None:
        self.ecommerce_user_repo = authos_ecommerce_user_repo
        self.ecommerce_user_restaurant_relation_repo = (
            ecommerce_user_restaurant_relation_repo
        )
        self.restaurant_business_handler = restaurant_business_handler
        self.restaurant_branch_handler = restaurant_branch_handler
        if orden_handler is not None:
            self.orden_handler = orden_handler
        if mxinvoice_handler is not None:
            self.mxinvoice_handler = mxinvoice_handler
        if ecomerce_seller_repo:
            self.ecomerce_seller_repo = ecomerce_seller_repo
        if restaurant_business_account_repo:
            self.restaurant_business_account_repo = restaurant_business_account_repo
        if supplier_restaurant_repo:
            self.supplier_restaurant_repo = supplier_restaurant_repo
        if supplier_unit_repo:
            self.supplier_unit_repo = supplier_unit_repo

    async def _fetch_ecomm_user(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
    ) -> EcommerceUser:
        ecomm_user = await self.ecommerce_user_repo.fetch(
            ecommerce_user_id, ref_secret_key
        )
        if not ecomm_user:
            raise GQLApiException(
                "Ecommerce user not found",
                GQLApiErrorCodeType.AUTHOS_ERROR_TABLE_NOT_FOUND.value,
            )
        return ecomm_user

    async def _fetch_rest_business(
        self,
        ecommerce_user_id: UUID,
    ) -> RestaurantBusiness:
        # fetch relation with rest businss
        ecomm_user_rest_bus_rel = (
            await self.ecommerce_user_restaurant_relation_repo.fetch(
                "ecommerce_user_id", ecommerce_user_id
            )
        )
        if not ecomm_user_rest_bus_rel:
            raise GQLApiException(
                "Ecommerce user restaurant relation not found",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch rest business, if not found it raises exception
        rest_bus = await self.restaurant_business_handler.fetch_restaurant_business(
            ecomm_user_rest_bus_rel.restaurant_business_id
        )
        return rest_bus

    async def _fetch_ecommerce_rest_business_relation(
        self,
        id: Optional[UUID] = None,
        restaurant_business_id: Optional[UUID] = None,
        ecommerce_user_id: Optional[UUID] = None,
    ) -> EcommerceUserRestaurantRelation | NoneType:
        if not id and not restaurant_business_id and not ecommerce_user_id:
            raise GQLApiException(
                "No key to find ecommerce restaurant business",
                GQLApiErrorCodeType.DATAVAL_NO_DATA.value,
            )
        if id:
            # fetch relation with rest businss
            ecomm_user_rest_bus_rel = (
                await self.ecommerce_user_restaurant_relation_repo.fetch("id", id)
            )
            if ecomm_user_rest_bus_rel:
                return ecomm_user_rest_bus_rel
            else:
                return None
        if restaurant_business_id:
            # fetch relation with rest businss
            ecomm_user_rest_bus_rel = (
                await self.ecommerce_user_restaurant_relation_repo.fetch(
                    "restaurant_business_id", restaurant_business_id
                )
            )
            if ecomm_user_rest_bus_rel:
                return ecomm_user_rest_bus_rel
            else:
                return None
        if ecommerce_user_id:
            # fetch relation with rest businss
            ecomm_user_rest_bus_rel = (
                await self.ecommerce_user_restaurant_relation_repo.fetch(
                    "ecommerce_user_id", ecommerce_user_id
                )
            )
            if ecomm_user_rest_bus_rel:
                return ecomm_user_rest_bus_rel
            else:
                return None
        return None

    async def new_ecommerce_restaurant_user(
        self, restaurant_branch_id: UUID, email: str
    ) -> IEcommerceUser:
        rest_branch_list = (
            await self.restaurant_branch_handler.fetch_restaurant_branches(
                restaurant_branch_id=restaurant_branch_id
            )
        )
        if len(rest_branch_list) != 1:
            raise GQLApiException(
                msg="Issues to get restaurant branch",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED.value,
            )
        rest_branch = rest_branch_list[0]
        eurr = await self.ecommerce_user_restaurant_relation_repo.fetch(
            "restaurant_business_id", rest_branch.restaurant_business_id
        )

        if eurr:
            raise GQLApiException(
                msg="This restaurant already has a user",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        srr = await self.supplier_restaurant_repo.fetch_by_restaurant_branch(
            restaurant_branch_id
        )
        if not srr:
            raise GQLApiException(
                msg="Issues to find supplier restaurant relation",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_unit = await self.supplier_unit_repo.fetch(id=srr.supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Issues to find supplier unit",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_unit_obj = SupplierUnit(**supplier_unit)

        ecommerce_seller = await self.ecomerce_seller_repo.fetch(
            "supplier_business_id", supplier_unit_obj.supplier_business_id
        )
        if not ecommerce_seller:
            raise GQLApiException(
                msg="there is no ecommerce",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        ecommerce_user = await self.ecommerce_user_repo.fetch_by_email(
            email=email, ref_secret_key=ecommerce_seller.secret_key
        )
        if ecommerce_user:
            raise GQLApiException(
                msg="This email already in use",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        rb = await self.restaurant_business_handler.fetch_restaurant_business(
            id=rest_branch.restaurant_business_id
        )
        rba_list = await self.restaurant_business_account_repo.find(
            query={
                "restaurant_business_id": Binary.from_uuid(
                    rest_branch.restaurant_business_id
                )
            }
        )
        if not rb or not rba_list[0]:
            raise GQLApiException(
                msg="Issues to find supplier business",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        rba = rba_list[0]
        characters = string.ascii_letters + string.digits
        password = "".join(secrets.choice(characters) for _ in range(12))
        hpswd = EcommerceJWTHandler.hash_password(password)
        ecommerce_id = uuid.uuid4()
        ecommerce_gql = IEcommerceUser(
            id=ecommerce_id,
            password=password,
            first_name=rb.name,
            last_name=rb.name,
            phone_number=rba["phone_number"],  # type: ignore (safe)
            email=email,
        )
        if not await self.ecommerce_user_repo.add(
            IEcommerceUser(
                id=ecommerce_id,
                password=hpswd,
                first_name=rb.name,
                last_name=rb.name,
                phone_number=rba["phone_number"],  # type: ignore (safe)
                email=email,
            ),
            ref_secret_key=ecommerce_seller.secret_key,
        ):
            raise GQLApiException(
                msg="Error to create ecommerse user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        if not await self.ecommerce_user_restaurant_relation_repo.add(
            restaurant_business_id=rest_branch.restaurant_business_id,
            ecommerce_user_id=ecommerce_id,
        ):
            await self.ecommerce_user_repo.delete(
                ecommerce_id, ecommerce_seller.secret_key
            )
            raise GQLApiException(
                msg="Error to create ecommerse user restaurant relation",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )

        return ecommerce_gql

    async def edit_ecommerce_restaurant_user(
        self, restaurant_branch_id: UUID, email: str
    ) -> IEcommerceUser:
        rest_branch_list = (
            await self.restaurant_branch_handler.fetch_restaurant_branches(
                restaurant_branch_id=restaurant_branch_id
            )
        )
        if len(rest_branch_list) != 1:
            raise GQLApiException(
                msg="Issues to get restaurant branch",
                error_code=GQLApiErrorCodeType.DATAVAL_DUPLICATED.value,
            )
        rest_branch = rest_branch_list[0]
        eurr = await self.ecommerce_user_restaurant_relation_repo.fetch(
            "restaurant_business_id", rest_branch.restaurant_business_id
        )
        if not eurr:
            raise GQLApiException(
                msg="This restaurant don't have ecommerce user",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        srr = await self.supplier_restaurant_repo.fetch_by_restaurant_branch(
            restaurant_branch_id
        )
        if not srr:
            raise GQLApiException(
                msg="Issues to find supplier restaurant relation",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_unit = await self.supplier_unit_repo.fetch(id=srr.supplier_unit_id)
        if not supplier_unit:
            raise GQLApiException(
                msg="Issues to find supplier unit",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        supplier_unit_obj = SupplierUnit(**supplier_unit)
        ecommerce_seller = await self.ecomerce_seller_repo.fetch(
            "supplier_business_id", supplier_unit_obj.supplier_business_id
        )
        if not ecommerce_seller:
            raise GQLApiException(
                msg="there is no ecommerce",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        ecommerce_user_by_email = await self.ecommerce_user_repo.fetch_by_email(
            email=email, ref_secret_key=ecommerce_seller.secret_key
        )
        if ecommerce_user_by_email:
            raise GQLApiException(
                msg="This email already in use",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EXISTING_RECORD.value,
            )
        ecommerce_user = await self.ecommerce_user_repo.fetch(
            eurr.ecommerce_user_id, ref_secret_key=ecommerce_seller.secret_key
        )
        if not ecommerce_user:
            raise GQLApiException(
                msg="Issues to find ecommerce user",
                error_code=GQLApiErrorCodeType.FETCH_SQL_DB_EMPTY_RECORD.value,
            )
        edit_ecommerce_user = IEcommerceUser(
            id=ecommerce_user.id,
            password=ecommerce_user.password,
            first_name=ecommerce_user.first_name,
            last_name=ecommerce_user.last_name,
            phone_number=ecommerce_user.phone_number,
            email=email,
        )
        if not await self.ecommerce_user_repo.edit(
            edit_ecommerce_user,
            ref_secret_key=ecommerce_seller.secret_key,
        ):
            raise GQLApiException(
                msg="Error to edit ecommerse user",
                error_code=GQLApiErrorCodeType.INSERT_SQL_DB_ERROR.value,
            )
        return edit_ecommerce_user

    async def get_b2becommerce_client_info(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
    ) -> B2BEcommerceUserInfo:
        """Get ecommerce client info
            - get ecomm user from ecommerce_user_id
            - get rest business id from ecommerce_user_id
            - get rest business from rest business id
            - get rest branches from rest business id

        Args:
            ecommerce_user_id (UUID): Ecommerce user id
            ref_secret_key (str): Ref secret key

        Returns:
            B2BEcommerceUserInfo
        """
        # get ecommerce user
        ecomm_user = await self._fetch_ecomm_user(ecommerce_user_id, ref_secret_key)
        # get rest business from ecommerce user rest bus rel
        rest_bus = await self._fetch_rest_business(ecomm_user.id)
        # get rest branches
        rest_branches = []
        try:
            _branchs = await self.restaurant_branch_handler.fetch_restaurant_branches(
                restaurant_business_id=rest_bus.id
            )
            # add tax info
            br_reqs = [
                self.restaurant_branch_handler.repository.fetch_tax_info(restaurant_branch_id=br.id)  # type: ignore safe
                for br in _branchs
            ]
            br_results: List[Dict[Any, Any]] = await asyncio.gather(*br_reqs)
            for br, tax_info in zip(_branchs, br_results):
                if tax_info:
                    br.tax_info = RestaurantBranchMxInvoiceInfo(**tax_info)
            # fetch tags
            br_tags = await self.restaurant_branch_handler.repository.fetch_tags_from_many(  # type: ignore safe
                restaurant_branch_ids=[br.id for br in _branchs]
            )
            for jbr, _br in enumerate(_branchs):
                _tags = []
                for tag in br_tags:
                    if tag.restaurant_branch_id == _br.id:
                        _tags.append(tag)
                _branchs[jbr].tags = _tags
            rest_branches = _branchs
        except GQLApiException as ge:
            logger.warning(ge)
        # return formatted
        return B2BEcommerceUserInfo(
            user=ecomm_user,
            client=rest_bus,
            addresses=rest_branches,
        )

    async def add_b2becommerce_client_address(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
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
        category_id: Optional[UUID] = None,
        # optional tax info
        mx_sat_id: Optional[str] = None,
        tax_email: Optional[str] = None,
        legal_name: Optional[str] = None,
        tax_full_address: Optional[str] = None,
        tax_zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
    ) -> B2BEcommerceUserInfo:
        """Add ecommerce client address
            - get ecomm user from ecommerce_user_id
            - get rest business id from ecommerce_user_id
            - get rest business from rest business id
            - add new rest branch
            - get rest branches from rest business id
            - return formatted

        Args:
            ecommerce_user_id (UUID): _description_
            branch_name (str): _description_
            full_address (str): _description_
            street (str): _description_
            external_num (str): _description_
            internal_num (str): _description_
            neighborhood (str): _description_
            city (str): _description_
            state (str): _description_
            country (str): _description_
            zip_code (str): _description_
            category_id (Optional[UUID], optional): _description_. Defaults to None.

        Returns:
            B2BEcommerceUserInfo: _description_
        """
        # get ecommerce user
        ecomm_user = await self._fetch_ecomm_user(ecommerce_user_id, ref_secret_key)
        # get rest business from ecommerce user rest bus rel
        rest_bus = await self._fetch_rest_business(ecomm_user.id)
        # add new rest branch - in case of error it raises exception
        n_branch = (
            await self.restaurant_branch_handler.new_ecommerce_restaurant_address(
                restaurant_business_id=rest_bus.id,
                branch_name=branch_name,
                full_address=full_address,
                street=street,
                external_num=external_num,
                internal_num=internal_num,
                neighborhood=neighborhood,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                category_id=category_id,
            )
        )
        # if there is tax info also add it
        if (
            mx_sat_id is not None
            and tax_email is not None
            and legal_name is not None
            and tax_full_address is not None
            and tax_zip_code is not None
            and sat_regime is not None
            and cfdi_use is not None
        ):
            if not await self.restaurant_branch_handler.new_restaurant_branch_tax_info(
                restaurant_branch_id=n_branch.id,
                mx_sat_id=mx_sat_id,
                email=tax_email,
                legal_name=legal_name,
                full_address=tax_full_address,
                zip_code=tax_zip_code,
                sat_regime=sat_regime,
                cfdi_use=cfdi_use,
            ):
                logger.warning("Error adding ecommerce client tax info")
        # get rest branches
        rest_branches = []
        try:
            _branchs = await self.restaurant_branch_handler.fetch_restaurant_branches(
                restaurant_business_id=rest_bus.id
            )
            rest_branches = _branchs
        except GQLApiException as ge:
            logger.warning(ge)
        # return formatted
        return B2BEcommerceUserInfo(
            user=ecomm_user,
            client=rest_bus,
            addresses=rest_branches,
        )

    async def edit_b2becommerce_client_address(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
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
        category_id: Optional[UUID] = None,
        # optional tax info
        mx_sat_id: Optional[str] = None,
        tax_email: Optional[str] = None,
        legal_name: Optional[str] = None,
        tax_full_address: Optional[str] = None,
        tax_zip_code: Optional[str] = None,
        sat_regime: Optional[RegimenSat] = None,
        cfdi_use: Optional[CFDIUse] = None,
    ) -> B2BEcommerceUserInfo:
        """Edit ecommerce client address
            - get ecomm user from ecommerce_user_id
            - get rest business id from ecommerce_user_id
            - get rest branches from rest business id
            - verify that branch belongs to rest business
            - edit new rest branch
            - get rest branches from rest business id
            - return formatted

        Args:
            ecommerce_user_id (UUID): _description_
            ref_secret_key (str): _description_
            restaurant_branch_id (UUID): _description_
            branch_name (Optional[str], optional): _description_. Defaults to None.
            full_address (Optional[str], optional): _description_. Defaults to None.
            street (Optional[str], optional): _description_. Defaults to None.
            external_num (Optional[str], optional): _description_. Defaults to None.
            internal_num (Optional[str], optional): _description_. Defaults to None.
            neighborhood (Optional[str], optional): _description_. Defaults to None.
            city (Optional[str], optional): _description_. Defaults to None.
            state (Optional[str], optional): _description_. Defaults to None.
            country (Optional[str], optional): _description_. Defaults to None.
            zip_code (Optional[str], optional): _description_. Defaults to None.
            category_id (Optional[UUID], optional): _description_. Defaults to None.
            mx_sat_id (Optional[str], optional): _description_. Defaults to None.
            tax_email (Optional[str], optional): _description_. Defaults to None.
            legal_name (Optional[str], optional): _description_. Defaults to None.
            tax_full_address (Optional[str], optional): _description_. Defaults to None.
            tax_zip_code (Optional[str], optional): _description_. Defaults to None.
            sat_regime (Optional[RegimenSat], optional): _description_. Defaults to None.
            cfdi_use (Optional[CFDIUse], optional): _description_. Defaults to None.

        Returns:
            B2BEcommerceUserInfo: _description_
        """
        # get ecommerce user
        ecomm_user = await self._fetch_ecomm_user(ecommerce_user_id, ref_secret_key)
        # get rest business from ecommerce user rest bus rel
        rest_bus = await self._fetch_rest_business(ecomm_user.id)
        # get rest branches
        rest_branches: List[RestaurantBranchGQL] = []
        try:
            _branchs = await self.restaurant_branch_handler.fetch_restaurant_branches(
                restaurant_business_id=rest_bus.id
            )
            rest_branches = _branchs
        except GQLApiException as ge:
            logger.warning(ge)
            raise GQLApiException(
                "Error fetching restaurant branches",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # get rest branch by id
        rest_branch = None
        for br in rest_branches:
            if br.id == restaurant_branch_id:
                rest_branch = br
                break
        if rest_branch is None:
            raise GQLApiException(
                "Restaurant branch not found",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        if rest_branch.restaurant_business_id != rest_bus.id:
            raise GQLApiException(
                "Restaurant branch does not belong to Restaurant Business",
                GQLApiErrorCodeType.DATAVAL_NO_MATCH.value,
            )

        # add new rest branch - in case of error it raises exception
        ed_branch = (
            await self.restaurant_branch_handler.edit_ecommerce_restaurant_branch(
                restaurant_branch_id=restaurant_branch_id,
                branch_name=branch_name,
                full_address=full_address,
                street=street,
                external_num=external_num,
                internal_num=internal_num,
                neighborhood=neighborhood,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                category_id=category_id,
            )
        )
        # if there is tax info also add it
        if (
            mx_sat_id is not None
            or tax_email is not None
            or legal_name is not None
            or tax_full_address is not None
            or tax_zip_code is not None
            or sat_regime is not None
            or cfdi_use is not None
        ):
            ed_tax_info = (
                await self.restaurant_branch_handler.edit_restaurant_branch_tax_info(
                    restaurant_branch_id=ed_branch.id,
                    mx_sat_id=mx_sat_id,
                    email=tax_email,
                    legal_name=legal_name,
                    full_address=tax_full_address,
                    zip_code=tax_zip_code,
                    sat_regime=sat_regime,
                    cfdi_use=cfdi_use,
                )
            )
            ed_branch.tax_info = ed_tax_info
        # update local branches
        edited_branches = []
        for br in rest_branches:
            if br.id == ed_branch.id:
                edited_branches.append(ed_branch)
            else:
                edited_branches.append(br)
        # return formatted
        return B2BEcommerceUserInfo(
            user=ecomm_user,
            client=rest_bus,
            addresses=edited_branches,
        )

    async def get_b2becommerce_historic_ordenes(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> B2BEcommerceHistorialOrdenes:
        page = page or 1
        page_size = page_size or 10
        # get ecommerce user
        ecomm_user = await self.get_b2becommerce_client_info(
            ecommerce_user_id=ecommerce_user_id,
            ref_secret_key=ref_secret_key,
        )
        # search orders for all branches
        orders: List[OrdenGQL] = []
        for br in ecomm_user.addresses:
            try:
                _orders = await self.orden_handler.search_orden(
                    restaurant_branch_id=br.id,
                    from_date=from_date,
                    to_date=to_date,
                )
                orders.extend(_orders)
            except GQLApiException as ge:
                logger.warning("Error searching orders for branch: %s", br.id)
                logger.error(ge)
        if len(orders) == 0:
            return B2BEcommerceHistorialOrdenes(
                ordenes=[],
                total_results=0,
            )
        # sort and paginate
        t_res = len(orders)
        # sorted oldest - newest and filtered based on page and page_size
        _s_orders: List[OrdenGQL] = sorted(orders, key=lambda x: x.created_at, reverse=True)  # type: ignore
        s_orders = _s_orders[((page - 1) * page_size): page * page_size]
        sords_uuids = [o.id for o in s_orders]
        # fetch invoices
        _invoices = await self.mxinvoice_handler.fetch_invoices(sords_uuids)
        invoice_idx = {iv.orden_id: iv for iv in _invoices}
        # format response
        oi_orders: List[B2BEcommerceOrdenInfo] = []
        for o in s_orders:
            _oi = B2BEcommerceOrdenInfo(
                orden=o,
                invoice=invoice_idx.get(o.id),
            )
            oi_orders.append(_oi)
        return B2BEcommerceHistorialOrdenes(
            ordenes=oi_orders,
            total_results=t_res,
        )

    async def get_b2becommerce_orden_details(
        self,
        ecommerce_user_id: UUID,
        ref_secret_key: str,
        orden_id: UUID,
    ) -> B2BEcommerceOrdenInfo:
        # get ecommerce user
        ecomm_user = await self.get_b2becommerce_client_info(
            ecommerce_user_id=ecommerce_user_id,
            ref_secret_key=ref_secret_key,
        )
        # search order from orden id
        _orden: Optional[OrdenGQL] = None
        try:
            ordenes = await self.orden_handler.search_orden(
                orden_id=orden_id,
            )
            if len(ordenes) > 0:
                _orden = ordenes[0]
        except GQLApiException as ge:
            logger.error(ge)
        if _orden is None or _orden.details is None:
            raise GQLApiException(
                "Orden not found",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # verify that orden belongs to client
        _branch_ids = [str(br.id) for br in ecomm_user.addresses]
        if str(_orden.details.restaurant_branch_id) not in _branch_ids:
            raise GQLApiException(
                "Orden does not belong to client",
                GQLApiErrorCodeType.FETCH_SQL_DB_NOT_FOUND.value,
            )
        # fetch invoices
        _invoices = await self.mxinvoice_handler.fetch_invoices([_orden.id])
        invoice_idx = {iv.orden_id: iv for iv in _invoices}
        # format response
        return B2BEcommerceOrdenInfo(
            orden=_orden,
            invoice=invoice_idx.get(_orden.id),
        )
