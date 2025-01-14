from abc import ABC, abstractmethod
from typing import Dict


class PaymentsInterface(ABC):

    @abstractmethod
    def delete_card(input, stripe_customer_id, stripe_card_id):
        raise NotImplementedError

    @abstractmethod
    def get_customer(stripe_customer_id):
        raise NotImplementedError

    @abstractmethod
    def update_default_pm(input, stripe_customer_id, stripe_card_id):
        raise NotImplementedError

    @abstractmethod
    def get_list_pm(stripe_customer_id):
        raise NotImplementedError

    # @deprecated
    @abstractmethod
    def find_customer(email: str) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def find_customer_hdler(email: str) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def find_customer_by_id(uid: str) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def set_stripe_id(doc: Dict, stripe_id: str):
        raise NotImplementedError

    @abstractmethod
    def set_stripe_id_hdler(bid: str, stripe_id: str):
        raise NotImplementedError
