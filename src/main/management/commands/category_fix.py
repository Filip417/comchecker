import pandas as pd
from django.core.management.base import BaseCommand
from main.models import Product, Currency, Commodity, CommodityProduction, MaterialProportion, CommodityPrice, Subscription, SubscriptionPrice

class Command(BaseCommand):
    help = 'Category fix'

    def handle(self, *args, **kwargs):
        products_dw = Product.objects.filter(category_3="Doors & Windows")
        for p in products_dw:
            p.category_3 = "Doors, Windows"
            p.save()

        products_pbs = Product.objects.filter(category_3="Panels, Boards & Structural")
        for p in products_pbs:
            p.category_3 = "Panels, Boards, Structural"
            p.save()

        products_ph = Product.objects.filter(category_3="Plumbing & HVAC")
        for p in products_ph:
            p.category_3 = "Plumbing, HVAC"
            p.save()

        self.stdout.write(self.style.SUCCESS('Categories fixed'))