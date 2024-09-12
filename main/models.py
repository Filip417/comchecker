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
    created_at = models.DateTimeField(default=timezone.now)  # Change to DateTimeField

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
    viewed_at = models.DateTimeField(default=timezone.now)

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

    created_at = models.DateTimeField(default=timezone.now)
    activated = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    seen_activated = models.BooleanField(default=False)
    seen_activated_at = models.DateTimeField(null=True, blank=True)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        if self.product:
            return f"Notification of Product: {self.product.name} {self.change} by {self.change_by} at {self.viewed_at}"
        elif self.commodity:
            return f"Notification of Commodity: {self.commodity.name} {self.change} by {self.change_by} at {self.viewed_at}"
        return "View Record"


@receiver(post_save, sender=MaterialProportion)
@receiver(post_delete, sender=MaterialProportion)
def update_unique_commodities_count(sender, instance, **kwargs):
    product = instance.product
    # Update the unique commodities count based on the distinct commodities in MaterialProportion
    product.unique_commodities_count = product.material_proportions.values('commodity').distinct().count()
    product.save(update_fields=['unique_commodities_count'])  # Only save the updated field


