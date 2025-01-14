from abc import ABC, abstractmethod
from typing import Dict

from gqlapi.domain.models.v1.user import Session


class UserInterface(ABC):

    @abstractmethod
    def get_session(self, token: str) -> Session:
        raise NotImplementedError

    @abstractmethod
    def create_user(self, user_info: Dict) -> bool:
        """ Verify if exists in DB,
            if not create in Firestore & PSQL

        Parameters
        ----------
        user_info : Dict
            Auth info from Firebase

        Returns
        -------
        bool
            Flag
        """
        raise NotImplementedError

    @abstractmethod
    def create_settings(self, user_info: Dict, settings: Dict) -> bool:
        """ Upsert user account settings
            - Verify is business user exists
            - If user account exists -> update
            - else -> create record

        Parameters
        ----------
        user_info : Dict
            User info with email and uid
        settings : Dict


        Returns
        -------
        bool
            Flag
        """
        raise NotImplementedError

    @abstractmethod
    def set_delivery_plan(self, user_info: Dict) -> bool:
        """ Set delivery premium plan

        Parameters
        ----------
        user_info : Dict
            FB user info

        Returns
        -------
        bool
            Flag
        """
        raise NotImplementedError

    @abstractmethod
    def upsert_address(self, user_info: Dict, address_info: Dict) -> bool:
        """ Add / Update  Address to Business User

        Parameters
        ----------
        user_info : Dict
            FB user info

        Returns
        -------
        bool
            Flag
        """
        raise NotImplementedError

    @abstractmethod
    def set_payment(self, user_info: Dict, pay_method: str) -> bool:
        """ Set Payment method

        Parameters
        ----------
        user_info : Dict
            User info
        pay_method : str
            Payment method

        Returns
        -------
        bool
            Flag
        """
        raise NotImplementedError

    @abstractmethod
    def get_referral_wallet(self, user_info: Dict) -> Dict:
        """ Get User wallet

        Parameters
        ----------
        user_info : Dict
            Auth user info

        Returns
        -------
        Dict
            User's Referral Wallet info
        """
        raise NotImplementedError

    @abstractmethod
    def get_user(self, user_info: Dict) -> Dict:
        """ Get User info from profile, account and delivery

        Parameters
        ----------
        user_info : Dict
            Auth user info

        Returns
        -------
        Dict
            Business User info
        """
        raise NotImplementedError
