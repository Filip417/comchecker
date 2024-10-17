from django.core.management.base import BaseCommand
from main.models import SubscriptionPrice

class Command(BaseCommand):
    help = 'delete null sub prices'

    def handle(self, *args, **kwargs):
        sub_prices = SubscriptionPrice.objects.filter(subscription__name__isnull=True)
        sub_prices.delete()
        self.stdout.write(self.style.SUCCESS('Sub prices deleted'))