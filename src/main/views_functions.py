from django.shortcuts import redirect
from .models import *
from django.db.models import Q, Count
from datetime import datetime, timedelta
from collections import defaultdict
import csv
import xlwt
from django.http import HttpResponse
from datetime import date
from .update_prices import add_1y_increase_to_products, add_top_value_commodities
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count
from django.utils.timezone import now, timedelta
from django.db.models import Count, OuterRef, Subquery
from collections import OrderedDict
import pandas as pd
from itertools import chain
from django.db.models import Count




def get_table_data_project(project):
    new_table_data = {}
    
    # Use list comprehension to build product data
    for product in project.products.all():
        graph_x, table_y = get_cumulative_line_chart_and_table_data_product(product.id)
        
        # Initialize product data
        product_data = {
            'commodity': [],
            'name': product.name,
            'slug': product.slug,
        }
        
        # Aggregate commodity data
        for com_name, interval_key in table_y.items():
            product_data['commodity'].append(com_name)
            for label, value in interval_key.items():
                if label != 'material':
                    product_data[label] = product_data.get(label, 0) + value
        
        new_table_data[product.id] = product_data
    
    return new_table_data


def get_cumulative_line_chart_and_table_data_product(product_id):
    today = datetime.now().date()
    five_years = timedelta(days=5 * 365)
    start_date, end_date = today - five_years, today + five_years

    ordered_colors = [
        'rgba(20, 33, 61, 1)', 'rgba(0, 0, 0, 1)', 'rgba(37, 99, 235, 1)',
        'rgba(252, 163, 17, 1)', 'rgba(229, 229, 229, 1)'
    ] + ['rgba(151, 157, 172, 1)'] * 30

    # Fetch related objects in a single query
    materials_proportions = MaterialProportion.objects.filter(product_id=product_id).select_related('commodity')
    commodity_lookup = {mp.commodity.id: mp.commodity for mp in materials_proportions}

    def generate_date_range(start_date, end_date):
        return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    all_dates = generate_date_range(start_date, end_date)
    all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates]

    graph_data = defaultdict(lambda: defaultdict(float))
    table_data = defaultdict(lambda: defaultdict(list))

    # Process each material proportion
    for material_proportion in materials_proportions:
        commodity = commodity_lookup[material_proportion.commodity_id]
        rate_for_price_kg = commodity.rate_for_price_kg
        currency_rate = commodity.currency.rate
        com_name = commodity.name

        table_data[com_name]['material'].append(material_proportion.material)

        # Fetch prices for the commodity within the date range
        prices = CommodityPrice.objects.filter(
            commodity_id=material_proportion.commodity_id,
            date__range=[start_date, end_date]
        ).order_by('date')

        for price in prices:
            price_value = (float(price.price) if price.price else float(price.projected_price) if price.projected_price and price.date > today else 0)
            if price_value:
                value = (price_value * float(material_proportion.proportion) * float(rate_for_price_kg)) / float(currency_rate)
                graph_data[com_name][price.date.strftime('%Y-%m-%d')] = value

    def fill_missing_dates(dates, data):
        df = pd.DataFrame({
            'date': [date.strftime('%Y-%m-%d') for date in dates],
            'value': [data.get(date.strftime('%Y-%m-%d'), 0) for date in dates]
        })

        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(full_index)

        df['value'] = df['value'].replace(0, pd.NA)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['value'] = df['value'].interpolate(method='time').ffill().bfill()

        return {date.strftime('%Y-%m-%d'): value for date, value in df['value'].items()}

    # Fill missing dates and normalize values
    for material_name, data in graph_data.items():
        filled_data = fill_missing_dates(all_dates, data)
        graph_data[material_name] = {date: filled_data.get(date, 0) for date in all_dates_str}

    today_str = today.strftime('%Y-%m-%d')
    today_sum = sum(data.get(today_str, 1.0) for data in graph_data.values())

    for com_name, data in graph_data.items():
        graph_data[com_name] = {date: round((value / today_sum) * 100, 2) for date, value in data.items()}

    sorted_graph_data = dict(sorted(graph_data.items(), key=lambda item: item[1][today_str], reverse=True))

    chart_data = {
        'labels': all_dates_str,
        'datasets': [
            {
                'label': material_name,
                'data': list(data.values()),
                'backgroundColor': ordered_colors[i % len(ordered_colors)],
                'fill': True,
                'pointRadius': 0
            }
            for i, (material_name, data) in enumerate(sorted_graph_data.items())
        ]
    }

    intervals = {
        '5y_ago': today - five_years,
        '2y_ago': today - timedelta(days=2 * 365),
        '1y_ago': today - timedelta(days=365),
        '6m_ago': today - timedelta(days=183),
        'today': today,
        '6m_ahead': today + timedelta(days=183),
        '1y_ahead': today + timedelta(days=365),
        '2y_ahead': today + timedelta(days=2 * 365),
        '5y_ahead': today + five_years
    }

    for com_name, data in sorted_graph_data.items():
        for interval_key, interval_date in intervals.items():
            table_data[com_name][interval_key] = data.get(interval_date.strftime("%Y-%m-%d"), 0)

    return chart_data, dict(OrderedDict(reversed(list(table_data.items())))) 


def get_cumulative_line_chart_and_table_data_commodity(commodity_id):
    # Set the reference date
    today = date.today()
    start_date = today - timedelta(days=5*365)  # Approximation for 5 years ago
    end_date = today + timedelta(days=5*365)  # Approximation for 1 year ahead

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

    def generate_date_range(start_date, end_date):
        return [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]

    all_dates = generate_date_range(start_date, end_date)
    all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates]

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
        # Create DataFrame with dates and corresponding values
        df = pd.DataFrame({
            'date': [date.strftime('%Y-%m-%d') for date in dates],
            'value': [data.get(date.strftime('%Y-%m-%d'), 0) for date in dates]
        })

        # Convert 'date' to datetime and set it as index
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)

        # Create a full date range and reindex the DataFrame
        full_index = pd.date_range(start=df.index.min(), end=df.index.max(), freq='D')
        df = df.reindex(full_index)

        # Replace zeros with NaN, convert values to numeric, and interpolate
        df['value'] = df['value'].replace(0, pd.NA)
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        df['value'] = df['value'].interpolate(method='time').ffill()
        if bfill:
            df['value'] = df['value'].bfill()

        # Return as a dictionary with dates in 'YYYY-MM-DD' format
        return {date.strftime('%Y-%m-%d'): value for date, value in df['value'].items()}

    # Apply the filling function to each dataset in graph_data
    for key, data in graph_data.items():
        if key == 'Price':
            filled_data = fill_missing_dates(all_dates, data)
            graph_data[key] = {date_str: round(filled_data.get(date_str, 0), 2) for date_str in filled_data.keys()}
        elif key != 'Price' and date_obj > today:
            filled_data = fill_missing_dates(all_dates, data, bfill=False)
            graph_data[key] = {date_str: round(filled_data.get(date_str, 0), 2) for date_str in filled_data.keys()}

    # Prepare data for the chart
    chart_data = {
        'labels': all_dates_str,
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
        chart_data['datasets'].append({
                'label': label,
                'data': [data.get(date, None) for date in all_dates_str],  # Use None for missing data
                'backgroundColor': ordered_colors[round(color_index) % len(ordered_colors)],
                'borderColor': border_colors[round(color_index) % len(border_colors)],
                'borderWidth': 2 if label == 'Price' else 1,
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
    # First, check if there's an exact match for the given date
    exact_price = CommodityPrice.objects.filter(commodity_id=commodity_id, date=target_date).first()

    if exact_price:
        # If price exists, use it; if not, use projected_price
        if exact_price.price:
            return exact_price.price
        elif exact_price.projected_price:
            return exact_price.projected_price

    # Define a range for the search
    date_range_start = target_date - timedelta(days=365)
    date_range_end = target_date + timedelta(days=365)

    # Retrieve all prices within the date range
    possible_prices = CommodityPrice.objects.filter(
        commodity_id=commodity_id,
        date__range=(date_range_start, date_range_end),
    ).order_by('date')

    if not possible_prices.exists():
        return None  # No prices found in the date range

    # Find the closest date in the possible prices
    closest_price = min(possible_prices, key=lambda x: abs(x.date - target_date))
    closest_past = possible_prices.filter(date__lte=target_date).order_by('-date').first()
    closest_future = possible_prices.filter(date__gte=target_date).order_by('date').first()

    closest_past_price = None
    if closest_past:
        days_to_closest_past = (target_date - closest_past.date).days
        if closest_past.price:
            closest_past_price = closest_past.price
        elif closest_past.projected_price:
            closest_past_price = closest_past.projected_price
    
    closest_future_price = None
    if closest_future:
        days_to_closest_future = (closest_future.date - target_date).days
        if closest_future.price:
            closest_future_price = closest_future.price
        elif closest_future.projected_price:
            closest_future_price = closest_future.projected_price

    total_days = days_to_closest_past + days_to_closest_future
    if closest_past_price and closest_future_price:
        new_commodity_price = closest_past_price * days_to_closest_past / total_days + closest_future_price * days_to_closest_future / total_days
    
    if not closest_past_price:
        new_commodity_price = closest_future_price
    
    if not closest_future_price:
        new_commodity_price = closest_past_price

    return new_commodity_price

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

    all_dates = sorted(all_date_objs)
    # Generate labels in the desired ISO format
    all_dates_str = [d.strftime('%Y-%m-%d') for d in all_dates]
    
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
        'labels': all_dates_str,
        'datasets': []
    }



    chart_data['datasets'].append({
            'label': 'Futures',
            'data': [graph_data.get(date_str, None) for date_str in all_dates_str],  # Use None for missing data
            'backgroundColor':border_color,
            'pointRadius': 2,
        })

    return chart_data, processed_table_data



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
        new_product.manufacturer_name = None
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


def get_popular_items(model_name, time_period, return_items, user_id=None):
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
    elif model_name == 'commodity':
        model_class = Commodity
        related_field = 'commodity'
    else:
        raise ValueError("Invalid model_name. Choose from 'product', 'commodity'.")

    # Subquery to count views for each model instance
    view_counts = View.objects.filter(
        viewed_at__date__gte=start_date,
        **{f'{related_field}__isnull': False}
    ).values(f'{related_field}__id').annotate(total_views=Count('id')).order_by('-total_views')

    # Query to get the top 10 products or commodities by view count
    if model_name == 'product':
        popular_items = (
            model_class.objects.filter(
                Q(user_id__isnull=True) | Q(user_id=user_id),  # Check if user is null or matches user_id
                id__in=Subquery(view_counts.values(f'{related_field}__id'))
            )
            .annotate(
                total_views=Subquery(
                    view_counts.filter(**{f'{related_field}__id': OuterRef('pk')}).values('total_views')
                )
            )
            .order_by('-total_views')[:return_items]
        )
    else:
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

