from abc import ABC
from enum import Enum
from gqlapi.lib.environ.environ.environ import get_app
from gqlapi.lib.logger.logger.basic_logger import get_logger
from typing import Any, Dict, List, Literal, Optional

import requests
from strawberry import type as strawberry_type


logger = get_logger(get_app())


@strawberry_type
class GoDaddyResponse(ABC):
    status: str
    status_code: int
    msg: str
    result: Optional[str] = None
    value: Optional[str] = None


class GoDaddyEndpoints(Enum):
    NEW_RECORD = "v1/domains/{domain}/records"
    GET_RECORD = "v1/domains/{domain}/records/{type}/{name}"


class GoDaddyClientApi:
    def __init__(
        self, env: str, godaddy_key: str, godaddy_secret: str, godaddy_domain: str
    ) -> None:
        """_summary_

        Args:
            env (str): environment
            godaddy_key (str): key for godaddy
            godaddy_secret (str): secret for godaddy
            godaddy_domain (str): principal domain

        Raises:
            ValueError: _description_
        """
        # Cambiar var envs a self
        if not godaddy_key or not godaddy_secret or not godaddy_domain:
            raise ValueError("GoDaddy ENV VARS are not defined")
        self.godaddy_domain = godaddy_domain
        self.headers = {
            "Authorization": "sso-key " + godaddy_key + ":" + godaddy_secret,
            "content-type": "application/json",
        }
        self.url_base = (
            "https://api.godaddy.com/{endpoint}"
            if env.lower() == "prod"
            else "https://api.ote-godaddy.com/{endpoint}"
        )

    def find_record(
        self,
        record_name: str,
        type: Literal["A", "AAAA", "CNAME", "MX", "NS", "SOA", "SRV", "TXT"],
    ) -> GoDaddyResponse:
        try:
            url = self.url_base.format(
                endpoint=GoDaddyEndpoints.GET_RECORD.value.format(
                    domain=self.godaddy_domain, type=type, name=record_name
                )
            )
            fact_resp = requests.get(url=url, headers=self.headers)
            if fact_resp.status_code == 200:
                return GoDaddyResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    value=fact_resp.json(),
                    msg="ok",
                )
            return GoDaddyResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"GODADDY Error: {e}")
            return GoDaddyResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )

    def new_cname_record(
        self, ecommerce_name: str, data_record: str
    ) -> GoDaddyResponse:
        """_summary_
        Example:
        ```python

        Args:
            ecommerce_name (str): subdomain
            data (str): cname.record.com.


        Returns:
            GoDaddyResponse: _description_
        """
        try:
            url = self.url_base.format(
                endpoint=GoDaddyEndpoints.NEW_RECORD.value.format(
                    domain=self.godaddy_domain
                )
            )
            data: List[Dict[Any, Any]] = [
                {
                    "data": data_record,
                    "name": ecommerce_name,
                    "ttl": 3600,
                    "type": "CNAME",
                }
            ]
            fact_resp = requests.patch(url=url, headers=self.headers, json=data)
            if fact_resp.status_code == 200:
                return GoDaddyResponse(
                    status="ok",
                    status_code=fact_resp.status_code,
                    msg="ok",
                )
            return GoDaddyResponse(
                status="error",
                status_code=fact_resp.status_code,
                msg=fact_resp.content.decode("utf-8"),
            )
        except Exception as e:
            logger.error(f"GODADDY Error: {e}")
            return GoDaddyResponse(
                status="error",
                status_code=500,
                msg=str(e),
            )
