import typing
from gqlapi.domain.models.v2.utils import AlimaCustomerType

from starlette.requests import Request
from starlette.websockets import WebSocket
from strawberry.permission import BasePermission
from strawberry.types import Info as StrawberryInfo


class IsAuthenticated(BasePermission):
    message = "User is not authenticated"

    def has_permission(
        self, source: typing.Any, info: StrawberryInfo, **kwargs
    ) -> bool:
        request: typing.Union[Request, WebSocket] = info.context["request"]
        # starlette auth backend validation
        if not request.user.is_authenticated:
            return False
        # firebase auth backend validation
        if not hasattr(request.user, "firebase_user"):
            return False
        return True


class IsAppUserAuthorized(BasePermission):
    message = "App User is not authorized"
    user_type_allowed: AlimaCustomerType

    def has_permission(
        self, source: typing.Any, info: StrawberryInfo, **kwargs
    ) -> bool:
        self.request: typing.Union[Request, WebSocket] = info.context["request"]

        # auth backend validation
        if not hasattr(self.request.user, "user_type"):
            return False

        # alima user type validation
        if self.request.user.user_type != self.user_type_allowed:
            return False

        return True


class IsAlimaRestaurantAuthorized(IsAppUserAuthorized):
    message = "Alima Restaurant is not authorized"
    user_type_allowed: AlimaCustomerType = AlimaCustomerType.DEMAND


class IsAlimaDriverAuthorized(IsAppUserAuthorized):
    message = "Alima Driver is not authorized"
    user_type_allowed: AlimaCustomerType = AlimaCustomerType.LOGISTICS


class IsAlimaSupplyAuthorized(IsAppUserAuthorized):
    message = "Alima Supplier is not authorized"
    user_type_allowed: AlimaCustomerType = AlimaCustomerType.SUPPLY


class IsAlimaEmployeeAuthorized(IsAppUserAuthorized):
    message = "Alima Employee is not authorized"
    user_type_allowed: AlimaCustomerType = AlimaCustomerType.INTERNAL_USER


class IsB2BEcommerceUserAuthorized(IsAppUserAuthorized):
    message = "B2B Ecommerce User is not authorized"
    user_type_allowed: AlimaCustomerType = AlimaCustomerType.B2B_ECOMMERCE
