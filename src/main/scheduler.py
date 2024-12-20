from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.core.management import call_command
from datetime import datetime

scheduler = None  # Global scheduler instance

def start_scheduler():
    global scheduler
    if scheduler is None:  # Check if scheduler is already initialized
        scheduler = BackgroundScheduler()
        scheduler.add_jobstore(DjangoJobStore(), "default")

        # Check if jobs already exist, only add if they don't
        # set 12 hours for proper updates with higher cost
        if not scheduler.get_job("dailytasks"):
            scheduler.add_job(run_daily_tasks, 'interval', days=30, id="dailytasks", replace_existing=True)
            
        # set 12 hours for proper updates with higher cost
        if not scheduler.get_job("sync_subs"):
            scheduler.add_job(sync_subs, 'interval', days=30, id="sync_subs", replace_existing=True)
        
        if not scheduler.get_job("clear_dangling_subs"):
            # Schedule `clear_dangling_subs` for monthly execution
            scheduler.add_job(clear_dangling_subs, 'interval', days=30, id="clear_dangling_subs", replace_existing=True)
        
        scheduler.start()  # Start the scheduler without interrupting current jobs


def run_daily_tasks():
    call_command('dailytasks')

def sync_subs():
    call_command("sync_user_subs", "--day-start", "0", "--day-end", "1")

def clear_dangling_subs():
    call_command("sync_user_subs", "--clear-dangling")
