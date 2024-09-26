from typing import Any
from django.core.management.base import BaseCommand


from main.models import UserSubscription
from customers.models import Customer
import helpers.billing

class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any):
        qs = Customer.objects.filter(stripe_id__isnull=False)
        for customer_obj in qs:
            user = customer_obj.user
            customer_stripe_id = customer_obj.stripe_id
            subs = helpers.billing.get_customer_active_subscriptions(customer_stripe_id)

            for sub in subs:
                existing_user_subs_qs = UserSubscription.objects.filter(
                    stripe_id__iexact=f"{sub.id}".strip())
                if existing_user_subs_qs.exists():
                    continue
                helpers.billing.cancel_subscription(sub.id,
                                                    reason="Dangling active subscription",
                                                    cancel_at_period_end=True)
                

        # TODO add refresh_active_users_subscriptions functions 
        # to go through with sync_user_subs? from view_functions.py
