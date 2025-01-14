from abc import ABC, abstractmethod
from types import NoneType
from typing import List, Optional, Dict, Any
from uuid import UUID
from gqlapi.domain.models.v2.utils import PayMethodType, SellingOption, ServiceDay

import strawberry

from gqlapi.domain.models.v2.supplier import (
    DeliveryOptions,
    SupplierUnit,
    SupplierUnitCategory,
    SupplierUnitDeliveryOptions,
)
from gqlapi.domain.models.v2.core import MxSatInvoicingCertificateInfo, SupplierEmployeeInfo
from gqlapi.lib.future.future.deprecation import deprecated


@strawberry.type
class SupplierUnitError:
    msg: str
    code: int


@strawberry.type
class SupplierUnitContactInfo:
    business_name: Optional[str] = None
    display_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None


@strawberry.input
class ServiceDayInput(ServiceDay):
    pass


@strawberry.input
class SupplierUnitDeliveryOptionsInput(DeliveryOptions):
    selling_option: List[SellingOption]
    service_hours: List[ServiceDayInput]


@strawberry.type
class SupplierUnitGQL(SupplierUnit):
    unit_category: Optional[SupplierUnitCategory] = None
    tax_info: Optional[MxSatInvoicingCertificateInfo] = None
    contact_info: Optional[SupplierUnitContactInfo] = None
    delivery_info: Optional[SupplierUnitDeliveryOptions] = None


SupplierUnitResult = strawberry.union(
    "SupplierUnitResult",
    (SupplierUnitGQL, SupplierUnitError),
)


class SupplierUnitHandlerInterface(ABC):
    @abstractmethod
    async def new_supplier_unit(
        self,
        supplier_business_id: UUID,
        unit_name: str,
        full_address: str,
        street: str,
        external_num: str,
        internal_num: str,
        neighborhood: str,
        city: str,
        state: str,
        country: str,
        zip_code: str,
        firebase_id: str,
        category_id: UUID,
        delivery_options: DeliveryOptions,
        allowed_payment_methods: List[PayMethodType],
        account_number: str,
    ) -> SupplierUnitGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_suppliers_asoc_with_user(
        self,
        firebase_id: str,
        supplier_unit_id: Optional[UUID] = None,
    ) -> List[SupplierUnitGQL]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_units(
        self,
        supplier_business_id: Optional[UUID] = None,
        supplier_unit_id: Optional[UUID] = None,
        unit_name: Optional[str] = None,
    ) -> List[SupplierUnitGQL]:
        raise NotImplementedError

    @abstractmethod
    async def count_supplier_units(
        self,
        supplier_business_id: UUID,
    ) -> int:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_unit(
        self,
        supplier_unit_id: UUID,
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
        category_id: Optional[UUID] = None,
        deleted: Optional[bool] = None,
        delivery_options: Optional[SupplierUnitDeliveryOptions] = None,
        allowed_payment_methods: Optional[List[PayMethodType]] = None,
        account_number: Optional[str] = None,
    ) -> SupplierUnitGQL:
        raise NotImplementedError


class SupplierUnitRepositoryInterface(ABC):
    @deprecated("Use add() instead", "gqlapi.repository")
    @abstractmethod
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
    ) -> UUID:  # type: ignore
        raise NotImplementedError

    @deprecated("Use edit() instead", "gqlapi.repository")
    @abstractmethod
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
        raise NotImplementedError

    @deprecated("Use fetch() instead", "gqlapi.repository")
    @abstractmethod
    async def get(self, id: UUID) -> Dict[Any, Any]:  # type: ignore
        raise NotImplementedError

    @deprecated("Use exists() instead", "gqlapi.repository")
    @abstractmethod
    async def exist(self, id: UUID) -> NoneType:  # type: ignore
        raise NotImplementedError

    @deprecated("Use find() instead", "gqlapi.repository")
    @abstractmethod
    async def search(
        self,
        supplier_business_id: Optional[UUID] = None,
        unit_name: Optional[str] = None,
    ) -> List[SupplierUnit]:
        raise NotImplementedError

    @abstractmethod
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
    ) -> UUID:  # type: ignore
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, id: UUID) -> bool:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        supplier_business_id: Optional[UUID] = None,
        unit_name: Optional[str] = None,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def count(
        self,
        supplier_business_id: UUID,
        deleted: bool = False,
    ) -> int:
        raise NotImplementedError

    async def raw_query(
        self, query: str, vals: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class SupplierUnitDeliveryRepositoryInterface(ABC):
    @abstractmethod
    async def add(
        self,
        supplier_unit_id: UUID,
        delivery_options: DeliveryOptions,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        supplier_unit_ids: List[UUID] = [],
        regions: List[str] = [],
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self, supplier_unit_id: UUID, delivery_options: DeliveryOptions
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, supplier_unit_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError


class SupplierUnitEmployeeHandlerInterface(ABC):
    @abstractmethod
    async def new_supplier_unit_employee(
        self,
        supplier_business_id: UUID,
        supplier_unit_id: UUID,
        name: str,
        last_name: str,
        phone_number: str,
        email: str,
        department: Optional[str] = None,
        position: Optional[str] = None,
    ) -> SupplierEmployeeInfo:
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_unit_employee(
        self,
        supplier_business_id: UUID,
        id: UUID,
        name: Optional[str] = None,
        last_name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
    ) -> SupplierEmployeeInfo:
        raise NotImplementedError
