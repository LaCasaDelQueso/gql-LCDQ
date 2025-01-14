import json
import logging
from typing import Dict

import requests


class FirebaseAuthApi:
    # Ref: https://firebase.google.com/docs/reference/rest/auth
    version = "1.0.0"
    _url = "https://identitytoolkit.googleapis.com/v1"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def signup_with_email(self, email: str, password: str) -> Dict[str, str]:
        """Sign Up with email

        Parameters
        ----------
        email : str
            Email
        password : str
            Password

        Returns
        -------
        Dict[str, str]
            Firebase User | Error
        """
        _payload = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True}
        )
        _headers = {"Content-Type": "application/json"}
        _resp = requests.request(
            "POST",
            "/".join([self._url, "accounts:signUp?key=" + self.api_key]),
            headers=_headers,
            data=_payload,
        )
        logging.debug(f"Firebase signup user: {_resp.status_code}")
        return _resp.json()

    def signin_with_email(self, email: str, password: str) -> Dict[str, str]:
        """Sign In with email

        Parameters
        ----------
        email : str
            Email
        password : str
            Password

        Returns
        -------
        Dict[str, str]
            Firebase User | Error
        """
        _payload = json.dumps(
            {"email": email, "password": password, "returnSecureToken": True}
        )
        _headers = {"Content-Type": "application/json"}
        _resp = requests.request(
            "POST",
            "/".join([self._url, "accounts:signInWithPassword?key=" + self.api_key]),
            headers=_headers,
            data=_payload,
        )
        logging.debug(f"Firebase sign in user: {_resp.status_code}")
        return _resp.json()

    def delete(self, id_token: str) -> Dict[str, str]:
        """Delete User

        Parameters
        ----------
        id_token : str
            Id Token

        Returns
        -------
        Dict[str, str]
            Firebase Reply | Error
        """
        _payload = json.dumps({"idToken": id_token})
        _headers = {"Content-Type": "application/json"}
        _resp = requests.request(
            "POST",
            "/".join([self._url, "accounts:delete?key=" + self.api_key]),
            headers=_headers,
            data=_payload,
        )
        logging.debug(f"Firebase delete user: {_resp.status_code}")
        return _resp.json()

    def update_profile(self, id_token: str, **kwargs) -> Dict[str, str]:
        """Update Firebase User Profile

        Parameters
        ----------
        id_token : str
            Firebase Auth Id Token
        kwargs : dict
            User profile data

        Returns
        -------
        Dict[str, str]
            Firebase Reply | Error
        """
        _allowed_keys = ["displayName", "photoUrl"]
        _payload = {"idToken": id_token, "returnSecureToken": True}
        for k, v in kwargs.items():
            if k not in _allowed_keys:
                continue
            _payload[k] = v
        _headers = {"Content-Type": "application/json"}
        _resp = requests.request(
            "POST",
            "/".join([self._url, "accounts:update?key=" + self.api_key]),
            headers=_headers,
            data=json.dumps(_payload),
        )
        logging.debug(f"Firebase update profile: {_resp.status_code}")
        return _resp.json()

    def send_reset_password_email(self, email: str) -> Dict[str, str]:
        """Send Reset Password Email

        Parameters
        ----------
        email : str
            Firebase User email

        Returns
        -------
        Dict[str, str]
            Firebase Reply | Error
        """
        _payload = {"email": email, "requestType": "PASSWORD_RESET"}
        _headers = {"Content-Type": "application/json"}
        _resp = requests.request(
            "POST",
            "/".join([self._url, "accounts:sendOobCode?key=" + self.api_key]),
            headers=_headers,
            data=json.dumps(_payload),
        )
        logging.debug(f"Firebase send password reset email: {_resp.status_code}")
        return _resp.json()
