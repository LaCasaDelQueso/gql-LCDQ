from datetime import datetime
from enum import Enum
import json
from typing import Dict, List
import stripe

from gqlapi.lib.logger.logger.basic_logger import get_logger
import stripe.error


class StripeCurrency(Enum):
    MXN = "mxn"


class StripePaymentIntentError:
    def __init__(self, code: str, payment_intent_id: str | None, json_result: str):
        self.code: str = code
        self.payment_intent_id: str | None = payment_intent_id
        self.json_result: str = json_result


class StripeApi:
    """Stripe API Client

    Reference
    ---------
        MX SPEI Transfer: https://docs.stripe.com/payments/bank-transfers/accept-a-payment

    Parameters
    ----------
    stripe_api_secret : str
        API Secret Key, generally stored as env var (STRIPE_API_SECRET)
    """

    def __init__(self, app_name: str, stripe_api_secret: str):
        stripe.api_key = stripe_api_secret
        self.logger = get_logger(app_name)

    def create_setup_intent(self, stripe_customer_id: str) -> stripe.SetupIntent | None:
        """Create Setup Intent

        Args:
            stripe_customer_id (str): _description_

        Returns:
            stripe.SetupIntent | None
        """
        try:
            setup_intent = stripe.SetupIntent.create(
                customer=stripe_customer_id,
            )
        except Exception as e:
            self.logger.warning(
                "Error creating setup intent, StripeApi.create_setup_intent"
            )
            self.logger.error(e)
            return None

        return setup_intent

    # Customer Methods
    def create_customer(
        self, email: str, name: str, metadata: Dict[str, str]
    ) -> stripe.Customer | None:
        """Create Stripe Customer

        Args:
            email (str): _description_
            name (str): _description_

        Returns:
            stripe.Customer | None
        """
        try:
            customer = stripe.Customer.create(email=email, name=name, metadata=metadata)
        except Exception as e:
            self.logger.warning("Error creating customer, StripeApi.create_customer")
            self.logger.error(e)
            return None

        return customer

    def get_customer(self, stripe_customer_id: str) -> stripe.Customer | None:
        """Get Stripe Customer

        Args:
            stripe_customer_id (str): _description_

        Returns:
            stripe.Customer | None
        """
        try:
            customer = stripe.Customer.retrieve(stripe_customer_id)
        except Exception as e:
            self.logger.warning("Error fetching customer, StripeApi.get_customer")
            self.logger.error(e)
            return None

        return customer

    # Card Methods
    def get_cards_list(self, stripe_customer_id: str) -> List[stripe.PaymentMethod]:
        """Get List of Cards

        Args:
            stripe_customer_id (str): _description_

        Returns:
            List[stripe.PaymentMethod]
        """
        try:
            payment_methods = stripe.PaymentMethod.list(
                customer=stripe_customer_id, type="card"
            )
        except Exception as e:
            self.logger.warning("Error fetching cards, StripeApi.get_cards_list")
            self.logger.error(e)
            return []

        return [pm for pm in payment_methods]

    def is_card_default(self, stripe_customer_id: str, stripe_card_id: str) -> bool:
        """Check if Card is Default

        Args:
            stripe_customer_id (str): _description_
            stripe_card_id (str): _description_

        Returns:
            bool
        """
        try:
            customer = stripe.Customer.retrieve(stripe_customer_id)
            return customer.invoice_settings.default_payment_method == stripe_card_id
        except Exception as e:
            self.logger.warning(
                "Error fetching default card, StripeApi.is_card_default"
            )
            self.logger.error(e)
            return False

    def delete_card(self, stripe_customer_id: str, stripe_card_id: str) -> bool:
        """Delete Card
                - If it's the last card, return False and log warning

        Args:
            stripe_customer_id (str): _description_
            stripe_card_id (str): _description_

        Returns:
            bool: Card deleted correctly or not
        """
        try:
            # fetch cards
            payment_methods = self.get_cards_list(stripe_customer_id)
            if len(payment_methods) <= 1:
                self.logger.warning("Cannot delete last card, StripeApi.delete_card")
                return False
            # delete card
            spm = stripe.PaymentMethod(stripe_card_id)
            spm.detach()
        except Exception as e:
            self.logger.warning("Error deleting card, StripeApi.delete_card")
            self.logger.error(e)
            return False
        return True

    def update_default_card(self, stripe_customer_id: str, stripe_card_id: str) -> bool:
        """Update Default Card

        Args:
            stripe_customer_id (str): _description_
            stripe_card_id (str): _description_

        Returns:
            bool: _description_
        """
        try:
            self.logger.info(f"Updating default card for customer {stripe_customer_id}")
            stripe.Customer.modify(
                stripe_customer_id,
                invoice_settings={
                    "custom_fields": None,
                    "default_payment_method": stripe_card_id,
                    "footer": None,
                },
            )
        except Exception as e:
            self.logger.warning(
                "Error updating default card, StripeApi.update_default_card"
            )
            self.logger.error(e)
            return False
        return True

    def create_card_payment_intent(
        self,
        stripe_customer_id: str,
        stripe_card_id: str,
        charge_description: str,
        charge_amount: float,
        email_to_confirm: str,
        charge_metadata: Dict[str, str],
        currency: StripeCurrency = StripeCurrency.MXN,
    ) -> stripe.PaymentIntent | StripePaymentIntentError:
        """Create Payment Intent for Card

        Args:
            stripe_customer_id (str): _description_
            stripe_card_id (str): _description_
            charge_description (str): _description_
            charge_amount (float): _description_
            email_to_confirm (str): _description_
            charge_metadata (Dict[str, str]): _description_
            currency (StripeCurrency, optional): _description_. Defaults to StripeCurrency.MXN.

        Returns:
            stripe.PaymentIntent | StripePaymentIntentError: _description_
        """
        try:
            pi_r = stripe.PaymentIntent.create(
                amount=int(charge_amount * 100),  # amount in cents
                currency=currency.value,
                description=charge_description,
                customer=stripe_customer_id,
                payment_method=stripe_card_id,
                receipt_email=email_to_confirm,
                off_session=True,
                confirm=True,
                metadata=charge_metadata,
            )
            return pi_r
        except stripe.error.CardError as e:
            err = e.error
            self.logger.warning("Card Error creating card payment intent")
            self.logger.error(
                "Error create_card_payment_intent. Code is: %s" % err.code
            )
            payment_intent_id = err.payment_intent["id"]
            return StripePaymentIntentError(
                code=str(err.code),
                payment_intent_id=payment_intent_id,
                json_result=str(e.json_body),
            )
        except Exception as e:
            self.logger.warning("Generic Error create_card_payment_intent")
            self.logger.error(e)
            return StripePaymentIntentError(
                code="unknown",
                payment_intent_id=None,
                json_result=json.dumps(json.dumps({"error": str(e)})),
            )

    # Transfer Methods
    def create_transfer_payment_intent(
        self,
        stripe_customer_id: str,
        charge_description: str,
        charge_amount: float,
        email_to_confirm: str,
        charge_metadata: Dict[str, str],
        currency: StripeCurrency = StripeCurrency.MXN,
    ) -> stripe.PaymentIntent | StripePaymentIntentError:
        """Create Payment Intent for Transfer

        Args:
            stripe_customer_id (str): _description_
            charge_description (str): _description_
            charge_amount (str): _description_
            email_to_confirm (str): _description_
            charge_metadata (Dict[str, str]): _description_
            currency (StripeCurrency, optional): _description_. Defaults to StripeCurrency.MXN.

        Returns:
            stripe.PaymentIntent | StripePaymentIntentError: _description_
        """
        try:
            pi_r = stripe.PaymentIntent.create(
                amount=int(charge_amount * 100),  # amount in cents
                currency=currency.value,
                description=charge_description,
                customer=stripe_customer_id,
                payment_method_types=["customer_balance"],
                payment_method_data={"type": "customer_balance"},
                payment_method_options={
                    "customer_balance": {
                        "funding_type": "bank_transfer",
                        "bank_transfer": {
                            "type": "mx_bank_transfer",
                        },
                    }
                },
                # off_session=True,
                confirm=True,
                receipt_email=email_to_confirm,
                metadata=charge_metadata,
            )
            return pi_r
        except Exception as e:
            self.logger.warning("Error creating transfer payment intent")
            self.logger.error(e)
            return StripePaymentIntentError(
                code="unknown",
                payment_intent_id=None,
                json_result=json.dumps(json.dumps({"error": str(e)})),
            )

    # Payment Intent Methods

    def get_payment_intent(
        self, payment_intent_id: str
    ) -> stripe.PaymentIntent | StripePaymentIntentError:
        """Get Payment Intent for Card

        Args:
            payment_intent_id (str): _description_

        Returns:
            stripe.PaymentIntent | StripePaymentIntentError: _description_
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.CardError as e:
            err = e.error
            self.logger.warning("Error en payment_intent_get. Code is: %s" % err.code)
            self.logger.error(e)
            payment_intent_id = err.payment_intent["id"]
            return StripePaymentIntentError(
                code=str(err.code),
                payment_intent_id=payment_intent_id,
                json_result=str(e.json_body),
            )
        except Exception as e:
            self.logger.warning("Error en payment_intent_get")
            self.logger.error(e)
            return StripePaymentIntentError(
                code="unknown",
                payment_intent_id=None,
                json_result=json.dumps(json.dumps({"error": str(e)})),
            )

        return payment_intent

    def construct_event(self, payload: bytes | str) -> stripe.Event | None:
        try:
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except ValueError as e:
            self.logger.warning("Invalid payload")
            self.logger.error(e)
            return None
        except stripe.error.SignatureVerificationError as e:
            self.logger.warning("Invalid signature")
            self.logger.error(e)
            return None
        except Exception as e:
            self.logger.warning("Error constructing event")
            self.logger.error(e)
            return None
        return event

    def get_transfer_payments(
        self, start_date: datetime, end_date: datetime
    ) -> int | None:
        try:
            balance_transactions = stripe.BalanceTransaction.list(
                created={
                    "gte": int(start_date.timestamp()),
                    "lte": int(end_date.timestamp()),
                }
            )
            # Filter to get only input transactions (e.g., payments)
            balance_transactions_inputs = [
                bt
                for bt in balance_transactions.auto_paging_iter()  # type: ignore #safe
                if bt.type in ["payment", "adjustment", "transfer"]
            ]
        except stripe.error.StripeError as e:
            self.logger.warning("Error fetching transfer")
            self.logger.error(e)
            return None
        return len(balance_transactions_inputs)
