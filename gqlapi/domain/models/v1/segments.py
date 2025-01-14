from dataclasses import dataclass


@dataclass
class CustomerSegment:
    key: str
    description: str
    update_cadence: str


@dataclass
class ProductSegment:
    key: str
    description: str
