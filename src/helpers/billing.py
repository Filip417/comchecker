# Set your secret key. Remember to switch to your live secret key in production.
# See your keys here: https://dashboard.stripe.com/apikeys
import stripe
from decouple import config
from . import date_utils
from customers.models import Customer
from datetime import datetime


DJANGO_DEBUG=config("DJANGO_DEBUG", default=False, cast=bool)
STRIPE_SECRET_KEY=config("STRIPE_SECRET_KEY", default="", cast=str)
STRIPE_TEST_OVERRIDE = config("STRIPE_TEST_OVERRIDE", default=False, cast=bool)

if "sk_test" in STRIPE_SECRET_KEY and not DJANGO_DEBUG:
    raise ValueError("Invalid stripe key for prod")

stripe.api_key = STRIPE_SECRET_KEY


def serialise_subscription_data(subscription_response):
    status = subscription_response.status
    current_period_start = date_utils.timestamp_as_datetime(subscription_response.current_period_start)
    current_period_end = date_utils.timestamp_as_datetime(subscription_response.current_period_end)
    cancel_at_period_end = subscription_response.cancel_at_period_end
    currency = subscription_response.currency
    price = subscription_response['items']['data'][0]['price']['unit_amount']
    interval = subscription_response['items']['data'][0]['price']['recurring']['interval']
    
    return {
        "current_period_start":current_period_start,
        "current_period_end":current_period_end,
        "status":status,
        "cancel_at_period_end":cancel_at_period_end,
        "currency":currency,
        "cancel_at_period_end":cancel_at_period_end,
        "interval":interval,
        "price":price,
        }


def create_customer(
        name="",
        email="",
        metadata={},
        raw=False):
    response = stripe.Customer.create(
        name=name,
        email=email,
        metadata=metadata
    )
    if raw:
        return response
    stripe_id = response.id
    return stripe_id

def create_product(
        name="",
        metadata={},
        raw=False):
    response = stripe.Product.create(
        name=name,
        metadata=metadata
    )
    if raw:
        return response
    stripe_id = response.id
    return stripe_id

def create_price(currency="gbp",
                 unit_amount="9999",
                 interval="month",
                 product=None,
                 metadata={},
                raw=False):
    if product is None:
        return None
    response = stripe.Price.create(
            currency=currency,
            unit_amount=unit_amount,
            recurring={"interval": interval},
            product=product,
            metadata=metadata
            )
    if raw:
        return response
    stripe_id = response.id
    return stripe_id


def start_checkout_session(customer_id,
                           success_url="", 
                           cancel_url="",
                           price_stripe_id="", 
                           raw=True):
    if not success_url.endswith("?session_id={CHECKOUT_SESSION_ID}"):
        success_url = f"{success_url}" + "?session_id={CHECKOUT_SESSION_ID}" # TODO UPDATE
    response = stripe.checkout.Session.create(
        customer=customer_id,
        success_url=success_url,
        cancel_url=cancel_url,
        line_items=[{"price":price_stripe_id, "quantity": 1}],
        mode="subscription",
    )
    if raw:
        return response
    return response.url


def get_checkout_session(stripe_id, raw=True):
    response = stripe.checkout.Session.retrieve(
        stripe_id
    )
    if raw:
        return response
    return response.url


def get_subscription(stripe_id, raw=True):
    response = stripe.Subscription.retrieve(
        stripe_id
    )
    if raw:
        return response
    return serialise_subscription_data(response)


def get_customer_active_subscriptions(customer_stripe_id):
    response = stripe.Subscription.list(
        customer=customer_stripe_id,
        status="active",
    )
    return response

def cancel_subscription(stripe_id, reason="", feedback="other", cancel_at_period_end=False, raw=True):
    if cancel_at_period_end:
        response = stripe.Subscription.modify(
            stripe_id,
            cancel_at_period_end=cancel_at_period_end,
            cancellation_details={
                "comment": reason,
                "feedback":feedback,
            }
        )
    else:
        response = stripe.Subscription.cancel(
            stripe_id,
            cancellation_details={
                "comment": reason,
                "feedback":feedback,
            }
        )
    if raw:
        return response
    return serialise_subscription_data(response)


def get_checkout_customer_plan(session_id):
    checkout_r = get_checkout_session(session_id, raw=True)
    customer_id = checkout_r.customer
    sub_stripe_id = checkout_r.subscription
    sub_r = get_subscription(sub_stripe_id, raw=True)
    sub_plan = sub_r.plan
    subscription_data = serialise_subscription_data(sub_r)

    data = {
        "customer_id":customer_id,
        "plan_id":sub_plan.id,
        "sub_stripe_id":sub_stripe_id,
        **subscription_data
    }
    return data

def get_payment_history(
        user_id=None,
        limit=100):
    if user_id:
        try:
            customer = Customer.objects.get(user_id=user_id)
            customer_stripe_id = customer.stripe_id
            stripe_response = stripe.PaymentIntent.list(customer=customer_stripe_id, limit=limit)
        except:
            # customer does not exist
            return None
        payment_history_data = []
        for payment in stripe_response['data']:
            formatted_date = datetime.fromtimestamp(payment['created']).strftime("%d/%m/%Y")
            single_dict = {
                "invoice_id":payment['invoice'],
                "amount": payment['amount'],
                "currency":payment['currency'],
                "receipt_email":payment['receipt_email'],
                "status":payment['status'],
                "created":formatted_date
                }
            payment_history_data.append(single_dict)
        return payment_history_data
    return None

def get_active_cards(user_id=None, limit=10):
    if user_id:
        customer = Customer.objects.get(user_id=user_id)
        customer_stripe_id = customer.stripe_id
        customer_stripe_response = stripe.Customer.retrieve(id=customer_stripe_id)
        default_card_id = customer_stripe_response['default_source']
        stripe_response = stripe.Customer.list_payment_methods(customer=customer_stripe_id, limit=limit)
        cards_data = []
        present_card = stripe_response['data']['card_present']

        single_dict = {
                "last4": present_card["last4"],
                "brand": present_card["brand"],
                "display_brand":present_card['display_brand'],
                "default": True,
            }
        cards_data.append(single_dict)
        for payment_method in stripe_response['data']:
            card = payment_method['card']
            single_dict = {
                "last4": card["last4"],
                "brand": card["brand"],
                "display_brand":card['display_brand'],
                "default": False,
            }
            cards_data.append(single_dict)
        print(F"CARDS DATA: {cards_data}")
        return cards_data
    return None