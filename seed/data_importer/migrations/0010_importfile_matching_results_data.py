# -*- coding: utf-8 -*-
# Generated by Django 1.11.6 on 2018-07-13 15:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('data_importer', '0009_importfile_uploaded_filename'),
    ]

    operations = [
        migrations.AddField(
            model_name='importfile',
            name='matching_results_data',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
