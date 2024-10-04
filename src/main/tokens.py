from django.contrib.auth.tokens import PasswordResetTokenGenerator

class EmailNotificationTokenGenerator(PasswordResetTokenGenerator):
    pass

email_notification_token = EmailNotificationTokenGenerator()