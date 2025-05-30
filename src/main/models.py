from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models import Sum
from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models
from django.utils import timezone
import datetime
import random
import string
import helpers.billing
from django.db import models
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.urls import reverse
from django.db.models import Q
from django.db.models import UniqueConstraint

### Subscriptions - for Stripe ###

ALLOW_CUSTOM_GROUPS = True
SUBSCRIPTION_PERMISSIONS = [
            ("standard","Standard Perm"), # subscriptions.standard
            ("unlimited","Unlimited Perm"), # subscriptions.unlimited
        ]

class Subscription(models.Model):
    """
    Subscription = Stripe Product
    """
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)
    groups = models.ManyToManyField(Group) # can be one to one depending on usage TODO
    permissions = models.ManyToManyField(Permission,
        limit_choices_to={
            "content_type__app_label":"main",
            "codename__in":[x[0] for x in SUBSCRIPTION_PERMISSIONS]
            }
        )
    stripe_id = models.CharField(max_length=120, null=True, blank=True)
    order = models.IntegerField(default=-1, help_text='Ordering on Django pricing page')
    featured = models.BooleanField(default=True, help_text='Featured on Django pricing page')
    updated = models.DateField(auto_now=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField(help_text="Plan description e.g. who is it for",
                                   blank=True, null=True)
    features = models.TextField(help_text="Features for pricing, seperated by new line",
                                blank=True, null=True)

    class Meta:
        ordering = ['order', 'featured', '-updated']
        permissions = SUBSCRIPTION_PERMISSIONS

    def get_features_as_list(self):
        if not self.features:
            return []
        return [x.strip() for x in self.features.split('\n')]
    

    def save(self, *args, **kwargs):
        if not self.stripe_id:
            stripe_id = helpers.billing.create_product(name=self.name,
                    metadata={"subscription_plan_id":self.id,
                              }, raw=False)
            self.stripe_id = stripe_id  
        super().save(*args, **kwargs)

    
    def __str__(self):
        return f"{self.name}"

    class Meta:
        permissions = SUBSCRIPTION_PERMISSIONS


class SubscriptionPrice(models.Model):
    """
    Subscription Price = Stripe Price
    """
    class IntervalChoices(models.TextChoices):
        MONTHLY = "month", "Monthly"
        YEARLY = "year", "Yearly"

    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True)
    stripe_id = models.CharField(max_length=120, null=True, blank=True)
    interval = models.CharField(max_length=120,
                                default=IntervalChoices.MONTHLY,
                                choices=IntervalChoices.choices)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=99.00)
    order = models.IntegerField(default=-1, help_text='Ordering on Django pricing page')
    featured = models.BooleanField(default=True, help_text='Featured on Django pricing page')
    updated = models.DateField(auto_now=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['subscription__order', 'order', 'featured', '-updated']

    def get_checkout_url(self):
        return reverse("sub-price-checkout", kwargs= {"price_id": self.id})

    @property
    def display_features_list(self):
        if not self.subscription:
            return []
        return self.subscription.get_features_as_list()


    @property
    def display_sub_name(self):
        if not self.subscription.name:
            return "Plan"
        return self.subscription.name
    
    @property
    def product_stripe_id(self):
        if not self.subscription:
            return None
        return self.subscription.stripe_id
    
    @property
    def stripe_currency(self):
        return "gbp"
    
    @property
    def stripe_price(self):
        """
        remove decimal places for stripe
        """
        return int(self.price * 100)
    
    def save(self, *args, **kwargs):
        if (not self.stripe_id and
            self.product_stripe_id is not None):
            stripe_id = helpers.billing.create_price(
            currency=self.stripe_currency,
            unit_amount=self.stripe_price,
            interval=self.interval,
            product=self.product_stripe_id,
            metadata={
                "subscription_plan_price_id":self.id
            },
            raw=False
            )
            self.stripe_id = stripe_id
        super().save(*args, **kwargs)
        if self.featured and self.subscription:
            qs = SubscriptionPrice.objects.filter(
                subscription=self.subscription,
                interval=self.interval
            ).exclude(id=self.id)
            qs.update(featured=False)


class SubscriptionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    TRIALING = 'trialing', 'Trialing'
    INCOMPLETE = 'incomplete', 'Incomplete'
    INCOMPLETE_EXPIRED = 'incomplete_expired', 'Incomplete Expired'
    PAST_DUE = 'past_due', 'Past Due'
    CANCELED = 'canceled', 'Canceled'
    UNPAID = 'unpaid', 'Unpaid'
    PAUSED = 'paused', 'Paused'


class UserSubscriptionQuerySet(models.QuerySet):
    def by_range(self, days_start=7, days_end=120, verbose=True):
        now = timezone.now()
        days_start_from_now = now + datetime.timedelta(days=days_start)
        days_end_from_now = now + datetime.timedelta(days=days_end)
        range_start = days_start_from_now.replace(hour=0, minute=0, second=0, microsecond=0)
        range_end = days_end_from_now.replace(hour=23, minute=59, second=59, microsecond=59)
        if verbose:
            print(f"Range is {range_start} to {range_end}")
        return self.filter(
            current_period_end__gte=range_start,
            current_period_end__lte=range_end
        )
    
    def by_days_left(self, days_left=7):
        now = timezone.now()
        in_n_days = now + datetime.timedelta(days=days_left)
        day_start = in_n_days.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = in_n_days.replace(hour=23, minute=59, second=59, microsecond=59)
        return self.filter(
            current_period_end__gte=day_start,
            current_period_end__lte=day_end
        )
    
    def by_days_ago(self, days_ago=3):
        now = timezone.now()
        in_n_days = now - datetime.timedelta(days=days_ago)
        day_start = in_n_days.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = in_n_days.replace(hour=23, minute=59, second=59, microsecond=59)
        return self.filter(
            current_period_end__gte=day_start,
            current_period_end__lte=day_end
        )

    def by_active_trialing(self):
        active_qs_lookup = (
            Q(status = SubscriptionStatus.ACTIVE) |
            Q(status = SubscriptionStatus.TRIALING)
        )
        return self.filter(active_qs_lookup)
    
    def by_user_ids(self, user_ids=None):
        qs = self
        if isinstance(user_ids, list):
            qs = self.filter(user_id__in=user_ids)
        elif isinstance(user_ids, int):
            qs = self.filter(user_id__in=[user_ids])
        elif isinstance(user_ids, str):
            qs = self.filter(user_id__in=[user_ids])
        return qs


class UserSubscriptionManager(models.Manager):
    def get_queryset(self):
        return UserSubscriptionQuerySet(self.model, using=self._db)

    # def by_user_ids(self, user_ids=None):
    #     return self.get_queryset().by_user_ids(user_ids=user_ids)
       

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    stripe_id = models.CharField(max_length=120, null=True, blank=True)
    active = models.BooleanField(default=True)
    user_cancelled = models.BooleanField(default=False)
    original_period_start = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    current_period_start = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    current_period_end = models.DateTimeField(auto_now=False, auto_now_add=False, blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    status = models.CharField(max_length=20,
                              choices=SubscriptionStatus.choices, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    currency = models.CharField(max_length=10, default='gbp')
    interval = models.CharField(max_length=20, default="month")
    price = models.IntegerField(default=0)

    objects = UserSubscriptionManager()

    def get_absolute_url(self):
        return reverse("pricing-view")
    
    def get_cancel_url(self):
        return reverse("pricing-view-cancel")
    
    @property
    def is_active_status(self):
        return self.status in [SubscriptionStatus.ACTIVE,
                               SubscriptionStatus.TRIALING]
    
    @property
    def plan_name(self):
        if not self.subscription:
            return None
        return self.subscription.name

    def serialize(self):
        return {
            "plan_name": self.plan_name,
            "status": self.status,
            "current_period_start": self.current_period_start,
            "current_period_end": self.current_period_end,
            "currency":self.currency,
            "cancel_at_period_end":self.cancel_at_period_end,
            "interval":self.interval,
            "price":self.price,
            "is_active_status":self.is_active_status,
        }

    @property
    def billing_cycle_anchor(self):
        """
        https://docs.stripe.com/payments/checkout/billing-cycle?locale=en-GB
        Optional delay to start new subscription in 
        Stripe checkout
        """
        if self.current_period_end:
            return None
        return int(self.current_period_end.timestamp())

    def save(self, *args, **kwargs):
        if self.original_period_start is None and self.current_period_start is not None:
            self.original_period_start = self.current_period_start
        super().save(*args, **kwargs)


def user_sub_post_save(sender, instance, *args, **kwargs):
    user_sub_instance = instance
    user = user_sub_instance.user
    subscription_obj = user_sub_instance.subscription
    groups_ids = []
    if subscription_obj is not None:
        groups = subscription_obj.groups.all()
        groups_ids = groups.values_list('id', flat=True)
    if not ALLOW_CUSTOM_GROUPS:
        user.groups.set(groups_ids)
    else:
        subs_qs = Subscription.objects.filter(active=True)
        if subscription_obj is not None:
            subs_qs = subs_qs.exclude(id=subscription_obj.id)
        subs_groups = subs_qs.values_list("groups__id", flat=True)
        subs_groups_set = set(subs_groups)
        # groups_ids = groups.values_list('id', flat=True) # [1, 2, 3] 
        current_groups = user.groups.all().values_list('id', flat=True)
        groups_ids_set = set(groups_ids)
        current_groups_set = set(current_groups) - subs_groups_set
        final_group_ids = list(groups_ids_set | current_groups_set)
        user.groups.set(final_group_ids)


post_save.connect(user_sub_post_save, sender=UserSubscription)



### App models ###

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_notification = models.BooleanField(default=True)
    cookie_essential = models.BooleanField(default=True)
    cookie_personalisation = models.BooleanField(default=False)
    
    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=50)
    symbol = models.CharField(max_length=10, blank=True, null=True)
    date = models.DateField()
    rate = models.FloatField(blank=True, null=True, )

    def __str__(self):
        return self.code


class Commodity(models.Model):
    # Relationships
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(max_length=100)
    futures = models.BooleanField(default=False)
    category = models.CharField(max_length=100, null=True, blank=True)
    price_update_date = models.DateField(null=True, blank=True)
    price_now = models.FloatField(null=True, blank=True)
    price_for_kg = models.FloatField(null=True, blank=True)
    rate_for_price_kg = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    price_source = models.CharField(max_length=256)
    count_of_products_with = models.IntegerField(null=True, blank=True)
    price_history_source = models.CharField(max_length=256)
    price_history_name = models.CharField(max_length=256)
    price_history_type = models.CharField(max_length=20)
    production_date = models.DateField(null=True, blank=True)
    production_unit = models.CharField(max_length=256, null=True, blank=True)
    production_source = models.CharField(max_length=256, null=True, blank=True)
    production_name = models.CharField(max_length=256, null=True, blank=True)
    production_total = models.BigIntegerField(null=True, blank=True)
    basic_description = models.TextField()
    use = models.TextField(null=True, blank=True)
    world_total = models.TextField(null=True, blank=True)
    events_trends_issues = models.TextField(null=True, blank=True)
    substitutes = models.TextField(null=True, blank=True)
    recycling = models.TextField(null=True, blank=True)
    increasefromlastyear = models.FloatField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    image_format = models.CharField(max_length=5, blank=True, null=True)

    def __str__(self):
        return self.name
    
    def update_production_total(self):
        total_production = self.commodityproduction_set.aggregate(Sum('production'))['production__sum'] or 0
        self.production_total = round(total_production)
        self.save()

    def add_view(self, user=None):
        self.view_count = F('view_count') + 1
        self.save()
        self.refresh_from_db()
        View.objects.create(commodity=self, user=user)
    
class Product(models.Model):
    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    top_value_commodity = models.ForeignKey(Commodity, on_delete=models.SET_NULL, null=True, blank=True)

    # Fields with data
    epd_id = models.IntegerField(null=True)
    slug = models.SlugField(max_length=255, null=True, unique=True)
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=500, null=True, blank=True)
    product_img_url = models.TextField(null=True, blank=True)
    description = models.TextField(null=True)
    pcr = models.CharField(max_length=256, null=True, blank=True) 
    pcr_category = models.CharField(max_length=255, null=True, blank=True)
    category_1 = models.CharField(max_length=255, null=True, blank=True)
    category_2 = models.CharField(max_length=255, null=True, blank=True)
    category_3 = models.CharField(max_length=255, null=True, blank=True)
    reg_date = models.DateField(null=True)
    version_date = models.DateField(null=True, blank=True)
    geographical_scopes = models.CharField(max_length=255, null=True, blank=True)
    manufacturer_name = models.CharField(max_length=255, null=True, blank=True)
    manufacturer_country = models.CharField(max_length=255, null=True, blank=True)
    manufacturer_website = models.URLField(null=True, blank=True)
    included_products_in_this_epd = models.TextField(null=True, blank=True)
    manufacturer_img_url = models.URLField(null=True, blank=True)
    increasefromlastyear = models.FloatField(null=True, blank=True)
    unique_commodities_count = models.IntegerField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    first_prod_image_format = models.CharField(max_length=5, blank=True, null=True)
    first_man_image_format = models.CharField(max_length=5, blank=True, null=True)
    # Price points adjusted for today = 100
    ago_5y =  models.FloatField(null=True, blank=True)
    ago_2y = models.FloatField(null=True, blank=True)
    ago_1y = models.FloatField(null=True, blank=True)
    ago_6m = models.FloatField(null=True, blank=True)
    today = models.FloatField(null=True, blank=True)
    ahead_6m = models.FloatField(null=True, blank=True)
    ahead_1y = models.FloatField(null=True, blank=True)
    ahead_2y = models.FloatField(null=True, blank=True)
    ahead_5y = models.FloatField(null=True, blank=True)

    def __str__(self):
        return self.name
    
    def add_view(self, user=None):
        self.view_count = F('view_count') + 1
        self.save()
        self.refresh_from_db()
        View.objects.create(product=self, user=user)
    
    @property
    def price_history_sources(self):
        # Distinct list of price history sources from commodities in material proportions
        return list(self.material_proportions.values_list('commodity__price_history_source', flat=True).distinct())

    @property
    def production_sources(self):
        # Distinct list of production sources from commodities in material proportions
        return list(self.material_proportions.values_list('commodity__production_source', flat=True).distinct())
    
    def save(self, *args, **kwargs):
    # Automatically generate slug from name if not provided
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        if self.ago_1y is not None and self.ago_1y != 0:
            self.increasefromlastyear = float((self.today - self.ago_1y) / self.ago_1y * 100)
        else:
            self.increasefromlastyear = None  # or set to 0 if preferred

        super().save(*args, **kwargs)

    def create_new_slug(self):
        self.slug = self.generate_unique_slug()
    
    def generate_unique_slug(self):
        def generate_random_string(length=8):
            """Generate a random string of fixed length."""
            characters = string.ascii_lowercase + string.digits
            return ''.join(random.choice(characters) for _ in range(length))
        base_slug = slugify(self.name)
        random_suffix = generate_random_string()
        unique_slug = base_slug + random_suffix
        num = 1
        while Product.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{num}"
            num += 1
        return unique_slug


class Project(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, related_name='owned_projects')
    shared_with = models.ManyToManyField(User, related_name='shared_projects', blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Change to DateTimeField

    # Many-to-many relationships
    products = models.ManyToManyField(Product, related_name='projects', blank=True)
    commodities = models.ManyToManyField(Commodity, related_name='projects', blank=True)

    unique_commodities_count = models.IntegerField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    increasefromlastyear = models.FloatField(null=True, blank=True)

    def add_view(self, user=None):
        self.view_count = F('view_count') + 1
        self.save()
        self.refresh_from_db()
        # Record the view in the View model
        View.objects.create(project=self, user=user)

    def generate_unique_slug(self):
        def generate_random_string(length=8):
            """Generate a random string of fixed length."""
            characters = string.ascii_lowercase + string.digits
            return ''.join(random.choice(characters) for _ in range(length))
        base_slug = slugify(self.name)
        random_suffix = generate_random_string()
        unique_slug = base_slug + random_suffix
        num = 1
        while Project.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{base_slug}-{num}"
            num += 1
        return unique_slug

    def save(self, *args, **kwargs):
        # Ensure slug is generated
        if not self.slug:
            self.slug = self.generate_unique_slug()

        super().save(*args, **kwargs)

    def calculate_increase(self):
        product_increase_sum = 0.0
        total_items = 0

        # Iterate through the products to calculate the increase
        for product in self.products.all():
            if product.ago_1y is not None and product.ago_1y != 0:
                increase = (product.today - product.ago_1y) / product.ago_1y * 100
                product_increase_sum += increase
                total_items += 1

        # Update the increasefromlastyear for the project
        if total_items > 0:
            self.increasefromlastyear = product_increase_sum / total_items
        else:
            self.increasefromlastyear = None  # or set a default value if desired

        self.save()
        
    
    def __str__(self):
        return self.name

class MaterialProportion(models.Model):
    # ForeignKey relationships
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='material_proportions')
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, related_name='material_proportions', null=True)

    # Material fields
    material_proportion_other_id = models.IntegerField(null=True)
    material = models.CharField(max_length=255, blank=False, null=False)
    proportion = models.FloatField(blank=False, null=False, )
    unit = models.CharField(max_length=52, default='%')

    def __str__(self):
        return f"{self.material} ({self.proportion}{self.unit}) - {self.commodity.name} for {self.product.name}"


class CommodityProduction(models.Model):
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, null=True)
    country_code = models.CharField(max_length=3)
    country_name = models.CharField(max_length=100)
    production = models.FloatField()
    unit = models.CharField(max_length=50)
    date = models.DateField()

    def __str__(self):
        return f'{self.commodity.name} - {self.country_name} - {self.date}'


class CommodityPrice(models.Model):
    commodity = models.ForeignKey(Commodity, on_delete=models.SET_NULL, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.SET_NULL, null=True)
    date = models.DateField()
    price = models.FloatField(blank=True, null=True)
    projected_price = models.FloatField(blank=True, null=True)
    futures_price = models.FloatField(blank=True, null=True)
    top_90_percent = models.FloatField(blank=True, null=True)
    bottom_90_percent = models.FloatField(blank=True, null=True)
    top_75_percent = models.FloatField(blank=True, null=True)
    bottom_75_percent = models.FloatField(blank=True, null=True)
    top_50_percent = models.FloatField(blank=True, null=True)
    bottom_50_percent = models.FloatField(blank=True, null=True)
    top_25_percent = models.FloatField(blank=True, null=True)
    bottom_25_percent = models.FloatField(blank=True, null=True)
    top_10_percent = models.FloatField(blank=True, null=True)
    bottom_10_percent = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f'{self.commodity.name} - {self.currency.code} - {self.date}'

    # AFTER CLEANING DB:
    class Meta:
        constraints = [
            UniqueConstraint(fields=['commodity', 'currency', 'date'], name='unique_commodity_currency_date')
        ]

class View(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)  # Track the user who viewed
    viewed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.product:
            return f"View of Product: {self.product.name} by {self.user} at {self.viewed_at}"
        elif self.commodity:
            return f"View of Commodity: {self.commodity.name} by {self.user} at {self.viewed_at}"
        elif self.project:
            return f"View of Project: {self.project} by {self.user} at {self.viewed_at}"
        return "View Record"



class Notification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    commodity = models.ForeignKey(Commodity, on_delete=models.CASCADE, null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    change = models.FloatField()
    change_by = models.DateField()
    change_by_ml = models.CharField(max_length=2, null=True, blank=True) # input ">=" or "<="
    email_notification = models.BooleanField()

    created_at = models.DateTimeField(auto_now_add=True)
    activated = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    activated_value = models.FloatField(null=True, blank=True)
    seen_activated = models.BooleanField(default=False)
    seen_activated_at = models.DateTimeField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.product:
            return f"Notification of Product: {self.product.name} {self.change} by {self.change_by}"
        elif self.commodity:
            return f"Notification of Commodity: {self.commodity.name} {self.change} by {self.change_by}"
        return "View Record"


@receiver(post_save, sender=MaterialProportion)
@receiver(post_delete, sender=MaterialProportion)
def update_unique_commodities_count(sender, instance, **kwargs):
    product = instance.product
    # Update the unique commodities count based on the distinct commodities in MaterialProportion
    product.unique_commodities_count = product.material_proportions.values('commodity').distinct().count()
    product.save(update_fields=['unique_commodities_count'])  # Only save the updated field


