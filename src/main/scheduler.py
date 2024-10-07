from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management import call_command
from datetime import datetime, timedelta

scheduler = None  # Global scheduler instance

def start_scheduler():
    global scheduler
    if scheduler is None:  # Check if scheduler is already initialized
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.remove_all_jobs()

        # Schedule the `run_daily_tasks` command to run every 24 hours
        job = scheduler.add_job(run_daily_tasks, 'interval', hours=24, id="dailytasks", replace_existing=True)

        scheduler.start()


def run_daily_tasks():
    call_command('dailytasks')