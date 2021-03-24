#!/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2021, The Regents of the University of California,
through Lawrence Berkeley National Laboratory (subject to receipt of any
required approvals from the U.S. Department of Energy) and contributors.
All rights reserved.  # NOQA
:author: Fable Turas fable@raintechpdx.com

This provides a custom DRF ModelViewSet for rendering SEED API views with the
necessary decorator and organization queryset mixins added, inheriting from
DRF's ModelViewSet and setting SEED relevant defaults to renderer_classes,
parser_classes, authentication_classes, and pagination_classes attributes.
"""

# Imports from Django
from rest_framework.authentication import SessionAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from oauth2_provider.contrib.rest_framework import OAuth2Authentication
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
)

# Local Imports
from seed.authentication import SEEDAuthentication
from seed.decorators import DecoratorMixin
from seed.lib.superperms.orgs.permissions import SEEDOrgPermissions
from seed.renderers import SEEDJSONRenderer as JSONRenderer
from seed.utils.api import (
    OrgCreateUpdateMixin,
    OrgQuerySetMixin,
    drf_api_endpoint
)

# Constants
AUTHENTICATION_CLASSES = (
    OAuth2Authentication,
    SessionAuthentication,
    SEEDAuthentication,
)
PARSER_CLASSES = (FormParser, MultiPartParser, JSONParser)
RENDERER_CLASSES = (JSONRenderer,)
PERMISSIONS_CLASSES = (SEEDOrgPermissions,)


class UpdateWithoutPatchModelMixin(object):
    # Taken from: https://github.com/encode/django-rest-framework/pull/3081#issuecomment-518396378
    # Rebuilds the UpdateModelMixin without the patch action
    def update(self, request, *args, **kwargs):
        return UpdateModelMixin.update(self, request, *args, **kwargs)

    def perform_update(self, serializer):
        return UpdateModelMixin.perform_update(self, serializer)


class SEEDOrgModelViewSet(DecoratorMixin(drf_api_endpoint), OrgQuerySetMixin, ModelViewSet):
    """Viewset class customized with SEED standard attributes.

    Attributes:
        renderer_classes: Tuple of classes, default set to SEEDJSONRenderer.
        parser_classes: Tuple of classes, default set to drf's JSONParser.
        authentication_classes: Tuple of classes, default set to drf's
            SessionAuthentication and SEEDAuthentication.
    """
    renderer_classes = RENDERER_CLASSES
    parser_classes = PARSER_CLASSES
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSIONS_CLASSES


class SEEDOrgReadOnlyModelViewSet(DecoratorMixin(drf_api_endpoint), OrgQuerySetMixin,
                                  ReadOnlyModelViewSet):
    """Viewset class customized with SEED standard attributes.

    Attributes:
        renderer_classes: Tuple of classes, default set to SEEDJSONRenderer.
        parser_classes: Tuple of classes, default set to drf's JSONParser.
        authentication_classes: Tuple of classes, default set to drf's
            SessionAuthentication and SEEDAuthentication.
    """
    renderer_classes = RENDERER_CLASSES
    parser_classes = PARSER_CLASSES
    authentication_classes = AUTHENTICATION_CLASSES
    permission_classes = PERMISSIONS_CLASSES


class SEEDOrgCreateUpdateModelViewSet(OrgCreateUpdateMixin, SEEDOrgModelViewSet):
    """Extends SEEDModelViewset to add perform_create method to attach org.

    Provides the perform_create and update_create methods to save the
    Organization foreignkey relationship for models that have linked via an
    'organization' fieldname.

    This viewset is not suitable for models using 'super_organization' or
    having additional foreign key relationships, such as user. Any such models
    should instead extend SEEDOrgModelViewset and create perform_create
    and/or perform_update overrides appropriate to the model's needs.
    """
    pass


class SEEDOrgNoPatchOrOrgCreateModelViewSet(SEEDOrgReadOnlyModelViewSet,
                                            CreateModelMixin,
                                            DestroyModelMixin,
                                            UpdateWithoutPatchModelMixin):
    """Extends SEEDOrgReadOnlyModelViewSet to include update (without patch),
    create, and destroy actions.
    """
    pass
