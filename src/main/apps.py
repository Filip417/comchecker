from django.apps import AppConfig
from django.db.models.signals import post_migrate



class MainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'main'

    def ready(self):
        # Start the scheduler when the Django app is ready
        from .scheduler import start_scheduler
        start_scheduler()