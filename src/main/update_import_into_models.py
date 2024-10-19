import os
import sys
import pandas as pd
from django.core.exceptions import ObjectDoesNotExist
from django.utils.text import slugify
import ast

# Set the Django settings module environment variable
# Add the Django project root directory to the Python path
project_root = r'C:\\Coding projects\\Commodity Project\\django_project\\comchecker\\src'
sys.path.append(project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comchecker.settings")

# Initialize Django
import django
django.setup()


from main.models import (
    Product, 
    MaterialProportion, 
    Commodity, 
    CommodityProduction, 
    Currency, 
    CommodityPrice
)

# Load the Excel file
excel_file_path = r'C:\Coding projects\Commodity Project\django_project\comchecker\src\static\db_v1_demo\db_v_1_0.xlsx'
excel_file_path = r'C:\Coding projects\Commodity Project\django_project\comchecker\src\main\new_products_to_add.xlsx'
xls = pd.ExcelFile(excel_file_path)

# Try to load the Excel file and catch exceptions if any
try:
    xls = pd.ExcelFile(excel_file_path)
    print(f"Successfully loaded Excel file: {excel_file_path}")
except FileNotFoundError:
    print(f"Error: File not found at {excel_file_path}")
    sys.exit(1)
except Exception as e:
    print(f"Error loading Excel file: {e}")
    sys.exit(1)

def populate_products():
    print("Starting to populate Product model...")
    df = xls.parse('Product')

    for index, row in df.iterrows():
        reg_date = pd.to_datetime(row['reg_date'], errors='coerce')
        version_date = pd.to_datetime(row['version_date'], errors='coerce')

        # Replace ast.literal_eval with a manual parser if preferred
        product_img_url = ast.literal_eval(row['product_img_url']) if pd.notna(row['product_img_url']) else []

        # Use get_or_create to avoid duplicates
        product, created = Product.objects.get_or_create(
            epd_id=row['epd_id'],
            defaults={
                'name': row['name'],
                'original_name' : row['original_name'],
                'product_img_url': product_img_url,
                'description': row['description'],
                'pcr': row['pcr'],
                'pcr_category': row['pcr_category'],
                'category_1': row['category_1'],
                'category_2': row['category_2'],
                'category_3': row['category_3'],
                'reg_date': reg_date.date() if pd.notna(reg_date) else None,
                'version_date': version_date.date() if pd.notna(version_date) else None,
                'geographical_scopes': row['geographical_scopes'],
                'manufacturer_name': row['manufacturer_name'],
                'manufacturer_country': row['manufacturer_country'],
                'manufacturer_website': row['manufacturer_website'],
                'included_products_in_this_epd': row['included_products_in_this_epd'],
                'manufacturer_img_url': row['manufacturer_img_url']
            }
        )
        if created:
            print(f"Created {product.name}")
        else:
            product.name = row['name']
            product.original_name = row['original_name']
            product.product_img_url = product_img_url
            product.description = row['description']
            product.pcr = row['pcr']
            product.pcr_category = row['pcr_category']
            product.category_1 = row['category_1']
            product.category_2 = row['category_2']
            product.category_3 = row['category_3']
            product.reg_date = reg_date.date() if pd.notna(reg_date) else None
            product.version_date = version_date.date() if pd.notna(version_date) else None
            product.geographical_scopes = row['geographical_scopes']
            product.manufacturer_name = row['manufacturer_name']
            product.manufacturer_country = row['manufacturer_country']
            product.manufacturer_website = row['manufacturer_website']
            product.included_products_in_this_epd = row['included_products_in_this_epd']
            product.manufacturer_img_url = row['manufacturer_img_url']

            product.save()
            print(f"Updated {product.name}")


def populate_currencies():
    df = xls.parse('Currency')
    for index, row in df.iterrows():
        currency, created = Currency.objects.get_or_create(
            code=row['code'],
            defaults={
                'name': row['name'],
                'symbol': row['symbol'],
                'date': pd.to_datetime(row['date'], errors='coerce'),
                'rate': row['rate']
            }
        )
        print(f"{'Created' if created else 'Updated'} Currency: {currency.code}")

def populate_commodities():
    df = xls.parse('Commodity')

    for index, row in df.iterrows():  
        if pd.isna(row['name']):
            break

        # Convert dates from string/other formats to datetime
        price_update_date = pd.to_datetime(row['price_update_date'], errors='coerce')
        production_date = pd.to_datetime(row['production_date'], errors='coerce')

        # Get the currency object
        currency = Currency.objects.get(code=row['currency'])

        # Create or get the commodity
        commodity, created = Commodity.objects.get_or_create(
            name=row['name'],
            defaults={
                'futures': row['futures'],
                'category': row['category'],
                'price_update_date': price_update_date.date() if pd.notna(price_update_date) else None,
                'price_for_kg': row['price_for_kg'],
                'rate_for_price_kg': row['rate_for_price_kg'],
                'currency': currency,
                'unit': row['unit'],
                'price_source': row['price_source'],
                'count_of_products_with': row['count_of_products_with'],
                'price_history_source': row['price_history_source'],
                'price_history_name': row['price_history_name'],
                'price_history_type': row['price_history_type'],
                'production_date': production_date.date() if pd.notna(production_date) else None,
                'production_unit': row['production_unit'],
                'production_source': row['production_source'],
                'production_name': row['production_name'],
                'basic_description': row['basic_description'],
                'use': row['use'],
                'world_total': row['world_total'],
                'events_trends_issues': row['events_trends_issues'],
                'substitutes': row['substitutes'],
                'recycling': row['recycling']
            }
        )

        # If the commodity already exists, update the necessary fields
        if not created:
            commodity.futures = row['futures']
            commodity.category = row['category']
            commodity.price_update_date = price_update_date.date() if pd.notna(price_update_date) else None
            commodity.price_for_kg = row['price_for_kg']
            commodity.rate_for_price_kg = row['rate_for_price_kg']
            commodity.currency = currency
            commodity.unit = row['unit']
            commodity.price_source = row['price_source']
            commodity.count_of_products_with = row['count_of_products_with']
            commodity.price_history_source = row['price_history_source']
            commodity.price_history_name = row['price_history_name']
            commodity.price_history_type = row['price_history_type']
            commodity.production_date = production_date.date() if pd.notna(production_date) else None
            commodity.production_unit = row['production_unit']
            commodity.production_source = row['production_source']
            commodity.production_name = row['production_name']
            commodity.basic_description = row['basic_description']
            commodity.use = row['use']
            commodity.world_total = row['world_total']
            commodity.events_trends_issues = row['events_trends_issues']
            commodity.substitutes = row['substitutes']
            commodity.recycling = row['recycling']
            
            # Save the updates
            commodity.save()

        print(f"{'Created' if created else 'Updated'} Commodity: {commodity.name}")



def populate_commodity_production():
    df = xls.parse('CommodityProduction')
    errors = []
    for index, row in df.iterrows():
        try:
            commodity = Commodity.objects.get(id=row['commodity_id'])
            production, created = CommodityProduction.objects.get_or_create(
                commodity=commodity,
                country_code=row['country_code'],
                defaults={
                    'country_name': row['country_name'],
                    'production': row['production'],
                    'unit': row['unit'],
                    'date': pd.to_datetime(row['date'], errors='coerce')
                }
            )
            print(f"{'Created' if created else 'Updated'} CommodityProduction: {production}")
        except ObjectDoesNotExist as e:
            errors.append(f'Error: {e} {row['country_name']} {row['production']} {row['unit']}')
            print(f"Error: {e}")
    print(f'Errors are: {errors}')

def populate_material_proportions():
    df = xls.parse('MaterialProportion')
    errors = []
    for index, row in df.iterrows():
        try:
            product = Product.objects.get(epd_id=row['product_epd_id'])
            commodity = Commodity.objects.get(name=row['commodity'])
            material_proportion, created = MaterialProportion.objects.get_or_create(
                product=product,
                commodity=commodity,
                material_proportion_other_id=row['material_proportion_other_id'],
                material=row['material'],
                defaults={
                'proportion':row['proportion'],
                'unit':row['unit']
                }
            )
            if not created:
                material_proportion.product = product
                material_proportion.commodity = commodity
                material_proportion.material_proportion_other_id = row['material_proportion_other_id']
                material_proportion.material = row['material']
                material_proportion.proportion = row['proportion']
                material_proportion.unit = row['unit']
            print(f"{'Created' if created else 'Updated'} Material Proportion: {material_proportion} EPD_ID: {material_proportion.product.epd_id}")
        except ObjectDoesNotExist as e:
            errors.append(f'Error: {e} {row['product_epd_id']} {row['commodity']} {row['material']} {row['proportion']}')
            print(f"Error: {e}")
    print(f'Errors are: {errors}')



def populate_commodity_prices():
    df = xls.parse('CommodityPrice')
    errors = []
    for index, row in df.iterrows():
        try:
            commodity = Commodity.objects.get(id=row['commodity_id'])
            currency = Currency.objects.get(id=row['currency_id'])
            price, created = CommodityPrice.objects.get_or_create(
                commodity=commodity,
                currency=currency,
                date=pd.to_datetime(row['date'], errors='coerce'),
                defaults={
                    'price': row['price'],
                }
            )
            # If the commodity already exists, update the necessary fields
            if not created:
                price.date = pd.to_datetime(row['date'], errors='coerce')
                price.commodity = commodity
                price.currency = currency
                price.price = row['price']

                price.save()
            print(f"{'Created' if created else 'Updated'} CommodityPrice: {price}")
        except ObjectDoesNotExist as e:
            errors.append(f'Error: {e} {row['date']} {row['price']} {row['unit']} {currency.code}')
            print(f"Error: {e}")
    print(f'Errors are: {errors}')


def main():
    # populate_currencies()
    # populate_commodities()
    # populate_products()
    # populate_material_proportions()
    # populate_commodity_production()
    # populate_commodity_prices()
    pass