# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2022, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from django.core.files.uploadedfile import SimpleUploadedFile

import logging

import os.path as osp

from quantityfield.units import ureg

from seed.data_importer import tasks
from seed.data_importer.tests.util import (
    FAKE_MAPPINGS,
)
from seed.lib.mcm import mapper
from seed.models import (
    ASSESSED_RAW,
    DATA_STATE_IMPORT,
    Column,
)
from seed.models.column_mappings import get_column_mapping
from seed.test_helpers.fake import (
    FakePropertyFactory,
    FakePropertyStateFactory,
    FakePropertyViewFactory,
)
from seed.tests.util import DataMappingBaseTestCase

logger = logging.getLogger(__name__)


class TestMapping(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars

        self.property_factory = FakePropertyFactory(organization=self.org)
        self.property_state_factory = FakePropertyStateFactory(organization=self.org)
        self.property_view_factory = FakePropertyViewFactory(organization=self.org)

    def test_mapping(self):
        """Test objects in database can be converted to mapped fields"""
        # for mapping, you have to create an import file, even it is just one record. This is
        # more of an ID to track imports

        state = self.property_state_factory.get_property_state_as_extra_data(
            import_file_id=self.import_file.id,
            source_type=ASSESSED_RAW,
            data_state=DATA_STATE_IMPORT,
            random_extra=42
        )
        # set import_file save done to true
        self.import_file.raw_save_done = True
        self.import_file.save()

        # Create mappings from the new states
        # TODO #239: Convert this to a single helper method to suggest and save
        suggested_mappings = mapper.build_column_mapping(
            list(state.extra_data.keys()),
            Column.retrieve_all_by_tuple(self.org),
            previous_mapping=get_column_mapping,
            map_args=[self.org],
            thresh=80
        )

        # Convert mapping suggests to the format needed for saving
        mappings = []
        for raw_column, suggestion in suggested_mappings.items():
            # Single suggestion looks like:'lot_number': ['PropertyState', 'lot_number', 100]
            mapping = {
                "from_field": raw_column,
                "from_units": None,
                "to_table_name": suggestion[0],
                "to_field": suggestion[1],
                "to_field_display_name": suggestion[1],
            }
            mappings.append(mapping)

        # Now save the mappings
        # print(mappings)
        Column.create_mappings(mappings, self.org, self.user, self.import_file.id)
        # END TODO

        tasks.map_data(self.import_file.id)

        props = self.import_file.find_unmatched_property_states()
        self.assertEqual(len(props), 1)
        self.assertEqual(state.extra_data['year_built'], props.first().year_built)
        self.assertEqual(state.extra_data['random_extra'], props.first().extra_data['random_extra'])

        # from seed.utils.generic import pp
        # for p in props:
        #     pp(p)

    def test_remapping_with_and_without_unit_aware_columns_doesnt_lose_data(self):
        """
        During import, when the initial -State objects are created from the extra_data values,
        ColumnMapping objects are used to take the extra_data dictionary values and create the
        -State objects, setting the DB-level values as necessary - e.g. taking a raw
        "Site EUI (kBtu/ft2)" value and inserting it into the DB field "site_eui".

        Previously, remapping could cause extra Column objects to be created, and subsequently,
        this created extra ColumnMapping objects. These extra ColumnMapping objects could cause
        raw values to be inserted into the wrong DB field on -State creation.
        """
        # Just as in the previous test, build extra_data PropertyState
        state = self.property_state_factory.get_property_state_as_extra_data(
            import_file_id=self.import_file.id,
            source_type=ASSESSED_RAW,
            data_state=DATA_STATE_IMPORT,
            random_extra=42,
        )

        # Replace the site_eui key-value that gets autogenerated by get_property_state_as_extra_data
        del state.extra_data['site_eui']
        state.extra_data['Site EUI (kBtu/ft2)'] = 123
        state.save()

        self.import_file.raw_save_done = True
        self.import_file.save()

        # Build 2 sets of mappings - with and without a unit-aware destination site_eui data
        suggested_mappings = mapper.build_column_mapping(
            list(state.extra_data.keys()),
            Column.retrieve_all_by_tuple(self.org),
            previous_mapping=get_column_mapping,
            map_args=[self.org],
            thresh=80
        )

        ed_site_eui_mappings = []
        unit_aware_site_eui_mappings = []
        for raw_column, suggestion in suggested_mappings.items():
            if raw_column == 'Site EUI (kBtu/ft2)':
                # Make this an extra_data field (without from_units)
                ed_site_eui_mappings.append({
                    "from_field": raw_column,
                    "from_units": None,
                    "to_table_name": 'PropertyState',
                    "to_field": raw_column,
                    "to_field_display_name": raw_column,
                })

                unit_aware_site_eui_mappings.append({
                    "from_field": raw_column,
                    "from_units": 'kBtu/ft**2/year',
                    "to_table_name": 'PropertyState',
                    "to_field": 'site_eui',
                    "to_field_display_name": 'Site EUI',
                })
            else:
                other_mapping = {
                    "from_field": raw_column,
                    "from_units": None,
                    "to_table_name": suggestion[0],
                    "to_field": suggestion[1],
                    "to_field_display_name": suggestion[1],
                }
                ed_site_eui_mappings.append(other_mapping)
                unit_aware_site_eui_mappings.append(other_mapping)

        # Map and remap the file multiple times with different mappings each time.
        # Round 1 - Map site_eui data into Extra Data
        Column.create_mappings(ed_site_eui_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.id)

        # There should only be one raw 'Site EUI (kBtu/ft2)' Column object
        self.assertEqual(1, self.org.column_set.filter(column_name='Site EUI (kBtu/ft2)', table_name='').count())
        # The one propertystate should have site eui info in extra_data
        prop = self.import_file.find_unmatched_property_states().get()
        self.assertIsNone(prop.site_eui)
        self.assertIsNotNone(prop.extra_data.get('Site EUI (kBtu/ft2)'))

        # Round 2 - Map site_eui data into the PropertyState attribute "site_eui"
        Column.create_mappings(unit_aware_site_eui_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.id, remap=True)

        self.assertEqual(1, self.org.column_set.filter(column_name='Site EUI (kBtu/ft2)', table_name='').count())
        # The one propertystate should have site eui info in site_eui
        prop = self.import_file.find_unmatched_property_states().get()
        self.assertIsNotNone(prop.site_eui)
        self.assertIsNone(prop.extra_data.get('Site EUI (kBtu/ft2)'))

        # Round 3 - Map site_eui data into Extra Data
        Column.create_mappings(ed_site_eui_mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.id, remap=True)

        self.assertEqual(1, self.org.column_set.filter(column_name='Site EUI (kBtu/ft2)', table_name='').count())
        # The one propertystate should have site eui info in extra_data
        prop = self.import_file.find_unmatched_property_states().get()
        self.assertIsNone(prop.site_eui)
        self.assertIsNotNone(prop.extra_data.get('Site EUI (kBtu/ft2)'))

    def test_mapping_takes_into_account_selected_units(self):
        # Just as in the previous test, build extra_data PropertyState
        raw_state = self.property_state_factory.get_property_state_as_extra_data(
            import_file_id=self.import_file.id,
            source_type=ASSESSED_RAW,
            data_state=DATA_STATE_IMPORT,
        )

        # Replace the site_eui and gross_floor_area key-value that gets
        # autogenerated by get_property_state_as_extra_data
        del raw_state.extra_data['site_eui']
        raw_state.extra_data['Site EUI'] = 100

        del raw_state.extra_data['gross_floor_area']
        raw_state.extra_data['Gross Floor Area'] = 100
        raw_state.save()

        self.import_file.raw_save_done = True
        self.import_file.save()

        # Build mappings - with unit-aware destinations and non-default unit choices
        suggested_mappings = mapper.build_column_mapping(
            list(raw_state.extra_data.keys()),
            Column.retrieve_all_by_tuple(self.org),
            previous_mapping=get_column_mapping,
            map_args=[self.org],
            thresh=80
        )

        mappings = []
        for raw_column, suggestion in suggested_mappings.items():
            if raw_column == 'Site EUI':
                mappings.append({
                    "from_field": raw_column,
                    "from_units": 'kWh/m**2/year',
                    "to_table_name": 'PropertyState',
                    "to_field": 'site_eui',
                    "to_field_display_name": 'Site EUI',
                })
            elif raw_column == 'Gross Floor Area':
                mappings.append({
                    "from_field": raw_column,
                    "from_units": 'm**2',
                    "to_table_name": 'PropertyState',
                    "to_field": 'gross_floor_area',
                    "to_field_display_name": 'Gross Floor Area',
                })
            else:
                other_mapping = {
                    "from_field": raw_column,
                    "from_units": None,
                    "to_table_name": suggestion[0],
                    "to_field": suggestion[1],
                    "to_field_display_name": suggestion[1],
                }
                mappings.append(other_mapping)

        # Perform mapping, creating the initial PropertyState records.
        Column.create_mappings(mappings, self.org, self.user, self.import_file.id)
        tasks.map_data(self.import_file.id)

        # Verify that the values have been converted appropriately
        state = self.import_file.find_unmatched_property_states().get()

        self.assertAlmostEqual(state.site_eui, (100 * ureg('kWh/m**2/year')).to('kBtu/ft**2/year'))
        self.assertAlmostEqual(state.gross_floor_area, (100 * ureg('m**2')).to('ft**2'))


class TestDuplicateFileHeaders(DataMappingBaseTestCase):
    def setUp(self):
        filename = getattr(self, 'filename', 'example-data-properties-duplicate-headers.xlsx')
        import_file_source_type = ASSESSED_RAW
        self.fake_mappings = FAKE_MAPPINGS['portfolio']
        selfvars = self.set_up(import_file_source_type)
        self.user, self.org, self.import_file, self.import_record, self.cycle = selfvars
        filepath = osp.join(osp.dirname(__file__), 'data', filename)
        self.import_file.file = SimpleUploadedFile(
            name=filename,
            content=open(filepath, 'rb').read()
        )
        self.import_file.save()

    def test_duplicate_headers_throws_400(self):
        tasks.save_raw_data(self.import_file.pk)
        Column.create_mappings(self.fake_mappings, self.org, self.user, self.import_file.pk)

        with self.assertRaises(Exception):
            tasks.map_data(self.import_file.pk)
