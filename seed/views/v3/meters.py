# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.parsers import FormParser, JSONParser
from rest_framework.renderers import JSONRenderer

from seed.models import Meter, PropertyView
from seed.serializers.meters import MeterSerializer
from seed.utils.api_schema import AutoSchemaHelper
from seed.utils.viewsets import SEEDOrgNoPatchOrOrgCreateModelViewSet


@method_decorator(
    name='create',
    decorator=swagger_auto_schema(
        manual_parameters=[
            AutoSchemaHelper.base_field(
                name='property_pk',
                location_attr='IN_PATH',
                type='TYPE_INTEGER',
                required=True,
                description='ID of the property view where the meter is associated.'),
        ],
        request_body=AutoSchemaHelper.schema_factory(
            {
                'type': Meter.ENERGY_TYPES,
                'alias': 'string',
                'source': Meter.SOURCES,
                'source_id': 'string',
                'scenario_id': 'integer',
                'is_virtual': 'boolean'
            },
            required=['type', 'source'],
            description='New meter to add. The type must be taken from a constrained list.'
        )
    ),
)
class MeterViewSet(SEEDOrgNoPatchOrOrgCreateModelViewSet):
    """API endpoint for managing meters."""

    serializer_class = MeterSerializer
    renderer_classes = (JSONRenderer,)
    pagination_class = None
    model = Meter
    parser_classes = (JSONParser, FormParser)
    orgfilter = 'property__organization'

    def get_queryset(self):
        # get all the meters for the organization
        org_id = self.get_organization(self.request)
        # get the property id - since the meter is associated with the property (not the property view)

        # even though it is named 'property_pk' it is really the property view id
        property_view_pk = self.kwargs.get('property_pk', None)
        if not property_view_pk:
            # Return None otherwise swagger will not be able to process the request
            return Meter.objects.none()

        property_view = PropertyView.objects.get(pk=property_view_pk)
        self.property_pk = property_view.property.pk
        return Meter.objects.filter(property__organization_id=org_id, property_id=self.property_pk)

    def perform_create(self, serializer):
        """On create, make sure to add in the property id which comes from the URL kwargs."""

        # check permissions?
        if self.property_pk:
            serializer.save(property_id=self.property_pk)
        else:
            raise Exception('No property_pk (property view id) provided in URL to create the meter')
