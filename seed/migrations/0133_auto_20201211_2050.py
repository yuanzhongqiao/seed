# Generated by Django 2.2.13 on 2020-12-11 20:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('seed', '0132_auto_20201211_1949'),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysis',
            name='status',
            field=models.IntegerField(choices=[(8, 'Pending Creation'), (10, 'Creating'), (20, 'Ready'), (30, 'Queued'), (40, 'Running'), (50, 'Failed'), (60, 'Stopped'), (70, 'Completed')]),
        ),
    ]
