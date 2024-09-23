from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.db.models import Sum
from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import models
from django.utils import timezone
from datetime import datetime
import random
import string
import helpers.billing
from django.db import models
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_save
from django.contrib.auth.models import User


### Subscriptions - for Stripe ###

ALLOW_CUSTOM_GROUPS = True
SUBSCRIPTION_PERMISSIONS = [
            ("lite", "Lite Perm"), # subscriptions.lite
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
    price = models.DecimalField(max_digits=10, decimal_places=2, default=99.99)
    order = models.IntegerField(default=-1, help_text='Ordering on Django pricing page')
    featured = models.BooleanField(default=True, help_text='Featured on Django pricing page')
    updated = models.DateField(auto_now=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['subscription__order', 'order', 'featured', '-updated']

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




class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True)
    active = models.BooleanField(default=True)


def user_sub_post_save(sender, instance, *args, **kwargs):
    user_sub_instance = instance
    user = user_sub_instance.user
    subscription_obj = user_sub_instance.subscription
    groups_ids = []
    if subscription_obj is not None:
        groups = subscription_obj.groups.all()
        groups_ids = groups.values_list('id', flat=True)
    groups = subscription_obj.groups.all()
    if not ALLOW_CUSTOM_GROUPS:
        user.groups.set(groups_ids)
    else:
        subs_qs = Subscription.objects.filter(active=True).exclude(id=subscription_obj.id)
        if subscription_obj is not None:
            subs_qs = subs_qs.exclude(id=subscription_obj.id)
        subs_groups = subs_qs.values_list("groups__id", flat=True)
        subs_groups_set = set(subs_groups)
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
    code = models.CharField(max_length=3, unique=True)
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
    price_source = models.CharField(max_length=100)
    count_of_products_with = models.IntegerField(null=True, blank=True)
    price_history_source = models.CharField(max_length=100)
    price_history_name = models.CharField(max_length=100)
    price_history_type = models.CharField(max_length=20)
    production_date = models.DateField(null=True, blank=True)
    production_unit = models.CharField(max_length=100, null=True, blank=True)
    production_source = models.CharField(max_length=100, null=True, blank=True)
    production_name = models.CharField(max_length=100, null=True, blank=True)
    production_total = models.IntegerField(null=True, blank=True)
    basic_description = models.TextField()
    use = models.TextField(null=True, blank=True)
    world_total = models.TextField(null=True, blank=True)
    events_trends_issues = models.TextField(null=True, blank=True)
    substitutes = models.TextField(null=True, blank=True)
    recycling = models.TextField(null=True, blank=True)
    increasefromlastyear = models.FloatField(null=True, blank=True)
    view_count = models.IntegerField(default=0)
    
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
    slug = models.SlugField(null=True, unique=True)
    name = models.CharField(max_length=255)
    original_name = models.CharField(max_length=255, null=True, blank=True)
    product_img_url = models.URLField(null=True, blank=True)
    description = models.TextField(null=True)
    pcr = models.CharField(max_length=100, null=True, blank=True) 
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
        # Calculate the average increase from last year for products and commodities
        product_increase_sum = self.products.aggregate(total=models.Sum('increasefromlastyear'))['total'] or 0
        commodity_increase_sum = self.commodities.aggregate(total=models.Sum('increasefromlastyear'))['total'] or 0
        
        total_items = self.products.count() + self.commodities.count()
        
        # Avoid division by zero
        if total_items > 0:
            self.increasefromlastyear = (product_increase_sum + commodity_increase_sum) / total_items
        else:
            self.increasefromlastyear = None  # Or set a default value if desired
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


