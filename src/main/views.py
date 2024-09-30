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
from .subs_utils import refresh_active_users_subscriptions
import stripe
from django.http import JsonResponse
from customers.models import Customer





@logged_in_cant_access
def pricing(request):
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    user_sub_obj, created = UserSubscription.objects.get_or_create(user=request.user)

    sub_data = user_sub_obj.serialize()
    if request.method == 'POST':
        finished = refresh_active_users_subscriptions(user_ids=[request.user.id],
                                                      active_only=False)
        if finished:
            messages.success(request, "Membership data refreshed.")
        else:
            messages.error(request, "Membership data not refreshed. Please try again.")
        return redirect(user_sub_obj.get_absolute_url())

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
            messages.success(request, "Your plan has been cancelled")
        referer = request.META.get('HTTP_REFERER', '/')
        return redirect(referer)
    messages.error(request, "Your plan could not been cancelled. Contact support.")
    return redirect(reverse('logged'))



# Views
@logged_in_cant_access
def index(request):
    if request.user.is_authenticated:
        return redirect(reverse('logged'))
    
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
    }

    return render(request, "main/index.html", context=context)

@login_required
def index_logged_no_valid_membership(request):
    # TODO change whole template and view

    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
    }

    return render(request, "main/index.html", context=context)

@show_new_notifications
@valid_lite_membership_required
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

    # Limit the result to the top 20 products
    LIMIT = 30
    highest_products = unique_manufacturer_products[:LIMIT]
    lowest_products = unique_manufacturer_products[-LIMIT:]
    lowest_products.reverse()
    your_products = Product.objects.filter(user=request.user)
    highest_commodities = Commodity.objects.filter(increasefromlastyear__isnull=False).order_by('-increasefromlastyear')[:LIMIT]
    lowest_commodities = Commodity.objects.filter(increasefromlastyear__isnull=False).order_by('increasefromlastyear')[:LIMIT]
    all_products = Product.objects.all()

    # Choices: 'week', 'month', 'year'
    popular_products = get_popular_items('product', 'week', 20)
    popular_commodities= get_popular_items('commodity', 'month', 20)

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
                messages.error(request, "Error in deleting notification. Contact support.")
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)

@show_new_notifications
@valid_standard_membership_required
def set_notification(request):
    if request.method == 'POST':
        commodity_id = request.POST.get('commodity_id', None)
        product_id = request.POST.get('product_id', None)
        project_id = request.POST.get('project_id', None)
        change = request.POST.get('change', None)
        change_by = request.POST.get('change_by', None)
        email_notification = request.POST.get('email_notification')
        email_notification = True if email_notification == "on" else False

        if (commodity_id or product_id or project_id) and change and change_by:
            notification = Notification.objects.create(
                product_id=product_id,
                commodity_id=commodity_id,
                project_id=project_id,
                user=request.user,
                change=change,
                change_by=change_by,
                email_notification=email_notification
            )
            date_obj = datetime.strptime(notification.change_by, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d %b %Y")
            updated, sent = check_notification_and_send_email(notification.id)
            if notification.email_notification and updated and sent:
                messages.success(request,
            f"Email notification for {notification.change}% change by {formatted_date} has been set.")
            else:
                messages.success(request,
            f"Notification for {notification.change}% change by {formatted_date} has been set.")
        else:
            messages.error(request, "Error in seting up notification. Contact support.")
    
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
            messages.error(request, "Error in deleting project. Contact support.")
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
            messages.success(request, 'Project changes updated')
        else:
            messages.error(request, 'Cannot change project name to empty field')
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
            messages.error(request, 'Cannot be empty name to create new project')
    return redirect('project', project_slug=project.slug)

@can_create_project
def change_product_to_project(request, product_id):
    # Get the product object
    product = get_object_or_404(Product, id=product_id)
    
    if product.user != request.user and product.user != None:
        messages.error(request, "You have no access to this product")
        return redirect(reverse('logged'))

    if request.method == 'POST':
        project_id = request.POST.get('project_id')        
        # Check if a new project is being created or an existing one is selected
        if project_id == 'new':
            # Create a new project (You can extend this logic based on your form)
            new_project_name = request.POST.get('new_project_name', None)
            if new_project_name and new_project_name.strip() != '':
                project = Project.objects.create(user=request.user, name=new_project_name)
                messages.success(request, f"New project {project.name} has been created.")
            else:
                messages.error(request, 'Cannot be empty name to create new project')
                return redirect(request.META.get('HTTP_REFERER', '/'))
            # Check if project has been saved and has an id
            if not project.id:
                messages.error(request, "Failed to create the project.")
                return redirect(request.META.get('HTTP_REFERER', '/'))
        else:
            project = get_object_or_404(Project, id=project_id, user=request.user)

        # Check if the product is already in the project
        if product not in project.products.all():
            project.products.add(product)
            messages.success(request, f"Product {product.name} has been added to {project.name} project.")
        elif product in project.products.all():
            project.products.remove(product)
            messages.success(request, f"Product {product.name} has been removed from {project.name} project.")
        else:
            messages.error(request, f"Error in adding product to project.")
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
        messages.error(request, "You have no access to this product")
        return redirect(reverse('logged'))
    
    commodities = Commodity.objects.all().distinct()
    commodities = commodities.order_by('name')

    categories = Product.objects.all().values_list('category_3', flat=True).distinct().order_by('category_3')

    materialproportions = MaterialProportion.objects.filter(product_id=product.id)
    print(f"LENGTH: {len(materialproportions)}")

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
        messages.error(request, "Error in deleting product. Contact support.")
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
@login_required
def profile(request):
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
    }
    return render(request, "main/profile.html", context)

@show_new_notifications
@can_access_product
def product(request, slug):
    # Retrieve the product object, handle the case where it might not exist
    product = get_object_or_404(Product, slug=slug)

    if product.user != None and product.user!= request.user:
        messages.error(request, "You have no access to this product")
        return redirect(reverse('logged'))

    material_proportions = MaterialProportion.objects.filter(product=product).order_by('-proportion')

    cumulative_line_chart_data, table_data = get_cumulative_line_chart_and_table_data_product(product.id)
    map_data = get_map_data_product(product.id)

    if request.method == "POST":
        action = request.POST.get('action')
        if action == 'table_export_excel':
            response = download_table_excel_product(product.name, table_data)
            return response  
        elif action == 'table_export_csv':
            response = download_table_csv_product(product.name, table_data)
            return response  
        elif action == 'map_export_excel':
            response = download_map_excel(product.name, map_data)
            return response  
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
            return response  
        elif action == 'table_export_csv':
            response = download_table_csv_commodity(commodity.name, table_data)
            return response  
        elif action == 'map_export_excel':
            response = download_map_excel(commodity.name, map_data)
            return response  
        elif action == 'map_export_csv':
            response = download_map_csv(commodity.name, map_data)
            return response  
        elif action == 'futures_table_excel':
            response = download_futures_excel(commodity.name, futures_table_data)
            return response
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

@show_new_notifications
@login_required
def project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)

    if project.user != request.user and request.user not in project.shared_with.all():
        messages.error(request, "You have no access to this project")
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

    unique_sources = []
    all_products = project.products.all()
    for product in all_products:
        for n in product.price_history_sources:
            if n not in unique_sources:
                unique_sources.append(n)

    similar_products = get_similar_products_for_products(all_products, request)
    top_value_commodity_ids = project.products.values_list('top_value_commodity', flat=True).distinct()[:20]
    top_value_commodities = Commodity.objects.filter(id__in=top_value_commodity_ids)
    your_products = Product.objects.filter(user=request.user)
    popular_products = get_popular_items('product', 'week', 20)

    project.add_view(user=request.user)

    # User-specific products and projects
    owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)

    context = {
        'project': project,
        "product_categories":product_categories,
        "table_data":table_data,
        "unique_sources":unique_sources,
        "similar_products":similar_products,
        "top_value_commodities":top_value_commodities,
        "your_products":your_products,
        "popular_products":popular_products,
        "owned_projects": owned_projects,
        "shared_projects":shared_projects,
        "your_projects":your_projects,
        "products_in_projects": json.dumps(products_in_projects),
    }
    return render(request, "main/project.html",context)

@show_new_notifications
@login_required
def search(request):
    products = Product.objects.filter(Q(user=None) | Q(user=request.user)).order_by('-view_count')
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


    # Handle search query
    search_query = request.GET.get('q')
    if search_query:
        # Filter products matching name, manufacturer_name, or description
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(manufacturer_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(original_name__icontains=search_query) |
            Q(included_products_in_this_epd__icontains=search_query) 
        )
        commodities = commodities.filter(
            Q(name__icontains=search_query) |
            Q(category__icontains=search_query) |
            Q(basic_description__icontains=search_query) |
            Q(substitutes__icontains=search_query) |
            Q(use__icontains=search_query) 
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

    if pchangemin and pchangemax and pchangemax > pchangemin:
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
    
    user_has_products = True if products.filter(user=request.user).exists() else False

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


    ITEMS_PER_PAGE = 24

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


    owned_projects, shared_projects, your_projects, products_in_projects = get_product_project_variables(request)


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
@valid_standard_membership_required
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
def user_settings(request):
    pricing_qs = SubscriptionPrice.objects.filter(featured=True)
    month_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.MONTHLY)
    year_qs = pricing_qs.filter(interval=SubscriptionPrice.IntervalChoices.YEARLY)

    user_sub_obj, created = UserSubscription.objects.get_or_create(user=request.user)
    sub_data = user_sub_obj.serialize()

    if request.method == 'POST':
        # refresh data request
        finished = refresh_active_users_subscriptions(user_ids=[request.user.id],
                                                      active_only=False)
        if finished:
            messages.success(request, "Membership data refreshed.")
        else:
            messages.error(request, "Membership data not refreshed. Please try again.")
        referer = request.META.get('HTTP_REFERER', '/')
        return redirect(referer)

    context = {
        "month_qs":list(month_qs),
        "year_qs":list(year_qs),
        "subscription": sub_data,
    }
    return render(request, "main/settings.html", context)


@login_required
def update_settings(request):
    if request.method == 'POST':
        profile = request.user.userprofile
        
        profile.cookie_personalisation = 'personalisation' in request.POST
        profile.email_notification = 'email_notification' in request.POST
        
        profile.save()
        return redirect('settings')



@login_required
def help(request):
    return render(request, 'main/help.html')


@login_required
def logged_contact_form(request):
    if request.method == "POST":
        text_content = request.POST.get("text-content")
        if text_content and text_content.strip() != '':
            user_email = request.user.email
            send_mail(
                f'New Contact Form Submission from {user_email}',
                f'{text_content}\n\nfrom {user_email}',
                settings.EMAIL_HOST_USER,  # Sender's email
                [settings.EMAIL_HOST_USER],  # Recipient's email
                fail_silently=False,
            )
            messages.success(request, 'Email has been sent, thank you for contacting us.')
            return redirect('help')
    return redirect('help')