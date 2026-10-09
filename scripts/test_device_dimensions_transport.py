"""Sizing must retain catalog envelopes through the extraction schema."""
import unittest
from app.schemas.ai import ExtractedDeviceSchema
from app.services.cad.physical_layout_engine import PhysicalLayoutEngine


class DimensionTransportTest(unittest.TestCase):
    def test_catalog_dimensions_survive_schema_round_trip(self):
        device = ExtractedDeviceSchema.model_validate({
            'category': 'MCB', 'name': 'MCB 2P', 'spec': '16A',
            'dimensions': {'w': 36, 'h': 85, 'd': 70},
            'cad': {'asset_id': 'selected-library-view'},
        }).model_dump()
        self.assertEqual(PhysicalLayoutEngine.get_component_dimensions(device), (36, 85, 70))
        self.assertEqual(device['cad']['asset_id'], 'selected-library-view')

    def test_absent_dimensions_remain_absent(self):
        device = ExtractedDeviceSchema(category='OTHER', name='unknown', spec='unknown')
        self.assertIsNone(device.dimensions)


if __name__ == '__main__':
    unittest.main()
