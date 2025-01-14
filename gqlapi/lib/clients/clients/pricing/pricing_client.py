import requests
import pickle

from typing import Dict, List
from uuid import UUID

from .consts import GET_BATCH_PRICES_ENDPOINT, GET_PRICE_RULES_ENDPOINT

from gqlapi.lib.environ.environ.environ import Environment
from gqlapi.domain.models.v1.pricing import Price, PriceRule
from gqlapi.domain.interfaces.v1.pricing_interface import PricingServiceInterface
from gqlapi.lib.logger.logger.basic_logger import get_logger


logger = get_logger(__name__)

endpoints = {
    Environment.LOCAL:      "http://0.0.0.0:8000",
    Environment.STAGING:    "https://stg.pricing.alima.aws"
}

timeouts = {
    Environment.LOCAL: 36000,
    Environment.STAGING: 36000,
}


class PricingClient(PricingServiceInterface):

    def __init__(self, env=None):
        self.env = env

    def get_batch_prices(self, customer_segment_id: int, product_ids: List[UUID]) -> Dict[UUID, Price]:
        if customer_segment_id == '':
            raise Exception("You must provide a customer_segment_id")
        if len(product_ids) == 0:
            raise Exception("You must provide a product_ids")

        url = '{}{}?customer_segment={}&product_ids={}'.format(
            endpoints[self.env],
            GET_BATCH_PRICES_ENDPOINT,
            str(customer_segment_id),
            ",".join([str(s) for s in product_ids])
        )

        resp = requests.get(url)
        if resp.status_code != 200:
            raise Exception("Error in the request")

        prices = pickle.loads(resp.text.encode('raw_unicode_escape'))
        return prices

    def get_price_rules(self) -> List[PriceRule]:
        url = '{}{}'.format(
            endpoints[self.env],
            GET_PRICE_RULES_ENDPOINT,
        )

        resp = requests.get(url)
        if resp.status_code != 200:
            raise Exception("Error in the request")

        rules = pickle.loads(resp.text.encode('raw_unicode_escape'))
        return rules
