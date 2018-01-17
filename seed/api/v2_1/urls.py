# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2018, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.conf.urls import url, include
from rest_framework import routers

from seed.api.v2_1.views import PropertyViewSetV21
from seed.views.portfoliomanager import PortfolioManagerViewSet
from seed.views.scenarios import ScenarioViewSet
from seed.views.tax_lot_properties import TaxLotPropertyViewSet

router = routers.DefaultRouter()
router.register(r'properties', PropertyViewSetV21, base_name="properties")
router.register(r'scenarios', ScenarioViewSet, base_name="scenarios")
router.register(r'tax_lot_properties', TaxLotPropertyViewSet, base_name="tax_lot_properties")
router.register(r'portfolio_manager', PortfolioManagerViewSet, base_name="portfolio_manager")

urlpatterns = [
    url(r'^', include(router.urls)),
]
