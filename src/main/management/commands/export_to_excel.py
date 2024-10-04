import pandas as pd
from django.core.management.base import BaseCommand
from main.models import Product, Currency, Commodity, CommodityProduction, MaterialProportion, CommodityPrice

class Command(BaseCommand):
    help = 'Exports data from multiple models into an Excel file'

    def handle(self, *args, **kwargs):
        # Create an Excel writer object
        with pd.ExcelWriter('exported_db_data.xlsx', engine='openpyxl') as writer:
            # Export Product data
            product_data = Product.objects.all().values()
            df_product = pd.DataFrame(list(product_data))
            df_product.to_excel(writer, sheet_name='Product Data', index=False)

            # Export Currency data
            currency_data = Currency.objects.all().values()
            df_currency = pd.DataFrame(list(currency_data))
            df_currency.to_excel(writer, sheet_name='Currency Data', index=False)

            # Export Commodity data
            commodity_data = Commodity.objects.all().values()
            df_commodity = pd.DataFrame(list(commodity_data))
            df_commodity.to_excel(writer, sheet_name='Commodity Data', index=False)

            # Export CommodityProduction data
            commodity_production_data = CommodityProduction.objects.all().values()
            df_commodity_production = pd.DataFrame(list(commodity_production_data))
            df_commodity_production.to_excel(writer, sheet_name='Commodity Production Data', index=False)

            # Export MaterialProportion data
            material_proportion_data = MaterialProportion.objects.all().values()
            df_material_proportion = pd.DataFrame(list(material_proportion_data))
            df_material_proportion.to_excel(writer, sheet_name='Material Proportion Data', index=False)

            # Export CommodityPrice data
            commodity_price_data = CommodityPrice.objects.all().values()
            df_commodity_price = pd.DataFrame(list(commodity_price_data))
            df_commodity_price.to_excel(writer, sheet_name='Commodity Price Data', index=False)

        self.stdout.write(self.style.SUCCESS('Data exported successfully to exported_data.xlsx'))