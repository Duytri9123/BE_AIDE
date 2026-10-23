import unittest
from unittest.mock import patch
from app.services.cad.automatic_selection import select_device_geometry


class UnavailableSelectedCadTests(unittest.TestCase):
    def test_stale_geometry_is_unresolved_without_changing_electrical_choice(self):
        row={'tag':'Q1','category':'MCB','part_number':'chosen-model','poles':2,'in_a':20,
             'dimensions':{'w':40,'h':80,'d':60},
             'cad':{'asset_id':'tb:retired','geometry_dimensions_mm':[40,80,60]}}
        with patch('app.services.cad.automatic_selection.resolve', side_effect=ValueError('missing')), \
             patch('app.services.cad.automatic_selection.candidates') as candidates:
            result=select_device_geometry(row)
        self.assertEqual(result['part_number'],'chosen-model')
        self.assertEqual(result['in_a'],20)
        self.assertNotIn('asset_id',result['cad'])
        self.assertNotIn('dimensions',result)
        self.assertEqual(result['cad']['unavailable_asset_id'],'tb:retired')
        self.assertEqual(result['cad']['automatic_selection']['reason'],'selected_asset_unavailable')
        self.assertIn('asset_id',row['cad'])
        candidates.assert_not_called()


if __name__=='__main__': unittest.main()
