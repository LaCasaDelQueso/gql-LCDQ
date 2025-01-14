from abc import ABC, abstractmethod
from typing import Dict, List


class OrderInterface(ABC):

    # @deprecated
    @abstractmethod
    def get_firestore_order_by_id(oid) -> Dict:
        """ Get order from Firestore by Order UUID

        Returns
        -------
        List
            List of Dicts (JSON)
        """
        raise NotImplementedError

    @abstractmethod
    def get_cart_sql(user_info: Dict) -> Dict:
        """ Get Cart data if exists

        Parameters
        ----------
        user_info : Dict
            User Auth info

        Returns
        -------
        Dict
            Check out data
        """
        raise NotImplementedError

    @abstractmethod
    def check_valid_discount(user_info: Dict, discode: str) -> Dict:
        """ Validate if Discount code is valid
            and not applied by user

        Parameters
        ----------
        user_info : Dict
            User Auth info

        Returns
        -------
        Dict
            Discount amount info
        """
        raise NotImplementedError

    @abstractmethod
    def update_delivery_date(order_id: str, date: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def update_pay_details(order_id: str, pay_method: str, note: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_active_order_sql(user_info: Dict) -> Dict:
        raise NotImplementedError

    @abstractmethod
    def get_order_sql(order_id: str) -> Dict:
        raise NotImplementedError

    # @deprcated
    @abstractmethod
    def get_firestore_orders() -> List:
        """ Get orders from Firestore

        Returns
        -------
        List
            List of Dicts (JSON)
        """
        raise NotImplementedError

    @abstractmethod
    def get_past_orders_by_user_sql(user_info: Dict) -> List:
        """ Get orders by user

        Parameters
        ----------
        user_info : Dict
            User

        Returns
        -------
        List
            List of orders
        """
        raise NotImplementedError

    @abstractmethod
    def get_orders_sql(day: str) -> List:
        """ Get orders from DB

        Parameters
        ----------
        day : str
            Day to get

        Returns
        -------
        List
            List of orders
        """
        raise NotImplementedError

    @abstractmethod
    def get_orders_sql_wo_canceled(day: str) -> List:
        """ Get orders where status is canceled

        Parameters
        ----------
        day : str
            Day to get

        Returns
        -------
        List
            List of orders where status is canceled
        """
        raise NotImplementedError

    @abstractmethod
    def get_order_payments_sql(day: str) -> List:
        """ Get orders payment details from DB

        Parameters
        ----------
        day : str
            Day to get

        Returns
        -------
        List
            List of orders
        """
        raise NotImplementedError

    # @deprecated
    @abstractmethod
    def upsert_firestore_cart(data: dict) -> Dict:
        """ Upsert Cart

        Returns
        -------
        Dict
            Response with validation
        """
        raise NotImplementedError

    @abstractmethod
    def upsert_cart_sql(checkout: Dict, user_info: Dict) -> bool:
        """ Upsert Cart into DB

        Parameters
        ----------
        checkout : Dict
            Checkout data (subtotal, cart, total)
        user_info : Dict
            User auth info

        Returns
        -------
        bool
            Flag if correctly saved
        """
        raise NotImplementedError

    @abstractmethod
    def create_order_sql(data: Dict, user_info: Dict, ord_uuid: str) -> Dict:
        raise NotImplementedError

    # @deprecated
    @abstractmethod
    def create_firestore_order(data: dict) -> Dict:
        """ Create new order

        Returns
        -------
        Dict
            Response with Order UUID
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_firestore_order(data: dict) -> Dict:
        """ Cancel order

        Returns
        -------
        Dict
            Response with Order UUID
        """
        raise NotImplementedError

    @abstractmethod
    def pay_order(data: dict, user_info, order_id: str) -> Dict:
        """ Pay order with saved card from user

        Returns
        -------
        Dict
            Response with Order UUID
        """
        raise NotImplementedError

    @abstractmethod
    def update_plan(uid: str, plan_day: dict, action: str):
        """ Update Profile Plan

        Parameters
        ----------
        uid : str
            [description]
        plan_day : dict
            [description]
        """
        raise NotImplementedError

    @abstractmethod
    def find_cart(uid: str):
        raise NotImplementedError
