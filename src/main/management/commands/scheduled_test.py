from django.core.management.base import BaseCommand
from main.models import Commodity

class Command(BaseCommand):
    help = 'Test command for scheduler'

    def handle(self, *args, **kwargs):
        print('schedule test started')
        commodity = Commodity.objects.get(id=1)
        commodity.price_now += 1
        commodity.save()
        self.stdout.write(self.style.SUCCESS('Successfully executed scheuled_test'))