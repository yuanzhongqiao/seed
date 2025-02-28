# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-09-20 21:06
from __future__ import unicode_literals

from django.db import migrations, models, transaction
from django.utils import timezone


def forwards(apps, schema_editor):
    Column = apps.get_model("seed", "Column")

    with transaction.atomic():
        original_identity_fields = [
            'address_line_1',  # Technically this was normalized_address, but matching logic handles this as such
            'custom_id_1',
            'pm_property_id',
            'jurisdiction_tax_lot_id',
            'ubid',
            'ulid'
        ]
        Column.objects.filter(column_name__in=original_identity_fields).update(is_matching_criteria=True)


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0109_auto_20190724_1251'),
    ]

    operations = [
        migrations.AddField(
            model_name='propertystate',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='propertystate',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='taxlotstate',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='taxlotstate',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='column',
            name='is_matching_criteria',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(forwards),
    ]
