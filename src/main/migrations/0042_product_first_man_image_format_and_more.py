# Generated by Django 5.0.6 on 2024-10-08 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0041_alter_commodityprice_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='first_man_image_format',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
        migrations.AddField(
            model_name='product',
            name='first_prod_image_format',
            field=models.CharField(blank=True, max_length=5, null=True),
        ),
    ]
