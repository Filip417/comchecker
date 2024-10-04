from django.core.management.base import BaseCommand
from main.update_import_into_models import main

class Command(BaseCommand):
    help = 'Imports data from excel file into the db. Excel: static\db_v1_demo\db_v_1_0.xlsx'

    def handle(self, *args, **kwargs):
        main()