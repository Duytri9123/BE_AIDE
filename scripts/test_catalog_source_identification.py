import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from app.services.catalog_source_identification import model_pattern,source_fingerprint,validated_identification,apply_source_identification
from scripts.resolve_catalog_source_labels import candidates


class SourceIdentificationTests(unittest.TestCase):
    def test_model_boundaries_and_pdf_typography(self):
        pattern=model_pattern('HYT-203')
        self.assertTrue(pattern.search('HYT–203'))
        self.assertTrue(pattern.search('HYT -\n203'))
        self.assertFalse(pattern.search('HYT-2030'))
        self.assertFalse(pattern.search('HYT-203A'))
        self.assertTrue(model_pattern('UK3N').search('UK 3 N'))

    def test_terminal_markings_are_not_new_model_candidates(self):
        scan={'texts':['A1','A2','C63','AX40-30-10'],'views':[]}
        models,_=candidates({'ma_dong_san_pham':'AX40-30-10'},scan)
        self.assertIn('AX40-30-10',models)
        self.assertNotIn('A1',models)
        self.assertNotIn('C63',models)

    def test_changed_profile_or_drawing_invalidates_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'profile.json';drawing=root/'view.dxf';drawing.write_bytes(b'original')
            raw={'cad_don':[{'id_hinh_goc':'v','duong_dan':'view.dxf'}]}
            record={'source_fingerprint':source_fingerprint(raw),'views':[{'path':'view.dxf','sha256':hashlib.sha256(b'original').hexdigest()}],
                'documented_models':[{'model':'HYT-203'}],'status':'documented_source_label'}
            with patch('app.services.catalog_source_identification.identifications',return_value={'profile.json':record}):
                self.assertEqual(validated_identification(raw,path,root),record)
                profile={'brand':None,'spec':{'current':None},'auto_select':False}
                apply_source_identification(profile,raw,path,root)
                self.assertEqual(profile['product_code'],'HYT-203')
                self.assertIsNone(profile['brand'])
                self.assertIsNone(profile['spec']['current'])
                self.assertNotIn('views',profile['source_identification'])
                raw['hang_xac_nhan']='Different'
                self.assertIsNone(validated_identification(raw,path,root))
                stale={'catalog_references':{'source_identification':{'status':'documented_source_label'},
                    'options':[{'model':'HYT-203','basis':'verified_cad_label'}]}}
                apply_source_identification(stale,raw,path,root)
                self.assertNotIn('source_identification',stale['catalog_references'])
                self.assertEqual(stale['catalog_references']['options'][0]['basis'],'catalog_type_reference')
                del raw['hang_xac_nhan'];drawing.write_bytes(b'changed')
                self.assertIsNone(validated_identification(raw,path,root))

    def test_outline_conflict_requires_current_preview_and_cannot_promote_code(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'profile.json'
            (root/'view.dxf').write_bytes(b'cad');preview=root/'xem_truoc.svg';preview.write_bytes(b'outline')
            raw={'cad_don':[{'id_hinh_goc':'v','duong_dan':'view.dxf'}]}
            record={'source_fingerprint':source_fingerprint(raw),'status':'source_label_conflict',
                'views':[{'id':'v','path':'view.dxf','sha256':hashlib.sha256(b'cad').hexdigest()}],
                'documented_models':[{'model':'BHA44'}],
                'reviewed_outline_label':{'view':'v','preview_sha256':hashlib.sha256(b'outline').hexdigest()}}
            with patch('app.services.catalog_source_identification.identifications',return_value={'profile.json':record}):
                profile={};apply_source_identification(profile,raw,path,root)
                self.assertNotIn('product_code',profile)
                preview.write_bytes(b'new outline')
                self.assertIsNone(validated_identification(raw,path,root))


if __name__=='__main__':unittest.main()
