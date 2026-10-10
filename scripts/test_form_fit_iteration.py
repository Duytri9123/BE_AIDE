import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app.services.cad.source_project_generator import SourceProjectGenerator


class FormFitIterationTests(unittest.TestCase):
    def test_tries_next_form_when_smallest_form_cannot_fit_devices(self):
        def form(key, h, w):
            return dict(id=key, status='needs_review', dimensions=dict(height=h, width=w, depth=250),
                        filename=key + '.dxf', distance=0, can_generate=True)
        forms = [form('small', 600, 400), form('larger', 700, 500)]
        with tempfile.TemporaryDirectory() as directory, \
             patch('app.services.cad.source_project_generator.cabinet_templates.candidates', return_value=forms), \
             patch('app.services.cad.source_project_generator.cabinet_templates.generate', return_value='test dxf'), \
             patch('app.services.cad.source_project_generator.cabinet_templates.source_path', return_value='source.dxf'), \
             patch('app.services.cad.source_project_generator.ezdxf.readfile'), \
             patch.object(SourceProjectGenerator, '_interior_region'), \
             patch.object(SourceProjectGenerator, '_place_devices', side_effect=[
                 ValueError('không đủ chỗ'), ('test dxf', [{'tag': 'Q0'}], [])]):
            result = SourceProjectGenerator.generate(16, directory, (600, 400, 250), devices=[{'tag': 'Q0'}])
            self.assertEqual(result['template_id'], 'larger')
            self.assertEqual(result['form_fit_attempts'][0]['template_id'], 'small')
            self.assertTrue(Path(result['path']).is_file())
            self.assertFalse(result['release_ready'])


if __name__ == '__main__':
    unittest.main()
