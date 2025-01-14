from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

import strawberry

from gqlapi.domain.models.v2 import CoreUser


@strawberry.type
class TokenValidity:
    token: str
    valid: bool
    valid_until: datetime
    info: Optional[CoreUser]


class FirebaseTokenHandlerInterface(ABC):
    @abstractmethod
    def verify(self, token: str) -> TokenValidity:
        raise NotImplementedError


class FirebaseTokenRepositoryInterface(ABC):
    @abstractmethod
    def verify_token(self, token: str) -> Dict[Any, Any]:
        raise NotImplementedError
