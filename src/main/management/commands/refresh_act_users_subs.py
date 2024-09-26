from typing import Any
from django.core.management.base import BaseCommand
import logging
from views_functions import refresh_active_users_subscriptions


logger = logging.getLogger(__name__)


class Command(BaseCommand):

    def handle(self, *args: Any, **options: Any):
        try:
            refresh_active_users_subscriptions()
            self.stdout.write(self.style.SUCCESS('Successfully refreshed all active users subs'))
            logger.info('refreshed all active users subs successfully')
        except Exception as e:
            logger.error(f'Error executing my_command: {e}')
            self.stdout.write(self.style.ERROR(f'Error: {e}'))