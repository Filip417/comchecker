from datetime import date
from django.db.models import Sum, F, ExpressionWrapper, fields
import sys
import os
import freecurrencyapi
from django.core.mail import send_mail
from django.conf import settings

# Live prices update
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import re
import random
import time
import pandas as pd
import os
from datetime import datetime, date
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import email_notification_token
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.db.models.functions import Cast
from django.db.models import ExpressionWrapper, F, fields
from django.db.models.functions import Abs, Extract
from django.db import transaction
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from decouple import config
# from commodities_data import commodities_data

# Set the Django settings module environment variable
# Add the Django project root directory to the Python path
# project_root = r'C:\\Users\\sawin\\Documents\\Commodity Project\\django_project\\comchecker'
# sys.path.append(project_root)

# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comchecker.settings")

# # Initialize Django
# import django
# django.setup()


from main.models import (
    Product, 
    MaterialProportion, 
    Commodity, 
    CommodityProduction, 
    Currency, 
    CommodityPrice,
    Notification,
    Project,
)

chrome_options = Options()

GITHUB_ACTIONS = config('GH_ACTIONS', cast=bool)
if GITHUB_ACTIONS:
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.83 Safari/537.36")
    chrome_options.add_argument("--window-size=1920,1080")
    # Optional to add perhaps to reduce load time for selenium
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-infobars")



today = date(2024, 7, 1)
last_year = date(2023, 7, 1)



futures_commodities_data_input  = {
    "Aluminium": {"url_code": "Q8Y00", "currency": "USD"},
    "Coal": {"url_code": "LQY00", "currency": "USD"},
    "Cobalt": {"url_code": "U8Y00", "currency": "USD"},
    "Copper": {"url_code": "O9Y00", "currency": "USD"},
    "Cotton": {"url_code": "CTY00", "currency": "USD"},
    "Crude Oil": {"url_code": "CLY00", "currency": "USD"},
    "Gold": {"url_code": "GCY00", "currency": "USD"},
    "Iron Ore": {"url_code": "TRY00", "currency": "USD"},
    "Kraft Pulp": {"url_code": "VLY00", "currency": "CNY"},
    "Lead": {"url_code": "R0Y00", "currency": "USD"},
    "Lumber": {"url_code": "LBY00", "currency": "USD"},
    "Natural Gas": {"url_code": "NGY00", "currency": "USD"},
    "Nickel": {"url_code": "Q0Y00", "currency": "USD"},
    "Palladium": {"url_code": "PAY00", "currency": "USD"},
    "Silver": {"url_code": "SIU00", "currency": "USD"},
    "Steel": {"url_code": "V7Y00", "currency": "USD"},
    "Steel Scrap": {"url_code": "C-F24", "currency": "USD"},
    "Tin": {"url_code": "S4Y00", "currency": "USD"},
    "Zinc": {"url_code": "O0Y00", "currency": "USD"},
    "EU Carbon Permits": {"url_code": "CKH23", "currency": "EUR"},
    "Rubber": {"url_code": "W2Y00", "currency": "USD"}
}




def get_price(date, commodity_id):
    closest_price_entry = (
        CommodityPrice.objects
        .filter(commodity=commodity_id)
        .annotate(date_diff=ExpressionWrapper(
            Abs(Extract(F('date') - date, 'epoch') / 86400),  # Extract seconds and convert to days
            output_field=fields.FloatField()  # Use a float field for the date difference
        ))
        .order_by('date_diff')  # Order by the smallest date difference
        .values('price')
        .first()
    )        
    return closest_price_entry['price'] if closest_price_entry else 0

def update_total_production(commodities):
    for commodity in commodities:
        commodity.update_production_total()
    print('total production updated for all commodities')



def add_1y_increase_to_products(products):
    # Pre-fetch material proportions for all products
    materials_proportions = MaterialProportion.objects.filter(product__in=products).select_related('commodity', 'commodity__currency')
    
    # Pre-fetch commodities data and store in lookup dict
    commodities = Commodity.objects.filter(id__in=[m.commodity_id for m in materials_proportions])
    commodity_lookup = {commodity.id: commodity for commodity in commodities}

    # Group materials by product for processing
    product_materials = {}
    for material in materials_proportions:
        product_materials.setdefault(material.product_id, []).append(material)
    
    # Process each product
    products_to_update = []
    for product in products:
        if product.id not in product_materials:
            continue
        
        materials = product_materials[product.id]
        total_proportion = sum([material.proportion for material in materials]) or 0

        weighted_price_lastyear = 0
        weighted_price_today = 0

        # Loop through up to 10 materials for the product
        for material in materials[:10]:
            commodity = commodity_lookup.get(material.commodity_id)
            
            # Retrieve last year and today prices once
            last_year_price_raw = get_price(last_year, material.commodity_id)
            today_price_raw = get_price(today, material.commodity_id)
            
            # Access commodity data
            rate_for_price_kg = commodity.rate_for_price_kg
            currency_rate = commodity.currency.rate

            if total_proportion > 0:
                weighted_price_lastyear += last_year_price_raw * material.proportion * rate_for_price_kg / currency_rate
                weighted_price_today += today_price_raw * material.proportion * rate_for_price_kg / currency_rate
        
        # Calculate increase and update product field
        if weighted_price_lastyear != 0:
            product.increasefromlastyear = (weighted_price_today - weighted_price_lastyear) / weighted_price_lastyear * 100
        else:
            product.increasefromlastyear = None
        
        products_to_update.append(product)
    
    # Perform bulk update
    Product.objects.bulk_update(products_to_update, ['increasefromlastyear'])
    print('Bulk update add_1y_increase_to_products done')



def add_1y_increase_to_commodities(commodities):
    # List to store updated commodities
    commodities_to_update = []
    
    for commodity in commodities:
        last_year_price = get_price(last_year, commodity.id)
        today_price = get_price(today, commodity.id)

        if last_year_price and today_price:
            commodity.increasefromlastyear = (today_price - last_year_price) / last_year_price * 100
        else:
            commodity.increasefromlastyear = None  # Or any default value
        
        # Append the modified commodity to the list
        commodities_to_update.append(commodity)
    
    # Perform a bulk update for all commodities
    Commodity.objects.bulk_update(commodities_to_update, ['increasefromlastyear'])

    print(f'1 year increase updated for {len(commodities_to_update)} commodities')


def add_price_now(commodities):
    # List to store commodities to be updated
    commodities_to_update = []
    
    for commodity in commodities:
        today_price = get_price(today, commodity.id)
        commodity.price_now = today_price
        
        # Append the modified commodity to the list
        commodities_to_update.append(commodity)
    
    # Perform a bulk update for all commodities
    Commodity.objects.bulk_update(commodities_to_update, ['price_now'])
    
    print(f'Price now updated for {len(commodities_to_update)} commodities')


def add_1y_increase_to_products_and_add_top_value_commodities(products, batch_size=100):
    # Pre-fetch all necessary data in bulk
    materials_proportions = MaterialProportion.objects.filter(product__in=products).select_related('commodity', 'commodity__currency')

    # Pre-fetch commodities data and store in lookup dict
    commodity_ids = [m.commodity_id for m in materials_proportions]
    commodities = Commodity.objects.filter(id__in=commodity_ids)
    commodity_lookup = {commodity.id: commodity for commodity in commodities}

    # Group materials by product for processing
    product_materials = {}
    for material in materials_proportions:
        product_materials.setdefault(material.product_id, []).append(material)

    # Create lists to hold updated products
    products_to_update = []
    
    for product in products:
        if product.id not in product_materials:
            continue
        
        materials = product_materials[product.id]
        total_proportion = sum([material.proportion for material in materials]) or 0

        weighted_price_lastyear = 0
        weighted_price_today = 0

        commodity_contributions = {}

        # Process up to 10 materials for each product
        for material in materials:
            commodity = commodity_lookup.get(material.commodity_id)

            # Retrieve last year and today prices once
            last_year_price_raw = get_price(last_year, material.commodity_id)
            today_price_raw = get_price(today, material.commodity_id)

            # Access commodity data
            rate_for_price_kg = commodity.rate_for_price_kg
            currency_rate = commodity.currency.rate

            if total_proportion > 0:
                # Calculate weighted prices for last year and today
                weighted_price_lastyear += last_year_price_raw * material.proportion * rate_for_price_kg / currency_rate
                weighted_price_today += today_price_raw * material.proportion * rate_for_price_kg / currency_rate

                # Calculate weighted value for top commodity
                weighted_today_value = today_price_raw * material.proportion * rate_for_price_kg / currency_rate
                if commodity.id not in commodity_contributions:
                    commodity_contributions[commodity.id] = {'commodity': commodity, 'contribution': 0}
                commodity_contributions[commodity.id]['contribution'] += weighted_today_value
        
        # Calculate the 1-year increase
        if weighted_price_lastyear != 0:
            product.increasefromlastyear = (weighted_price_today - weighted_price_lastyear) / weighted_price_lastyear * 100
        else:
            product.increasefromlastyear = None

        # Determine the top-value commodity by the highest cumulative contribution
        top_value_commodity = max(commodity_contributions.values(), key=lambda x: x['contribution'])['commodity'] if commodity_contributions else None
        product.top_value_commodity = top_value_commodity

        products_to_update.append(product)

        # Batch update every batch_size products
        if len(products_to_update) >= batch_size:
            with transaction.atomic():
                Product.objects.bulk_update(products_to_update, ['increasefromlastyear', 'top_value_commodity'])
            products_to_update.clear()

    # Final bulk update for remaining products
    if products_to_update:
        with transaction.atomic():
            Product.objects.bulk_update(products_to_update, ['increasefromlastyear', 'top_value_commodity'])

    print('Batch processing completed for products.')


def add_top_value_commodities(products):
    for product in products:
        materials_proportions = MaterialProportion.objects.filter(product=product.id)
        total_proportion = materials_proportions.aggregate(total_proportion=Sum('proportion'))['total_proportion'] or 0

        # Fetch all commodities that are in the materials_proportions list
        commodities = Commodity.objects.filter(id__in=[m.commodity_id for m in materials_proportions])

        # Build a lookup dictionary for commodities
        commodity_lookup = {commodity.id: commodity for commodity in commodities}

        commodity_contributions = {}
        # Loop through materials and process the required data
        for material in materials_proportions[:10]:
            commodity = commodity_lookup.get(material.commodity_id)
            
            # Retrieve prices for last year and today
            today_price_raw = get_price(today, material.commodity_id)
            
            # Accessing rate_for_price_kg and currency rate
            rate_for_price_kg = commodity.rate_for_price_kg
            currency_rate = commodity.currency.rate

            # Retrieve prices for last year and today
            today_price_raw = get_price(today, material.commodity_id)

            if total_proportion > 0:
                print(f'Material proportion: {material.proportion}')
                print(f'Rate price per kg: {rate_for_price_kg}')
                print(f'Currency rate: {currency_rate}')

                weighted_today_value = today_price_raw * material.proportion * rate_for_price_kg / currency_rate
                if commodity.id not in commodity_contributions:
                    commodity_contributions[commodity.id] = {'commodity': commodity, 'contribution': 0}
                commodity_contributions[commodity.id]['contribution'] += weighted_today_value
        
        # Determine the top-value commodity by the highest cumulative contribution
        top_value_commodity = max(commodity_contributions.values(), key=lambda x: x['contribution'])['commodity'] if commodity_contributions else None
        
        product.top_value_commodity = top_value_commodity if top_value_commodity else None
        product.save()


def update_currencies(API_KEY):
    client = freecurrencyapi.Client(API_KEY)

    latest_result = client.latest()
    print(f'Latest results: {latest_result}')

    # Assuming the API response has 'USD' as the base currency
    rates = latest_result.get('data', {})

    # Update each currency entry in the database
    for currency in Currency.objects.all():
        if currency.code == 'USD':
            continue  # Skip updating USD itself, it should remain 1

        rate_to_usd = rates.get(currency.code)
        if rate_to_usd is not None:
            Currency.objects.update_or_create(
                code=currency.code,
                defaults={
                    'rate': rate_to_usd,
                    'date': date.today(),  # Update with today's date
                }
            )



# products = Product.objects.all()
# commodities = Commodity.objects.all()

# add_1y_increase_to_products(products)
# add_1y_increase_to_commodities(commodities)
# add_price_now(commodities)
# add_top_value_commodities(products)
# update_total_production(commodities)

# API_KEY = 'fca_live_HKyQMt07Aa18hKfhzE2hj3YJFrmHpXhsGel3UKUb'
# update_currencies(API_KEY)


######################
# Live prices update #
######################

def get_fred_price(url, commodities_data, com):
    # Send a request to the website
    response = requests.get(url)
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract the relevant data from the page
    try:
        commodities_data[com]['observation_date'] = soup.find('span', class_='series-meta-value').text.strip()
        commodities_data[com]['price'] = float(soup.find('span', class_='series-meta-observation-value').text.strip())
        commodities_data[com]['updated_date'] = soup.find('span', class_='series-meta-updated-date').text.strip()
        commodities_data[com]['updated_time'] = soup.find('span', class_='series-meta-updated-time').text.strip()
        commodities_data[com]['date'] = datetime.now().strftime('%Y-%m-%d')
        print(f'{com}: {commodities_data[com]}')
    except AttributeError:
        print("Could not find one or more elements on the page.")


def get_investing_com_price(url, commodities_data, com):
    # Send a request to the website
    response = requests.get(url)
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    

    # Extract the date from the <time> tag
    try:
        time_element = soup.find('time', {'data-test': 'trading-time-label'})
        if time_element and time_element.has_attr('datetime'):
            commodities_data[com]['observation_date'] = time_element['datetime']  # Get the datetime attribute
    except AttributeError:
        print("Could not find the time element.")

    # Extract the value from the <div> tag
    try:
        value_element = soup.find('div', {'data-test': 'instrument-price-last'})
        if value_element:
            price_unformatted = value_element.text.strip()
            commodities_data[com]['price'] = float(price_unformatted.replace(',',''))
            commodities_data[com]['date'] = datetime.now().strftime('%Y-%m-%d')
            print(f'{com}: {commodities_data[com]}')
    except AttributeError:
        print("Could not find the value element.")

def get_trading_economics(url, element_id, commodities_data, com):
    # Initialize WebDriver (assuming you're using Chrome, you can adjust if using a different browser)
    driver = webdriver.Chrome(options=chrome_options)

    # Open the specified URL
    driver.get(url)
    
    try:
        # Wait for the price element to be present and visible on the page
        wait = WebDriverWait(driver, 10)  # Wait up to 10 seconds
        # print(driver.page_source) # TODO remove when github actions fixed
        price_element = wait.until(EC.visibility_of_element_located((By.ID, element_id)))
        
        if price_element:
            commodities_data[com]['price'] = float(price_element.text.strip())
            commodities_data[com]['date'] = datetime.now().strftime('%Y-%m-%d')
            print(f'{com}: {commodities_data[com]}')
    except Exception as e:
        print(f"Could not find the price element: {e}")

    # Close the WebDriver
    time.sleep(random.randrange(1,5,1))
    driver.quit()



def get_investing_com_v2_price(url, commodities_data, com):
    # Send a request to the website
    response = requests.get(url)
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all <span> elements and locate the one starting with "Actual"
    try:
        spans = soup.find_all('span')
        for span in spans:
            text = span.get_text(strip=True)
            if text.startswith("Actual"):
                # Extract the value after "Actual"
                match = re.search(r'Actual\s*(\S+)', text)
                if match:
                    commodities_data[com]['price'] = float(match.group(1).strip())  # Get the value and strip any extra whitespace
                    commodities_data[com]['date'] = datetime.now().strftime('%Y-%m-%d')
                    print(f'{com}: {commodities_data[com]}')
                break  # Exit loop once the target span is found
    except Exception as e:
        print(f"Could not find the value element: {e}")
    

def get_live_prices_commodities(commodities_data):
    commodities_to_exclude = [
    "Aluminium",
    "Cobalt",
    "Copper",
    "Cotton",
    "Crude Oil",
    "Gold",
    "Hot-Rolled Steel",
    "Iron Ore",
    "Lead",
    "Lumber",
    "Natural Gas",
    "Nickel",
    "Palladium",
    "Silver",
    "Tin",
    "Zinc"
    ]
    # TODO update code
    for com in commodities_data:
        print(com)
        if com not in commodities_to_exclude:        
            if commodities_data[com]['source'] == 'FRED':
                get_fred_price(commodities_data[com]['url'], commodities_data, com)
            elif commodities_data[com]['source'] == 'Investing.com':
                get_investing_com_price(commodities_data[com]['url'], commodities_data, com)
            elif commodities_data[com]['source'] == 'Trading Economics':
                get_trading_economics(commodities_data[com]['url'],
                                            commodities_data[com]['element_id'], commodities_data, com)
            elif commodities_data[com]['source'] == 'Investing.com v2':
                get_investing_com_v2_price(commodities_data[com]['url'], commodities_data, com)
            elif commodities_data[com]['source'] == 'ONS':
                print('Needs manual update 15/20th each month!')
        print(f'Commodity {com} excluded, price update from futures cash')
    print('Values updated')
    return commodities_data

def save_to_excel(new_dict, directory_to_save):
    try:
        # Create a DataFrame from the dictionary
        if not os.path.exists(directory_to_save):
            os.makedirs(directory_to_save)
        df = pd.DataFrame([new_dict])  # Ensure new_dict is treated as a single row
        
        # Define the file path
        file_path = os.path.join(directory_to_save, 'commodities_data.xlsx')
        
        if os.path.exists(file_path):
            # Load the existing Excel file
            with pd.ExcelFile(file_path) as xls:
                existing_df = pd.read_excel(xls, sheet_name='Sheet1')
            
            # Append the new data to the existing DataFrame
            updated_df = pd.concat([existing_df, df], ignore_index=True)
        else:
            # If the file does not exist, use the new DataFrame as is
            updated_df = df
        
        # Save the updated DataFrame to the Excel file
        updated_df.to_excel(file_path, sheet_name='Sheet1', index=False)
        print('saved to excel!')
    except:
        print('error occured not saved to excel')


def update_live_commodity_prices(commodity_data, batch_size=100):
    # Pre-fetch all commodities and currencies
    commodity_names = commodity_data.keys()
    commodities = Commodity.objects.filter(name__in=commodity_names)
    currencies = Currency.objects.filter(code__in=[data.get('currency') for data in commodity_data.values()])

    # Create lookup dictionaries for commodities and currencies
    commodity_lookup = {commodity.name: commodity for commodity in commodities}
    currency_lookup = {currency.code: currency for currency in currencies}

    # Lists to hold new or updated CommodityPrice instances
    prices_to_create = []
    prices_to_update = []

    # Fetch existing CommodityPrices to avoid duplicates during insert
    existing_prices = CommodityPrice.objects.filter(
        commodity__name__in=commodity_names,
        date__in=[data.get('date') for data in commodity_data.values()]
    )
    existing_prices_lookup = {
        (price.commodity_id, price.currency_id, price.date): price for price in existing_prices
    }

    # Process each commodity data
    for com, data in commodity_data.items():
        price = data.get('price')
        date = data.get('date')
        currency_code = data.get('currency')

        if price and date and currency_code and com:
            commodity = commodity_lookup.get(com)
            currency = currency_lookup.get(currency_code)

            if not commodity or not currency:
                # Skip if commodity or currency not found
                continue

            commodity = Commodity.objects.get(name=com)
            currency = Currency.objects.get(code=currency_code)

            # Update or create the CommodityPrice record
            obj, created = CommodityPrice.objects.update_or_create(
                commodity=commodity,
                currency=currency,
                date=date,
                defaults={'price': price}
            )

            # TODO remove printing when stable code Optionally, print to verify
            if created:
                print(f"Created new CommodityPrice record: {obj}")
            else:
                print(f"Updated CommodityPrice record: {obj}")

    print("Update live commodity prices completed.")

####
####
####




# new_dict = get_live_prices_commodities(commodities_data)
# directory_to_save = r'C:\Users\sawin\Documents\Commodity Project\django_project\comchecker\main'
# save_to_excel(new_dict, directory_to_save)
# update_live_commodity_prices(new_dict)



#########################
# Futures prices update #
#########################




def parse_contract_date(contract_name):
    # Extract the date part from the contract name, e.g., "Oct '24" from "VLV24 (Oct '24)"
    try:
        date_str = contract_name.split('(')[-1].strip(') ')
        if date_str == 'Cash':
            return datetime.today().strftime("%Y-%m-%d")
        # Convert "Oct '24" to "2024-10-01"
        date_obj = datetime.strptime(date_str, "%b '%y")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        return "Invalid Date"


def get_futures_prices(url_code):
    url = f'https://www.barchart.com/futures/quotes/{url_code}/futures-prices'
    data_dict = {}

    # Initialize WebDriver (assuming you're using Chrome)
    driver = webdriver.Chrome(options=chrome_options)

    # Open the specified URL
    driver.get(url)
    try:
        # Wait for the bc-data-grid element to load
        wait = WebDriverWait(driver, 20)  # Increase the wait to 20 seconds
        bc_data_grid = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "bc-data-grid"))
        )

        time.sleep(3)

        # Execute the JavaScript to scroll down to get all rows visible
        driver.execute_script("scroll(0, 2000);")

        time.sleep(3)

        # Use JavaScript to access nested shadow DOM elements in one step
        rows_script = """
        return Array.from(document.querySelector('bc-data-grid').shadowRoot
            .querySelector('div._grid').querySelectorAll('set-class.row'))
            .map(row => Array.from(row.children).map(cell => {
                const tb = cell.querySelector('text-binding');
                return tb && tb.shadowRoot ? tb.shadowRoot.innerHTML : '';
            }));
        """

        # Execute the JavaScript to get all the data from the shadow DOM
        rows = driver.execute_script(rows_script)

        # Define headers
        headers = ["Contract", "Last", "Change", "Open", "High", "Low", "Previous", "Volume", "Open Int", "Time"]

        # Create dictionary with contract names as keys
        
        for row in rows:
            if (len(row) - 2) == len(headers):  # Ensure each row has the correct number of columns
                contract_name = row[1]  # Assuming the contract name is in the second column
                date_str = parse_contract_date(contract_name)

                # Exclude the first and last columns from the row
                modified_row = row[1:-1]

                # Create a dictionary for the row based on the modified headers
                row_dict = {headers[i]: modified_row[i] for i in range(len(headers))}
                data_dict[date_str] = row_dict

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close the WebDriver
        driver.quit()
    
    return data_dict


def get_live_prices(futures_commodities_data):
    for com, data in futures_commodities_data.items():
        print(f'Commodity info gathering started for {com}')
        data['futures'] = get_futures_prices(data['url_code'])
        print(f'Commodity info gathered {com}')
    return futures_commodities_data

def update_futures_prices_in_db(futures_commodities_data):
    # Prepare to hold commodities and currencies
    commodities = Commodity.objects.filter(name__in=futures_commodities_data.keys())
    currency_codes = {data.get('currency') for data in futures_commodities_data.values()}
    currencies = Currency.objects.filter(code__in=currency_codes)

    # Create lookup dictionaries for commodities and currencies
    commodity_lookup = {commodity.name: commodity for commodity in commodities}
    currency_lookup = {currency.code: currency for currency in currencies}

    # Prepare to collect all CommodityPrice records for bulk updates
    prices_to_create_or_update = []
    
    for com, data in futures_commodities_data.items():
        currency_code = data.get('currency')
        commodity = commodity_lookup.get(com)
        currency = currency_lookup.get(currency_code)
        futures = data.get('futures')

        if not futures:
            print(f"No futures prices available for {com}")
            continue
        # Clear all existing futures_prices for this commodity before inserting new ones
        CommodityPrice.objects.filter(commodity=commodity).update(futures_price=None)
        for date, data in futures.items():
            # Extract relevant data
            try:
                price_str = re.sub(r'[^\d.,]', '', data.get('Last'))
                price = float(price_str.replace(',', ''))
            except ValueError:
                price = None
            if price and date and currency_code and commodity.id:
                # Update or create the CommodityPrice record
                today = datetime.today().strftime("%Y-%m-%d")
                
                # Handle the 'Cash' date case and futures price insertion
                final_date = today if date == 'Cash' else date
                
                # Insert price into 'price' if date is today, otherwise 'futures_price'
                obj, created = CommodityPrice.objects.update_or_create(
                    commodity=commodity,
                    currency=currency,
                    date=final_date,
                    defaults={'price': price} if final_date == today else {'futures_price': price}
                )
                # Optionally, print to verify
                if created:
                    print(f"Created new CommodityPrice record: {obj}")
                else:
                    print(f"Updated CommodityPrice record: {obj}")
    print("Futures prices update completed.")


# futures_commodities_data = get_live_prices(futures_commodities_data_input)
# update_futures_prices_in_db(futures_commodities_data)

from datetime import timedelta
from django.utils import timezone

def check_all_notifications_and_send_emails():
    notifications_to_check = Notification.objects.filter(user__isnull=False, activated=False)
    for notification in notifications_to_check:
        check_notification_and_send_email(notification.id)

def get_closest_commodity_price(commodity_id, target_date, days_range=365):
    # First, check if there's an exact match for the given date
    exact_price = CommodityPrice.objects.filter(commodity_id=commodity_id, date=target_date).first()

    if exact_price:
        # If price exists, use it; if not, use projected_price
        if exact_price.price:
            return exact_price.price
        elif exact_price.projected_price:
            return exact_price.projected_price

    # Define a range for the search
    date_range_start = target_date - timedelta(days_range)
    date_range_end = target_date + timedelta(days_range)

    # Retrieve all prices within the date range
    possible_past_prices = CommodityPrice.objects.filter(
        commodity_id=commodity_id,
        price__isnull=False,
        date__range=(date_range_start, target_date),
    ).order_by('-date')  # Ordering by date descending for closest past

    possible_future_prices = CommodityPrice.objects.filter(
        commodity_id=commodity_id,
        projected_price__isnull=False,
        date__range=(target_date, date_range_end),
    ).order_by('date')  # Ordering by date ascending for closest future

    if not possible_past_prices.exists() and not possible_future_prices.exists():
        return None  # No prices found in the date range

    closest_past = possible_past_prices.first() if possible_past_prices.exists() else None
    closest_future = possible_future_prices.first() if possible_future_prices.exists() else None

    # Initialize variables for prices and days
    closest_past_price = None
    closest_future_price = None

    # Calculate past-related values if closest_past exists
    if closest_past:
        days_to_closest_past = (target_date - closest_past.date).days
        closest_past_price = closest_past.price or closest_past.projected_price

    # Calculate future-related values if closest_future exists
    if closest_future:
        days_to_closest_future = (closest_future.date - target_date).days
        closest_future_price = closest_future.price or closest_future.projected_price

    # Handle cases where both past and future prices are present
    if closest_past and closest_future:
        total_days = days_to_closest_past + days_to_closest_future
        new_commodity_price = (
            closest_past_price * days_to_closest_past / total_days +
            closest_future_price * days_to_closest_future / total_days
        )
    elif closest_past:
        # If only past prices are available
        new_commodity_price = closest_past_price
    elif closest_future:
        # If only future prices are available
        new_commodity_price = closest_future_price
    else:
        return None  # Fallback in case something went wrong

    return new_commodity_price

def get_closest_product_price(product_id, target_date):
    # Fetch all material proportions for the product
    materials_proportions = MaterialProportion.objects.filter(product_id=product_id).select_related('commodity')

    if not materials_proportions.exists():
        return None  # No materials found for the product

    total_product_price = 0.0

    for materialproportion in materials_proportions:
        commodity = materialproportion.commodity

        # Get the closest commodity price for the given date
        closest_commodity_price = get_closest_commodity_price(commodity.id, target_date)

        if closest_commodity_price is None:
            continue  # Skip if no price found for the commodity

        # Calculate the price contribution for this material
        rate_for_price_kg = commodity.rate_for_price_kg
        currency_rate = commodity.currency.rate

        material_price = (
            closest_commodity_price * materialproportion.proportion * rate_for_price_kg / currency_rate
        )

        # Accumulate the total product price
        total_product_price += material_price

    return total_product_price if total_product_price > 0 else None  # Return total price or None if no price found

def get_closest_project_price(project_id, target_date):
    # Fetch the project
    project = Project.objects.prefetch_related('products').get(id=project_id)

    # Fetch all products associated with the project
    products = project.products.all()

    if not products.exists():
        return None  # No products found in the project

    total_price = 0.0
    product_count = 0

    for product in products:
        # Get the closest product price for the given date
        closest_product_price = get_closest_product_price(product.id, target_date)

        if closest_product_price is None:
            continue  # Skip if no price found for the product

        # Accumulate the total price and count of valid products
        total_price += closest_product_price
        product_count += 1

    # Calculate the average price across all products
    if product_count == 0:
        return None  # No valid prices found

    average_price = total_price / product_count

    return average_price    


def check_notification_and_send_email(notification_id):
    updated = False
    sent = False
    notification_to_check = Notification.objects.get(id=notification_id, user__isnull=False, activated=False)

    
    def update_notification_db(notification_id, new_activated_value):
        try:
            # Use get() to fetch the notification instance or raise an exception if it doesn't exist
            notification = Notification.objects.get(id=notification_id)
            notification.activated = True
            notification.activated_at = timezone.now()
            notification.activated_value = new_activated_value
            notification.save()
            return True
        except Notification.DoesNotExist:
            # Return False if the notification doesn't exist
            return False

    def send_notification_email(notification_id):
        try:
            # Use get() to fetch the notification instance or raise an exception if it doesn't exist
            notification = Notification.objects.get(id=notification_id)
            if notification.email_notification:
                user = notification.user
                if not user.userprofile.email_notification:
                    return False
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = email_notification_token.make_token(user)
                BASE_URL = settings.BASE_URL
                subject = f'Notification {notification} activated'
                from_email = settings.EMAIL_HOST_USER
                recipient_list = [user.email]
                text_content = f'{notification}\n\n email sent to {user.email}'
                html_content = render_to_string('main/notification_email.html',
                    {
                        'notification': notification,
                        'user': user,
                        'token':token,
                        'uidb64':uidb64,
                        'BASE_URL':BASE_URL,
                        })
                # Create the email
                email = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
                email.attach_alternative(html_content, "text/html")  # Attach the HTML version
                
                # Send the email
                email.send(fail_silently=False)

                # Save notification status in db
                notification.email_sent = True
                notification.email_sent_at = timezone.now()
                notification.save()
                return True
        except Notification.DoesNotExist:
            # Return False if the notification doesn't exist
            return False

    if notification_to_check:
        notification = notification_to_check
        if notification.product:
            creation_price = get_closest_product_price(notification.product.id, notification.created_at.date())
            future_check_price = get_closest_product_price(notification.product.id, notification.change_by)
        elif notification.commodity:
            creation_price = get_closest_commodity_price(notification.commodity.id, notification.created_at.date())
            future_check_price = get_closest_commodity_price(notification.commodity.id, notification.change_by)
        elif notification.project:
            creation_price = get_closest_project_price(notification.project.id, notification.created_at.date())
            future_check_price = get_closest_project_price(notification.project.id, notification.change_by)

        if creation_price and future_check_price:
            calculated_change = (future_check_price - creation_price) / creation_price * 100
            change_to_check = notification.change
            print(f'Calculated change: {calculated_change}')
            print(f'Change to check: {change_to_check}')
            if (change_to_check >= 0 and calculated_change >= change_to_check) or (change_to_check < 0 and calculated_change < change_to_check):
                updated = update_notification_db(notification.id, calculated_change)
                sent = send_notification_email(notification_id=notification.id)
    return updated, sent