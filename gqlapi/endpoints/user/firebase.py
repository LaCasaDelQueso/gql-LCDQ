import logging
import strawberry
from strawberry.types import Info as StrawberryInfo

from gqlapi.domain.interfaces.v2.user import TokenValidity
from gqlapi.handlers.user.firebase import FirebaseTokenHandler
from gqlapi.repository.user.firebase import MockTokenRepository


@strawberry.type
class FirebaseQuery:

    @strawberry.field
    def validatefb(self, info: StrawberryInfo, token: str) -> TokenValidity:  # noqa
        logging.info("Validate User Authentication Token")
        # instantiate handler
        _handler = FirebaseTokenHandler(
            MockTokenRepository()  # [TODO] change this to Actual Firebase Repo
        )
        # call validation
        return _handler.verify(token)
