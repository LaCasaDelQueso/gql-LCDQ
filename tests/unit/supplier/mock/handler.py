from typing import List, Optional
from uuid import UUID
from gqlapi.domain.interfaces.v2.supplier.supplier_business import (
    SupplierBusinessGQL,
    SupplierBusinessHandlerInterface,
)
from gqlapi.domain.models.v2.supplier import SupplierBusiness
from gqlapi.domain.models.v2.utils import NotificationChannelType


class MockSupplierBusinessHandler(SupplierBusinessHandlerInterface):
    def new_supplier_business(
        self,
        name: str,
        country: str,
        notification_preference: NotificationChannelType,
    ) -> SupplierBusiness:
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB
            name (str): supplier business name
            country (str): supplier business country
            notification_preference (NotificationChannelType): Chanel to notification

        Raises:
            GQLApiException

        Returns:
            SupplierBusiness: Supplier Business model
        """
        # post supplier business
        return SupplierBusiness(
            id=UUID("35dc0b51-6222-456d-a7be-7c4ae0da1674"),
            name=name,
            country=country,
            active=True,
            notification_preference=notification_preference,
        )

    def edit_supplier_business(
        self,
        id: UUID,
        name: Optional[str] = None,
        country: Optional[str] = None,
        notification_preference: Optional[
            NotificationChannelType
        ] = NotificationChannelType.SMS,
    ) -> SupplierBusiness:  # type: ignore
        """_summary_

        Args:
            info (StrawberryInfo): info to connect to DB
            id: unique supplier business id
            name (str): supplier business name, optional_
            country (str): supplier business country, optional
            notification_preference (NotificationChannelType): Chanel to notification, optional

        Raises:
            GQLApiException

        Returns:
            SupplierBusiness: Supplier Business model
        """
        name = "fercho"
        country = "México"
        notification_preference = NotificationChannelType.EMAIL
        # update
        return SupplierBusiness(
            id=id,
            name=name,
            country=country,
            active=True,
            notification_preference=notification_preference,
        )

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

    async def fetch_supplier_business_by_firebase_id(
        self,
        firebase_id: str,
    ) -> SupplierBusinessGQL:
        raise NotImplementedError
