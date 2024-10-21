from django.core.management.base import BaseCommand

from ...models import CommodityPrice, Commodity
import logging
logger = logging.getLogger(__name__)
import datetime

class Command(BaseCommand):
    help = 'It updates current, future and projected prices and corresponding model values and sends email notifications afterwards.'

    def handle(self, *args, **kwargs):
        try:
            # Update ONS prices and dates in dict below
            for com_name, data in commodities_data.items():
                com = Commodity.objects.get(name=com_name)
                com_price, created = CommodityPrice.objects.get_or_create(
                    commodity=com,
                    date=data["date"],
                    defaults={'price': data['new_price']}
                    )

                if created:
                    print(f'Commodity Price for {com_name} created')
                else:
                    com_price.price = data['new_price']
                    com_price.save()
                    print(f'Commodity Price for {com_name} updated')
            logger.info('Manual ONS prices update executed successfully')
        except Exception as e:
            logger.error(f'Error executing my_command: {e}')
            self.stdout.write(self.style.ERROR(f'Error: {e}'))




commodities_data = {
    "Chemical": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/gax4/ppi",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
        "date": datetime.datetime(year=2024, month=9, day=1),
        "new_price":131.9,
    },
    "Clay": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/g32g/ppi",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
        "date": datetime.datetime(year=2024, month=9, day=1),
        "new_price":177,
    },
    "Construction labour UK": {
        "url": "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/timeseries/k5ah/emp",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
        "date": datetime.datetime(year=2024, month=8, day=1),
        "new_price":210,
    },
    "Glass": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/g32e/ppi",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
        "date": datetime.datetime(year=2024, month=9, day=1),
        "new_price":137.7,
    },
    "Inflation UK": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/l55o/mm23",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "%",
        "date": datetime.datetime(year=2024, month=9, day=1),
        "new_price":2.6,
    },
    "Labour UK": {
        "url": "https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/bulletins/averageweeklyearningsingreatbritain/latest",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "GBP",
        "date": datetime.datetime(year=2024, month=8, day=1),
        "new_price":693,
    },
    "Other": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/producerpriceinflation/september2024includingservicesjulytoseptember2024",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
        "date": datetime.datetime(year=2024, month=9, day=1),
        "new_price":145.9,
    },
    "Water": {
        "url": "https://www.ons.gov.uk/economy/inflationandpriceindices/timeseries/dobs/mm23",
        "source": "ONS",
        "frequency": "Monthly",
        "update": "7w",
        "currency": "Index",
        "date": datetime.datetime(year=2024, month=9, day=1),
        "new_price":647.4,
    }
}