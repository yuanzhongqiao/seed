# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-12-20 00:06
from __future__ import unicode_literals

from django.db import migrations, transaction

from seed.lib.superperms.orgs.models import OrganizationUser
from seed.models import User


def deactivate_users_without_orgs(apps, schema_editor):
    with transaction.atomic():
        users_with_roles = OrganizationUser.objects.order_by().values_list('user_id', flat=True).distinct()
        for user in User.objects.all():
            if user.id not in users_with_roles:
                user.is_active = False
                user.save()


class Migration(migrations.Migration):
    dependencies = [
        ('seed', '0115_rehash_postal_code'),
    ]

    operations = [
        migrations.RunPython(deactivate_users_without_orgs)
    ]
