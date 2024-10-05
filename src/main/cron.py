from models import Commodity

def my_scheduled_job():
    commodity = Commodity.objects.get(id=1)
    commodity.price_now += 1
    commodity.save()