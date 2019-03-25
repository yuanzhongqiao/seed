# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2019, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
import datetime
import logging
import os.path as osp

from django.contrib.gis.geos import Polygon
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from seed.data_importer import tasks
from seed.data_importer.models import ImportFile, ImportRecord
from seed.data_importer.tests.util import (
    FAKE_EXTRA_DATA,
    FAKE_MAPPINGS,
    FAKE_ROW,
    TAXLOT_FOOTPRINT_MAPPING,
    PROPERTY_FOOTPRINT_MAPPING,
)
from seed.landing.models import SEEDUser as User
from seed.models import (
    Column,
    TaxLotState,
    DATA_STATE_IMPORT,
    DATA_STATE_MAPPING,
    ASSESSED_RAW,
)
from seed.models import (
    Cycle,
    PropertyState,
)
from seed.tests.util import DataMappingBaseTestCase
from seed.utils.organizations import create_organization

logger = logging.getLogger(__name__)


class TestDemoV2(DataMappingBaseTestCase):
    def set_up(self, import_file_source_type):
        """Override the base in DataMappingBaseTestCase."""

        # default_values
        import_file_data_state = getattr(self, 'import_file_data_state', DATA_STATE_IMPORT)

        user = User.objects.create(username='test')
        org, _, _ = create_organization(user, "test-organization-a")

        cycle, _ = Cycle.objects.get_or_create(
            name='Test Hack Cycle 2015',
            organization=org,
            start=datetime.datetime(2015, 1, 1, tzinfo=timezone.get_current_timezone()),
            end=datetime.datetime(2015, 12, 31, tzinfo=timezone.get_current_timezone()),
        )

        import_record_1 = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file_1 = ImportFile.objects.create(import_record=import_record_1,
                                                  cycle=cycle)

        import_record_2 = ImportRecord.objects.create(
            owner=user, last_modified_by=user, super_organization=org
        )
        import_file_2 = ImportFile.objects.create(import_record=import_record_2,
                                                  cycle=cycle)

        import_file_1.source_type = import_file_source_type
        import_file_1.data_state = import_file_data_state
        import_file_1.save()

        import_file_2.source_type = import_file_source_type
        import_file_2.data_state = import_file_data_state
        import_file_2.save()

        return user, org, import_file_1, import_record_1, import_file_2, import_record_2, cycle

    def setUp(self):
        property_filename = getattr(self, 'filename', 'example-data-properties-2-invalid-footprints.xlsx')
        tax_lot_filename = getattr(self, 'filename', 'example-data-taxlots-2-invalid-footprints.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_portfolio_mappings = FAKE_MAPPINGS['portfolio'] + [PROPERTY_FOOTPRINT_MAPPING]
        self.fake_taxlot_mappings = FAKE_MAPPINGS['taxlot'] + [TAXLOT_FOOTPRINT_MAPPING]
        self.fake_extra_data = FAKE_EXTRA_DATA
        self.fake_row = FAKE_ROW
        selfvars = self.set_up(import_file_source_type)

        (self.user,
         self.org,
         self.import_file_property,
         self.import_record_property,
         self.import_file_tax_lot,
         self.import_record_tax_lot,
         self.cycle) = selfvars

        filepath = osp.join(osp.dirname(__file__), '..', 'data', tax_lot_filename)
        self.import_file_tax_lot.file = SimpleUploadedFile(
            name=tax_lot_filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file_tax_lot.save()

        filepath = osp.join(osp.dirname(__file__), '..', 'data', property_filename)
        self.import_file_property.file = SimpleUploadedFile(
            name=property_filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file_property.save()

    def test_demo_v2(self):
        tasks.save_raw_data(self.import_file_tax_lot.pk)
        Column.create_mappings(self.fake_taxlot_mappings, self.org, self.user, self.import_file_tax_lot.id)
        Column.create_mappings(self.fake_portfolio_mappings, self.org, self.user, self.import_file_property.id)
        tasks.map_data(self.import_file_tax_lot.pk)

        # Check to make sure the taxlots were imported
        ts = TaxLotState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_tax_lot,
        )

        self.assertEqual(len(ts), 3)

        # Check taxlot_footprints
        tax_lot_1 = TaxLotState.objects.get(address_line_1='050 Willow Ave SE')
        self.assertTrue(isinstance(tax_lot_1.taxlot_footprint, Polygon))
        self.assertEqual(tax_lot_1.extra_data.get('Tax Lot Coordinates (Invalid Footprint)'), None)

        # For invalid footprints,
        # check that extra_data field added with ' (Invalid Footprint)' appended to original column title
        tax_lot_2 = TaxLotState.objects.get(address_line_1='2655 Welstone Ave NE')
        invalid_footprint_string = '(( -121.927490629756 37.3966545740305, -121.927428469962 37.3965654556064 ))'
        self.assertEqual(tax_lot_2.taxlot_footprint, None)
        self.assertEqual(tax_lot_2.extra_data['Tax Lot Coordinates (Invalid Footprint)'], invalid_footprint_string)

        tax_lot_3 = TaxLotState.objects.get(address_line_1='94000 Wellington Blvd')
        self.assertEqual(tax_lot_3.taxlot_footprint, None)
        self.assertEqual(tax_lot_3.extra_data['Tax Lot Coordinates (Invalid Footprint)'], '')

        # Import the property data
        tasks.save_raw_data(self.import_file_property.pk)
        tasks.map_data(self.import_file_property.pk)

        ps = PropertyState.objects.filter(
            data_state=DATA_STATE_MAPPING,
            organization=self.org,
            import_file=self.import_file_property,
        )

        self.assertEqual(len(ps), 3)

        # Check taxlot_footprints
        property_1 = PropertyState.objects.get(address_line_1='50 Willow Ave SE')
        self.assertTrue(isinstance(property_1.property_footprint, Polygon))
        self.assertEqual(property_1.extra_data.get('Property Coordinates (Invalid Footprint)'), None)

        # For invalid footprints,
        # check that extra_data field added with ' (Invalid Footprint)' appended to original column title
        property_2 = PropertyState.objects.get(address_line_1='2700 Welstone Ave NE')
        invalid_footprint_string = '(( -121.927490629756 37.3966545740305, -121.927428469962 37.3965654556064 ))'
        self.assertEqual(property_2.property_footprint, None)
        self.assertEqual(property_2.extra_data['Property Coordinates (Invalid Footprint)'], invalid_footprint_string)

        property_3 = PropertyState.objects.get(address_line_1='11 Ninth Street')
        self.assertEqual(property_3.property_footprint, None)
        self.assertEqual(property_3.extra_data['Property Coordinates (Invalid Footprint)'], 123)
