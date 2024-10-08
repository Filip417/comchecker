import os
from django import template
from django.templatetags.static import static
from django.contrib.staticfiles import finders
from django.conf import settings
import ast
from django.core.files.storage import default_storage
from django.utils.http import urlencode
from django.http import QueryDict
import datetime
from django import template
from django.utils.timezone import now

register = template.Library()

@register.simple_tag
def get_product_image_url(epd_id, format):
    SIZE = 'medium'
    if epd_id:
        path = f'main/images_resized/{epd_id}_prod_1_{SIZE}.{format}'
        return static(path)
    # Return default image if no format is found
    return static('main/images/product/default.png')


@register.simple_tag
def get_manufacturer_image(epd_id, format):
    SIZE = 'medium'
    if epd_id:
        path = f'main/images_resized/{epd_id}_man_1_{SIZE}.{format}'
        return static(path)
    return "data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs="


@register.simple_tag
def get_commodity_image_url(name, format):
    SIZE = 'large'
    if name:
        path = f'main/commodities_images_resized/{name}_{SIZE}.{format}'
        return static(path)
    return static('main/images/product/default.png')
        

@register.simple_tag(takes_context=True)
def build_query(context, **kwargs):
    request = context['request']
    query_dict = request.GET.copy()
    
    # Update the query dict with new parameters
    for key, value in kwargs.items():
        if value is None:
            query_dict.pop(key, None)
        else:
            query_dict[key] = value

    return query_dict.urlencode()


@register.filter
def slice_email(value):
    """Returns the part of the string before the '@' character."""
    if isinstance(value, str):
        return value.split('@')[0]
    return value

@register.filter
def time_since(value):
    """Returns the time since the given datetime value as a human-readable string."""

    if not isinstance(value, datetime.datetime):
        return f"Invalid datetime: {type(value)}"  # Return the value unchanged if it's not a datetime object

    time_diff = now() - value
    seconds = time_diff.total_seconds()

    # Define time durations in seconds
    periods = [
        (60 * 60 * 24 * 365, 'y'),  # years
        (60 * 60 * 24 * 30, 'm'),   # months
        (60 * 60 * 24 * 7, 'w'),    # weeks
        (60 * 60 * 24, 'd'),        # days
        (60 * 60, 'h'),             # hours
        (60, 'min'),                # minutes
    ]

    for period_seconds, period_name in periods:
        if seconds >= period_seconds:
            value_in_units = int(seconds // period_seconds)
            return f"{value_in_units}{period_name}"

    return "0min"

@register.filter
def word_break(value, length):
    """
    Insert a space or a break character in words that are longer than 'length'.
    """
    words = value.split()
    broken_words = [w if len(w) <= length else ' '.join([w[i:i+length] for i in range(0, len(w), length)]) for w in words]
    return ' '.join(broken_words)

@register.filter
def divide_by_100(value):
    try:
        return round(float(value) / 100, 2)
    except (ValueError, TypeError):
        return 0  # Return 0 or handle the error as needed