from django_cron import CronJobBase, Schedule
from main.models import Commodity

class MyCronJob(CronJobBase):
    RUN_EVERY_MINS = 1 # every 1 minute

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'main.my_cron_job'    # a unique code

    def do(self):
        print('cron started')
        commodity = Commodity.objects.get(id=1)
        commodity.price_now += 1
        commodity.save()
        self.stdout.write(self.style.SUCCESS('Successfully executed scheuled_test'))