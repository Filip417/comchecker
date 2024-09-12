from functools import wraps
from .models import Notification
from django.shortcuts import redirect
from django.urls import reverse

def show_new_notifications(func):
    @wraps(func)
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
        return func(request, *args, **kwargs)
    return wrapper


def logged_in_cant_access(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('logged'))  # Redirect to 'logged' view if user is authenticated
        return view_func(request, *args, **kwargs)
    return wrapper