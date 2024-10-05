from django.core.management.base import BaseCommand
from models import Commodity

class Command(BaseCommand):
    help = 'Imports data from excel file into the db. Excel: static\db_v1_demo\db_v_1_0.xlsx'

    def handle(self, *args, **kwargs):
        commodity = Commodity.objects.get(id=1)
        commodity.price_now += 1
        commodity.save()