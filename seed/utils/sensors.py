# !/usr/bin/env python
# encoding: utf-8

from calendar import month_name
from collections import defaultdict

from config.settings.common import TIME_ZONE
from django.db.models import Avg
from django.db.models.functions import TruncMonth, TruncYear
from pytz import timezone
from seed.models import Sensor


class PropertySensorReadingsExporter():
    """
    Returns readings and column definitions for UI-Grid. These readings can be
    returned in different intervals: exact, monthly, and yearly.

    Monthly and yearly aggregations are done here, and organization display
    settings are considered/used when returning actual reading magnitudes.
    """

    def __init__(self, property_id, org_id, excluded_sensor_ids, showOnlyOccupiedReadings):
        self._cache_factors = None
        self._cache_org_country = None

        self.sensors = Sensor.objects.select_related('data_logger').filter(data_logger__property_id=property_id).exclude(pk__in=excluded_sensor_ids)
        self.org_id = org_id
        self.showOnlyOccupiedReadings = showOnlyOccupiedReadings
        self.tz = timezone(TIME_ZONE)

    def readings_and_column_defs(self, interval):
        if interval == 'Exact':
            return self._usages_by_exact_times()
        elif interval == 'Month':
            return self._usages_by_month()
        elif interval == 'Year':
            return self._usages_by_year()

    def _usages_by_exact_times(self):
        """
        Returns readings and column definitions formatted to display all records and their
        start and end times.
        """

        # Used to consolidate different readings (types) within the same time window
        timestamps = defaultdict(lambda: {})

        # Construct column_defs using this dictionary's values for frontend to use
        column_defs = {
            '_timestamp': {
                'field': 'timestamp',
                '_filter_type': 'datetime',
            },
        }

        time_format = "%Y-%m-%d %H:%M:%S"

        for sensor in self.sensors:
            field_name = self._build_column_def(sensor, column_defs)

            sensor_readings = sensor.sensor_readings
            if self.showOnlyOccupiedReadings:
                sensor_readings = sensor_readings.filter(is_occupied=True)

            for sensor_reading in sensor_readings.all():
                timestamp = sensor_reading.timestamp.astimezone(tz=self.tz).strftime(time_format)
                times_key = str(timestamp)

                timestamps[times_key]["timestamp"] = timestamp
                timestamps[times_key][field_name] = sensor_reading.reading

        return {
            'readings': list(timestamps.values()),
            'column_defs': list(column_defs.values())
        }

    def _usages_by_month(self):
        """
        Returns readings and column definitions formatted and aggregated to display all
        records in monthly intervals.
        """
        # Used to consolidate different readings (types) within the same month
        monthly_readings = defaultdict(lambda: {})

        # Construct column_defs using this dictionary's values for frontend to use
        column_defs = {
            '_month': {
                'field': 'month',
                '_filter_type': 'datetime',
            },
        }

        for sensor in self.sensors:
            field_name = self._build_column_def(sensor, column_defs)

            sensor_readings = sensor.sensor_readings
            if self.showOnlyOccupiedReadings:
                sensor_readings = sensor_readings.filter(is_occupied=True)

            # group by month and avg readings
            readings_avg_by_month = sensor_readings \
                .annotate(month=TruncMonth('timestamp')) \
                .values('month').order_by('month') \
                .annotate(avg=Avg('reading')) \
                .values('month', 'avg')

            for reading in readings_avg_by_month:
                month_year = '{} {}'.format(month_name[reading['month'].month], reading['month'].year)

                monthly_readings[month_year]['month'] = month_year
                monthly_readings[month_year][field_name] = reading['avg']

        return {
            'readings': list(monthly_readings.values()),
            'column_defs': list(column_defs.values()),
        }

    def _usages_by_year(self):
        """
        Similarly to _usages_by_month, this returns readings and column definitions
        formatted and aggregated to display all records in yearly intervals.
        """
        # Used to consolidate different readings (types) within the same year
        yearly_readings = defaultdict(lambda: {})

        # Construct column_defs using this dictionary's values for frontend to use
        column_defs = {
            '_year': {
                'field': 'year',
                '_filter_type': 'datetime',
            },
        }

        for sensor in self.sensors:
            field_name = self._build_column_def(sensor, column_defs)

            sensor_readings = sensor.sensor_readings
            if self.showOnlyOccupiedReadings:
                sensor_readings = sensor_readings.filter(is_occupied=True)

            readings_avg_by_year = sensor_readings \
                .annotate(year=TruncYear('timestamp')) \
                .values('year').order_by('year') \
                .annotate(avg=Avg('reading')) \
                .values('year', 'avg')

            for reading in readings_avg_by_year:
                year = reading['year'].year

                yearly_readings[year]['year'] = year
                yearly_readings[year][field_name] = reading['avg']

        return {
            'readings': list(yearly_readings.values()),
            'column_defs': list(column_defs.values())
        }

    def _build_column_def(self, sensor, column_defs):
        field_name = sensor.display_name
        display_name = '{} ({})'.format(field_name, sensor.data_logger.display_name)

        column_defs[display_name] = {
            'field': display_name,
            'displayName': display_name,
            '_filter_type': 'reading',
        }

        return display_name
