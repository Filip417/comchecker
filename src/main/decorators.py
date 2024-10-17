from functools import wraps
from .models import Notification, View, UserSubscription, Product, Project
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404

LIMITS = {
    "standard":{
        "product_views":200,
        "commodity_views":100,
        "custom_products":20,
        "custom_projects":20,
        "monitoring_notifications":20,
    },
}


def show_new_notifications(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            # Fetch activated and new notifications for the current user
            activated_new_notifications = Notification.objects.filter(
                user=request.user, activated=True, seen_activated=False)
            # Add them to the request context
            request.new_notifications = activated_new_notifications
        else:
            request.new_notifications = []  # If the user is not authenticated, set it as empty
        # Call the view function
        return view_func(request, *args, **kwargs)
    return wrapper


def check_if_user_sub_active(user_id):
    try:
        user_sub = UserSubscription.objects.get(user_id=user_id)
        # Check if the subscription has an active status
        if user_sub.subscription and user_sub.is_active_status:
            return True
    except UserSubscription.DoesNotExist:
        # If the UserSubscription does not exist, it's considered inactive
        return False
    return False

def valid_unlimited_membership_required(view_func):
    @wraps(view_func)
    @login_required  # Ensure the user is authenticated before checking permissions
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.unlimited'):
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You have no valid Unlimited membership")
            return redirect(reverse('index_logged_no_valid_membership'))  # Redirect if the user doesn't have the required permission
    return wrapper

def valid_standard_membership_required(view_func):
    @wraps(view_func)
    @login_required  # Ensure the user is authenticated before checking permissions
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.standard') and check_if_user_sub_active(request.user.id):
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You have no valid Standard membership")
            return redirect(reverse('index_logged_no_valid_membership'))  # Redirect if the user doesn't have the required permission
    return wrapper


def logged_in_cant_access(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('logged'))  # Redirect to 'logged' view if user is authenticated
        return view_func(request, *args, **kwargs)
    return wrapper



def can_access_product(view_func):
    @wraps(view_func)
    @valid_standard_membership_required
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.unlimited'):
            return view_func(request, *args, **kwargs)
        elif request.user.has_perm('main.standard'):
            limit = LIMITS["standard"]["product_views"]
        user_subscription = get_object_or_404(UserSubscription, user=request.user)
        current_period_start = user_subscription.current_period_start
        if user_subscription.interval == 'year':
            limit *= 12
        user_views = View.objects.filter(
            product__isnull=False,
            user=request.user,
            viewed_at__gte=current_period_start
            ).count()
        if user_views > limit:
            messages.error(request, "You have Exceeded your product views available this month. Upgrade subscription in settings.")
            return redirect(reverse('logged')) 
        else:
            return view_func(request, *args, **kwargs)
    return wrapper

def can_access_commodity(view_func):
    @wraps(view_func)
    @valid_standard_membership_required
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.unlimited'):
            return view_func(request, *args, **kwargs)
        elif request.user.has_perm('main.standard'):
            limit = LIMITS["standard"]["commodity_views"]
        user_subscription = get_object_or_404(UserSubscription, user=request.user)
        current_period_start = user_subscription.current_period_start
        if user_subscription.interval == 'year':
            limit *= 12
        user_views = View.objects.filter(
            commodity__isnull=False,
            user=request.user,
            viewed_at__gte=current_period_start,
            ).count()
        if user_views > limit:
            messages.error(request, "You have Exceeded your commodity views available this month. Upgrade subscription in settings.")
            return redirect(reverse('logged')) 
        else:
            return view_func(request, *args, **kwargs)
    return wrapper

def can_create_product(view_func):
    @wraps(view_func)
    @valid_standard_membership_required
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.unlimited'):
            return view_func(request, *args, **kwargs)
        elif request.user.has_perm('main.standard'):
            limit = LIMITS["standard"]["custom_products"]

        user_products_count = Product.objects.filter(
            user=request.user,
            ).count()
        if user_products_count >= limit:
            messages.error(request, "Exceeded your custom products available. Upgrade subscription in settings or delete some products.")
            return redirect(reverse('logged')) 
        else:
            return view_func(request, *args, **kwargs)
    return wrapper

def can_create_project(view_func):
    @wraps(view_func)
    @valid_standard_membership_required
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.unlimited'):
            return view_func(request, *args, **kwargs)
        elif request.user.has_perm('main.standard'):
            limit = LIMITS["standard"]["custom_products"]
        elif request.user.has_perm('main.lite'):
            limit = LIMITS["lite"]["custom_products"]

        user_projects_count = Project.objects.filter(
            user=request.user,
            ).count()
        if user_projects_count >= limit:
            messages.error(request, "Exceeded your custom projects available. Upgrade subscription in settings or delete some projects.")
            return redirect(reverse('logged')) 
        else:
            return view_func(request, *args, **kwargs)
    return wrapper

def can_create_notification(view_func):
    @wraps(view_func)
    @valid_standard_membership_required
    def wrapper(request, *args, **kwargs):
        if request.user.has_perm('main.unlimited'):
            return view_func(request, *args, **kwargs)
        elif request.user.has_perm('main.standard'):
            limit = LIMITS["standard"]["monitoring_notifications"]

        not_activated_count = Notification.objects.filter(
            user=request.user,
            activated=False
            ).count()
        if not_activated_count >= limit:
            messages.error(request, "Exceeded your monitoring notifications available. Upgrade subscription in settings or delete some monitoring notifactions.")
            return redirect(reverse('logged')) 
        else:
            return view_func(request, *args, **kwargs)
    return wrapper