# Generated by Django 3.2.13 on 2022-07-11 19:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orgs', '0021_auto_20220622_2125'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='at_api_token',
        ),
        migrations.AddField(
            model_name='organization',
            name='audit_template_password',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='organization',
            name='audit_template_user',
            field=models.EmailField(blank=True, default='', max_length=128),
        ),
    ]
