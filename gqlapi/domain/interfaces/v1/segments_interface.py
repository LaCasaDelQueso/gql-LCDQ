from abc import ABC, abstractmethod
from uuid import UUID
from typing import List

from gqlapi.domain.models.v1.segments import CustomerSegment, ProductSegment


class SegmentsServiceInterface(ABC):

    # Queries

    @abstractmethod
    def get_customer_segments(self, customer_id: UUID) -> List[CustomerSegment]:
        raise NotImplementedError

    @abstractmethod
    def get_active_customer_segment(self, customer_id: UUID) -> List[CustomerSegment]:
        raise NotImplementedError

    @abstractmethod
    def get_active_products(self, customer_segment_key: str, page_token: int, page_size: int) -> List[UUID]:
        raise NotImplementedError

    @abstractmethod
    def get_product_segments(self, customer_segment: str) -> List[ProductSegment]:
        raise NotImplementedError

    # Mutations

    @abstractmethod
    def save_customer_segment(self, name: str, hierarchy: int, customer_ids: List[UUID]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def save_product_segment(self, name: str, hierarchy: int, product_ids: List[UUID]) -> bool:
        raise NotImplementedError
