# Generated by Django 5.0.6 on 2024-09-22 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('main', '0016_alter_subscription_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscription',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='subscription',
            name='permissions',
            field=models.ManyToManyField(limit_choices_to={'codename__in': ['lite', 'standard', 'unlimited'], 'content_type__app_label': 'main'}, to='auth.permission'),
        ),
    ]
