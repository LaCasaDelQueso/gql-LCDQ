from enum import Enum
from dataclasses import dataclass
from uuid import UUID


class ProductSegmentType(Enum):
    PRIMERO = 1
    SEGUNDO = 2


@dataclass
class Price:
    price_uuid: UUID
    product_uuid: UUID
    segment_id: int
    amt: float
    generated_at: int
    valid_until: int
    json: str


@dataclass
class PriceRule:
    id: int
    name: str
    logic: str
