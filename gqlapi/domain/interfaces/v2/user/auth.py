from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

import strawberry

from gqlapi.domain.models.v2 import CoreUser


@strawberry.enum
class ValidationType(Enum):
    EMAIL = 'email'
    WHATSAPP = 'whatsapp'


@dataclass
class VerificationValidation(ABC):
    status: str
    validation_type: ValidationType
    msg: str
    requested_time: datetime


class AccountVerificationHandlerInterface(ABC):
    @abstractmethod
    def send_by_email(self, user: CoreUser) -> VerificationValidation:
        raise NotImplementedError

    @abstractmethod
    def send_by_whatsapp(self, user: CoreUser) -> VerificationValidation:
        raise NotImplementedError
