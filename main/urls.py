from django.contrib import admin
from django.urls import path
from . import views
from django.urls import path


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
    path("login/", views.user_login, name="login"), # user_login not login to avoid clash with django function
    path("register/", views.register, name="register"),
    path("logout/", views.user_logout, name="logout"), # user_logout not login to avoid clash with django function
    path("password_reset/", views.password_reset, name="password_reset"),
    path('reset/<uidb64>/<token>/', views.reset_link, name='password_reset_confirm'),
    path('edit-product/<str:slug>', views.edit_product, name="edit_product"),
    path('delete-product/<str:slug>', views.delete_product, name="delete_product"),
    path('change-product-to-project/<int:product_id>/', views.change_product_to_project, name='change_product_to_project'),
    path('new-project/', views.new_project, name="new_project"),
    path('edit-project-name/', views.edit_project_name, name="edit_project_name"),
    path('delete-project/', views.delete_project, name="delete_project"),
    path('set-notification/', views.set_notification, name="set_notification")
]