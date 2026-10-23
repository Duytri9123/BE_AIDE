import tempfile
import unittest
from unittest.mock import patch
import ezdxf
from app.services.cad.reference_layout import ReferenceLayoutGenerator
from app.services.cad.automatic_selection import select_device_geometry
from app.services.cad.output_status import output_status


class ReferenceLayoutTests(unittest.TestCase):
    def test_generic_cb_resolves_geometry_without_changing_source_type(self):
        row = select_device_geometry(dict(category='CB',name='Branch',brand='LS',
            poles=2,in_a=16,icu_ka=6,quantity=1,selection_source='default_brand'),allow_unverified_electrical=True)
        self.assertTrue(row['cad'].get('asset_id'))
        self.assertEqual(row['category'],'CB')
        self.assertEqual(row['in_a'],16)
        self.assertFalse(row['cad']['exact_model'])

    def test_partial_drawing_keeps_real_geometry_and_lists_unresolved_device(self):
        known = select_device_geometry(dict(category='MCB',name='Branch',tag='L1',brand='LS',
            poles=2,in_a=16,icu_ka=6,quantity=2,selection_source='default_brand'),allow_unverified_electrical=True)
        unknown = dict(category='CB',name='Spare',tag='SPARE',quantity=1)
        with tempfile.TemporaryDirectory() as folder, patch(
            'app.services.cad.source_project_generator.SourceProjectGenerator.generate',
            side_effect=ValueError('No complete cabinet form')):
            result = ReferenceLayoutGenerator.generate(1,folder,(1000,600,300),[known,unknown])
            doc = ezdxf.readfile(result['path'])
            self.assertFalse(doc.audit().errors)
            self.assertEqual(doc.units,4)
            self.assertEqual(len(result['placements']),2)
            self.assertEqual(len(list(doc.modelspace().query('INSERT'))),2)
            self.assertEqual(result['unmatched_devices'],['SPARE'])
            self.assertTrue(any('SPARE' in e.dxf.text for e in doc.modelspace().query('TEXT')))
            self.assertFalse(result['release_ready'])
            self.assertFalse(output_status(True,None,result,devices=[known,unknown])['success'])
            a,b=result['placements']
            self.assertGreaterEqual(b['x'],a['x']+a['w'])
            for placement in result['placements']:
                self.assertGreaterEqual(placement['y'],40)
                self.assertLessEqual(placement['y']+placement['h'],960)

    def test_missing_source_dimensions_do_not_create_default_sized_cabinet(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                ReferenceLayoutGenerator.generate(1,folder,None,[])

    def test_available_device_geometry_can_propose_size_without_source_dimensions(self):
        known = select_device_geometry(dict(category='MCB',name='Branch',tag='L1',brand='LS',
            poles=2,in_a=16,icu_ka=6,quantity=1,selection_source='default_brand'),allow_unverified_electrical=True)
        with tempfile.TemporaryDirectory() as folder, patch(
            'app.services.cad.source_project_generator.SourceProjectGenerator.generate',
            side_effect=ValueError('No complete cabinet form')):
            result = ReferenceLayoutGenerator.generate(1,folder,None,[known])
            self.assertEqual(result['dimension_basis'],'proposed_from_available_device_geometry')
            self.assertIsNone(result['source_reference_dimensions'])
            self.assertTrue(all(v>0 for v in result['dimensions'].values()))
            self.assertFalse(result['release_ready'])
            self.assertFalse(ezdxf.readfile(result['path']).audit().errors)


if __name__=='__main__': unittest.main()
