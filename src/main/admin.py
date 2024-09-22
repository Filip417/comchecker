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
    UserSubscription
)

# Register your models here.
admin.site.register(Product)
admin.site.register(Commodity)
admin.site.register(CommodityProduction)
admin.site.register(MaterialProportion)
admin.site.register(Currency)
admin.site.register(CommodityPrice)
admin.site.register(Subscription)
admin.site.register(UserProfile)
admin.site.register(View)
admin.site.register(Notification)
admin.site.register(UserSubscription)