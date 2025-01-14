from abc import ABC, abstractmethod
from typing import Dict, List


class ProductsInterface(ABC):

    @abstractmethod
    def get_product_families(self) -> List:
        raise NotImplementedError

    @abstractmethod
    def get_family_details(self, product_key: str) -> List:
        raise NotImplementedError

    @abstractmethod
    def get_products(self) -> List:
        raise NotImplementedError

    # @deprecated
    @abstractmethod
    def get_prices() -> Dict:
        raise NotImplementedError

    # @deprecated
    @abstractmethod
    def insert_products(dfile: str) -> bool:
        raise NotImplementedError

    # @deprecated
    @abstractmethod
    def insert_prices(dfile: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def update_product_sql(prod_id: str, vals: Dict) -> bool:
        raise NotImplementedError

    @abstractmethod
    def update_product_price_sql(prod_id: str, vals: Dict) -> bool:
        raise NotImplementedError
