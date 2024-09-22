from django.db import models
from django.contrib.auth.models import User
import helpers.billing

# Create your models here.
class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_id = models.CharField(max_length=120, null=True, blank=True)
    init_email = models.EmailField(blank=True, null=True)
    init_email_confirmed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}"
    
    def save(self, *args, **kwargs):
        if not self.stripe_id:
            if self.init_email_confirmed and self.init_email:
                email = self.user.email
                if email != "" or email is not None:
                    stripe_id = helpers.billing.create_customer(email=email, raw=False)
                    self.stripe_id = stripe_id
        super().save(*args, **kwargs)