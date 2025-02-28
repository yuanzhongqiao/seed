# !/usr/bin/env python
# encoding: utf-8
"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
import json
from datetime import datetime

import dateutil


class CeleryDatetimeSerializer(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime):
            return {
                '__type__': '__datetime__',
                'iso8601': obj.isoformat()
            }
        else:
            return json.JSONEncoder.default(self, obj)

    @staticmethod
    def seed_decoder(obj):
        if '__type__' in obj:
            if obj['__type__'] == '__datetime__':
                return dateutil.parser.parse(obj['iso8601'])
        return obj

    # Encoder function
    @staticmethod
    def seed_dumps(obj):
        return json.dumps(obj, cls=CeleryDatetimeSerializer)

    # Decoder function
    @staticmethod
    def seed_loads(obj):
        return json.loads(obj, object_hook=CeleryDatetimeSerializer.seed_decoder)
