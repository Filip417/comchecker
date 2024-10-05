from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management import call_command

scheduler = None  # Global scheduler instance

def start():
    global scheduler
    if scheduler is None:  # Check if scheduler is already initialized
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.remove_all_jobs()

        # Schedule the `scheduled_test` command to run every minute
        scheduler.add_job(run_scheduled_test, 'interval', minutes=1, id='scheduled_test', replace_existing=True)

        scheduler.add_job(run_daily_tasks, 'interval', hours=24, id="dailytasks", replace_existing=True)

        scheduler.start()

def run_scheduled_test():
    # Calls the custom Django management command
    call_command('scheduled_test')

def run_daily_tasks():
    call_command('dailytasks')