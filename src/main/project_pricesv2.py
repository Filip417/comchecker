import os, sys
import pandas as pd
from prophet import Prophet
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q, F
import os, sys
import numpy as np
import pandas as pd
from prophet import Prophet
from matplotlib import pyplot as plt
from prophet.plot import add_changepoints_to_plot

# Set the Django settings module environment variable
# Add the Django project root directory to the Python path
# project_root = r'C:\\Users\\sawin\\Documents\\Commodity Project\\django_project\\comchecker'
# sys.path.append(project_root)
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comchecker.settings")
# # Initialize Django
# import django
# django.setup()
from main.models import (
    CommodityPrice,
    Commodity,
    Currency,
)

YEARS_FOR_FORECAST = 5
INFLATION = 0.03


adjustment_dict = {
    9:{
        "id":9,
        "name":"Cobalt",
        "years_history":5,
        "floor_value_multiple":0
    },
    11:{
        "id":11,
        "name":"Cotton",
        "years_history":5,
        "floor_value_multiple":1
    },
    13:{
        "id":13,
        "name":"Electronics",
        "years_history":10,
        "floor_value_multiple":1
    },
    16:{
        "id":16,
        "name":"EU Carbon Permits",
        "years_history":2,
        "floor_value_multiple":1
    },
    22:{
        "id":22,
        "name":"Iron Ore",
        "years_history":35,
        "floor_value_multiple":0
    },
    40:{
        "id":40,
        "name":"Palladium",
        "years_history":0.5,
        "floor_value_multiple":0.5
    },
    41:{
        "id":41,
        "name":"Rubber",
        "years_history":5,
        "floor_value_multiple":1
    },
    43:{
        "id":43,
        "name":"Silver",
        "years_history":10,
        "floor_value_multiple":1
    },
    44:{
        "id":44,
        "name":"Steel",
        "years_history":2,
        "floor_value_multiple":0.8
    },
    47:{
        "id":47,
        "name":"Tin",
        "years_history":10,
        "floor_value_multiple":1
    },
    48:{
        "id":48,
        "name":"Electricity UK",
        "years_history":10,
        "floor_value_multiple":0
    },
    52:{
        "id":52,
        "name":"Inflation UK",
        "years_history":25,
        "floor_value_multiple":1
    },
    54:{
        "id":54,
        "name":"Construction activity UK",
        "years_history":10,
        "floor_value_multiple":1
    },
}


def rolling_average(forecast, window=30):
    # Replace yhat, yhat_lower, and yhat_upper with their monthly moving averages
    forecast['yhat'] = forecast['yhat'].rolling(window=window).mean()
    forecast['yhat_lower'] = forecast['yhat_lower'].rolling(window=window).mean()
    forecast['yhat_upper'] = forecast['yhat_upper'].rolling(window=window).mean()

    # Fill in any NaN values that result from the rolling operation
    forecast['yhat'] = forecast['yhat'].bfill()
    forecast['yhat_lower'] = forecast['yhat_lower'].bfill()
    forecast['yhat_upper'] = forecast['yhat_upper'].bfill()

# Linear smoothing of predictions
def linear_smoothing(df_pro, forecast, months_to_smooth=12):
    days_to_smooth = months_to_smooth * 30

    # Get today's date
    today = pd.Timestamp.today()

    # Filter out rows where 'y' is NaN or 0
    df_pro_past = df_pro[df_pro['ds'] < today]
    df_pro_filtered = df_pro_past[(df_pro_past['y'].notna()) & (df_pro_past['y'] != 0)]

    if df_pro_filtered.empty:
        raise ValueError("No valid past prices found in df_pro.")

    # Compute the difference between the date and today
    df_pro_filtered = df_pro_filtered.copy()  # Create a deep copy to avoid SettingWithCopyWarning
    df_pro_filtered.loc[:, 'date_diff'] = df_pro_filtered['ds'] - today

    # Find the closest past date or today by finding the maximum negative value
    closest_past_dates = df_pro_filtered[df_pro_filtered['date_diff'] <= pd.Timedelta(0)]
    
    if closest_past_dates.empty:
        raise ValueError("No past dates found in df_pro after filtering invalid prices.")

    closest_date_idx = closest_past_dates['date_diff'].idxmax()

    # Get the closest past date and its associated price
    closest_date = df_pro_filtered.loc[closest_date_idx, 'ds']
    last_price = df_pro_filtered.loc[closest_date_idx, 'y']
    last_price_date = closest_date

    print(f'LAST PRICE: {last_price}')
    print(f'Last price date: {last_price_date}')

    # If last_price is NaN or 0, raise an error (this shouldn't happen due to earlier filtering)
    if pd.isna(last_price) or last_price == 0:
        raise ValueError(f"Invalid last price: {last_price} on date {last_price_date}")

    # Define the end date of the smoothing period
    smoothing_end_date = last_price_date + timedelta(days=days_to_smooth)
    
    # Create a mask for the smoothing period
    mask = (forecast['ds'] > last_price_date) & (forecast['ds'] <= smoothing_end_date)

    if not mask.any():
        raise ValueError("No dates found in forecast for the smoothing period.")

    # Calculate the number of days in the smoothing period
    smoothing_days_total = days_to_smooth

    # Calculate the linear interpolation for yhat, yhat_lower, and yhat_upper
    smoothing_days = (forecast.loc[mask, 'ds'] - last_price_date).dt.days

    # Ensure no division by zero occurs
    smoothing_days_total = max(smoothing_days_total, 1)

    # Replace fillna with bfill using recommended approach
    forecast['yhat'] = forecast['yhat'].bfill()
    forecast['yhat_lower'] = forecast['yhat_lower'].bfill()
    forecast['yhat_upper'] = forecast['yhat_upper'].bfill()

    # Linear interpolation
    forecast.loc[mask, 'yhat'] = last_price + (forecast.loc[mask, 'yhat'] - last_price) * (smoothing_days / smoothing_days_total)
    forecast.loc[mask, 'yhat_lower'] = last_price + (forecast.loc[mask, 'yhat_lower'] - last_price) * (smoothing_days / smoothing_days_total)
    forecast.loc[mask, 'yhat_upper'] = last_price + (forecast.loc[mask, 'yhat_upper'] - last_price) * (smoothing_days / smoothing_days_total)

    return forecast

def get_dataframe(commodity_id):
    # Load data from your database
    data = CommodityPrice.objects.filter(commodity_id=commodity_id).values(
        'date', 'price', 'futures_price', 'commodity_id', 'currency_id'
    )
    objects_with_price_or_futures_price = data.filter(
        Q(price__isnull=False) | Q(futures_price__isnull=False)
    )

    commodity = Commodity.objects.get(id=commodity_id)

    # Convert to a pandas DataFrame
    df = pd.DataFrame(objects_with_price_or_futures_price)

    # Ensure data is sorted by date
    df = df.sort_values('date')
    
    # Convert 'date' to datetime format
    df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d')

    # Convert 'futures_price' to float and handle None values by replacing them with NaN
    df['futures_price'] = pd.to_numeric(df['futures_price'], errors='coerce')

    # Filter data to include only the last 5 years
    today = pd.Timestamp.today()
    last_5_years = today - pd.DateOffset(years=5)
    
    if commodity.futures:
        # Assign futures_price to price where date > today and futures_price is not NaN
        df.loc[(df['date'] > today) & (df['futures_price'].notna()) & (df['futures_price'] != 0), 'price'] = df['futures_price']
    else:
        df = df[df['date'] <= today]

    # Convert 'date' column to the desired format '%d/%m/%Y'
    df['date'] = df['date'].dt.strftime('%d/%m/%Y')

    return df


def get_forecast_df(commodity_df, years_history=None, cap_value_multiple=1, floor_value_multiple=1):
    cumulative_rate = (1 + INFLATION) ** YEARS_FOR_FORECAST
    df_pro = commodity_df.drop(columns=['commodity_id','currency_id'])
    df_pro = df_pro.rename(columns={"price":"y","date":"ds"})
    df_pro['ds'] = pd.to_datetime(df_pro['ds'], format='%d/%m/%Y', errors='coerce')
    
    today = pd.to_datetime(datetime.now().date())
    cap_value = df_pro['y'].max() * cumulative_rate * cap_value_multiple
    floor_value = 0 * floor_value_multiple

    if years_history:
        df_pro = df_pro[df_pro['ds'] > (today - timedelta(days=years_history*365))]
    df_pro['cap'] = cap_value
    df_pro['floor'] = floor_value
    m = Prophet(growth='logistic', changepoint_prior_scale=0.001, interval_width=0.9)
    m.fit(df_pro)
    future = m.make_future_dataframe(periods=365*YEARS_FOR_FORECAST)
    future['cap'] = cap_value
    future['floor'] = floor_value
    forecast = m.predict(future)

    rolling_average(forecast, window=30)

    # Ensure yhat, yhat_upper, and yhat_lower are within cap_value and floor_value
    last_price = df_pro.iloc[-1]['y']
    floor_value = df_pro[df_pro['ds'] > (today - timedelta(days=5*365))]['y'].min() / 5
    def scale_values(row):
        # While loop to check and scale yhat, yhat_upper, yhat_lower until they are within bounds
        while (row['yhat'] > cap_value or row['yhat'] < floor_value or 
               row['yhat_upper'] > cap_value or row['yhat_lower'] < floor_value):
            if row['yhat'] > cap_value or row['yhat'] < floor_value:
                row['yhat'] = last_price + 0.9 * (row['yhat'] - last_price)
            if row['yhat_upper'] > cap_value:
                row['yhat_upper'] = last_price + 0.9 * (row['yhat_upper'] - last_price)
            if row['yhat_lower'] < floor_value:
                row['yhat_lower'] = last_price + 0.9 * (row['yhat_lower'] - last_price)
        return row
    forecast = forecast.apply(scale_values, axis=1)


    forecast = linear_smoothing(df_pro, forecast, months_to_smooth=36)
    # fig1 = m.plot(forecast)
    # a = add_changepoints_to_plot(fig1.gca(), m, forecast)
    # fig2 = m.plot_components(forecast)
    # plt.show()

    return forecast


def get_forecast_df_for_futures(commodity_df, years_history=1, cap_value_multiple=1, floor_value_multiple=1):
    today = pd.to_datetime(datetime.now().date())
    cumulative_rate = (1 + INFLATION) ** YEARS_FOR_FORECAST
    df_pro = commodity_df.drop(columns=['commodity_id','currency_id'])
    df_pro = df_pro.rename(columns={"price":"y","date":"ds"})
    df_pro['ds'] = pd.to_datetime(df_pro['ds'], format='%d/%m/%Y', errors='coerce')

    cap_value = df_pro['y'].max() * cumulative_rate * cap_value_multiple
    floor_value = df_pro[df_pro['ds'] > (today - timedelta(days=5*365))]['y'].min() * floor_value_multiple
    # Filter rows to include only those from today

    # TODO make custom historic horizon based on commodity with futures 
    df_pro = df_pro[df_pro['ds'] > (today - timedelta(days=years_history*365))]

    df_pro['cap'] = cap_value
    df_pro['floor'] = floor_value
    m = Prophet(growth='logistic', changepoint_prior_scale=0.001, interval_width=0.9)
    m.fit(df_pro)

    # TODO reduce days to forecast for efficiency - for many commodities dont need full days
    days_to_forecast = 365 * YEARS_FOR_FORECAST
    future = m.make_future_dataframe(periods=days_to_forecast, freq='D')
    future['cap'] = cap_value
    future['floor'] = floor_value
    forecast = m.predict(future)

    rolling_average(forecast, window=30)


    # Ensure yhat, yhat_upper, and yhat_lower are within cap_value and floor_value
    last_price = df_pro.iloc[-1]['y']

    def scale_values(row):
        # While loop to check and scale yhat, yhat_upper, yhat_lower until they are within bounds
        while (row['yhat'] > cap_value or row['yhat'] < floor_value or 
               row['yhat_upper'] > cap_value or row['yhat_lower'] < floor_value or
                row['yhat_upper'] < floor_value or row['yhat_lower'] > cap_value):
            if row['yhat'] > cap_value or row['yhat'] < floor_value:
                row['yhat'] = last_price + 0.9 * (row['yhat'] - last_price)
            if row['yhat_upper'] > cap_value or row['yhat_upper'] < floor_value:
                row['yhat_upper'] = last_price + 0.9 * (row['yhat_upper'] - last_price)
            if row['yhat_lower'] < floor_value or row['yhat_lower'] > cap_value:
                row['yhat_lower'] = last_price + 0.9 * (row['yhat_lower'] - last_price)
        return row
    forecast = forecast.apply(scale_values, axis=1)


    forecast = linear_smoothing(df_pro, forecast, months_to_smooth=36)
    # fig1 = m.plot(forecast)
    # a = add_changepoints_to_plot(fig1.gca(), m, forecast)
    # fig2 = m.plot_components(forecast)
    # plt.show()

    return forecast


# Assuming you have the futures_df loaded as pandas dataframe

def upload_to_db(commodity_df, futures_df, batch_size=1000):
    df_pro = commodity_df.drop(columns=['commodity_id', 'currency_id'])
    df_pro['date'] = pd.to_datetime(df_pro['date'], format='%d/%m/%Y', errors='coerce')
    df_pro.sort_values('date', inplace=True)

    futures_df['ds'] = pd.to_datetime(futures_df['ds'])
    futures_df.set_index('ds', inplace=True)

    today = timezone.now().date()
    # Get or create the commodity and currency references
    commodity = Commodity.objects.get(id=commodity_df.iloc[0]['commodity_id'])  # Example commodity
    currency = Currency.objects.get(id=commodity_df.iloc[0]['currency_id'])  # Example currency

    CommodityPrice.objects.filter(
        commodity=commodity,
        currency=currency
    ).update(
        projected_price=None,
        top_90_percent=None,
        bottom_90_percent=None,
        top_75_percent=None,
        bottom_75_percent=None,
        top_50_percent=None,
        bottom_50_percent=None,
        top_25_percent=None,
        bottom_25_percent=None,
        top_10_percent=None,
        bottom_10_percent=None
    )

    # Clean empty CommodityPrice
    CommodityPrice.objects.filter(
        commodity=commodity,
        currency=currency,
        price__isnull=True,
        futures_price__isnull=True
    ).delete()

    # Function to scale the confidence intervals linearly
    def scale_confidence_interval(yhat, yhat_lower, yhat_upper, date):
        years_5_future_date = today + timedelta(days=5 * 365)
        # Calculate the scale factor
        days_until_date = (date.date() - today).days
        days_until_5_years = (years_5_future_date - today).days
        scale_factor = days_until_date / days_until_5_years
        # if dont want to use scale_factor:
        scale_factor = 1

        return {
            "top_90_percent": yhat + scale_factor * (yhat_upper - yhat),
            "bottom_90_percent": yhat + scale_factor * (yhat_lower - yhat),
            "top_75_percent": yhat + scale_factor * (yhat_upper - yhat) * 0.75 / 0.9,
            "bottom_75_percent": yhat + scale_factor * (yhat_lower - yhat) * 0.75 / 0.9,
            "top_50_percent": yhat + scale_factor * (yhat_upper - yhat) * 0.50 / 0.9,
            "bottom_50_percent": yhat + scale_factor * (yhat_lower - yhat) * 0.50 / 0.9,
            "top_25_percent": yhat + scale_factor * (yhat_upper - yhat) * 0.25 / 0.9,
            "bottom_25_percent": yhat + scale_factor * (yhat_lower - yhat) * 0.25 / 0.9,
            "top_10_percent": yhat + scale_factor * (yhat_upper - yhat) * 0.10 / 0.9,
            "bottom_10_percent": yhat + scale_factor * (yhat_lower - yhat) * 0.10 / 0.9,
        }

    # Loop through the futures_df and insert/update records in CommodityPrice
    for date, row in futures_df.iterrows():
        # Insert the price into the .price field for dates starting from tomorrow
        if date.date() >= today + timedelta(days=1) and date.date() <= today + timedelta(days=5*365+15):
            # Calculate scaled confidence intervals
            scaled_intervals = scale_confidence_interval(
                yhat=row['yhat'],
                yhat_lower=row['yhat_lower'],
                yhat_upper=row['yhat_upper'],
                date=date
            )
            # Use update_or_create to update existing records or create new ones
            obj, created = CommodityPrice.objects.update_or_create(
                commodity=commodity,
                currency=currency,
                date=date.date(),
                defaults={
                    'price':None,
                    'projected_price': row['yhat'],
                    'top_90_percent': scaled_intervals['top_90_percent'],
                    'bottom_90_percent': scaled_intervals['bottom_90_percent'],
                    'top_75_percent': scaled_intervals['top_75_percent'],
                    'bottom_75_percent': scaled_intervals['bottom_75_percent'],
                    'top_50_percent': scaled_intervals['top_50_percent'],
                    'bottom_50_percent': scaled_intervals['bottom_50_percent'],
                    'top_25_percent': scaled_intervals['top_25_percent'],
                    'bottom_25_percent': scaled_intervals['bottom_25_percent'],
                    'top_10_percent': scaled_intervals['top_10_percent'],
                    'bottom_10_percent': scaled_intervals['bottom_10_percent'],
                }
            )
            # Do not modify futures_price if it exists
            if not created and obj.futures_price is not None:
                CommodityPrice.objects.filter(pk=obj.pk).update(futures_price=F('futures_price'))

    # Optionally, log that the upload is complete
    print("Upload to DB completed.")



def update_forecast_prices():
    list_to_update = range(1,55)
    for _ in list_to_update:
        print(f'Commodity id started: {_}')
        commodity_df = get_dataframe(_)
        commodity = Commodity.objects.get(id=_)
        if commodity.futures:
            if commodity.id in adjustment_dict.keys():
                futures_df = get_forecast_df_for_futures(commodity_df,
                            years_history=adjustment_dict[commodity.id]['years_history'],
                            floor_value_multiple=adjustment_dict[commodity.id]['floor_value_multiple'])
            else:
                futures_df = get_forecast_df_for_futures(commodity_df)
        else:
            if commodity.id in adjustment_dict.keys():
                # TODO fix error
                futures_df = get_forecast_df(commodity_df,
                            years_history=adjustment_dict[commodity.id]['years_history'],
                            floor_value_multiple=adjustment_dict[commodity.id]['floor_value_multiple'])
            else:
                futures_df = get_forecast_df(commodity_df)
        upload_to_db(commodity_df, futures_df)
        print(f'Forecast {commodity.name} uploaded to db')

# update_forecast_prices()

# TEMPORARY FOR EXTRA TEST

# TO_CHECK = 48
# commodity_df = get_dataframe(TO_CHECK)
# commodity = Commodity.objects.get(id=TO_CHECK)
# if commodity.futures:
#     if commodity.id in adjustment_dict.keys():
#         futures_df = get_forecast_df_for_futures(commodity_df,
#                     years_history=adjustment_dict[commodity.id]['years_history'],
#                     floor_value_multiple=adjustment_dict[commodity.id]['floor_value_multiple'])
#     else:
#         futures_df = get_forecast_df_for_futures(commodity_df)
# else:
#     if commodity.id in adjustment_dict.keys():
#         futures_df = get_forecast_df(commodity_df,
#                     years_history=adjustment_dict[commodity.id]['years_history'],
#                     floor_value_multiple=adjustment_dict[commodity.id]['floor_value_multiple'])
#     else:
#         futures_df = get_forecast_df(commodity_df)

# upload_to_db(commodity_df, futures_df)

