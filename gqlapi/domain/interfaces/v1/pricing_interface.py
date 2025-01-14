from abc import ABC, abstractmethod
from types import NoneType
from typing import Dict, List
from uuid import UUID

from gqlapi.domain.models.v1.pricing import PriceRule, Price


class PricingServiceInterface(ABC):

    # Queries

    @abstractmethod
    def get_batch_prices(self, customer_segment_id: str | NoneType, product_ids: List[str]) -> Dict[UUID, Price]:
        raise NotImplementedError

    @abstractmethod
    def get_price_rules() -> List[PriceRule]:
        raise NotImplementedError
