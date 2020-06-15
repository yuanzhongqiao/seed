# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2020, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""

import csv

from celery.utils.log import get_task_logger
from django.http import JsonResponse, HttpResponse
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets, serializers, status
from rest_framework.decorators import action
from unidecode import unidecode

from seed.data_importer.tasks import do_checks
from seed.decorators import ajax_request_class
from seed.lib.superperms.orgs.decorators import has_perm_class
from seed.lib.superperms.orgs.models import (
    Organization,
)
from seed.models.data_quality import (
    Rule,
    DataQualityCheck,
)
from seed.utils.api import api_endpoint_class
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.cache import get_cache_raw

logger = get_task_logger(__name__)


# TODO: Consider moving these serializers into seed/serializers (and maybe actually use them...)
class RulesSubSerializer(serializers.Serializer):
    field = serializers.CharField(max_length=100)
    severity = serializers.CharField(max_length=100)


class RulesSubSerializerB(serializers.Serializer):
    field = serializers.CharField(max_length=100)
    enabled = serializers.BooleanField()
    data_type = serializers.CharField(max_length=100)
    min = serializers.FloatField()
    max = serializers.FloatField()
    severity = serializers.CharField(max_length=100)
    units = serializers.CharField(max_length=100)


class RulesIntermediateSerializer(serializers.Serializer):
    missing_matching_field = RulesSubSerializer(many=True)
    missing_values = RulesSubSerializer(many=True)
    in_range_checking = RulesSubSerializerB(many=True)


class RulesSerializer(serializers.Serializer):
    data_quality_rules = RulesIntermediateSerializer()


class RulePayloadSerializer(serializers.ModelSerializer):
    # currently our requests put this in a different field
    label = serializers.IntegerField(source='status_label')

    class Meta:
        model = Rule
        exclude = ['id', 'status_label']


class DataQualityRulesSerializer(serializers.Serializer):
    properties = serializers.ListField(child=RulePayloadSerializer())
    taxlots = serializers.ListField(child=RulePayloadSerializer())


class SaveDataQualityRulesPayloadSerializer(serializers.Serializer):
    data_quality_rules = DataQualityRulesSerializer()


class DataQualityRulesResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    rules = DataQualityRulesSerializer()


def _get_js_rule_type(data_type):
    """return the JS friendly data type name for the data data_quality rule

    :param data_type: data data_quality rule data type as defined in data_quality.models
    :returns: (string) JS data type name
    """
    return dict(Rule.DATA_TYPES).get(data_type)


def _get_js_rule_severity(severity):
    """return the JS friendly severity name for the data data_quality rule

    :param severity: data data_quality rule severity as defined in data_quality.models
    :returns: (string) JS severity name
    """
    return dict(Rule.SEVERITY).get(severity)


def _get_rule_type_from_js(data_type):
    """return the Rules TYPE from the JS friendly data type

    :param data_type: 'string', 'number', 'date', or 'year'
    :returns: int data type as defined in data_quality.models
    """
    d = {v: k for k, v in dict(Rule.DATA_TYPES).items()}
    return d.get(data_type)


def _get_severity_from_js(severity):
    """return the Rules SEVERITY from the JS friendly severity

    :param severity: 'error', or 'warning'
    :returns: int severity as defined in data_quality.models
    """
    d = {v: k for k, v in dict(Rule.SEVERITY).items()}
    return d.get(severity)


class DataQualityViews(viewsets.ViewSet):
    """
    Handles Data Quality API operations within Inventory backend.
    (1) Post, wait, get…
    (2) Respond with what changed
    """

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.path_id_field(description="Organization ID - Used to identify the only data quality check for an organization."),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'property_state_ids': ['integer'],
                'taxlot_state_ids': ['integer'],
            },
            description='An object containing IDs of the records to perform'
                        ' data quality checks on. Should contain two keys- '
                        'property_state_ids and taxlot_state_ids, each of '
                        'which is an array of appropriate IDs.',
        ),
        responses={
            200: AutoSchemaHelper.schema_factory({
                'num_properties': 'integer',
                'num_taxlots': 'integer',
                'progress_key': 'string',
                'progress': {},
            })
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=True, methods=['POST'])
    def start(self, request, pk):
        """
        This API endpoint will create a new data_quality check process in the background,
        on potentially a subset of properties/taxlots, and return back a query key
        """
        body = request.data
        property_state_ids = body['property_state_ids']
        taxlot_state_ids = body['taxlot_state_ids']

        # pk, the organization_id, is the only key currently used to identify DataQualityChecks
        return_value = do_checks(pk, property_state_ids, taxlot_state_ids)

        return JsonResponse({
            'num_properties': len(property_state_ids),
            'num_taxlots': len(taxlot_state_ids),
            # TODO #239: Deprecate progress_key from here and just use the 'progess.progress_key'
            'progress_key': return_value['progress_key'],
            'progress': return_value,
        })

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_integer_field("run_id", True, "Import file ID or cache key"),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['GET'])
    def results_csv(self, request):
        """
        Download a CSV of the results from a data quality run based on either the ID that was
        given during the creation of the data quality task or the ID of the
        import file which had it's records checked.
        Note that it is not related to objects in the database, since the results
        are stored in redis!
        """
        run_id = request.query_params.get('run_id')
        if run_id is None:
            return JsonResponse({
                'status': 'error',
                'message': 'must include Import file ID or cache key as run_id'
            }, status=status.HTTP_400_BAD_REQUEST)

        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(run_id))
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="Data Quality Check Results.csv"'

        writer = csv.writer(response)
        if data_quality_results is None:
            writer.writerow(['Error'])
            writer.writerow(['data quality results not found'])
            return response

        writer.writerow(
            ['Table', 'Address Line 1', 'PM Property ID', 'Tax Lot ID', 'Custom ID', 'Field',
             'Applied Label', 'Condition', 'Error Message', 'Severity'])

        for row in data_quality_results:
            for result in row['data_quality_results']:
                writer.writerow([
                    row['data_quality_results'][0]['table_name'],
                    row['address_line_1'],
                    row['pm_property_id'] if 'pm_property_id' in row else None,
                    row['jurisdiction_tax_lot_id'] if 'jurisdiction_tax_lot_id' in row else None,
                    row['custom_id_1'],
                    result['formatted_field'],
                    result.get('label', None),
                    result['condition'],
                    # the detailed_message field can have units which has superscripts/subscripts, so unidecode it!
                    unidecode(result['detailed_message']),
                    result['severity']
                ])

        return response

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        responses={
            200: DataQualityRulesResponseSerializer
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['PUT'])
    def reset_default_data_quality_rules(self, request):
        """
        Resets an organization's data data_quality rules
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        dq = DataQualityCheck.retrieve(organization.id)
        dq.reset_default_rules()
        return self.data_quality_rules(request)

    @swagger_auto_schema(
        manual_parameters=[AutoSchemaHelper.query_org_id_field()],
        request_body=SaveDataQualityRulesPayloadSerializer,
        responses={
            200: DataQualityRulesResponseSerializer
        }
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_parent_org_owner')
    @action(detail=False, methods=['POST'])
    def save_data_quality_rules(self, request, pk=None):
        """
        Saves an organization's settings: name, query threshold, shared fields.
        The method passes in all the fields again, so it is okay to remove
        all the rules in the db, and just recreate them (albeit inefficient)
        """
        organization = Organization.objects.get(pk=request.query_params['organization_id'])

        body = request.data
        if body.get('data_quality_rules') is None:
            return JsonResponse({
                'status': 'error',
                'message': 'missing the data_quality_rules'
            }, status=status.HTTP_404_NOT_FOUND)

        posted_rules = body['data_quality_rules']
        updated_rules = []
        valid_rules = True
        validation_messages = set()
        for rule in posted_rules['properties']:
            if _get_severity_from_js(rule['severity']) == Rule.SEVERITY_VALID and rule['label'] is None:
                valid_rules = False
                validation_messages.add('Label must be assigned when using Valid Data Severity.')
            if rule['condition'] == Rule.RULE_INCLUDE or rule['condition'] == Rule.RULE_EXCLUDE:
                if rule['text_match'] is None or rule['text_match'] == '':
                    valid_rules = False
                    validation_messages.add('Rule must not include or exclude an empty string.')
            updated_rules.append(
                {
                    'field': rule['field'],
                    'table_name': 'PropertyState',
                    'enabled': rule['enabled'],
                    'condition': rule['condition'],
                    'data_type': _get_rule_type_from_js(rule['data_type']),
                    'rule_type': rule['rule_type'],
                    'required': rule['required'],
                    'not_null': rule['not_null'],
                    'min': rule['min'],
                    'max': rule['max'],
                    'text_match': rule['text_match'],
                    'severity': _get_severity_from_js(rule['severity']),
                    'units': rule['units'],
                    'status_label_id': rule['label']
                }
            )

        for rule in posted_rules['taxlots']:
            if _get_severity_from_js(rule['severity']) == Rule.SEVERITY_VALID and rule['label'] is None:
                valid_rules = False
                validation_messages.add('Label must be assigned when using Valid Data Severity.')
            if rule['condition'] == Rule.RULE_INCLUDE or rule['condition'] == Rule.RULE_EXCLUDE:
                if rule['text_match'] is None or rule['text_match'] == '':
                    valid_rules = False
                    validation_messages.add('Rule must not include or exclude an empty string.')
            updated_rules.append(
                {
                    'field': rule['field'],
                    'table_name': 'TaxLotState',
                    'enabled': rule['enabled'],
                    'condition': rule['condition'],
                    'data_type': _get_rule_type_from_js(rule['data_type']),
                    'rule_type': rule['rule_type'],
                    'required': rule['required'],
                    'not_null': rule['not_null'],
                    'min': rule['min'],
                    'max': rule['max'],
                    'text_match': rule['text_match'],
                    'severity': _get_severity_from_js(rule['severity']),
                    'units': rule['units'],
                    'status_label_id': rule['label']
                }
            )

        if valid_rules is False:
            return JsonResponse({
                'status': 'error',
                'message': '\n'.join(validation_messages),
            }, status=status.HTTP_400_BAD_REQUEST)

        # This pattern of deleting and recreating Rules is slated to be deprecated
        bad_rule_creation = False
        error_messages = set()
        dq = DataQualityCheck.retrieve(organization.id)
        dq.remove_all_rules()
        for rule in updated_rules:
            with transaction.atomic():
                try:
                    dq.add_rule(rule)
                except Exception as e:
                    error_messages.add('Rule could not be recreated: ' + str(e))
                    bad_rule_creation = True
                    continue

        if bad_rule_creation:
            return JsonResponse({
                'status': 'error',
                'message': '\n'.join(error_messages),
            }, status=status.HTTP_400_BAD_REQUEST)
        else:
            return self.data_quality_rules(request)

    @swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.query_integer_field("run_id", True, "Import file ID or cache key"),
        ]
    )
    @api_endpoint_class
    @ajax_request_class
    @has_perm_class('requires_member')
    @action(detail=False, methods=['GET'])
    def results(self, request):
        """
        Return the results of a data quality run based on either the ID that was
        given during the creation of the data quality task or the ID of the
        import file which had it's records checked.
        Note that it is not related to objects in the database, since the results
        are stored in redis!
        """
        data_quality_id = request.query_params['run_id']
        data_quality_results = get_cache_raw(DataQualityCheck.cache_key(data_quality_id))
        return JsonResponse({
            'data': data_quality_results
        })
