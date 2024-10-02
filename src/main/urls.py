from django.contrib import admin
from . import views
from django.urls import path, include
from checkouts import views as checkout_views
from django.conf.urls import handler404, handler400

handler404 = 'main.views.custom_404_view'
handler400 = 'main.views.custom_400_view'

urlpatterns = [
    path("",views.index,name="index"),
    path("create/",views.create, name="create"),
    path("profile/",views.profile, name="profile"),
    path("product/<str:slug>",views.product,name="product"),
    path("dashboard/", views.index_logged, name='logged'),  # Adjusted path for logged-in users
    path("search/",views.search, name="search"),
    path("notifications/",views.notifications, name="notifications"),
    path("commodity/<str:name>",views.commodity,name="commodity"),
    path("settings/",views.user_settings, name="settings"),
    path("project/<str:project_slug>",views.project,name="project"),
    path('edit-product/<str:slug>', views.edit_product, name="edit_product"),
    path('delete-product/<str:slug>', views.delete_product, name="delete_product"),
    path('change-product-to-project/<int:product_id>/', views.change_product_to_project, name='change_product_to_project'),
    path('new-project/', views.new_project, name="new_project"),
    path('edit-project-name/', views.edit_project_name, name="edit_project_name"),
    path('delete-project/', views.delete_project, name="delete_project"),
    path('set-notification/', views.set_notification, name="set_notification"),
    path('delete-notification/', views.delete_notification, name="delete_notification"),
    path('update-settings/', views.update_settings, name='update_settings'),
    path('help/', views.help, name="help"),
    path('logged-contact-form/', views.logged_contact_form, name="logged_contact_form"),
    # Account management
    path('accounts/', include('allauth.urls')),
    # Checkouts
    path("checkout/sub-price/<int:price_id>/",checkout_views.product_price_redirect_view, name="sub-price-checkout"),
    path("checkout/start/", checkout_views.checkout_redirect_view, name="stripe-checkout-start"),
    path("checkout/success/", checkout_views.checkout_finalize_view, name="stripe-checkout-end"),
    # pricing table temporary example TODO update correctly 
    path("pricing/", views.pricing, name="pricing-view"),
    path("cancel_membership/", views.user_subscription_cancel_view, name="cancel-membership"),
    path("no_membership/", views.index_logged_no_valid_membership, name="index_logged_no_valid_membership"),
    path("get_invoice_pdf/", views.get_invoice_pdf, name="get_invoice_pdf"),
]