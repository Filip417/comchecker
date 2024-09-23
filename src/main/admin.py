from django.contrib import admin
from main.models import (
    Product, 
    MaterialProportion, 
    Commodity, 
    CommodityProduction, 
    Currency, 
    CommodityPrice,
    Subscription,
    UserProfile,
    View,
    Notification,
    UserSubscription,
    SubscriptionPrice
)

# Register your models here.
admin.site.register(Product)
admin.site.register(Commodity)
admin.site.register(CommodityProduction)
admin.site.register(MaterialProportion)
admin.site.register(Currency)
admin.site.register(CommodityPrice)
admin.site.register(UserProfile)
admin.site.register(View)
admin.site.register(Notification)


# Subscriptions
class SubscriptionPrice(admin.TabularInline):
    model = SubscriptionPrice
    readonly_fields = ['stripe_id']
    can_delete = False
    extra = 0

class SubscriptionAdmin(admin.ModelAdmin):
    inlines = [SubscriptionPrice]
    list_display = ['name', 'active']
    readonly_fields = ['stripe_id']

admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(UserSubscription)