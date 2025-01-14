from dataclasses import dataclass
from typing import List
from enum import Enum


@dataclass
class Session:
    session_id: str
    password_hash: str
    user_id: str
    experiment_assinments: List[str]


@dataclass
class User:
    user_id: str
    email: str


class DeliveryOption(Enum):
    SCHEDULED = 'scheduled'
    ONDEMAND = 'on_demand'


class PaymentMethod(Enum):
    CARD = 'card'
    CASHONDELIVERY = 'cash_on_delivery'
    BUSINESSCREDIT = 'business_credit'


"""
-- user
business_user
business_address
person_to_notify
user_account
premium_delivery

-- product
product_category
product_supplier
product
product_price

-- cart
cart
cart_products (?) -> only cart

-- discounts
discount_code
referral_code
referral_ledger

-- orders
order
order_discount
order_status
order_payment_status

-- pricing
pricing
competitors_map
monthly_frozen_prices

-- admin
alima_employee
employee_activity
"""
