from abc import ABC, abstractmethod
from types import NoneType
from typing import Any, List, Optional, Dict
from uuid import UUID

import strawberry
from strawberry.file_uploads import Upload

from gqlapi.domain.models.v2.supplier import (
    InvoicingOptions,
    MinimumOrderValue,
    DeliveryOptions,
    SupplierBusiness,
    SupplierBusinessAccount,
    SupplierBusinessCommertialConditions,
    SupplierUserPermission,
)
from gqlapi.domain.models.v2.utils import (
    NotificationChannelType,
    BusinessType,
    PayMethodType,
    SupplierBusinessType,
)
from gqlapi.domain.models.v2.core import SupplierEmployeeInfo
from gqlapi.lib.future.future.deprecation import deprecated


@strawberry.type
class SupplierBusinessError:
    msg: str
    code: int


@strawberry.type
class SupplierBusinessImageStatus:
    msg: str
    status: bool


@strawberry.type
class SupplierBusinessAccountError:
    msg: str
    code: int


# [TODO] Cambiar a Supplier
@strawberry.input
class EmployeeInfoInput(SupplierEmployeeInfo):
    pass


@strawberry.input
class EmployeesInfoInput:
    employees: List[EmployeeInfoInput]


@strawberry.input
class MinimumOrderValueInput(MinimumOrderValue):
    pass


@strawberry.input
class SellingOptionsInput(DeliveryOptions):
    pass


@strawberry.input
class InvoicingOptionsInput(InvoicingOptions):
    pass


@strawberry.input
class SupplierBusinessAccountInput:
    business_type: Optional[SupplierBusinessType] = None
    legal_business_name: Optional[str] = None
    incorporation_file: Optional[Upload] = None
    legal_rep_name: Optional[str] = None
    legal_rep_id: Optional[Upload] = None
    legal_address: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    mx_sat_regimen: Optional[str] = None
    mx_sat_rfc: Optional[str] = None
    mx_sat_csf: Optional[Upload] = None
    mx_zip_code: Optional[str] = None
    displays_in_marketplace: Optional[bool] = None
    minimum_order_value: Optional[MinimumOrderValueInput] = None
    allowed_payment_methods: Optional[List[PayMethodType]] = None
    account_number: Optional[str] = None
    policy_terms: Optional[str] = None


@strawberry.type
class SupplierBusinessGQL(SupplierBusiness):
    account: Optional[SupplierBusinessAccount] = None
    permission: Optional[SupplierUserPermission] = None


SupplierBusinessResult = strawberry.union(
    "SupplierBusinessResult", (SupplierBusinessError, SupplierBusinessGQL)
)

SupplierBusinessImageResult = strawberry.union(
    "SupplierBusinessImageResult", (SupplierBusinessError, SupplierBusinessImageStatus)
)

SupplierBusinessAccountResult = strawberry.union(
    "SupplierBusinessAccountResult",
    (SupplierBusinessAccountError, SupplierBusinessAccount),
)


class SupplierBusinessHandlerInterface(ABC):
    @abstractmethod
    async def new_supplier_business(
        self,
        firebase_id: str,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
        business_type: SupplierBusinessType,
        phone_number: str,
        email: str,
        minimum_order_value: MinimumOrderValue,
        allowed_payment_methods: List[PayMethodType],
        policy_terms: str,
        website: Optional[str] = None,
        account_number: Optional[str] = None,
    ) -> SupplierBusinessGQL:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def edit_supplier_business(
        self,
        firebase_id: str,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        account: Optional[SupplierBusinessAccount] = None,
    ) -> SupplierBusinessGQL:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def search_supplier_business(
        self,
        id: Optional[UUID] = None,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[NotificationChannelType] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> List[SupplierBusinessGQL]:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_business_by_firebase_id(
        self,
        firebase_id: str,
    ) -> SupplierBusinessGQL:
        raise NotImplementedError

    @abstractmethod
    async def fetch_supplier_business(
        self, supplier_business_id: UUID
    ) -> SupplierBusinessGQL:
        raise NotImplementedError

    @abstractmethod
    async def patch_add_supplier_business_image(
        self, supplier_business_id, logo: Upload
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def delete_supplier_business_image(self, supplier_business_id) -> bool:
        raise NotImplementedError


class SupplierBusinessRepositoryInterface(ABC):
    @deprecated("Use add() instead", "domain")
    @abstractmethod
    async def new(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> UUID:  # type: ignore
        raise NotImplementedError

    @deprecated("Use edit() instead", "domain")
    @abstractmethod
    async def update(
        self,
        id: UUID,
        name: Optional[str] = "",
        country: Optional[str] = "",
        notification_preference: Optional[
            NotificationChannelType
        ] = NotificationChannelType.SMS,
    ) -> bool:
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    async def get(self, id: UUID) -> Dict[Any, Any]:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def exists(self, id: UUID) -> NoneType:  # type: ignore
        raise NotImplementedError

    @deprecated("Use exists() instead", "domain")
    @abstractmethod
    async def exist(self, id: UUID) -> NoneType:  # type: ignore
        raise NotImplementedError

    @deprecated("Use search() instead", "domain")
    @abstractmethod
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

    @abstractmethod
    async def add(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> UUID:  # type: ignore
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        id: UUID,
        name: Optional[str] = "",
        country: Optional[str] = "",
        notification_preference: Optional[
            NotificationChannelType
        ] = NotificationChannelType.SMS,
        active: Optional[bool] = None,
        logo_url: Optional[str] = None,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
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

    @abstractmethod
    async def delete_image(self, supplier_business_id) -> bool:
        raise NotImplementedError


class SupplierBusinessAccountRepositoryInterface(ABC):
    @deprecated("Use add() instead", "domain")
    @abstractmethod
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
    ) -> bool:
        raise NotImplementedError

    @deprecated("Use edit() instead", "domain")
    @abstractmethod
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
        raise NotImplementedError

    @deprecated("Use fetch() instead", "domain")
    @abstractmethod
    async def get(self, supplier_business_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def add(
        self,
        supplier_business_id: UUID,
        account: SupplierBusinessAccount,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def edit(
        self,
        supplier_business_id: UUID,
        account: SupplierBusinessAccount,
    ) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def fetch(self, supplier_business_id: UUID) -> Dict[Any, Any]:
        raise NotImplementedError

    @abstractmethod
    async def find(
        self,
        core_element_collection: str,
        core_element_name: str,
        core_query: Dict[Any, Any],
        max_length: int = 1000000,
    ) -> List[Dict[Any, Any]]:
        raise NotImplementedError

    @abstractmethod
    async def raw_query(
        self, collection: str, query: Dict[str, Any], **kwargs
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError
