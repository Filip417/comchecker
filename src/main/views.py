from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import *
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Count
from datetime import datetime
import json
from collections import defaultdict
from django.contrib.auth import login, authenticate, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.template.loader import render_to_string
from django.contrib.auth.hashers import check_password
from django.db.models import Count
from itertools import chain
from django.db.models import Sum, Count
from .decorators import *
from django.utils import timezone
from .views_functions import *
from .update_prices import check_notification_and_send_email
import helpers.billing
from .subs_utils import refresh_active_users_subscriptions, get_payment_intents
import stripe
from django.http import JsonResponse
from customers.models import Customer
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .tokens import email_notification_token
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Case, When, IntegerField, Value
from django.utils.html import format_html



def pricing(request):
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    if request.user.is_authenticated:
        user_sub_obj, created = UserSubscription.objects.get_or_create(user=request.user)

        sub_data = user_sub_obj.serialize()
        if request.method == 'POST':
            finished = refresh_active_users_subscriptions(user_ids=[request.user.id],
                                                        active_only=False)
            if finished:
                messages.success(request, "Membership data refreshed.")
            else:
                messages.error(request, "Membership data not refreshed. Please try again or contact support.")
            return redirect(user_sub_obj.get_absolute_url())
    else:
        sub_data = None

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
        "subscription": sub_data
    }

    return render(request, "main/pricing_tobeedited.html", context=context)

@login_required
def user_subscription_cancel_view(request):
    user_sub_obj, created = UserSubscription.objects.get_or_create(user=request.user)

    sub_data = user_sub_obj.serialize()
    if request.method == 'POST':
        if user_sub_obj.stripe_id and user_sub_obj.is_active_status:
            sub_data = helpers.billing.cancel_subscription(
                user_sub_obj.stripe_id,
                cancel_at_period_end=True,
                reason="User wanted to end",
                feedback="other",
                raw=False)
            for k, v in sub_data.items():
                setattr(user_sub_obj, k, v)
            user_sub_obj.save()
            messages.success(request, "Your plan has been cancelled.")
        referer = request.META.get('HTTP_REFERER', '/')
        return redirect(referer)
    messages.error(request, "Your plan could not been cancelled. Try again or contact support.")
    return redirect(reverse('logged'))


def privacy_tc(request):
    return render(request, 'main/privacytc.html')


EXAMPLE_PRODUCTS = [ 4752, 12946, 6929, 13046, 7031, 
                    12392,  6927,  5782, 1427, 8255,
                    11665, 10359, 8574, 11582, 15109,
                    16800, 10901, 6643, 5889, 12407, 
                    11583, 791, 10618, 12773, 10900,
                     ]

# Views
@logged_in_cant_access
def index(request):
    if request.user.is_authenticated:
        return redirect(reverse('logged'))
    
    commodities = get_priority_commodities()
    
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    example_products = []
    for n in EXAMPLE_PRODUCTS:
        example_products.append(Product.objects.get(epd_id=n))

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
        "commodities":commodities,
        "example_products":example_products,
    }

    return render(request, "main/index.html", context=context)

@login_required
def index_logged_no_valid_membership(request):

    commodities = get_priority_commodities()
    
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    example_products = Product.objects.filter(epd_id__in=EXAMPLE_PRODUCTS)

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
        "commodities":commodities,
        "scroll_to_pricing": True,
        "example_products":example_products,
    }
    return render(request, "main/index.html", context=context)

@show_new_notifications
@valid_subscription
def index_logged(request):
    # Adjust this view for a logged-in user's dashboard or main page
    # Step 1: Get all products sorted by 'increasefromlastyear' and filter by at least 3 unique commodities
    all_products = (
        Product.objects.filter(Q(user=None) | Q(user=request.user),
                               increasefromlastyear__isnull=False,
                               unique_commodities_count__gte=3).order_by('-increasefromlastyear'))

    # Step 2: Select products with unique manufacturers
    products_by_manufacturer = defaultdict(list)
    for product in all_products:
        products_by_manufacturer[product.manufacturer_name].append(product)

    # Flatten the list to get the top product per manufacturer
    unique_manufacturer_products = [products[0] for products in products_by_manufacturer.values()]

    # Limit the result of products
    LIMIT = 40
    highest_products = unique_manufacturer_products[:LIMIT]
    lowest_products = unique_manufacturer_products[-LIMIT:]
    lowest_products.reverse()
    your_products = Product.objects.filter(user=request.user)
    highest_commodities = Commodity.objects.filter(increasefromlastyear__isnull=False).order_by('-increasefromlastyear')[:LIMIT]
    lowest_commodities = Commodity.objects.filter(increasefromlastyear__isnull=False).order_by('increasefromlastyear')[:LIMIT]
    all_products = Product.objects.all()

    # Choices: 'week', 'month', 'year'
    popular_products = get_popular_items('product', 'week', 30, user_id=request.user.id)
    popular_commodities= get_popular_items('commodity', 'month', 30, user_id=request.user.id)

    # User-specific products and projects
    owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)

    context = {
        "highest_products":highest_products,
        "lowest_products":lowest_products,
        "your_products":your_products,
        "highest_commodities":highest_commodities,
        "lowest_commodities":lowest_commodities,
        "all_products":all_products,
        "popular_products":popular_products,
        "popular_commodities":popular_commodities,
        "owned_projects": owned_projects,
        "shared_projects":shared_projects,
        "your_projects":your_projects,
        "products_in_projects": json.dumps(products_in_projects),
    }
    return render(request, 'main/index_logged.html', context=context)


@show_new_notifications
def delete_notification(request):
    if request.method == 'POST':
        notification_id = request.POST.get('notification_id', None)
        if (notification_id):
            notification = get_object_or_404(Notification, id=notification_id, user=request.user)
            try:
                notification.delete()
                messages.success(request, "Notification has been deleted.")
            except:
                messages.error(request, "Error in deleting notification. Try again or contact support.")
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)

@show_new_notifications
@can_create_notification
def set_notification(request):
    if request.method == 'POST':
        commodity_id = request.POST.get('commodity_id', None)
        product_id = request.POST.get('product_id', None)
        project_id = request.POST.get('project_id', None)
        change = request.POST.get('change', None)
        change_by = request.POST.get('change_by', None)
        change_by_ml = request.POST.get('change_by_ml', None)
        email_notification = request.POST.get('email_notification')
        email_notification = True if email_notification == "on" else False

        if (commodity_id or product_id or project_id) and change and change_by and change_by_ml:
            notification = Notification.objects.create(
                product_id=product_id,
                commodity_id=commodity_id,
                project_id=project_id,
                user=request.user,
                change=change,
                change_by=change_by,
                change_by_ml=change_by_ml,
                email_notification=email_notification
            )
            date_obj = datetime.strptime(notification.change_by, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d %b %Y")
            updated, sent = check_notification_and_send_email(notification.id)
            messages.success(request,
            f"Notification for {notification.change}% change by {formatted_date} has been set.")
        else:
            messages.error(request, "Error in seting up notification. Try again or contact support.")
    
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)

@login_required
def delete_project(request):
    if request.method == 'POST':
        project_id = request.POST.get('project_id') 
        project = get_object_or_404(Project, id=project_id, user=request.user)
        try:
            project.delete()
            messages.success(request, "Project has been deleted.")
        except:
            messages.error(request, "Error in deleting project. Try again or contact support.")
    return redirect(reverse('logged'))

@login_required
def edit_project_name(request):
    if request.method == 'POST':
        new_project_name = request.POST.get('new_project_name', None)
        new_project_description = request.POST.get('new_project_description', None)
        project_id = request.POST.get('project_id') 
        if new_project_name and project_id and new_project_name.strip() != '':
            project = get_object_or_404(Project, id=project_id, user=request.user)
            project.name = new_project_name
            project.slug = project.generate_unique_slug()
            project.description = new_project_description
            project.save()
            messages.success(request, 'Project has been updated.')
        else:
            messages.error(request, 'Cannot change project name to empty field.')
    return redirect('project', project_slug=project.slug)

@can_create_project
def new_project(request):
    if request.method == 'POST':
        new_project_name = request.POST.get('new_project_name', None)
        new_project_description = request.POST.get('new_project_description', None)
        if new_project_name and new_project_name.strip() != '':
            project = Project.objects.create(user=request.user, name=new_project_name, description=new_project_description)
            project.calculate_increase()
            project.save()
            messages.success(request, f"New project {project.name} has been created.")
        else:
            messages.error(request, 'Cannot use empty name to create new project.')
    return redirect('project', project_slug=project.slug)

@valid_subscription
def change_product_to_project(request, product_id):
    # Get the product object
    product = get_object_or_404(Product, id=product_id)
    
    if product.user != request.user and product.user != None:
        messages.error(request, "You have no access to this product.")
        return redirect(reverse('logged'))

    if request.method == 'POST':
        project_id = request.POST.get('project_id')        
        # Check if a new project is being created or an existing one is selected
        if project_id == 'new':
            # Create a new project (You can extend this logic based on your form)
            @can_create_project
            def create_new_project(request):
                new_project_name = request.POST.get('new_project_name', None)
                if new_project_name and new_project_name.strip() != '':
                    project = Project.objects.create(user=request.user, name=new_project_name)
                    project_url = reverse('project', args=[project.slug])
                    messages.success(request, format_html(
                        "New project <a class='hover:underline' href='{}'>{}</a> has been created.",
                        project_url, project.name
                    ))
                    return project
                else:
                    messages.error(request, 'Cannot use empty name to create new project.')
                    return redirect(request.META.get('HTTP_REFERER', '/'))
            project = create_new_project(request)
        else:
            project = get_object_or_404(Project, id=project_id, user=request.user)

        # Check if the product is already in the project
        if product not in project.products.all():
            project.products.add(product)
            product_url = reverse('product', args=[product.slug])
            project_url = reverse('project', args=[project.slug])
            messages.success(request, format_html(
                "Product <a class='hover:underline' href='{}'>{}</a> has been added to <a class='hover:underline' href='{}'>{}</a> project.", product_url, product.name, project_url, project.name
            ))
        elif product in project.products.all():
            project.products.remove(product)
            product_url = reverse('product', args=[product.slug])
            project_url = reverse('project', args=[project.slug])
            messages.success(request, format_html(
                "Product <a class='hover:underline' href='{}'>{}</a> has been removed from <a class='hover:underline' href='{}'>{}</a> project.", product_url, product.name, project_url, project.name
            ))
        else:
            messages.error(request, f"Error in adding product to project. Try again or contact support.")
        project.calculate_increase()
        project.save()
    # Redirect back to the referer URL
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)

@can_create_product
def edit_product(request, slug):
    # Retrieve the product object, handle the case where it might not exist
    product = get_object_or_404(Product, slug=slug)

    if product.user != request.user and product.user != None:
        messages.error(request, "You have no access to this product.")
        return redirect(reverse('logged'))
    
    commodities = Commodity.objects.all().distinct()
    commodities = commodities.order_by('name')

    categories = Product.objects.all().values_list('category_3', flat=True).distinct().order_by('category_3')

    materialproportions = MaterialProportion.objects.filter(product_id=product.id)

    context = {
        "product":product,
        "commodities":commodities,
        "materialproportions":materialproportions,
        "categories":categories,
    }

    if request.method == 'POST':
        return save_new_product(request)  

    return render(request, "main/create.html", context=context)

@login_required
def delete_product(request, slug):
    # Retrieve the product object, handle the case where it might not exist
    product = get_object_or_404(Product, slug=slug)

    if product.user == None or product.user != request.user:
        messages.error(request, "You have no access to this product")
        return redirect(reverse('logged'))
    
    try:
        product.delete()
        messages.success(request, "Product has been deleted.")
    except:
        messages.error(request, "Error in deleting product. Try again or contact support.")
    return redirect(reverse('logged'))
    

@show_new_notifications
@can_create_product
def create(request):
    commodities = Commodity.objects.all().distinct().order_by('name')

    categories = Product.objects.all().values_list('category_3', flat=True).distinct().order_by('category_3')

    context = {
        "commodities":commodities,
        "categories":categories,
    }
    
    if request.method == 'POST':
        return save_new_product(request)  

    return render(request, "main/create.html", context=context)

@show_new_notifications
@valid_subscription
def profile(request):
    user_sub_obj, created = UserSubscription.objects.get_or_create(user=request.user)
    sub_data = user_sub_obj.serialize()

    owned_projects = request.user.owned_projects.all().order_by('-name')
    shared_projects = request.user.shared_projects.all().order_by('-name')

    sort = request.GET.get('sort')
    if sort == 'az':
        owned_projects = owned_projects.order_by('name')
        shared_projects = shared_projects.order_by('name')
    elif sort == 'za':
        owned_projects = owned_projects.order_by('-name')
        shared_projects = shared_projects.order_by('-name')
    elif sort == 'price_asc':
        owned_projects = owned_projects.order_by('increasefromlastyear')
        shared_projects = shared_projects.order_by('increasefromlastyear')
    elif sort == 'price_desc':
        owned_projects = owned_projects.order_by('-increasefromlastyear')
        shared_projects = shared_projects.order_by('-increasefromlastyear')
    else:
        pass  # TODO Default sorting (if any)

    your_projects = list(chain(owned_projects, shared_projects))
    your_products = Product.objects.filter(user=request.user)

    # Calculate the total sum of increasefromlastyear and the count of products
    total_increase = your_products.aggregate(total=Sum('increasefromlastyear'))['total'] or 0
    product_count = your_products.count()

    # Calculate the average 1-year increase (handle division by zero)
    if product_count > 0:
        your_products_average_1y_increase = total_increase / product_count
    else:
        your_products_average_1y_increase = 0

    context = {
        "your_projects":your_projects,
        "your_products":your_products,
        "your_products_average_1y_increase":your_products_average_1y_increase,
        "sort":sort,
        "subscription": sub_data,
    }
    return render(request, "main/profile.html", context)

def product_example(request, slug):
    # Retrieve the product object, handle the case where it might not exist
    product = get_object_or_404(Product, slug=slug)

    if product.user != None and product.user!= request.user:
        messages.error(request, "You have no access to this product.")
        return redirect(reverse('logged'))
    
    if product.epd_id not in EXAMPLE_PRODUCTS:
        return redirect(reverse('logged'))

    material_proportions = MaterialProportion.objects.filter(product=product).order_by('-proportion')

    cumulative_line_chart_data, table_data = get_cumulative_line_chart_and_table_data_product(product.id)
    map_data = get_map_data_product(product.id)

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'table_export_excel':
            response = download_table_excel_product(product.name, table_data)
        elif action == 'table_export_csv':
            response = download_table_csv_product(product.name, table_data)
        elif action == 'map_export_excel':
            response = download_map_excel(product.name, map_data)
        elif action == 'map_export_csv':
            response = download_map_csv(product.name, map_data)
        return response  

    # Filter for similar products (products with the same manufacturer_name)
    similar_products = get_similar_products(product, request)[:25]

    # Filter for products from the same manufacturer, excluding the current product
    from_same_manufacturer = Product.objects.filter(manufacturer_name=product.manufacturer_name, user=None).exclude(id=product.id)[:50]

    product.add_view(user=None) # or remove this 

    owned_projects, shared_projects, your_projects, products_in_projects = None, None, None, None # get_product_project_variables(request)

    context = {
        "product": product,
        "cumulative_line_chart_data": json.dumps(cumulative_line_chart_data),
        "table_data": table_data,
        "map_data":map_data,
        "similar_products": similar_products,
        "from_same_manufacturer": from_same_manufacturer,
        "material_proportions":material_proportions,
        "owned_projects": owned_projects,
        "shared_projects":shared_projects,
        "your_projects":your_projects,
        "products_in_projects": json.dumps(products_in_projects),
        "product_example":True,
    }
    return render(request, "main/product.html", context)

@show_new_notifications
@can_access_product
def product(request, slug):
    # Retrieve the product object, handle the case where it might not exist
    product = get_object_or_404(Product, slug=slug)

    if product.user != None and product.user!= request.user:
        messages.error(request, "You have no access to this product.")
        return redirect(reverse('logged'))

    material_proportions = MaterialProportion.objects.filter(product=product).order_by('-proportion')

    cumulative_line_chart_data, table_data = get_cumulative_line_chart_and_table_data_product(product.id)
    map_data = get_map_data_product(product.id)

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'table_export_excel':
            response = download_table_excel_product(product.name, table_data)
        elif action == 'table_export_csv':
            response = download_table_csv_product(product.name, table_data)
        elif action == 'map_export_excel':
            response = download_map_excel(product.name, map_data)
        elif action == 'map_export_csv':
            response = download_map_csv(product.name, map_data)
        return response  

    # Filter for similar products (products with the same manufacturer_name)
    similar_products = get_similar_products(product, request)[:50]

    # Filter for products from the same manufacturer, excluding the current product
    from_same_manufacturer = Product.objects.filter(manufacturer_name=product.manufacturer_name, user=None).exclude(id=product.id)[:50]

    product.add_view(user=request.user)

    owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)

    context = {
        "product": product,
        "cumulative_line_chart_data": json.dumps(cumulative_line_chart_data),
        "table_data": table_data,
        "map_data":map_data,
        "similar_products": similar_products,
        "from_same_manufacturer": from_same_manufacturer,
        "material_proportions":material_proportions,
        "owned_projects": owned_projects,
        "shared_projects":shared_projects,
        "your_projects":your_projects,
        "products_in_projects": json.dumps(products_in_projects),
    }
    return render(request, "main/product.html", context)

@show_new_notifications
@can_access_commodity
def commodity(request, name):
    commodity = get_object_or_404(Commodity, name=name)
    cumulative_line_chart_data, table_data = get_cumulative_line_chart_and_table_data_commodity(commodity.id)
    map_data = get_map_data_commodity(commodity.id)

    futures_chart_data, futures_table_data = get_futures_chart_and_table_data_commodity(commodity.id)

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'table_export_excel':
            response = download_table_excel_commodity(commodity.name, table_data)
        elif action == 'table_export_csv':
            response = download_table_csv_commodity(commodity.name, table_data)
        elif action == 'map_export_excel':
            response = download_map_excel(commodity.name, map_data)
        elif action == 'map_export_csv':
            response = download_map_csv(commodity.name, map_data)
        elif action == 'futures_table_excel':
            response = download_futures_excel(commodity.name, futures_table_data)
        elif action == 'futures_table_csv':
            response = download_futures_csv(commodity.name, futures_table_data)
        return response

    # Filter for similar products (products with the same manufacturer_name)
    similar_commodities = get_similar_commodities(commodity)[:20]

    made_from = get_products_by_commodity(commodity, request)[:20]

    commodity.add_view(user=request.user)

    owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)

    context = {
        "commodity":commodity,
        "map_data":map_data,
        "cumulative_line_chart_data": json.dumps(cumulative_line_chart_data),
        "table_data": table_data,
        "similar_commodities":similar_commodities,
        "made_from":made_from,
        "futures_chart_data":futures_chart_data,
        "futures_table_data":futures_table_data,
        "owned_projects": owned_projects,
        "shared_projects":shared_projects,
        "your_projects":your_projects,
        "products_in_projects": json.dumps(products_in_projects),
    }
    return render(request, "main/commodity.html", context)
import time
@show_new_notifications
@valid_subscription
def project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if project.user != request.user and request.user not in project.shared_with.all():
        messages.error(request, "You have no access to this project.")
        return redirect(reverse('logged'))

    product_categories = project.products.values_list('category_3', flat=True).distinct()

    table_data = get_table_data_project(project)

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'table_export_excel':
            response = download_table_excel_project(project.name, table_data)
            return response  
        elif action == 'table_export_csv':
            response = download_table_csv_project(project.name, table_data)
            return response  

    all_products = project.products.all()
    # unique_sources = []
    # 
    # for product in all_products:
    #     for n in product.price_history_sources:
    #         if n not in unique_sources:
    #             unique_sources.append(n)
    
    similar_products = get_similar_products_for_products(all_products, request)
    top_value_commodity_ids = project.products.values_list('top_value_commodity', flat=True).distinct()[:20]
    top_value_commodities = Commodity.objects.filter(id__in=top_value_commodity_ids)
    your_products = Product.objects.filter(user=request.user)
    popular_products = get_popular_items('product', 'week', 20, user_id=request.user.id)

    project.add_view(user=request.user)

    owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)

    context = {
        'project': project,
        "product_categories": product_categories,
        "table_data": table_data,
        # "unique_sources": unique_sources,
        "similar_products": similar_products,
        "top_value_commodities": top_value_commodities,
        "your_products": your_products,
        "popular_products": popular_products,
        "owned_projects": owned_projects,
        "shared_projects": shared_projects,
        "your_projects": your_projects,
        "products_in_projects": json.dumps(products_in_projects),
    }
    return render(request, "main/project.html", context)

@show_new_notifications
def search(request):
    default_sorting = '-view_count'
    if request.user.is_authenticated:
        products = Product.objects.filter(Q(user=None) | Q(user=request.user)).order_by(default_sorting)
    else:
        products = Product.objects.filter(user=None).order_by(default_sorting)
    commodities = Commodity.objects.all().order_by('name')

    # Handle Products & Commodity filter
    pro = request.GET.get('product')
    com = request.GET.get('commodity')
    value_on_input = 'show'
    product_show = 'show'
    commodity_show = 'show'

    if pro == value_on_input and com != value_on_input:
        commodity_show = 'hide'
        # empty commodities
        commodities = commodities.filter(id=-1)
    elif pro != value_on_input and com == value_on_input:
        product_show = 'hide'
        # empty products
        products = products.filter(id=-1)


    search_query = request.GET.get('q')
    if search_query:
        # Split the query into individual words
        search_terms = search_query.split()

        # Construct a Q object for products and commodities
        product_queries = Q()
        commodity_queries = Q()

        for word in search_terms:
            # Handle plural forms
            if word[-1].lower() == 's' and len(word) > 3:
                word = word[:-1]  # Remove the last character if it's 's'

            # Build the product queries
            product_queries |= Q(name__icontains=word) \
                            | Q(original_name__icontains=word) \
                            | Q(included_products_in_this_epd__icontains=word) \
                            | Q(category_1__icontains=word) \
                            | Q(category_2__icontains=word) \
                            | Q(category_3__icontains=word) \
                            | Q(manufacturer_name__icontains=word) \
                            | Q(description__icontains=word) \
                            | Q(epd_id__icontains=word)

            # Build the commodity queries
            commodity_queries |= Q(name__icontains=word) \
                            | Q(category__icontains=word) \
                            | Q(basic_description__icontains=word) \
                            | Q(substitutes__icontains=word) \
                            | Q(use__icontains=word)

        # Filter the products
        products = Product.objects.filter(product_queries)

        # Annotate with priorities for products
        products = products.annotate(
            priority_name=Case(
                When(name__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_original_name=Case(
                When(original_name__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_included_products=Case(
                When(included_products_in_this_epd__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_category_1=Case(
                When(category_1__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_category_2=Case(
                When(category_2__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_category_3=Case(
                When(category_3__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_manufacturer_name=Case(
                When(manufacturer_name__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_description=Case(
                When(description__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_epd_id=Case(
                When(epd_id__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by(
            '-priority_name', 
            '-priority_original_name', 
            '-priority_included_products', 
            '-priority_category_1', 
            '-priority_category_2', 
            '-priority_category_3', 
            '-priority_manufacturer_name', 
            '-priority_description', 
            '-priority_epd_id'
        )

        # Filter and annotate commodities similarly
        commodities = Commodity.objects.filter(commodity_queries).annotate(
            priority_name=Case(
                When(name__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_category=Case(
                When(category__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_basic_description=Case(
                When(basic_description__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_substitutes=Case(
                When(substitutes__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ),
            priority_use=Case(
                When(use__icontains=search_query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by(
            '-priority_name', 
            '-priority_category', 
            '-priority_basic_description', 
            '-priority_substitutes', 
            '-priority_use'
        )

    # Handle category filter
    selected_categories = request.GET.getlist('category')
    if selected_categories:
        products = products.filter(category_3__in=selected_categories)

    # Handle manufacturer filter
    selected_manufacturers = request.GET.getlist('manufacturer')
    if selected_manufacturers:
        products = products.filter(manufacturer_name__in=selected_manufacturers)

    # Handle manufacturer country filter
    selected_manufacturer_countries = request.GET.getlist('mcountry')
    if selected_manufacturer_countries:
        products = products.filter(manufacturer_country__in=selected_manufacturer_countries)

    # Handle commodity price source filter
    selected_commodities_price_source = request.GET.getlist('comps')
    if selected_commodities_price_source:
        commodities = commodities.filter(price_history_source__in=selected_commodities_price_source)

    # Handle Top commodities in products filter
    selected_top_commodities = request.GET.getlist('topcom')
    if selected_top_commodities:
        products = products.filter(top_value_commodity__name__in=selected_top_commodities)

    only_user_products_selected = request.GET.get('up')
    if only_user_products_selected:
        products = products.filter(user=request.user)

    selected_comtype = request.GET.getlist('comtype')
    if selected_comtype:
        commodities = commodities.filter(price_history_type__in=selected_comtype)

    # Apply price change filters
    pchangemin = request.GET.get('pchangemin')
    pchangemax = request.GET.get('pchangemax')

    if pchangemin and pchangemax and pchangemax >= pchangemin:
        products = products.filter(increasefromlastyear__gte=float(pchangemin), increasefromlastyear__lte=float(pchangemax))
        commodities = commodities.filter(increasefromlastyear__gte=float(pchangemin), increasefromlastyear__lte=float(pchangemax))
    elif pchangemin:
        products = products.filter(increasefromlastyear__gte=float(pchangemin))
        commodities = commodities.filter(increasefromlastyear__gte=float(pchangemin))
        # if the values are impossible to meet than filter for min works, and max resets
        pchangemax = None
    elif pchangemax:
        products = products.filter(increasefromlastyear__lte=float(pchangemax))
        commodities = commodities.filter(increasefromlastyear__lte=float(pchangemax))

    # Get list of available categories
    visible_categories = products.filter(category_3__isnull=False).exclude(category_3='None').values_list('category_3', flat=True).distinct().order_by('category_3')

    # Get list of visible manufacturers
    visible_manufacturers = products.filter(manufacturer_name__isnull=False).exclude(manufacturer_name='').values_list('manufacturer_name', flat=True).distinct().order_by('manufacturer_name')

    # Get list of visible manufacturers countries
    visible_manufacturer_countries = products.filter(manufacturer_country__isnull=False).exclude(manufacturer_country='').values_list('manufacturer_country', flat=True).distinct().order_by('manufacturer_country')  

    # Get list of visible price sources
    visible_commodities_price_source = commodities.values_list('price_history_source', flat=True).distinct().order_by('price_history_source')

    visible_commodities_type = commodities.values_list('price_history_type', flat=True).distinct().order_by('price_history_type')
    # Get list of visible top commodities for products
    # Order A-Z
    # visible_top_commodities = products.filter(top_value_commodity__isnull=False).values_list('top_value_commodity__name', flat=True).distinct().order_by('top_value_commodity__name')
    
    # Order by commodity_count
    visible_top_commodities = products.filter(top_value_commodity__isnull=False) \
                                  .values('top_value_commodity__name') \
                                  .annotate(commodity_count=Count('top_value_commodity')) \
                                  .order_by('-commodity_count') \
                                  .values_list('top_value_commodity__name', flat=True)
    
    if request.user.is_authenticated:
        user_has_products = True if products.filter(user=request.user).exists() else False
    else:
        user_has_products = False

    # Handle sorting
    sort = request.GET.get('sort')
    if sort == 'az':
        products = products.order_by('name')
        commodities = commodities.order_by('name')
    elif sort == 'za':
        products = products.order_by('-name')
        commodities = commodities.order_by('-name')
    elif sort == 'price_asc':
        products = products.order_by('increasefromlastyear')  # Ascending order
        commodities = commodities.order_by('increasefromlastyear')
    elif sort == 'price_desc':
        products = products.order_by('-increasefromlastyear')  # Descending order
        commodities = commodities.order_by('-increasefromlastyear')
    else:
        pass  # TODO Default sorting (if any)


    ITEMS_PER_PAGE = 24 # 24 multiplier

    paginator = Paginator(products, ITEMS_PER_PAGE)
    page_number = request.GET.get('page')
    try:
        page = paginator.page(page_number)
    except PageNotAnInteger:
        page = paginator.page(1)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    paginator_commodity = Paginator(commodities, ITEMS_PER_PAGE)
    page_number_commodity = request.GET.get('pagec')
    try:
        page_commodity = paginator_commodity.page(page_number_commodity)
    except PageNotAnInteger:
        page_commodity = paginator_commodity.page(1)
    except EmptyPage:
        page_commodity = paginator_commodity.page(paginator_commodity.num_pages)

    if request.user.is_authenticated:
        owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)
    else:
        owned_projects, shared_projects, your_projects, products_in_projects = None, None, None, None

    context = {
        "page":page,
        "page_commodity":page_commodity,
        "search_query":search_query,
        'visible_categories':visible_categories,
        'selected_categories':selected_categories,
        'visible_manufacturers': visible_manufacturers,
        'selected_manufacturers': selected_manufacturers,
        "selected_manufacturer_countries":selected_manufacturer_countries,
        "visible_manufacturer_countries":visible_manufacturer_countries,
        "selected_commodities_price_source":selected_commodities_price_source,
        "visible_commodities_price_source":visible_commodities_price_source,
        "selected_top_commodities":selected_top_commodities,
        "visible_top_commodities":visible_top_commodities,
        "selected_comtype":selected_comtype,
        "visible_commodities_type":visible_commodities_type,
        "sort":sort,
        "pchangemin":pchangemin,
        "pchangemax":pchangemax,
        "product_show":product_show,
        "commodity_show":commodity_show,
        "user_has_products":user_has_products,
        "only_user_products_selected":only_user_products_selected,
        "owned_projects": owned_projects,
        "shared_projects":shared_projects,
        "your_projects":your_projects,
        "products_in_projects": json.dumps(products_in_projects),
    }

    return render(request, 'main/search.html', context)

@show_new_notifications
@valid_subscription
def notifications(request):
    active_notifications = Notification.objects.filter(user=request.user, activated=False).order_by('-created_at')
    activated_notifications = Notification.objects.filter(user=request.user, activated=True).order_by('-activated_at')

    new_activated_count = activated_notifications.filter(seen_activated=False).count()
    activated_notifications.filter(seen_activated=False).update(
        seen_activated=True, seen_activated_at=timezone.now())

    for notification in activated_notifications:
        time_diff = timezone.now() - notification.seen_activated_at
        notification.is_recent = time_diff.total_seconds() < 5

    context = {
        "active_notifications" : active_notifications,
        "activated_notifications" : activated_notifications,
        "new_activated_count" : new_activated_count,
    }
    return render(request, "main/notifications.html",context)

@login_required
def get_invoice_pdf(request):
    if request.method == 'POST':
        invoice_id = request.POST.get("invoice_id")
        if invoice_id:
            inv_obj = stripe.Invoice.retrieve(invoice_id)
            inv_url = inv_obj['invoice_pdf']
            if inv_url:
                return redirect(inv_url)
    return redirect('settings')

@login_required
def user_settings(request):
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    user_sub_obj, created = UserSubscription.objects.get_or_create(user=request.user)
    sub_data = user_sub_obj.serialize()
    
    payment_intents = get_payment_intents(request.user.id, limit=24)

    stripe_customer_portal_link = settings.STRIPE_CUSTOMER_PORTAL

    if request.method == 'POST':
        # refresh data request
        finished = refresh_active_users_subscriptions(user_ids=[request.user.id],
                                                      active_only=False)
        if finished:
            messages.success(request, "Membership data refreshed.")
        else:
            messages.error(request, "Membership data not refreshed. Please try again or contact support.")
        referer = request.META.get('HTTP_REFERER', '/')
        return redirect(referer)

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
        "subscription": sub_data,
        "payment_intents":payment_intents,
        "stripe_customer_portal_link":stripe_customer_portal_link,
    }
    return render(request, "main/settings.html", context)


@login_required
def after_billing_changes(request):
    finished = refresh_active_users_subscriptions(user_ids=[request.user.id],
                                                      active_only=False)
    if finished:
        messages.success(request, "Membership data updated.")
    else:
        messages.error(request, "Membership data not updated. Please try refreshing in settings.")
    return redirect(reverse('logged'))

@login_required
def update_settings(request):
    if request.method == 'POST':
        profile = request.user.userprofile
        
        profile.cookie_personalisation = 'personalisation' in request.POST
        profile.email_notification = 'email_notification' in request.POST
        
        profile.save()
        return redirect('settings')


def turn_off_email_notifications(request, uidb64, token):
    try:
        # TODO base64 encoding for future use
        # uid = force_str(urlsafe_base64_decode(uidb64))
        uid = uidb64
        user = get_object_or_404(User, id=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Verify the token and ensure it matches the user
    if user and email_notification_token.check_token(user, token):
        profile = user.userprofile
        profile.email_notification = False
        profile.save()
        messages.success(request, "Email notifications have been turned off.")
        return redirect('index')
    else:
        return HttpResponseForbidden("Invalid token.")


def help(request):
    return render(request, 'main/help.html')


@login_required
def logged_contact_form(request):
    if request.method == "POST":
        text_content = request.POST.get("text-content")
        user_email = request.POST.get("contact-email")
        if text_content and text_content.strip() != '' and user_email:
            send_mail(
                subject=f'New Contact Form Submission from {user_email}',
                message=f'{text_content}\n\nfrom {user_email}',
                from_email=settings.EMAIL_HOST_USER,  # Sender's email
                recipient_list=[settings.EMAIL_HOST_USER],  # Recipient's email
                fail_silently=False,
            )
            messages.success(request, 'Email has been sent, thank you for contacting us.')
            return redirect('help')
    return redirect('help')

# Template with error 404 and 400 TODO if add 403 or 500
def custom_404_view(request, exception):
    return render(request, 'main/404.html', status=404)

def custom_400_view(request, exception):
    return render(request, 'main/404.html', status=400)

def project_calculate_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Extract required values
        project_id = data.get('project_id', None)
        date1 = data.get('date1', None)
        price1 = data.get('price1', 0)
        date2 = data.get('date2', None)
        products = data.get('products', [])

        data_for_calc = {
            "project_id":project_id,
            "date1": date1,
            "price1": price1,
            "date2": date2,
            "products":products,
            "commodities":
                [
                    {"name":"Electricity UK",
                     "commodity_id": 48,
                     "weight":float(data.get('electricity_uk_weight', 0)),
                     },
                     {"name":"Labour UK",
                      "commodity_id": 51,
                     "weight":float(data.get('labour_uk_weight', 0)),
                     },
                     {"name":"Inflation UK",
                      "commodity_id": 52,
                     "weight":float(data.get('inflation_uk_weight', 0)),
                     },
                     {"name":"Containerized Freight China-Europe",
                      "commodity_id": 50,
                     "weight":float(data.get('freight_china_europe_weight', 0)),
                     },
                     {"name":"EU Carbon Permits",
                      "commodity_id": 16,
                     "weight":float(data.get('eu_carbon_permits_weight', 0)),
                     },
                     {"name":"Crude Oil",
                      "commodity_id": 12,
                     "weight":float(data.get('crude_oil_weight', 0)),
                     },
                     {"name":"Construction labour UK",
                      "commodity_id": 53,
                     "weight":float(data.get('construction_labour_uk_weight', 0)),
                     },   
                ],
        }
        if price1 <= 0:
            return JsonResponse({'error_message':"Enter valid Starting price for calculations.",})
        if not date1:
            return JsonResponse({'error_message':"Enter Starting date for calculations.",})
        if not date2:
            return JsonResponse({'error_message':"Enter Date to calculate for calculations.",})
        if project_id:
            calculated_price_2, success = calculate_price2_for_project(data_for_calc)
            if success:
                price2 = calculated_price_2
                return JsonResponse({'price2':price2,})
            return JsonResponse({'error_message':"Invalid input for calcualtions. Contact support.",})
    return JsonResponse({'error': 'Invalid request'}, status=400)

def commodity_calculate_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        # Extract required values
        commodity_id = data.get('commodity_id', None)
        date1 = data.get('date1', None)
        price1 = data.get('price1', 0)
        date2 = data.get('date2', None)

        data_for_calc = {
            "commodity_id":commodity_id,
            "date1": date1,
            "price1": price1,
            "date2": date2,
        }
        if price1 <= 0:
            return JsonResponse({'error_message':"Enter valid Starting price for calculations.",})
        if not date1:
            return JsonResponse({'error_message':"Enter Starting date for calculations.",})
        if not date2:
            return JsonResponse({'error_message':"Enter Date to calculate for calculations.",})
        if commodity_id:
            calculated_price_2, success = calculate_price2_for_commodity(data_for_calc)
            if success:
                price2 = calculated_price_2
                return JsonResponse({'price2':price2,})
            return JsonResponse({'error_message':"Invalid input for calculations. Contact support.",})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def product_calculate_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        # Extract required values
        product_id = data.get('product_id', None)
        date1 = data.get('date1', None)
        price1 = data.get('price1', 0)
        date2 = data.get('date2', None)
        product_weight = float(data.get('product_weight', 0))

        data_for_calc = {
            "product_id":product_id,
            "date1": date1,
            "price1": price1,
            "date2": date2,
            "product_weight": product_weight,
            "commodities":
                [
                    {"name":"Electricity UK",
                     "commodity_id": 48,
                     "weight":float(data.get('electricity_uk_weight', 0)),
                     },
                     {"name":"Labour UK",
                      "commodity_id": 51,
                     "weight":float(data.get('labour_uk_weight', 0)),
                     },
                     {"name":"Inflation UK",
                      "commodity_id": 52,
                     "weight":float(data.get('inflation_uk_weight', 0)),
                     },
                     {"name":"Containerized Freight China-Europe",
                      "commodity_id": 50,
                     "weight":float(data.get('freight_china_europe_weight', 0)),
                     },
                     {"name":"EU Carbon Permits",
                      "commodity_id": 16,
                     "weight":float(data.get('eu_carbon_permits_weight', 0)),
                     },
                     {"name":"Crude Oil",
                      "commodity_id": 12,
                     "weight":float(data.get('crude_oil_weight', 0)),
                     },
                     {"name":"Construction labour UK",
                      "commodity_id": 53,
                     "weight":float(data.get('construction_labour_uk_weight', 0)),
                     },   
                ],
        }

        # Perform calculations here
        price2 = None
        if price1 <= 0:
            return JsonResponse({'error_message':"Enter valid Starting price for calculations.",})
        if product_weight <= 0:
            return JsonResponse({'error_message':"Enter valid Product weight for calculations.",})
        if not date1:
            return JsonResponse({'error_message':"Enter Starting date for calculations.",})
        if not date2:
            return JsonResponse({'error_message':"Enter Date to calculate for calculations.",})
        if product_id:
            for n in data_for_calc['commodities']:
                if n['weight'] < 0:
                    return JsonResponse({'error_message':"Enter valid weights for calculations.",})
            calculated_price_2, success = calculate_price2_for_product(data_for_calc)
            if success:
                price2 = calculated_price_2
                return JsonResponse({'price2':price2,})
            return JsonResponse({'error_message':"Invalid input for calculations. Contact support.",})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def contact_us_enterprise(request):
    if request.method == "POST":
        contact_email = request.POST.get("contact-email")
        contact_company = request.POST.get("contact-company")
        contact_mobile = request.POST.get("contact-mobile")
        contact_time = request.POST.get("contact-time")
        inputs_to_check = [contact_email , contact_company, contact_mobile]
        if not contact_email and contact_email.strip() == '':
            messages.error(request, 'Invalid email. Please try again.')
            return
        
        for n in inputs_to_check:
            if not n and n.strip() == '':
                messages.error(request, 'Invalid email, mobile or company. Please try again.')
                return render(request, 'main/contact_us_enterprise.html')
            
            send_mail(
                subject=f'New Enterprise Contact from {contact_email}',
                message=f'Email: {contact_email}\n\nCompany: {contact_company}\n\n Mobile: {contact_mobile}\n\n Best contact time: {contact_time}',
                from_email=settings.EMAIL_HOST_USER,  # Sender's email
                recipient_list=[settings.EMAIL_HOST_USER],  # Recipient's email
                fail_silently=False,
            )
            messages.success(request, 'Thank you for contacting us. We will reach out asap.')
            return redirect('help')

    return render(request, 'main/contact_us_enterprise.html')