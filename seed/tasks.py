# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2016, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from __future__ import absolute_import

import calendar
import datetime

from celery import chord
from celery import shared_task
from celery.utils.log import get_task_logger
from django.apps import apps
from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse_lazy
from django.template import loader
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from seed import search
from seed.audit_logs.models import AuditLog
from seed.decorators import lock_and_track
from seed.landing.models import SEEDUser as User
from seed.lib.exporter import Exporter
from seed.lib.mcm.utils import batch
from seed.lib.superperms.orgs.models import Organization, OrganizationUser
from seed.models import (
    BuildingSnapshot,
    CanonicalBuilding,
    Compliance,
    Project,
    ProjectBuilding,
    Property, PropertyState,
    TaxLot, TaxLotState
)
from seed.utils import time as time_utils
from seed.utils.buildings import get_search_query
from seed.utils.cache import set_cache, increment_cache, get_cache

logger = get_task_logger(__name__)


@shared_task
def export_buildings(export_id, export_name, export_type,
                     building_ids, export_model='seed.BuildingSnapshot',
                     selected_fields=None):
    model = apps.get_model(*export_model.split("."))

    selected_buildings = model.objects.filter(pk__in=building_ids)

    def _row_cb(i):
        data = get_cache("export_buildings__%s" % export_id)
        data['buildings_processed'] = i

        if data['total_buildings'] == 0 or not data['total_buildings']:
            data['progress'] = 100
        else:
            data['progress'] = (i * 100) / data['total_buildings']

        set_cache("export_buildings__%s" % export_id, data['status'], data)

    exporter = Exporter(export_id, export_name, export_type)
    if not exporter.valid_export_type():
        _row_cb(-1)  # this means there was an error
        return

    exporter.export(selected_buildings, selected_fields, _row_cb)
    # file return value is not used

    _row_cb(selected_buildings.count())  # means we're done!


@shared_task
def invite_to_seed(domain, email_address, token, user_pk, first_name):
    """Send invitation email to newly created user.

    domain -- The domain name of the running seed instance
    email_address -- The address to send the invitation to
    token -- generated by Django's default_token_generator
    user_pk --primary key for this user record
    first_name -- First name of the new user

    Returns: nothing
    """
    signup_url = reverse_lazy('landing:signup', kwargs={
        'uidb64': urlsafe_base64_encode(force_bytes(user_pk)),
        'token': token
    })
    context = {
        'email': email_address,
        'domain': domain,
        'protocol': 'https',
        'first_name': first_name,
        'signup_url': signup_url
    }

    subject = 'New SEED account'
    email_body = loader.render_to_string(
        'seed/account_create_email.html',
        context
    )
    reset_email = settings.SERVER_EMAIL
    send_mail(subject, email_body, reset_email, [email_address])
    try:
        bcc_address = settings.SEED_ACCOUNT_CREATION_BCC
        new_subject = "{} ({})".format(subject, email_address)
        send_mail(new_subject, email_body, reset_email, [bcc_address])
    except AttributeError:
        pass


@shared_task
def add_buildings(project_slug, project_dict, user_pk):
    """adds buildings to a project. if a user has selected all buildings,
       then the the search parameters within project_dict are used to determine
       the total set
       of buildings.
       also creates a Compliance inst. if satisfying params are present

       :param str project_slug: a project's slug used to get the project
       :param dict project_dict: contains search params, and browser state
       information
       :user_pk int or str: the user's pk or id

    """
    project = Project.objects.get(slug=project_slug)

    # Initialize the progress cache
    prog_key = project.adding_buildings_status_percentage_cache_key
    data = {
        'status': 'processing',
        'progress': 0,
        'progress_key': prog_key,
        'numerator': 0,
        'denominator': 0,
    }
    set_cache(project.adding_buildings_status_percentage_cache_key,
              data['status'], data)

    user = User.objects.get(pk=user_pk)
    project.last_modified_by = user
    project.save()

    # Perform the appropriate filtering to get the raw list of buildings.
    params = search.process_search_params(project_dict, user,
                                          is_api_request=False)
    buildings_queryset = search.orchestrate_search_filter_sort(
        params=params,
        user=user,
    )

    # Get selected buildings based on either individual selection or select-all
    # selection.
    if project_dict.get('select_all_checkbox'):
        selected_buildings = buildings_queryset
    else:
        selected_buildings = buildings_queryset.filter(
            id__in=project_dict.get('selected_buildings', []),
        )

    denominator = len(selected_buildings)

    # Loop over the buildings adding them to the project and updating the
    # progress cache.
    for idx, bs in enumerate(selected_buildings):
        data = {
            'status': 'processing',
            'progress': (float(idx) / denominator * 100),
            'progress_key': prog_key,
            'numerator': idx,
            'denominator': denominator
        }
        set_cache(prog_key, data['status'], data)
        ProjectBuilding.objects.get_or_create(
            project=project, building_snapshot=bs
        )

    # Mark the progress cache as complete.
    result = {
        'status': 'completed',
        'progress': 100,
        'progress_key': prog_key,
        'numerator': denominator,
        'denominator': denominator
    }
    set_cache(prog_key, result['status'], result)

    deadline_date = time_utils.parse_datetime(
        project_dict.get('deadline_date'))

    end_date = time_utils.parse_datetime(project_dict.get('end_date'))

    if end_date:
        last_day_of_month = calendar.monthrange(
            end_date.year, end_date.month
        )[1]
        end_date = datetime.datetime(
            end_date.year, end_date.month, last_day_of_month
        )

    if project_dict.get('compliance_type'):
        compliance = Compliance.objects.create(
            compliance_type=project_dict.get('compliance_type'),
            end_date=end_date,
            deadline_date=deadline_date,
            project=project
        )
        compliance.save()


@shared_task
def remove_buildings(project_slug, project_dict, user_pk):
    """adds buildings to a project. if a user has selected all buildings,
       then the the search parameters within project_dict are used to determine
       the total set of buildings.

       :param str project_slug: a project's slug used to get the project
       :param dict project_dict: contains search params, and browser state
           information
       :user_pk int or str: the user's pk or id
    """
    project = Project.objects.get(slug=project_slug)
    user = User.objects.get(pk=user_pk)
    project.last_modified_by = user
    project.save()

    selected_buildings = project_dict.get('selected_buildings', [])
    prog_key = project.removing_buildings_status_percentage_cache_key
    data = {
        'status': 'processing',
        'progress': 0,
        'progress_key': prog_key,
        'numerator': 0,
        'denominator': 0,
    }
    set_cache(prog_key, data['status'], data)
    i = 0
    denominator = 1
    if not project_dict.get('select_all_checkbox', False):
        for sfid in selected_buildings:
            i += 1
            denominator = len(selected_buildings)
            data = {
                'status': 'processing',
                'progress': (float(i) / max(len(selected_buildings), 1) * 100),
                'progress_key': prog_key,
                'numerator': i,
                'denominator': denominator
            }
            set_cache(prog_key, data['status'], data)
            ab = BuildingSnapshot.objects.get(pk=sfid)
            ProjectBuilding.objects.get(
                project=project, building_snapshot=ab
            ).delete()
    else:
        query_buildings = get_search_query(user, project_dict)
        denominator = query_buildings.count() - len(selected_buildings)
        data = {
            'status': 'processing',
            'progress': 10,
            'progress_key': prog_key,
            'numerator': i,
            'denominator': denominator
        }
        set_cache(prog_key, data['status'], data)
        for b in query_buildings:
            ProjectBuilding.objects.get(
                project=project, building_snapshot=b
            ).delete()
        data = {
            'status': 'processing',
            'progress': 50,
            'progress_key': prog_key,
            'numerator': denominator - len(selected_buildings),
            'denominator': denominator
        }
        set_cache(prog_key, data['status'], data)
        for building in selected_buildings:
            i += 1
            ab = BuildingSnapshot.objects.get(source_facility_id=building)
            ProjectBuilding.objects.create(
                project=project, building_snapshot=ab
            )
            data = {
                'status': 'processing',
                'progress': (float(denominator - len(
                    selected_buildings) + i) / denominator * 100),
                'progress_key': prog_key,
                'numerator': denominator - len(selected_buildings) + i,
                'denominator': denominator
            }
            set_cache(prog_key, data['status'], data)

    result = {
        'status': 'complete',
        'progress': 100,
        'progress_key': prog_key,
        'numerator': i,
        'denominator': denominator
    }
    set_cache(prog_key, result['status'], result)


@shared_task
@lock_and_track
def delete_organization(org_pk, deleting_cache_key, chunk_size=100, *args,
                        **kwargs):
    result = {
        'status': 'success',
        'progress': 0,
        'progress_key': deleting_cache_key
    }

    set_cache(deleting_cache_key, result['status'], result)

    if CanonicalBuilding.objects.filter(
            canonical_snapshot__super_organization=org_pk).exists():
        _delete_canonical_buildings.delay(org_pk)

    if BuildingSnapshot.objects.filter(super_organization=org_pk).exists():
        ids = list(
            BuildingSnapshot.objects.filter(
                super_organization=org_pk).values_list('id', flat=True)
        )

        step = float(chunk_size) / len(ids)
        tasks = []
        for del_ids in batch(ids, chunk_size):
            # we could also use .s instead of .subtask and not wrap the *args
            tasks.append(
                _delete_organization_buildings_chunk.subtask(
                    (del_ids, deleting_cache_key, step, org_pk)
                )
            )
        chord(tasks, interval=15)(_delete_organization_related_data.subtask(
            [org_pk, deleting_cache_key]))
    else:
        _delete_organization_related_data(None, org_pk, deleting_cache_key)


@shared_task
@lock_and_track
def _delete_organization_related_data(chain, org_pk, prog_key):
    # Get all org users
    user_ids = OrganizationUser.objects.filter(
        organization_id=org_pk).values_list('user_id', flat=True)
    users = list(User.objects.filter(pk__in=user_ids))

    Organization.objects.get(pk=org_pk).delete()

    # Delete any abandoned users.
    for user in users:
        if not OrganizationUser.objects.filter(user_id=user.pk).exists():
            user.delete()

    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)


@shared_task
@lock_and_track
def delete_organization_buildings(org_pk, deleting_cache_key, chunk_size=100,
                                  *args, **kwargs):
    """Deletes all BuildingSnapshot instances within an organization."""
    result = {
        'status': 'success',
        'progress_key': deleting_cache_key
    }

    if not BuildingSnapshot.objects.filter(super_organization=org_pk).exists():
        result['progress'] = 100
    else:
        result['progress'] = 0

    set_cache(deleting_cache_key, result['status'], result)

    if result['progress'] == 100:
        return

    _delete_canonical_buildings.delay(org_pk)

    ids = list(
        BuildingSnapshot.objects.filter(super_organization=org_pk).values_list(
            'id', flat=True)
    )

    step = float(chunk_size) / len(ids)
    tasks = []
    for del_ids in batch(ids, chunk_size):
        # we could also use .s instead of .subtask and not wrap the *args
        tasks.append(
            _delete_organization_buildings_chunk.subtask(
                (del_ids, deleting_cache_key, step, org_pk)
            )
        )
    chord(tasks, interval=15)(
        _finish_delete.subtask([org_pk, deleting_cache_key]))


@shared_task
def _finish_delete(results, org_pk, prog_key):
    result = {
        'status': 'success',
        'progress': 100,
        'progress_key': prog_key
    }
    set_cache(prog_key, result['status'], result)


@shared_task
def _delete_organization_buildings_chunk(del_ids, prog_key, increment,
                                         org_pk, *args, **kwargs):
    """deletes a list of ``del_ids`` and increments the cache"""
    qs = BuildingSnapshot.objects.filter(super_organization=org_pk)
    qs.filter(pk__in=del_ids).delete()
    increment_cache(prog_key, increment * 100)


@shared_task
def _delete_canonical_buildings(org_pk, chunk_size=300):
    """deletes CanonicalBuildings

    :param org_id: organization id
    :param chunk_size: number of CanonicalBuilding instances to delete per
    iteration
    """
    ids = list(CanonicalBuilding.objects.filter(
        canonical_snapshot__super_organization=org_pk
    ).values_list('id', flat=True))
    for del_ids in batch(ids, chunk_size):
        CanonicalBuilding.objects.filter(pk__in=del_ids).delete()


@shared_task
def log_deleted_buildings(ids, user_pk, chunk_size=300):
    """
    AuditLog logs a delete entry for the canonical building or each
    BuildingSnapshot in ``ids``
    """
    for del_ids in batch(ids, chunk_size):
        for b in BuildingSnapshot.objects.filter(pk__in=del_ids):
            AuditLog.objects.create(
                user_id=user_pk,
                content_object=b.canonical_building,
                organization=b.super_organization,
                action='delete_building',
                action_note='Deleted building.'
            )


@shared_task
@lock_and_track
def delete_organization_inventory(org_pk, deleting_cache_key, chunk_size=100, *args, **kwargs):
    """Deletes all properties & taxlots within an organization."""
    result = {
        'status': 'success',
        'progress_key': deleting_cache_key,
        'progress': 0
    }

    property_ids = list(
        Property.objects.filter(organization_id=org_pk).values_list('id', flat=True)
    )
    property_state_ids = list(
        PropertyState.objects.filter(organization_id=org_pk).values_list('id', flat=True)
    )
    taxlot_ids = list(
        TaxLot.objects.filter(organization_id=org_pk).values_list('id', flat=True)
    )
    taxlot_state_ids = list(
        TaxLotState.objects.filter(organization_id=org_pk).values_list('id', flat=True)
    )

    total = len(property_ids) + len(property_state_ids) + len(taxlot_ids) + len(taxlot_state_ids)

    if total == 0:
        result['progress'] = 100

    set_cache(deleting_cache_key, result['status'], result)

    if total == 0:
        return

    step = float(chunk_size) / total
    tasks = []
    for del_ids in batch(property_ids, chunk_size):
        # we could also use .s instead of .subtask and not wrap the *args
        tasks.append(
            _delete_organization_property_chunk.subtask(
                (del_ids, deleting_cache_key, step, org_pk)
            )
        )
    for del_ids in batch(property_state_ids, chunk_size):
        # we could also use .s instead of .subtask and not wrap the *args
        tasks.append(
            _delete_organization_property_state_chunk.subtask(
                (del_ids, deleting_cache_key, step, org_pk)
            )
        )
    for del_ids in batch(taxlot_ids, chunk_size):
        # we could also use .s instead of .subtask and not wrap the *args
        tasks.append(
            _delete_organization_taxlot_chunk.subtask(
                (del_ids, deleting_cache_key, step, org_pk)
            )
        )
    for del_ids in batch(taxlot_state_ids, chunk_size):
        # we could also use .s instead of .subtask and not wrap the *args
        tasks.append(
            _delete_organization_taxlot_state_chunk.subtask(
                (del_ids, deleting_cache_key, step, org_pk)
            )
        )
    chord(tasks, interval=15)(
        _finish_delete.subtask([org_pk, deleting_cache_key]))


@shared_task
def _delete_organization_property_chunk(del_ids, prog_key, increment, org_pk, *args, **kwargs):
    """deletes a list of ``del_ids`` and increments the cache"""
    qs = Property.objects.filter(organization_id=org_pk, pk__in=del_ids)
    qs.delete()
    increment_cache(prog_key, increment * 100)


@shared_task
def _delete_organization_property_state_chunk(del_ids, prog_key, increment, org_pk, *args, **kwargs):
    """deletes a list of ``del_ids`` and increments the cache"""
    qs = PropertyState.objects.filter(organization_id=org_pk, pk__in=del_ids)
    for i in range(0, 10):
        while True:
            try:
                qs.delete()
            except RuntimeError:
                # RuntimeError occurred while deleting property_states, possibly due to too many cascading deletes
                continue
            break
    increment_cache(prog_key, increment * 100)


@shared_task
def _delete_organization_taxlot_chunk(del_ids, prog_key, increment, org_pk, *args, **kwargs):
    """deletes a list of ``del_ids`` and increments the cache"""
    qs = TaxLot.objects.filter(organization_id=org_pk, pk__in=del_ids)
    qs.delete()
    increment_cache(prog_key, increment * 100)


@shared_task
def _delete_organization_taxlot_state_chunk(del_ids, prog_key, increment, org_pk, *args, **kwargs):
    """deletes a list of ``del_ids`` and increments the cache"""
    qs = TaxLotState.objects.filter(organization_id=org_pk, pk__in=del_ids)
    for i in range(0, 10):
        while True:
            try:
                qs.delete()
            except RuntimeError:
                # RuntimeError occurred while deleting taxlot_states, possibly due to too many cascading deletes
                continue
            break
    increment_cache(prog_key, increment * 100)
