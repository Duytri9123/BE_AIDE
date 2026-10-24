import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.services.cad.source_project_generator import SourceProjectGenerator


class FormFitIterationTests(unittest.TestCase):
    def test_device_depth_rejects_shallow_form(self):
        import ezdxf, io
        stream=io.StringIO();ezdxf.new().write(stream)
        with patch('app.services.cad.library_assets.requested_asset',return_value=(True,'selected')), \
             patch.object(SourceProjectGenerator,'_interior_region',return_value=(0,0,400,600)):
            with self.assertRaisesRegex(ValueError,'Chiều sâu'):
                SourceProjectGenerator._place_devices(stream.getvalue(),
                    [dict(tag='Q1',dimensions=dict(w=100,h=200,d=300))],
                    dict(height=600,width=400,depth=250),{})

    def test_unresolved_geometry_does_not_reenter_legacy_catalog_matching(self):
        from app.services.cad.library_assets import requested_asset
        self.assertEqual(requested_asset(dict(cad=dict(requires_selection=True))), (False,None))

    def test_stretched_faces_follow_source_dimension_bands(self):
        item = dict(id='source',dimensions=dict(height=600,width=400,depth=250),
                    faces=[dict(kind='mounting_plate',clean_bounds=[20,20,380,580])])
        axes = [[dict(start=0,end=400,dimension='width')],
                [dict(start=0,end=600,dimension='height')]]
        with patch('app.services.cad.source_project_generator.cabinet_templates.source_path',return_value='source.dxf'), \
             patch('app.services.cad.source_project_generator.ezdxf.readfile'), \
             patch('app.services.cad.source_project_generator.cabinet_templates.stretch_axes',return_value=axes):
            result = SourceProjectGenerator._layout_form(item,dict(height=700,width=500,depth=250))
        self.assertEqual(result['faces'][0]['clean_bounds'],[20,20,480,680])
        self.assertEqual(item['faces'][0]['clean_bounds'],[20,20,380,580])

    def test_real_mounting_plate_can_be_smaller_than_outer_enclosure(self):
        import ezdxf
        item = dict(faces=[dict(kind='mounting_plate',clean_bounds=[20,20,380,580])])
        with patch('app.services.cad.source_project_generator.usable_region',side_effect=lambda bounds,*args:bounds):
            region=SourceProjectGenerator._interior_region(ezdxf.new(),dict(height=600,width=400,depth=250),item)
        self.assertEqual(region,(20,20,380,580))

    def test_tries_next_form_when_smallest_form_cannot_fit_devices(self):
        import ezdxf, io
        stream=io.StringIO(); ezdxf.new().write(stream)
        test_dxf=stream.getvalue()
        def form(key, h, w):
            return dict(id=key, status='needs_review', dimensions=dict(height=h, width=w, depth=250),
                        filename=key + '.dxf', distance=0, can_generate=True)
        forms = [form('small', 600, 400), form('larger', 700, 500)]
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.services.cad.library_assets.requested_asset', return_value=(True, 'selected')), \
             patch('app.services.cad.source_project_generator.cabinet_templates.candidates', return_value=forms), \
             patch('app.services.cad.source_project_generator.cabinet_templates.generate', return_value='test dxf'), \
             patch('app.services.cad.source_project_generator.cabinet_templates.source_path', return_value='source.dxf'), \
             patch('app.services.cad.source_project_generator.ezdxf.readfile'), \
             patch.object(SourceProjectGenerator, '_interior_region'), \
             patch.object(SourceProjectGenerator, '_place_devices', side_effect=[
                 ValueError('không đủ chỗ'), (test_dxf, [{'tag': 'Q0'}], [])]):
            result = SourceProjectGenerator.generate(16, directory, (600, 400, 250), devices=[{'tag': 'Q0'}])
            self.assertEqual(result['template_id'], 'larger')
            self.assertEqual(result['form_fit_attempts'][0]['template_id'], 'small')
            self.assertTrue(Path(result['path']).is_file())
            self.assertFalse(result['release_ready'])

    def test_missing_device_geometry_does_not_generate_every_cabinet(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.services.cad.library_assets.requested_asset', return_value=(False, None)), \
             patch('app.services.cad.source_project_generator.cabinet_templates.generate') as generate:
            with self.assertRaisesRegex(ValueError, 'Thiếu CAD thiết bị: Q0'):
                SourceProjectGenerator.generate(16, directory, (600, 400, 250), devices=[{'tag': 'Q0'}])
            generate.assert_not_called()

    def test_review_search_stops_after_three_unusable_forms(self):
        forms = [dict(id=str(i), status='needs_review', dimensions=dict(height=600,width=400,depth=250),
                      filename='bad.dxf', distance=i, can_generate=True) for i in range(20)]
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.services.cad.source_project_generator.cabinet_templates.candidates',return_value=forms), \
             patch('app.services.cad.source_project_generator.cabinet_templates.source_path',return_value='bad.dxf'), \
             patch('app.services.cad.source_project_generator.ezdxf.readfile'), \
             patch.object(SourceProjectGenerator,'_interior_region',side_effect=ValueError('missing face')) as check:
            with self.assertRaises(ValueError):
                SourceProjectGenerator.generate(16,directory,(600,400,250),devices=[{'tag':'Q0'}],allow_partial=True)
            self.assertEqual(check.call_count,3)

    def test_unusable_source_face_is_rejected_before_expensive_generation(self):
        forms = [dict(id='bad', status='needs_review', dimensions=dict(height=600,width=400,depth=250),
                      filename='bad.dxf', distance=0, can_generate=True)]
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.services.cad.source_project_generator.cabinet_templates.candidates',return_value=forms), \
             patch('app.services.cad.source_project_generator.cabinet_templates.source_path',return_value='bad.dxf'), \
             patch('app.services.cad.source_project_generator.ezdxf.readfile'), \
             patch.object(SourceProjectGenerator,'_interior_region',side_effect=ValueError('missing face')), \
             patch('app.services.cad.source_project_generator.cabinet_templates.generate') as generate:
            with self.assertRaisesRegex(ValueError,'missing face'):
                SourceProjectGenerator.generate(16,directory,(600,400,250),devices=[{'tag':'Q0'}],allow_partial=True)
            generate.assert_not_called()


if __name__ == '__main__':
    unittest.main()
