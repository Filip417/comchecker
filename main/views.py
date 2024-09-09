from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from .models import Product, Project, MaterialProportion, CommodityPrice, Commodity, CommodityProduction, View
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Count
from datetime import datetime, timedelta
import json
from collections import defaultdict
import csv
import xlwt
from django.http import HttpResponse
from django.contrib.auth import login, authenticate, logout
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
from django.contrib.auth.hashers import make_password
from django.db.models import Max
import uuid
from datetime import date
from django.db.models import F, Func, Value, FloatField
from django.db.models.functions import Abs
from .update_prices import add_1y_increase_to_products, add_top_value_commodities
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.utils.timezone import now, timedelta
from django.db.models import Count, OuterRef, Subquery
from collections import OrderedDict
import numpy as np
import pandas as pd
from django.http import JsonResponse
from itertools import chain
from django.db.models import Sum, Count


#Decorator
def logged_in_cant_access(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(reverse('logged'))  # Redirect to 'logged' view if user is authenticated
        return view_func(request, *args, **kwargs)
    return wrapper


# Views
@logged_in_cant_access
def index(request):
    if request.user.is_authenticated:
        return redirect(reverse('logged'))
    return render(request, "main/index.html")


@logged_in_cant_access
def register(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        user = User.objects.filter(username=email)
        if user.exists():
            messages.info(request, "Email already used, log in.")
            return redirect('/login/')

        if password1 != password2:
            messages.error(request, "Passwords do not match.")
            return redirect('/register/')
        
        # Validate password complexity
        try:
            validate_password(password1)
        except ValidationError as e:
            messages.error(request, "\n".join(e))
            return redirect('/register/')

        # Hash the password
        hashed_password = make_password(password1)

        # Create a new User object with the provided information
        user = User.objects.create_user(
            username=email,
            email=email,
            password=hashed_password
        )

        login(request, user)
        messages.success(request, "Account created Successfully!")
        return redirect(reverse('logged'))
    return render(request, 'main/register.html')

@logged_in_cant_access
def user_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(username=email, password=password)
        
        if user is None:
            messages.error(request, 'Invalid credentials')
            return redirect('/login/')          
        else:
            login(request, user)
            return redirect(reverse('logged'))

    return render(request, 'main/login.html')

@logged_in_cant_access
def password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
            # Generate token and UID
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            # Construct password reset URL
            reset_url = request.build_absolute_uri(
                reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            )
            # Send email with password reset link
            subject = 'Password Reset'
            html_message = render_to_string('main/password_reset_email.html', {
                'user': user,
                'reset_url': reset_url,
                'new_date': datetime.now(),
                'email_start':email.split("@")[0]
            })
            send_mail(
                subject,
                '',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
                html_message=html_message  # Specify the html_message parameter
            )
            messages.success(request, 'Check your email for the password reset link.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Email address not found.')
    return render(request, 'main/password_reset.html')

@logged_in_cant_access
def reset_link(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')

            if password1 and password2 and password1 == password2:
                 # Validate password complexity
                try:
                    validate_password(password1)
                except ValidationError as e:
                    messages.error(request, "\n".join(e))
                    return redirect(reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token}))
                
                # Hash the new password
                user.set_password(password1)
                user.save()
                messages.success(request, 'Your new password has been successfully set.')
                login(request, user)
                return redirect(reverse('logged'))
            else:
                messages.error(request, 'Passwords do not match.')
        else:
            context = {
                'uidb64': uidb64,
                'token': token,
            }
            return render(request, 'main/password_reset_link.html', context)
    else:
        messages.error(request, 'The reset link is invalid or has expired.')
        return redirect('password_reset')

    return render(request, 'main/password_reset_link.html')

@login_required
def user_logout(request):
    logout(request)
    return redirect('index')

@login_required
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
        if new_project_name and project_id:
            project = get_object_or_404(Project, id=project_id, user=request.user)
            project.name = new_project_name
            project.slug = project.generate_unique_slug()
            project.description = new_project_description
            project.save()
    return redirect('project', project_slug=project.slug)

@login_required
def new_project(request):
    if request.method == 'POST':
        new_project_name = request.POST.get('new_project_name', 'Unnamed Project')
        new_project_description = request.POST.get('new_project_description', None)
        project = Project.objects.create(user=request.user, name=new_project_name, description=new_project_description)
        project.calculate_increase()
        project.save()
        messages.success(request, f"New project {project.name} has been created.")
    
    return redirect('project', project_slug=project.slug)

@login_required
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
            new_project_name = request.POST.get('new_project_name', 'Unnamed Project')
            project = Project.objects.create(user=request.user, name=new_project_name)
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

@login_required
def edit_product(request, slug):
    # Retrieve the product object, handle the case where it might not exist
    product = get_object_or_404(Product, slug=slug)

    if product.user != request.user:
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
    


@login_required
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

    product.add_view()

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

    commodity.add_view()

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

def notifications(request):
    context = {
        "name":"name"
    }
    return render(request, "main/notifications.html",context)


def user_settings(request):
    context = {
        "name":"name"
    }
    return render(request, "main/settings.html", context)




###
###
###
###
###
### Not views
def get_table_data_project(project):
    new_table_data = {}
    for product in project.products.all():
        graph_x, table_y = get_cumulative_line_chart_and_table_data_product(product.id)
        new_table_data[product.id] = {}
        new_table_data[product.id]['commodity'] = []
        new_table_data[product.id]['name'] = product.name
        new_table_data[product.id]['slug'] = product.slug
        for com_name, interval_key in table_y.items():
            new_table_data[product.id]['commodity'].append(com_name)
            for label, value in interval_key.items():
                if label != 'material':
                    try:
                        new_table_data[product.id][label] += value
                    except KeyError:
                        new_table_data[product.id][label] = 0
                        new_table_data[product.id][label] += value
    
    return new_table_data
    




def get_cumulative_line_chart_and_table_data_product(product_id):
    today = datetime.now().date()
    start_date = today - timedelta(days=5*365)  # Approximation for 5 years ago
    end_date = today + timedelta(days=5*365)  # Approximation for 5 years ahead

    ordered_colors = [
        'rgba(20, 33, 61, 1)',
        'rgba(0, 0, 0, 1)',
        'rgba(37, 99, 235, 1)',
        'rgba(252, 163, 17, 1)',
        'rgba(229, 229, 229, 1)'
    ]
    
    for n in range(0, 30):
        ordered_colors.append('rgba(151, 157, 172, 1)') 

    graph_data = defaultdict(lambda: defaultdict(float))
    table_data = defaultdict(lambda: defaultdict(list))

    materials_proportions = MaterialProportion.objects.filter(product_id=product_id)

    # Fetch all commodities that are in the materials_proportions list
    commodities = Commodity.objects.filter(id__in=[m.commodity_id for m in materials_proportions])

    # Build a lookup dictionary for commodities
    commodity_lookup = {commodity.id: commodity for commodity in commodities}

    # Populate graph_data with raw values
    for materialproportion in materials_proportions:
        commodity = commodity_lookup.get(materialproportion.commodity_id)

        # Accessing rate_for_price_kg and currency rate
        rate_for_price_kg = commodity.rate_for_price_kg
        currency_rate = commodity.currency.rate
        com_name = commodity.name

        # FOR TABLE DATA
        # Check if 'material' key exists and if it is a list
        if 'material' not in table_data[com_name] or not isinstance(table_data[com_name]['material'], list):
            table_data[com_name]['material'] = []

        # Append the material to the list
        table_data[com_name]['material'].append(materialproportion.material)


        # Fetch prices for the given commodity and filter by date range
        prices_for_material = CommodityPrice.objects.filter(
            commodity_id=materialproportion.commodity_id,
            date__range=[start_date, end_date]
        ).order_by('date')

        all_date_objs = [today]
        for price in prices_for_material:
            if price.price or price.projected_price:
                # Parse date and calculate first day of the month
                date_obj = price.date
                if date_obj not in all_date_objs:
                    all_date_objs.append(date_obj)

        all_dates_objs_sorted = sorted(all_date_objs)
        # Generate labels in the desired ISO format
        all_dates_label = [d.strftime('%Y-%m-%d') for d in all_dates_objs_sorted]

        # Calculate the value
        for price in prices_for_material:
            if price.price:
                value = float(price.price) * float(materialproportion.proportion) * float(rate_for_price_kg) / float(currency_rate)
                date_str = price.date.strftime('%Y-%m-%d')
                if value != 0:
                    graph_data[com_name][date_str] = value
            if price.projected_price and price.date > today:
                value = float(price.projected_price) * float(materialproportion.proportion) * float(rate_for_price_kg) / float(currency_rate)
                date_str = price.date.strftime('%Y-%m-%d')
                if value != 0:
                    graph_data[com_name][date_str] = value


    # Fill missing dates with the last known value
    def fill_missing_dates(dates, data):
        sorted_dates = sorted(dates)
        filled_data = {}
        # Forward fill
        last_value = None
        for date in sorted_dates:
            date_str = date.strftime('%Y-%m-%d')
            if date_str in data:
                last_value = data[date_str]
            if last_value is not None:
                filled_data[date_str] = last_value
        
        # Backward fill
        next_value = None
        for date in reversed(sorted_dates):
            date_str = date.strftime('%Y-%m-%d')
            if date_str in filled_data:
                next_value = filled_data[date_str]
            elif next_value is not None:
                filled_data[date_str] = next_value

        return filled_data

    # Apply the filling function to each dataset in graph_data
    for material_name, data in graph_data.items():
        # Convert all_dates_objs_sorted to strings for filling
        sorted_dates_strings = [d.strftime('%Y-%m-%d') for d in all_dates_objs_sorted]
        filled_data = fill_missing_dates(all_dates_objs_sorted, data)
        # Use the filled data to update the graph_data
        graph_data[material_name] = {date_str: filled_data.get(date_str, 0) for date_str in sorted_dates_strings}       


    # # Step 2: Calculate the total sum across all materials for
    today_str = date(today.year, today.month, today.day).strftime('%Y-%m-%d')
    today_sum = sum(
        data.get(today_str, 0.0) for data in graph_data.values()
    )
 
    # Step 3: Change values to represent the percentage of total sum of Today
    for com_name, data in graph_data.items():
        for date_str in data.keys():
            new_value_indexed = round((data[date_str] / today_sum) * 100, 2)
            graph_data[com_name][date_str] = new_value_indexed

    # Step 4: Sort the graph_data based on the value on jan_first
    sorted_graph_data = dict(
        sorted(graph_data.items(), key=lambda item: item[1][today_str], reverse=True)
    )


    # Prepare data for the chart
    chart_data = {
        'labels': all_dates_label,
        'datasets': []
    }

    color_index = 0
    for material_name, data in sorted_graph_data.items():
        chart_data['datasets'].append({
            'label': material_name,
            'data': list(data.values()),  # Use list of values here
            'backgroundColor': ordered_colors[color_index % len(ordered_colors)],
            'fill': True,
            'pointRadius': 0,
        })
        color_index += 1



    # TABLE DATA CODE - for table_data variable

    # Convert interval values to datetime objects
    intervals = {
        '5y_ago': (today - timedelta(days=5*365)),
        '2y_ago': (today - timedelta(days=2*365)),
        '1y_ago': (today - timedelta(days=1*365)),
        '6m_ago': (today - timedelta(days=183)),
        'today': today,
        '6m_ahead': (today + timedelta(days=183)),
        '1y_ahead': (today + timedelta(days=1*365)),
        '2y_ahead': (today + timedelta(days=2*365)),
        '5y_ahead': (today + timedelta(days=5*365))
    }

    def find_closest_date(target_date, date_list):
        """Find the closest date to the target_date from the date_list."""
        closest_date = min(date_list, key=lambda d: abs(d - target_date))
        return closest_date

    def convert_to_date(date_str):
        """Convert a date string to a date object."""
        return datetime.strptime(date_str, "%Y-%m-%d").date()

    # Collect all dates from graph_data and convert to datetime.date objects
    graph_data_dates = {}
    for com_name, data in sorted_graph_data.items():
        graph_data_dates[com_name] = {convert_to_date(date_str): value for date_str, value in data.items()}

    # Assign data values for table
    for com_name, data in graph_data_dates.items():
        for interval_key, interval_date in intervals.items():
            # Find the closest date in graph_data to the current interval_date
            closest_date = find_closest_date(interval_date, list(data.keys()))
            # Assign the value from graph_data to table_data based on closest_date
            table_data[com_name][interval_key] = data[closest_date]


    reversed_table_data = OrderedDict(reversed(list(table_data.items())))

    # Return the updated table data
    return chart_data, dict(reversed_table_data)
    

def download_table_excel_project(project_name, table_data):
    # Download table_data in excel format
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{project_name} raw materials data.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(f'Table data')

    # Modify the table data
    modified_table_data = {}

    for key, value in table_data.items():
        # Remove 'slug'
        value.pop('slug', None)
        
        # Use 'name' as the new key
        name = value.pop('name')
        
        # Add modified entry to new dictionary
        modified_table_data[name] = value
    
    table_data = modified_table_data

    if table_data:
        # Extract headers dynamically from the first item in table_data
        first_key = next(iter(table_data))
        headers = ['Product name'] + list(table_data[first_key].keys())

        # Write the header row
        for col_num, column_title in enumerate(headers):
            ws.write(0, col_num, column_title)

        # Write the data rows
        for row_num, (key, data) in enumerate(table_data.items(), start=1):
            ws.write(row_num, 0, key)
            
            for col_num, header in enumerate(headers[1:], start=1):  # Skip 'Commodity' and 'Material'
                value = data.get(header, '-')
                if isinstance(value, list):  # Handle list values if necessary
                    value = ', '.join(map(str, value))
                if isinstance(value, float):
                    ws.write(row_num, col_num, round(value,2))
                else:
                    ws.write(row_num, col_num, value)
    
    wb.save(response)
    return response

def download_table_csv_project(project_name, table_data):
    # Download table_data in csv format and ignore render, because page will not change
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{project_name} raw materials data.csv"'

    writer = csv.writer(response)

    if table_data:
        # Write the header row
        writer.writerow(['Product name','Commodities','-5y','-2y','-1y','-6m','now','+6m','+1y','+2y','+5y'])

        # Write the data rows
        for commodity, data in table_data.items():
            coms = data['commodity']  # assuming data['material'] is your list of materials
            coms_str = ', '.join(coms) if len(coms) > 1 else coms[0]
            writer.writerow([
                data['name'],
                coms_str,
                round(data['5y_ago'],2),
                round(data['2y_ago'],2),
                round(data['1y_ago'],2),
                round(data['6m_ago'],2),
                round(data['today'],2),
                round(data['6m_ahead'],2),
                round(data['1y_ahead'],2),
                round(data['2y_ahead'],2),
                round(data['5y_ahead'],2)
            ])
    return response

def download_table_excel_product(product_name, table_data):
    # Download table_data in excel format
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{product_name} raw materials data.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(f'Table data')
    
    if table_data:
        # Extract headers dynamically from the first item in table_data
        first_key = next(iter(table_data))
        headers = ['Commodity'] + list(table_data[first_key].keys())

        # Write the header row
        for col_num, column_title in enumerate(headers):
            ws.write(0, col_num, column_title)

        # Write the data rows
        for row_num, (key, data) in enumerate(table_data.items(), start=1):
            ws.write(row_num, 0, key)
            
            for col_num, header in enumerate(headers[1:], start=1):  # Skip 'Commodity' and 'Material'
                value = data.get(header, '-')
                if isinstance(value, list):  # Handle list values if necessary
                    value = ', '.join(map(str, value))
                ws.write(row_num, col_num, value)
    
    wb.save(response)
    return response

def download_table_csv_product(product_name, table_data):
    # Download table_data in csv format and ignore render, because page will not change
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{product_name} raw materials data.csv"'

    writer = csv.writer(response)

    if table_data:
        # Write the header row
        writer.writerow(['Commodity','Material','-5y','-2y','-1y','-6m','now','+6m','+1y','+2y','+5y'])

        # Write the data rows
        for commodity, data in table_data.items():
            materials = data['material']  # assuming data['material'] is your list of materials
            materials_str = ', '.join(materials) if len(materials) > 1 else materials[0]
            writer.writerow([
                commodity,
                materials_str,
                data['5y_ago'],
                data['2y_ago'],
                data['1y_ago'],
                data['6m_ago'],
                data['today'],
                data['6m_ahead'],
                data['1y_ahead'],
                data['2y_ahead'],
                data['5y_ahead']
            ])
    return response


def get_closest_commodity_price(commodity_id, target_date):
    # Define a range for the search; adjust the timedelta as needed
    date_range_start = target_date - timedelta(days=120)
    date_range_end = target_date + timedelta(days=120)

    # Retrieve all prices within the date range
    possible_prices = CommodityPrice.objects.filter(
        commodity_id=commodity_id,
        date__range=(date_range_start, date_range_end),
        price__isnull=False
    ).order_by('date')

    if not possible_prices.exists():
        return None  # No prices found in the date range

    # Convert queryset to list for using min()
    possible_prices_list = list(possible_prices)

    # Find the closest date
    closest_price = min(possible_prices_list, key=lambda x: abs(x.date - target_date))

    return closest_price.price

def get_map_data_product(product_id):
    today = datetime.now().date()

    map_data = defaultdict(lambda: {'production': 0.0, 'country_name': ''})
    total_production = 0

    # Retrieve the material proportions for the product
    materials_proportions = MaterialProportion.objects.filter(product_id=product_id)

    # Fetch all commodities that are in the materials_proportions list
    commodities = Commodity.objects.filter(id__in=[m.commodity_id for m in materials_proportions])

    # Build a lookup dictionary for commodities
    commodity_lookup = {commodity.id: commodity for commodity in commodities}

    # Step 1: Populate map_data with total productions
    for materialproportion in materials_proportions:
        # Retrieve commodity production data
        com_productions = CommodityProduction.objects.filter(commodity_id=materialproportion.commodity_id)
        commodity = commodity_lookup.get(materialproportion.commodity_id)
        commodity_price = get_closest_commodity_price(materialproportion.commodity_id, today)

        for com_production in com_productions:
            if commodity_price:
                country_code = com_production.country_code
                material_production = com_production.production * commodity_price * materialproportion.proportion * commodity.rate_for_price_kg / commodity.currency.rate
                
                map_data[country_code]['production'] += material_production
                total_production += material_production
                map_data[country_code]['country_name'] = com_production.country_name


    # Step 2: Calculate percentages based on total_production
    if total_production > 0:
        for country_code in map_data:
            map_data[country_code]['production'] = (map_data[country_code]['production'] / total_production) * 100

    # Convert defaultdict to regular dictionary before returning
    return dict(map_data)


def get_futures_chart_and_table_data_commodity(commodity_id):
    border_color = 'rgba(13, 71, 161, 1)'

    today = date.today()
    start_date = today
    end_date = today + timedelta(days=10*365)  # Approximation for 1 year ahead
    
    # Fetch all prices for the given commodity and filter by date range
    commodity_prices = CommodityPrice.objects.filter(
        commodity_id=commodity_id,
        date__range=[today, end_date],
        futures_price__isnull=False
    ).order_by('date')


    all_date_objs = []
    graph_data = {}
    table_data = {}
    for price in commodity_prices:
        date_obj = price.date
        if date_obj not in all_date_objs:
            all_date_objs.append(date_obj)
        date_str = date_obj.strftime('%Y-%m-%d')

        if price.futures_price:
            graph_data[date_str] = round(price.futures_price, 2)

    all_dates_objs_sorted = sorted(all_date_objs)
    # Generate labels in the desired ISO format
    all_dates_label = [d.strftime('%Y-%m-%d') for d in all_dates_objs_sorted]
    
    table_data = graph_data

    formatted_table_data = {}
    for date_key in table_data.keys():
        date_object = datetime.strptime(date_key, "%Y-%m-%d")
        formatted_date = date_object.strftime("%b %Y")
        formatted_table_data[formatted_date] = table_data[date_key]

    # Create a list of tuples with the price difference direction
    processed_table_data = []
    previous_price = None

    for date_key_formatted, price in formatted_table_data.items():
        if previous_price is None:
            direction = None  # No comparison for the first item
        elif price > previous_price:
            direction = "up"
        elif price < previous_price:
            direction = "down"
        else:
            direction = "same"
        
        processed_table_data.append((date_key_formatted, price, direction))
        previous_price = price

        

    # Prepare data for the chart
    chart_data = {
        'labels': all_dates_label,
        'datasets': []
    }



    chart_data['datasets'].append({
            'label': 'Futures',
            'data': [graph_data.get(date_str, None) for date_str in all_dates_label],  # Use None for missing data
            'backgroundColor':border_color,
            'pointRadius': 2,
        })

    return chart_data, processed_table_data

def get_cumulative_line_chart_and_table_data_commodity(commodity_id):
    # Set the reference date
    today = date.today()
    start_date = today - timedelta(days=5*365)  # Approximation for 5 years ago
    end_date = today + timedelta(days=5*365)  # Approximation for 1 year ahead

    # Adjust start_date and end_date to be the first day of their respective months
    start_date = start_date.replace(day=1)
    end_date = end_date.replace(day=1)


    ordered_colors = [
        'rgba(13, 71, 161, 0.01)',  # Forecast not shown
        'rgba(187, 222, 251, 0.02)',  # 90%
        'rgba(187, 222, 251, 0.02)',  # 90%
        'rgba(100, 181, 246, 0.03)',  # 75%
        'rgba(100, 181, 246, 0.03)',  # 75%
        'rgba(33, 150, 243, 0.06)',  # 50%
        'rgba(33, 150, 243, 0.06)',  # 50%
        'rgba(25, 118, 210, 0.1)'   # 25%
        'rgba(25, 118, 210, 0.1)'   # 25%
        'rgba(21, 101, 192, 0.2)'   # 10%
        'rgba(21, 101, 192, 0.2)'   # 10%
    ]

    border_colors = [
        'rgba(13, 71, 161, 1)',    # Forecast
        'rgba(187, 222, 251, 1)',    # 90%
        'rgba(187, 222, 251, 1)',    # 90%
        'rgba(100, 181, 246, 1)',    # 75%
        'rgba(100, 181, 246, 1)',    # 75%
        'rgba(33, 150, 243, 1)',    # 50%
        'rgba(33, 150, 243, 1)',    # 50%
        'rgba(25, 118, 210, 1)',   # 25%
        'rgba(25, 118, 210, 1)',   # 25%
        'rgba(21, 101, 192, 1)'    # 10%
        'rgba(21, 101, 192, 1)'    # 10%
    ]

    graph_data = defaultdict(lambda: defaultdict(float))
    table_data = defaultdict(lambda: defaultdict(list))

    # Fetch all prices for the given commodity and filter by date range
    commodity_prices = CommodityPrice.objects.filter(
        commodity_id=commodity_id,
        date__range=[start_date, end_date]
    ).order_by('date')

    all_date_objs = []
    date_for_loop = start_date
    while date_for_loop <= end_date + timedelta(days=1):
        all_date_objs.append(date_for_loop)
        date_for_loop += timedelta(days=1)

    all_dates_objs_sorted = sorted(all_date_objs)
    # Generate labels in the desired ISO format
    all_dates_label = [d.strftime('%Y-%m-%d') for d in all_dates_objs_sorted]

    for price in commodity_prices:
        date_obj = price.date
        date_str = date_obj.strftime('%Y-%m-%d')

        if price.price:
            price_to_assign = price.price
        elif price.projected_price:
            price_to_assign = price.projected_price
        else:
            price_to_assign = None

        # Collect the different percentiles
        percentiles = {
            'Price': price_to_assign,
            'Top 90%': float(price.top_90_percent) if price.top_90_percent else None,
            'Bottom 90%': float(price.bottom_90_percent) if price.bottom_90_percent and price.projected_price else None,
            'Top 75%': float(price.top_75_percent) if price.top_75_percent and price.projected_price else None,
            'Bottom 75%': float(price.bottom_75_percent) if price.bottom_75_percent and price.projected_price else None,
            'Top 50%': float(price.top_50_percent) if price.top_50_percent and price.projected_price else None,
            'Bottom 50%': float(price.bottom_50_percent) if price.bottom_50_percent and price.projected_price else None,
            'Top 25%': float(price.top_25_percent) if price.top_25_percent and price.projected_price else None,
            'Bottom 25%': float(price.bottom_25_percent) if price.bottom_25_percent and price.projected_price else None,
            'Top 10%': float(price.top_10_percent) if price.top_10_percent and price.projected_price else None,
            'Bottom 10%': float(price.bottom_10_percent) if price.bottom_10_percent and price.projected_price else None,
        }

        for label, value in percentiles.items():
            if value:
                # Filter 'Price' data to show only up to today's date
                if label == 'Price':
                    graph_data[label][date_str] = round(value, 2)
                elif label != 'Price' and date_obj > today:
                    graph_data[label][date_str] = round(value, 2)
    

    def fill_missing_dates(dates, data, bfill=True):
            # Convert the original data to a DataFrame
            df = pd.DataFrame(list(data.items()), columns=['Date', 'Value'])
            df['Date'] = pd.to_datetime(df['Date'])
            df.set_index('Date', inplace=True)
            
            # Create a full date range DataFrame
            full_range = pd.DataFrame(index=pd.to_datetime(dates))
            
            # Reindex to fill missing dates, preserving original values
            df_full = df.reindex(full_range.index)
            
            # Perform linear interpolation and forward/backward filling
            if bfill:
                df_full['Value'] = df_full['Value'].interpolate(method='linear').ffill().bfill()
            else:
                df_full['Value'] = df_full['Value'].interpolate(method='linear').ffill()

            # Combine with the original data to ensure existing values are not overwritten
            df_full.update(df)

            # Convert back to dictionary
            filled_data = df_full['Value'].to_dict()
            return {date.strftime('%Y-%m-%d'): value for date, value in filled_data.items()}

    # Apply the filling function to each dataset in graph_data
    for key, data in graph_data.items():
        if key == 'Price':
            filled_data = fill_missing_dates(all_dates_objs_sorted, data)
            graph_data[key] = {date_str: round(filled_data.get(date_str, 0), 2) for date_str in filled_data.keys()}
        elif key != 'Price' and date_obj > today:
            filled_data = fill_missing_dates(all_dates_objs_sorted, data, bfill=False)
            graph_data[key] = {date_str: round(filled_data.get(date_str, 0), 2) for date_str in filled_data.keys()}

    # Prepare data for the chart
    chart_data = {
        'labels': all_dates_label,
        'datasets': []
    }

    # Define how to apply the fill property dynamically
    fill_options = {
        'Top 90%': '+1',   # Fill between the Top 90% and the dataset below it
        'Top 75%': '+1',
        'Top 50%': '+1',
        'Top 25%': '+1',
        'Price': False,     # The actual price line won't fill
        'Bottom 90%': False,
        'Bottom 75%': False,
        'Bottom 50%': False,
        'Bottom 25%': False,
    }

    color_index = 0
    for label, data in graph_data.items():
        if label == 'Price':
            chart_data['datasets'].append({
                'label': label,
                'data': [data.get(date, None) for date in all_dates_label],  # Use None for missing data
                'backgroundColor': ordered_colors[color_index % len(ordered_colors)],
                'borderColor': border_colors[color_index % len(border_colors)],
                'borderWidth': 2,
                'fill': fill_options.get(label, False),
                'pointRadius': 0,
            })
        else:
            chart_data['datasets'].append({
                'label': label,
                'data': [data.get(date, None) for date in all_dates_label],  # Use None for missing data
                'backgroundColor': ordered_colors[round(color_index) % len(ordered_colors)],
                'borderColor': border_colors[round(color_index) % len(border_colors)],
                'borderWidth': 1,
                'borderDash': [5, 5],
                'fill': fill_options.get(label, False),
                'pointRadius': 0,
            })
        color_index += 1

    # Define intervals for table data
    intervals = {
        '5y_ago': (today - timedelta(days=5*365)).strftime('%Y-%m-%d'),
        '2y_ago': (today - timedelta(days=2*365)).strftime('%Y-%m-%d'),
        '1y_ago': (today - timedelta(days=365)).strftime('%Y-%m-%d'),
        '6m_ago': (today - timedelta(days=183)).strftime('%Y-%m-%d'),
        'today': today.strftime('%Y-%m-%d'),
        '6m_ahead': (today + timedelta(days=183)).strftime('%Y-%m-%d'),
        '1y_ahead': (today + timedelta(days=365)).strftime('%Y-%m-%d'),
        '2y_ahead': (today + timedelta(days=2*365)).strftime('%Y-%m-%d'),
        '5y_ahead': (today + timedelta(days=5*365)).strftime('%Y-%m-%d')
    }


    table_data = defaultdict(lambda: defaultdict(list))

    for label, data in graph_data.items():
        for key_interval, interval_date in intervals.items():
            # Handle the 'Price' label specifically
            if label == 'Price':
                table_data['Price'][key_interval] = data.get(interval_date, "-")
            else:
                # Match the last 3 characters of 'label' with the first 3 characters of 'key_table_data'
                percentile_key = f'{label[-3:]} Chance'
                table_data[percentile_key][key_interval].append(data.get(interval_date, "-"))


    return chart_data, dict(table_data)



def get_map_data_commodity(commodity_id):
    map_data = defaultdict(lambda: {'production': 0.0, 'country_name': ''})

    com_productions = CommodityProduction.objects.filter(commodity_id=commodity_id)

    if com_productions:
        for com_production in com_productions:
            country_code = com_production.country_code

            map_data[country_code]['production'] = com_production.production
            map_data[country_code]['country_name'] = com_production.country_name

    return dict(map_data)





def similarity_score(string1, string2):
    # Split strings into lists of words
    try:
        words1 = string1.split()
        words2 = string2.split()
    except AttributeError:
        return 0
    
    # Initialize a counter for matching words
    match_count = 0
    
    # Iterate through each word in words1 and check if it exists in words2
    for word1 in words1:
        if word1 in words2:
            match_count += 1
    
    # Calculate similarity score as the percentage of matching words in string1
    try:
        score = (match_count / len(words1)) * 100
    except ZeroDivisionError:
        score = 0
    return score


def get_similar_commodities(commodity):
    # Initialize variables to store similar commodities and their scores
    similar_commodities = []

    # Iterate over all products to find most similar ones
    all_commodities = Commodity.objects.all()
    for other_commodity in all_commodities:
        if other_commodity.id != commodity.id:
            name_score = similarity_score(commodity.name, other_commodity.name)
            category_score = similarity_score(commodity.category, other_commodity.category)
            price_history_type_score = similarity_score(commodity.price_history_type, other_commodity.price_history_type)
            description_score = similarity_score(commodity.basic_description, other_commodity.basic_description)
            substitutes_score = similarity_score(commodity.substitutes, other_commodity.substitutes)

            # Calculate combined similarity score (you can adjust weights as needed)
            combined_similarity = name_score + description_score + substitutes_score + category_score + price_history_type_score

            # Store the commodity and its similarity score
            similar_commodities.append((other_commodity, combined_similarity))

    similar_commodities.sort(key=lambda x: x[1], reverse=True)
    similar_commodities = [commodity for commodity, score in similar_commodities]
    
    return similar_commodities

def get_similar_products_for_products(products, request, limit=50):
    # Initialize variables to store similar products and their scores
    similar_products = []
    
    # Iterate over all products to find most similar ones
    all_products = Product.objects.filter(Q(user=None) | Q(user=request.user))

    input_product_ids = []
    for pro in products:
        if pro.id not in input_product_ids:
            input_product_ids.append(pro.id)

    for other_product in all_products:
        for input_product in products:
            if other_product.id not in input_product_ids:
                # Get word counts for other product's name and description
                name_score = similarity_score(input_product.name, other_product.name)
                category_1_score = similarity_score(input_product.category_1, other_product.category_1)
                category_3_score = 1 if input_product.category_3 == other_product.category_3 else 0
                original_name_score = similarity_score(input_product.original_name, other_product.original_name)
                description_score = similarity_score(input_product.description, other_product.description)

                # Calculate combined similarity score (you can adjust weights as needed)
                combined_similarity = name_score + description_score + category_1_score + category_3_score + original_name_score

                # Store the product and its similarity score
                similar_products.append((other_product, combined_similarity))

    # Sort similar products by similarity score in descending order
    similar_products.sort(key=lambda x: x[1], reverse=True)

    # Extract only the products from the sorted list
    similar_products = [product for product, score in similar_products[:limit]]
    
    return similar_products

def get_similar_products(product, request):
    # Initialize variables to store similar products and their scores
    similar_products = []
    
    # Iterate over all products to find most similar ones
    all_products = Product.objects.filter(Q(user=None) | Q(user=request.user))

    for other_product in all_products:
        if other_product.id != product.id:
            # Get word counts for other product's name and description
            name_score = similarity_score(product.name, other_product.name)
            category_1_score = similarity_score(product.category_1, other_product.category_1)
            category_3_score = 1 if product.category_3 == other_product.category_3 else 0
            original_name_score = similarity_score(product.original_name, other_product.original_name)
            description_score = similarity_score(product.description, other_product.description)

            # Calculate combined similarity score (you can adjust weights as needed)
            combined_similarity = name_score + description_score + category_1_score + category_3_score + original_name_score

            # Store the product and its similarity score
            similar_products.append((other_product, combined_similarity))

    # Sort similar products by similarity score in descending order
    similar_products.sort(key=lambda x: x[1], reverse=True)

    # Extract only the products from the sorted list
    similar_products = [product for product, score in similar_products]
    
    return similar_products

def get_products_by_commodity(commodity, request):
    # Get all product IDs that have the given commodity_id in MaterialProportion
    product_ids = MaterialProportion.objects.filter(commodity_id=commodity.id).values_list('product_id', flat=True)
    
    # Get all products that match the found product IDs
    products = Product.objects.filter(Q(user=None) | Q(user=request.user), id__in=product_ids)

    return products

def download_table_excel_commodity(name, table_data):
    # Download table_data in excel format
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{name} raw materials data.xls"'
    
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(f'Table data')

    if table_data:
        # Extract headers dynamically from the first item in table_data
        first_key = next(iter(table_data))
        headers = list(table_data[first_key].keys())

        # Write the header row
        for col_num, column_title in enumerate(['Forecast'] + headers):
            ws.write(0, col_num, column_title)

        # Write the data rows
        for row_num, (key, data) in enumerate(table_data.items(), start=1):
            ws.write(row_num, 0, key)
            for col_num, header in enumerate(headers, start=1):  # Start from 1 since 0 is 'Key'
                value = data.get(header, '-')
                if isinstance(value, list):  # Handle list values if necessary
                    value = ', '.join(map(str, value))
                ws.write(row_num, col_num, value)
    
    wb.save(response)
    return response

def download_table_csv_commodity(name, table_data):
    # Download table_data in csv format and ignore render, because page will not change
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{name} raw materials data.csv"'

    writer = csv.writer(response)

    if table_data:
            # Extract headers dynamically from the first item in table_data
            first_key = next(iter(table_data))
            headers = list(table_data[first_key].keys())

            # Write the header row
            writer.writerow(['Forecast'] + headers)

            # Write the data rows
            for key, data in table_data.items():
                row = [key]
                for header in headers:
                    value = data.get(header, '-')
                    if isinstance(value, list):  # Handle list values if necessary
                        value = ', '.join(map(str, value))
                    row.append(value)
                writer.writerow(row)

    return response



def download_map_excel(name, map_data):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{name} geo production data.xls"'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(f'Table data')
    
    if map_data:
        # Write the header row
        col_num = 0
        for column_title in ['Country', 'Country name', 'Production']:
            ws.write(0, col_num, column_title)
            col_num +=1
        
        #Write the data rows
        row_num = 1
        for country, data in map_data.items():
            ws.write(row_num, 0, country)
            ws.write(row_num, 1, data['country_name'])
            ws.write(row_num, 2, data['production'])
            row_num += 1
    
    wb.save(response)
    return response


def download_map_csv(name, map_data):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{name} geo production data.csv"'
    writer = csv.writer(response)

    if map_data:
        # Write the header row
        writer.writerow(['Country code', 'Country name', 'Production'])

        # Write the data rows
        for country, data in map_data.items():
            writer.writerow([
                country,
                data['country_name'],
                data['production'],
            ])

    return response


def download_futures_excel(name, futures_data):
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = f'attachment; filename="{name} futures quotes.xls"'
    wb = xlwt.Workbook(encoding='utf-8')
    ws = wb.add_sheet(f'Futures data')

    if futures_data:
        # Write the header row
        col_num = 0
        for column_title in ['Date', 'Price', 'Change']:
            ws.write(0, col_num, column_title)
            col_num +=1
        
        #Write the data rows
        row_num = 1
        for data in futures_data:
            ws.write(row_num, 0, data[0])
            ws.write(row_num, 1, data[1])
            ws.write(row_num, 2, data[2])
            row_num += 1
    
    wb.save(response)
    return response

def download_futures_csv(name, futures_data):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{name} futures quotes.csv"'
    writer = csv.writer(response)

    if futures_data:
        # Write the header row
        writer.writerow(['Date', 'Price', 'Change'])

        # Write the data rows
        for data in futures_data:
            writer.writerow([
                data[0],
                data[1],
                data[2]
            ])

    return response


def save_new_product(request):
    # future feature perhaps image_file = request.FILES.get('image-file')
    product_slug = request.POST.get('slug')
    product_name = request.POST.get('title')
    description = request.POST.get('description')
    category = request.POST.get('category')
    if not category or category == 'None':
        category == 'Other'


    # Initialize a new product variable
    new_product = None

    # If user is request.user and slug product slug than just assign values 
    # otherwise create new product
    try:
        # Try to get an existing product
        new_product = Product.objects.get(slug=product_slug, user=request.user)
        # Update the existing product
        new_product.name = product_name
        new_product.description = description
        new_product.reg_date = date.today()
        new_product.category_3 = category
        new_product.category_2 = category
        new_product.category_1 = category
        new_product.manufacturer_name = 'Your product'
        new_product.manufacturer_country = 'United Kingdom'
        new_product.create_new_slug()
    except ObjectDoesNotExist:
        # Create a new Product instance if it does not exist
        new_product = Product(
            name=product_name,
            description=description,
            user=request.user,
            reg_date=date.today(),
            category_3=category,
            category_2=category,
            category_1=category,
            manufacturer_name = 'Your product',
            manufacturer_country = 'United Kingdom',
        )
    new_product.save()

    # Iterate through dynamically added rows
    material_proportion_cleared = False
    row_number = 0
    while row_number < 100:
        content_name = request.POST.get(f'content-name-{row_number}')
        content_commodity_id = request.POST.get(f'content-commodity-{row_number}')
        content_proportion = request.POST.get(f'content-proportion-{row_number}')

        if content_name and content_commodity_id and content_proportion:
            if not material_proportion_cleared:
                MaterialProportion.objects.filter(product_id=new_product.id).delete()
                material_proportion_cleared = True
            new_proportion = MaterialProportion(
                product_id=new_product.id,
                material=content_name,
                proportion=content_proportion,
                commodity_id=content_commodity_id
            )
            new_proportion.save()
        row_number += 1

    
    products_to_add_1y_price_change = []
    products_to_add_1y_price_change.append(new_product)
    add_1y_increase_to_products(products_to_add_1y_price_change)
    add_top_value_commodities(products_to_add_1y_price_change)

    return redirect('product', slug=new_product.slug)


def get_popular_items(model_name, time_period, return_items):
    today = now().date()
    
    if time_period == 'week':
        start_date = today - timedelta(days=today.weekday())  # Start of the week
    elif time_period == 'month':
        start_date = today.replace(day=1)  # Start of the month
    elif time_period == 'year':
        start_date = today.replace(month=1, day=1)  # Start of the year
    else:
        raise ValueError("Invalid time_period. Choose from 'week', 'month', 'year'.")

    if model_name == 'product':
        model_class = Product
        related_field = 'product'
        related_model = Product
    elif model_name == 'commodity':
        model_class = Commodity
        related_field = 'commodity'
        related_model = Commodity
    else:
        raise ValueError("Invalid model_name. Choose from 'product', 'commodity'.")

    # Subquery to count views for each model instance
    view_counts = View.objects.filter(
        viewed_at__date__gte=start_date,
        **{f'{related_field}__isnull': False}
    ).values(f'{related_field}__id').annotate(total_views=Count('id')).order_by('-total_views')

    # Query to get the top 10 products or commodities by view count
    popular_items = (
        model_class.objects.filter(
            id__in=Subquery(view_counts.values(f'{related_field}__id'))
        )
        .annotate(total_views=Subquery(view_counts.filter(**{f'{related_field}__id': OuterRef('pk')}).values('total_views')))
        .order_by('-total_views')[:return_items]
    )

    return popular_items


def get_product_project_variables(request):
    owned_projects = request.user.owned_projects.all().order_by('-created_at')
    shared_projects = request.user.shared_projects.all().order_by('-created_at')
    # Combine owned and shared projects
    your_projects = list(chain(owned_projects, shared_projects))

    # Check if products are already associated with any project
    products_in_projects = {}
    for project in your_projects:
        project_products = project.products.all()
        for product in project_products:
            if product.id not in products_in_projects:
                products_in_projects[product.id] = [project.id]
            else:
                products_in_projects[product.id].append(project.id)
    return owned_projects, shared_projects, your_projects, products_in_projects