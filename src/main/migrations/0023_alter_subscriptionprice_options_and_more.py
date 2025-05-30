# Generated by Django 5.0.6 on 2024-09-23 20:08

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0022_subscriptionprice_timestamp_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='subscriptionprice',
            options={'ordering': ['order', 'featured', '-updated']},
        ),
        migrations.AddField(
            model_name='subscription',
            name='featured',
            field=models.BooleanField(default=True, help_text='Featured on Django pricing page'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='order',
            field=models.IntegerField(default=-1, help_text='Ordering on Django pricing page'),
        ),
        migrations.AddField(
            model_name='subscription',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='subscription',
            name='updated',
            field=models.DateField(auto_now=True),
        ),
    ]
