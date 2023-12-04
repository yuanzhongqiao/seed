# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import datetime

from django.urls import reverse
from django.utils import timezone
from xlrd import open_workbook

from seed.models import (
    ASSESSED_RAW,
    Column,
    Property,
    PropertyState,
    PropertyView
)
from seed.test_helpers.fake import FakeCycleFactory
from seed.tests.util import DataMappingBaseTestCase


class ExportReport(DataMappingBaseTestCase):
    def setUp(self):
        selfvars = self.set_up(ASSESSED_RAW)
        # cycle_1 starts 2015
        self.user, self.org, _import_file, _import_record, self.cycle = selfvars

        user_details = {
            'username': 'test_user@demo.com',
            'password': 'test_pass',
            'email': 'test_user@demo.com'
        }
        self.client.login(**user_details)
        self.cycle_factory = FakeCycleFactory(organization=self.org, user=self.user)
        start = datetime.datetime(2016, 1, 1, tzinfo=timezone.get_current_timezone())
        self.cycle_2 = self.cycle_factory.get_cycle(name="Cycle 2", start=start)

        # create 5 records with site_eui and gross_floor_area in each cycle
        for i in range(1, 6):
            ps_a = PropertyState.objects.create(
                organization_id=self.org.id,
                site_eui=i,
                gross_floor_area=i * 100
            )
            property_a = Property.objects.create(organization_id=self.org.id)
            PropertyView.objects.create(
                state_id=ps_a.id,
                property_id=property_a.id,
                cycle_id=self.cycle.id
            )

            ps_b = PropertyState.objects.create(
                organization_id=self.org.id,
                site_eui=i,
                gross_floor_area=i * 100
            )
            property_b = Property.objects.create(organization_id=self.org.id)
            PropertyView.objects.create(
                state_id=ps_b.id,
                property_id=property_b.id,
                cycle_id=self.cycle_2.id
            )

    def test_report_export_excel_workbook(self):
        url = reverse('api:v3:organizations-report-export', args=[self.org.pk])

        # needs to be turned into post?
        response = self.client.get(url, data={
            'cycle_ids': [self.cycle.id, self.cycle_2.id],
            'x_var': 'site_eui',
            'x_label': 'Site EUI',
            'y_var': 'gross_floor_area',
            'y_label': 'Gross Floor Area',
        })

        self.assertEqual(200, response.status_code)

        wb = open_workbook(file_contents=response.content)

        # Spot check each sheet
        counts_sheet = wb.sheet_by_index(0)
        self.assertEqual('Counts', counts_sheet.name)

        # check count of properties with data
        self.assertEqual('Properties with Data', counts_sheet.cell(0, 1).value)
        self.assertEqual(5, counts_sheet.cell(1, 1).value)
        self.assertEqual(5, counts_sheet.cell(2, 1).value)

        raw_sheet = wb.sheet_by_index(1)
        self.assertEqual('Raw', raw_sheet.name)

        # check Site EUI values
        matching_columns = Column.objects.filter(organization_id=self.org.id, is_matching_criteria=True, table_name="PropertyState")
        for i, matching_column in enumerate(matching_columns):
            self.assertEqual(matching_column.display_name, raw_sheet.cell(0, i).value)

        self.assertEqual('Site EUI', raw_sheet.cell(0, len(matching_columns)).value)
        self.assertEqual(1, raw_sheet.cell(1, len(matching_columns)).value)
        self.assertEqual(2, raw_sheet.cell(2, len(matching_columns)).value)

        agg_sheet = wb.sheet_by_index(2)
        self.assertEqual('Agg', agg_sheet.name)

        # check Gross Floor Area values
        self.assertEqual('Gross Floor Area', agg_sheet.cell(0, 1).value)
        self.assertEqual('0-99k', agg_sheet.cell(1, 1).value)
        self.assertEqual('0-99k', agg_sheet.cell(2, 1).value)

    def test_report(self):
        url = reverse('api:v3:organizations-report', args=[self.org.pk])
        data = {
            'cycle_ids': [self.cycle.id, self.cycle_2.id],
            'x_var': 'site_eui',
            'y_var': 'gross_floor_area',
        }
        response = self.client.get(url, data)

        assert response.json()["data"]["property_counts"] == [
            {'yr_e': '2016', 'num_properties': 5, 'num_properties_w-data': 5},
            {'yr_e': '2015', 'num_properties': 5, 'num_properties_w-data': 5}
        ]

        data["cycle_ids"] = [self.cycle.id]
        response = self.client.get(url, data)

        assert response.json()["data"]["property_counts"] == [
            {'yr_e': '2015', 'num_properties': 5, 'num_properties_w-data': 5}
        ]

    def test_report_aggregated(self):
        url = reverse('api:v3:organizations-report-aggregated', args=[self.org.pk])
        data = {
            'cycle_ids': [self.cycle.id, self.cycle_2.id],
            'x_var': 'site_eui',
            'y_var': 'gross_floor_area',
        }
        response = self.client.get(url, data)

        assert response.json()["aggregated_data"]["property_counts"] == [
            {'yr_e': '2016', 'num_properties': 5, 'num_properties_w-data': 5},
            {'yr_e': '2015', 'num_properties': 5, 'num_properties_w-data': 5}
        ]

        data["cycle_ids"] = [self.cycle.id]
        response = self.client.get(url, data)

        assert response.json()["aggregated_data"]["property_counts"] == [
            {'yr_e': '2015', 'num_properties': 5, 'num_properties_w-data': 5}
        ]

    def test_report_missing_arg(self):
        url = reverse('api:v3:organizations-report-aggregated', args=[self.org.pk])
        data = {
            'cycle_ids': [self.cycle.id, self.cycle_2.id],
            'x_var': 'site_eui',
            # 'y_var': 'gross_floor_area', it's missing!
        }
        response = self.client.get(url, data)

        assert response.status_code == 400
