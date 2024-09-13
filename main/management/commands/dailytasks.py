from django.core.management.base import BaseCommand
import logging
from ...update_prices import (
    update_currencies,
    add_1y_increase_to_commodities,
    add_1y_increase_to_products,
    add_price_now, add_top_value_commodities,
    update_total_production,
    get_live_prices,
    get_live_prices_commodities,
    save_to_excel,
    update_live_commodity_prices,
    futures_commodities_data_input,
    update_futures_prices_in_db,
    check_all_notifications_and_send_emails,
)

from ...project_pricesv2 import (
    update_forecast_prices
)
import os
from ...models import Product, Commodity
logger = logging.getLogger(__name__)

from django.conf import settings

class Command(BaseCommand):
    help = 'Describe what your command does here'

    def handle(self, *args, **kwargs):
        try:
            # Currencies
            # API_KEY = settings.CURRENCIES_API_KEY
            # update_currencies(API_KEY)

            # # Live prices
            # new_dict = get_live_prices_commodities(commodities_data)
            # directory_to_save = r'C:\Users\sawin\Documents\Commodity Project\django_project\comchecker\main'
            # save_to_excel(new_dict, directory_to_save)
            # update_live_commodity_prices(new_dict)

            # # Futures prices
            # futures_commodities_data = get_live_prices(futures_commodities_data_input)
            # update_futures_prices_in_db(futures_commodities_data)

            # # Update values
            # products = Product.objects.all()
            # commodities = Commodity.objects.all()
            # add_1y_increase_to_products(products)
            # add_1y_increase_to_commodities(commodities)
            # add_price_now(commodities)
            # add_top_value_commodities(products)
            # update_total_production(commodities)

            # Forecast prices
            # update_forecast_prices()

            # Check notifications
            check_all_notifications_and_send_emails()

            self.stdout.write(self.style.SUCCESS('Successfully executed dailytasks'))
            logger.info('dailytasks executed successfully')
        except Exception as e:
            logger.error(f'Error executing my_command: {e}')
            self.stdout.write(self.style.ERROR(f'Error: {e}'))




commodities_data = {
    "Aggregate": {
        "url": "https://fred.stlouisfed.org/series/WPS1321",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Argon": {
        "url": "https://fred.stlouisfed.org/series/PCU325120325120C",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Cement": {
        "url": "https://fred.stlouisfed.org/series/PCU32733273",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Electronics": {
        "url": "https://fred.stlouisfed.org/series/PCU334334",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Ethanol": {
        "url": "https://fred.stlouisfed.org/series/WPU06140341",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Fibre Glass": {
        "url": "https://fred.stlouisfed.org/series/PCU326199326199A",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Glue": {
        "url": "https://fred.stlouisfed.org/series/PCU325520325520P",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Granite": {
        "url": "https://fred.stlouisfed.org/series/PCU3279913279911",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Gypsum": {
        "url": "https://fred.stlouisfed.org/series/PCU3274203274201",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Limestone": {
        "url": "https://fred.stlouisfed.org/series/PCU2123122123120",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Marble": {
        "url": "https://fred.stlouisfed.org/series/PCU3279913279917",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Metal": {
        "url": "https://fred.stlouisfed.org/series/PMETAINDEXM",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Mineral Wool": {
        "url": "https://fred.stlouisfed.org/series/PCU3279933279934",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Nylon": {
        "url": "https://fred.stlouisfed.org/series/WPU031",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Organic Chemical": {
        "url": "https://fred.stlouisfed.org/series/WPU0614",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Paper": {
        "url": "https://fred.stlouisfed.org/series/WPU0911",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Stainless Steel": {
        "url": "https://fred.stlouisfed.org/series/WPU10170674",
        "source": "FRED",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Chromium": {
        "url": "https://www.investing.com/commodities/chromium-99-min-china-futures",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "CNY",
    },
    "Kraft Pulp": {
        "url": "https://uk.investing.com/commodities/shfe-bleached-softwood-kraft-pulp-futures-historical-data",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "CNY",
    },
    "Lithium": {
        "url": "https://uk.investing.com/commodities/lithium-carbonate-99.5-min-china-futures",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "CNY",
    },
    "Lumber": {
        "url": "https://uk.investing.com/commodities/lumber-historical-data",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "USD",
    },
    "Palladium": {
        "url": "https://uk.investing.com/commodities/palladium-historical-data",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "USD",
    },
    "Polyethylene": {
        "url": "https://uk.investing.com/commodities/lldpe-futures-historical-data",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "CNY",
    },
    "Polypropylene": {
        "url": "https://uk.investing.com/commodities/pp-futures",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "CNY",
    },
    "Polyvinyl": {
        "url": "https://uk.investing.com/commodities/pvc-com-futures-historical-data",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "CNY",
    },
    "Rubber": {
        "url": "https://www.investing.com/commodities/rubber-tsr20-futures-historical-data",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "USD",
    },
    "Steel": {
        "url": "https://uk.investing.com/commodities/steel-rebar",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "USD",
    },
    "Steel Scrap": {
        "url": "https://uk.investing.com/commodities/steel-scrap",
        "source": "Investing.com",
        "frequency": "Live",
        "update": "Live",
        "currency": "USD",
    },
    "Chemical": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/gax4/ppi",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Clay": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/g32g/ppi",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Construction labour UK": {
        "url": "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/k5ah/emp",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Glass": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/g32e/ppi",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Inflation UK": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/l55o/mm23",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "%",
    },
    "Labour UK": {
        "url": "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/bulletins/averageweeklyearningsingreatbritain/latest",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "GBP",
    },
    "Other": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/producerpriceinflation/june2024includingservicesapriltojune2024",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Water": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/dobs/mm23",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Aluminium": {
        "url": "https://tradingeconomics.com/commodity/aluminum",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-lmahds03",
        "currency": "USD",
    },
    "Coal": {
        "url": "https://tradingeconomics.com/commodity/coal",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-xal1",
        "currency": "USD",
    },
    "Cobalt": {
        "url": "https://tradingeconomics.com/commodity/cobalt",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-lco1",
        "currency": "USD",
    },
    "Construction activity UK": {
        "url": "https://www.investing.com/economic-calendar/construction-pmi-44",
        "source": "Investing.com v2",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
    },
    "Containerized Freight China-Europe": {
        "url": "https://tradingeconomics.com/commodity/containerized-freight-index",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-spscfi",
        "currency": "USD",
    },
    "Copper": {
        "url": "https://tradingeconomics.com/commodity/copper",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-hg1",
        "currency": "USD",
    },
    "Cotton": {
        "url": "https://tradingeconomics.com/commodity/cotton",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id":"Label-ct1",
        "currency": "USD",
    },
    "Crude Oil": {
        "url": "https://tradingeconomics.com/commodity/crude-oil",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id":"Label-cl1",
        "currency": "USD",

    },
    "Electricity UK": {
        "url": "https://tradingeconomics.com/united-kingdom/electricity-price",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-gbrelepri",
        "currency": "GBP",
    },
    "EU Carbon Permits": {
        "url": "https://tradingeconomics.com/commodity/carbon",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-eecxm",
        "currency": "EUR",
    },
    "Gold": {
        "url": "https://tradingeconomics.com/commodity/gold",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-xauusd",
        "currency": "USD",
    },
    "Iron Ore": {
        "url": "https://tradingeconomics.com/commodity/iron-ore",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-sco",
        "currency": "USD",
    },
    "Lead": {
        "url": "https://tradingeconomics.com/commodity/lead",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-ll1",
        "currency": "USD",
    },
    "Natural Gas": {
        "url": "https://tradingeconomics.com/commodity/natural-gas",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-ng1",
        "currency": "USD",
    },
    "Nickel": {
        "url": "https://tradingeconomics.com/commodity/nickel",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-ln1",
        "currency": "USD",
    },
    "Silver": {
        "url": "https://tradingeconomics.com/commodity/silver",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-xagusd",
        "currency": "USD",
    },
    "Tin": {
        "url": "https://tradingeconomics.com/commodity/tin",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-lmsnds03",
        "currency": "USD",
    },
    "Zinc": {
        "url": "https://tradingeconomics.com/commodity/zinc",
        "source": "Trading Economics",
        "frequency": "Live",
        "update": "Live",
        "element_id": "Label-lmzsds03",
        "currency": "USD",
    }
}