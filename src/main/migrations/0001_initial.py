# Generated by Django 5.0.6 on 2024-09-08 11:16

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Commodity',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('futures', models.BooleanField(default=False)),
                ('category', models.CharField(blank=True, max_length=100, null=True)),
                ('price_update_date', models.DateField(blank=True, null=True)),
                ('price_now', models.FloatField(blank=True, null=True)),
                ('price_for_kg', models.FloatField(blank=True, null=True)),
                ('rate_for_price_kg', models.FloatField(blank=True, null=True)),
                ('unit', models.CharField(blank=True, max_length=50, null=True)),
                ('price_source', models.CharField(max_length=100)),
                ('count_of_products_with', models.IntegerField(blank=True, null=True)),
                ('price_history_source', models.CharField(max_length=100)),
                ('price_history_name', models.CharField(max_length=100)),
                ('price_history_type', models.CharField(max_length=20)),
                ('production_date', models.DateField(blank=True, null=True)),
                ('production_unit', models.CharField(blank=True, max_length=100, null=True)),
                ('production_source', models.CharField(blank=True, max_length=100, null=True)),
                ('production_name', models.CharField(blank=True, max_length=100, null=True)),
                ('production_total', models.IntegerField(blank=True, null=True)),
                ('basic_description', models.TextField()),
                ('use', models.TextField(blank=True, null=True)),
                ('world_total', models.TextField(blank=True, null=True)),
                ('events_trends_issues', models.TextField(blank=True, null=True)),
                ('substitutes', models.TextField(blank=True, null=True)),
                ('recycling', models.TextField(blank=True, null=True)),
                ('increasefromlastyear', models.FloatField(blank=True, null=True)),
                ('view_count', models.IntegerField(default=0)),
            ],
        ),
        migrations.CreateModel(
            name='Currency',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=3, unique=True)),
                ('name', models.CharField(max_length=50)),
                ('symbol', models.CharField(blank=True, max_length=10, null=True)),
                ('date', models.DateField()),
                ('rate', models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='CommodityProduction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('country_code', models.CharField(max_length=3)),
                ('country_name', models.CharField(max_length=100)),
                ('production', models.FloatField()),
                ('unit', models.CharField(max_length=50)),
                ('date', models.DateField()),
                ('commodity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.commodity')),
            ],
        ),
        migrations.CreateModel(
            name='CommodityPrice',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('price', models.FloatField(blank=True, null=True)),
                ('projected_price', models.FloatField(blank=True, null=True)),
                ('futures_price', models.FloatField(blank=True, null=True)),
                ('top_90_percent', models.FloatField(blank=True, null=True)),
                ('bottom_90_percent', models.FloatField(blank=True, null=True)),
                ('top_75_percent', models.FloatField(blank=True, null=True)),
                ('bottom_75_percent', models.FloatField(blank=True, null=True)),
                ('top_50_percent', models.FloatField(blank=True, null=True)),
                ('bottom_50_percent', models.FloatField(blank=True, null=True)),
                ('top_25_percent', models.FloatField(blank=True, null=True)),
                ('bottom_25_percent', models.FloatField(blank=True, null=True)),
                ('top_10_percent', models.FloatField(blank=True, null=True)),
                ('bottom_10_percent', models.FloatField(blank=True, null=True)),
                ('commodity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.commodity')),
                ('currency', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.currency')),
            ],
        ),
        migrations.AddField(
            model_name='commodity',
            name='currency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.currency'),
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('epd_id', models.IntegerField(null=True)),
                ('slug', models.SlugField(null=True, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('original_name', models.CharField(blank=True, max_length=255, null=True)),
                ('product_img_url', models.URLField(blank=True, null=True)),
                ('description', models.TextField(null=True)),
                ('pcr', models.CharField(blank=True, max_length=100, null=True)),
                ('pcr_category', models.CharField(blank=True, max_length=255, null=True)),
                ('category_1', models.CharField(blank=True, max_length=255, null=True)),
                ('category_2', models.CharField(blank=True, max_length=255, null=True)),
                ('category_3', models.CharField(blank=True, max_length=255, null=True)),
                ('reg_date', models.DateField(null=True)),
                ('version_date', models.DateField(blank=True, null=True)),
                ('geographical_scopes', models.CharField(blank=True, max_length=255, null=True)),
                ('manufacturer_name', models.CharField(max_length=255)),
                ('manufacturer_country', models.CharField(max_length=255)),
                ('manufacturer_website', models.URLField(blank=True, null=True)),
                ('included_products_in_this_epd', models.TextField(blank=True, null=True)),
                ('manufacturer_img_url', models.URLField(blank=True, null=True)),
                ('increasefromlastyear', models.FloatField(blank=True, null=True)),
                ('unique_commodities_count', models.IntegerField(blank=True, null=True)),
                ('view_count', models.IntegerField(default=0)),
                ('top_value_commodity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='main.commodity')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='MaterialProportion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('material_proportion_other_id', models.IntegerField(null=True)),
                ('material', models.CharField(max_length=255)),
                ('proportion', models.FloatField()),
                ('unit', models.CharField(default='%', max_length=52)),
                ('commodity', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='material_proportions', to='main.commodity')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='material_proportions', to='main.product')),
            ],
        ),
        migrations.CreateModel(
            name='View',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('viewed_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('commodity', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.commodity')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='main.product')),
            ],
        ),
    ]
