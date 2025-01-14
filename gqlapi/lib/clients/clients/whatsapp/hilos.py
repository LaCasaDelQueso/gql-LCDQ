import json
import logging
from types import NoneType
from typing import Any, Dict, List

import requests


class HilosSender:
    base_url = "https://api.hilos.io/api/channels/whatsapp"
    template_url = f"{base_url}/template"

    def __init__(self, token: str) -> None:
        self.api_token = token

    def _get_phone(self, phone: str) -> str:
        """Get phone number in correct format

        Parameters
        ----------
        phone : str
            10 digit phone number

        Returns
        -------
        str
            Phone number in correct format
        """
        if len(phone) == 10:
            return f"+52{phone}"
        if len(phone) == 12:
            return f"+{phone}"
        return phone

    def verify_template(self, template_id: str) -> bool:
        """Verify if template exists and has the correct number of variables

        Parameters
        ----------
        template_id : str
            HCM template ID

        Returns
        -------
        bool
            Flag indicating if template exists and has the correct number of variables
        """
        url = f"{self.template_url}/{template_id}"
        payload = {}
        headers = {"Authorization": f"Token {self.api_token}"}
        try:
            response = requests.request("GET", url, headers=headers, data=payload, timeout=10)
            if response.status_code != 200:
                logging.error(f"Error verifying template {template_id}")
                logging.warning(str(response.content))
                return False
            jd = response.json()
            if jd["status"] == "approved":
                return True
            logging.error(f"Template {template_id} is not approved")
            return False
        except Exception as e:
            logging.error(f"Error verifying template {template_id}")
            logging.warning(str(e))
            return False

    def send_message(
        self, phone: str, template_id: str, template_vars: List[Any] = []
    ) -> Dict[str, str] | NoneType:
        """Send WhatsApp message from HCM template

        Parameters
        ----------
        phone : str
            10 digit phone number
        template_id : str
            HCM template ID
        template_vars : List[Any], optional
            Variables required for template, by default []

        Returns
        -------
        Dict[str,str] | NoneType
            Response from Hilos API ({"id": "...", "conversation": "..."})
        """
        # verify template
        if not self.verify_template(template_id):
            return None
        # send message
        url = f"{self.template_url}/{template_id}/send"

        payload = json.dumps({"phone": f"{self._get_phone(phone)}", "variables": template_vars})
        headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }
        response = requests.request("POST", url, headers=headers, data=payload)
        if response.status_code != 201:
            logging.error(f"Error sending message to {phone}")
            logging.warning(str(response.content))
            return None
        return response.json()
