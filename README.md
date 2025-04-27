# Material Wise: Construction Products Commodity Price Tracker

A comprehensive web application for tracking, analyzing, and forecasting construction material prices based on raw commodity inputs and market trends.

## Project Overview

Material Wise provides a sophisticated platform for construction professionals, suppliers, and buyers to access detailed price information and forecasts for construction materials. The application shows how raw material costs influence finished product prices, helping users make informed decisions about material procurement and project budgeting.

[materialwise.co.uk](https://materialwise.co.uk/) - working if hosting is active

-   **Comprehensive Material Database**: Access detailed information on a wide range of construction materials including precast concrete, steel products, copper wire, valves, and more.
    
-   **Price Tracking System**: View historical price data for construction materials, with records tracking back several years.
    
-   **Price Forecasting**: Access predictive pricing models showing potential future price trends for materials at intervals of 6 months, 1 year, 2 years, and 5 years.
    
-   **Weighted Price Calculation**: Our proprietary algorithm calculates material prices based on weighted contributions of raw material inputs, offering a transparent view of cost composition.
    
-   **Material Specification Details**: Each product includes comprehensive specifications, manufacturing country, compliance with standards (e.g., EN15804), and declaration dates.
    
-   **Sustainability Information**: Track the environmental impact of materials to support sustainable construction projects.
    
-   **User-Friendly Interface**: Intuitive design for easy navigation and quick access to critical price information.
    

## Technologies Used

-   Frontend: JavaScript, Tailwind CSS
    
-   Backend: Django (Python web framework)
    
-   Database: PostgreSQL
    
-   Hosting: AWS, Railway
    
## Additional Libraries & Tools

**Backend & Data Processing**

-   **Django**: Core backend framework for rapid web development.
    
-   **psycopg**: PostgreSQL database adapter for Python.
    
-   **dj-database-url**: Simplifies database configuration from URLs.
    
-   **gunicorn**: WSGI HTTP server for running Django in production.
    
-   **django-allauth / django-allauth-ui**: User authentication and registration.
    
-   **django-widget-tweaks, slippers**: Enhancements for Django forms and templating.
    
-   **django-storages, boto3**: Integration with AWS S3 for static/media file storage.
    
-   **apscheduler, django_apscheduler**: Scheduled background jobs (e.g., periodic data updates).
    
-   **stripe**: Payment processing integration.
    
-   **python-decouple**: Environment variable management.
    
-   **freecurrencyapi**: Real-time currency conversion for international pricing.
    

**Data Science & Forecasting**

-   **pandas, numpy**: Data manipulation and analysis.
    
-   **prophet**: Advanced time series forecasting for price predictions.
    
-   **matplotlib**: Data visualization and charting.
    
-   **xlwt**: Exporting data to Excel files.
    

**Web Scraping & Automation**

-   **beautifulsoup4**: HTML/XML parsing for data extraction.
    
-   **selenium**: Browser automation for dynamic web scraping.
    
-   **requests**: HTTP requests for API and web data access.
    

**Frontend & Visualization**

-   **Tailwind CSS**: Utility-first CSS framework for rapid UI development.
    
-   **Chart.js, Google Charts**: Interactive data visualization in the browser.
    
-   **Moment.js, chartjs-adapter-moment, chartjs-plugin-annotation**: Date/time parsing and advanced chart annotations.
    

**DevOps & Environment**

-   **Docker**: Containerization for consistent deployment.
    
-   **python:3.12-slim-bullseye**: Base image for lightweight Python environments.
    
-   **libpq-dev, libjpeg-dev, libcairo2, gcc**: System dependencies for database, image, and SVG processing.
    

This technology stack enables robust data collection, advanced forecasting, secure user management, and rich, interactive data visualization for construction commodity prices.

## Usage
    
### Searching for Materials and Commodities

1.  Use the search bar to find specific materials and commodities
    
2.  Filter by category, manufacturer country, or other specifications
    
3.  View detailed material information, including price histories, forecasts, regional raw materials manufacturing and other relevant materials


### Creating custom product

1.  From scratch or based on existing product
    
2.  Add commodity and indexes weights
    
3.  View detailed material information, including price histories, forecasts, regional raw materials manufacturing and other relevant materials

### Creating custom projects

1.  Categorise products, commodities and indexes in custom projects with weight adjustment.
    
2.  View detailed material information, including price histories, forecasts, regional raw materials manufacturing and other relevant products, commodities and projects.
    

### Analyzing Price Trends

1.  Navigate to a specific material, commodity or project page
    
2.  View the historical price chart
    
3.  Check the forecast section for future price predictions
    
4.  Analyze the weighted commodity components that influence the price and use calculator for easy calculation of current or future cost

    

## Data Sources

Commodity price data is sourced from reputable providers including:

-   London Metal Exchange
    
-   Intercontinental Exchange, Inc. US
    
-   The Office for National Statistics
    
-   U.S. Bureau of Labor Statistics
    
-   U.S. Geological Survey
    
-   World Bank
    
-   Eurostat
    

## API Documentation

Material Wise does not offer any API for developers to integrate our price data into their own applications.


## Future Development
    
-   Integration with building information modeling (BIM) software
    
-   Advanced analytics and reporting features
    
-   Market alerts and notifications for more frequent price changes

-   Advanced sustainability insights based on EPD - Environmental Product Declaration    

## License

This project is licensed under the [MIT License](https://choosealicense.com/licenses/mit/).

## Contact

Website: [materialwise.co.uk](https://materialwise.co.uk/)
Email: [sawinskif@gmail.com](mailto:sawinskif@gmail.com)
GitHub: [Filip417](https://github.com/Filip417)

© 2025 Material Wise. All rights reserved.
