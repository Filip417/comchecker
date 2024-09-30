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


import helpers.billing
from typing import Any
from django.core.management.base import BaseCommand

from main import subs_utils

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("--day-start", default=0, type=int)
        parser.add_argument("--day-end", default=0, type=int)
        parser.add_argument("--days-left", default=0, type=int)
        parser.add_argument("--days-ago", default=0, type=int)
        parser.add_argument("--clear-dangling", action="store_true", default=False)

    def handle(self, *args: Any, **options: Any):
        # python manage.py sync_user_subs --clear-dangling
        # print(options)
        days_left = options.get("days_left")
        days_ago = options.get("days_ago")
        day_start = options.get("day_start")
        day_end = options.get("day_end")
        clear_dangling = options.get("clear_dangling")
        if clear_dangling:
            print("Clearing dangling not in use active subs in stripe")
            subs_utils.clear_dangling_subs()
        else:
            print("Sync active subs")
            done = subs_utils.refresh_active_users_subscriptions(
                active_only=True, 
                days_left=days_left,
                days_ago=days_ago,
                day_start=day_start,
                day_end=day_end,
                verbose=True
                )
            if done:
                print("Done")