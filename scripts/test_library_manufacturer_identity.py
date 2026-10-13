import unittest
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from app.services.library_manufacturer_identity import manufacturer_identity


class ManufacturerIdentityTests(unittest.TestCase):
    def test_reviewed_source_evidence_requires_unchanged_drawing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            drawing = root / 'view.dxf'
            drawing.write_bytes(b'original drawing')
            registry = root / 'evidence.json'
            registry.write_text(json.dumps({'evidence': {'TB-test': {
                'brand': 'CHINT', 'status': 'manufacturer_label_reviewed',
                'note': 'Original nested block label reviewed.',
                'views': [{'view_id': 'side', 'sha256': hashlib.sha256(drawing.read_bytes()).hexdigest()}]
            }}}), encoding='utf8')
            current = {'cad_don': [{'id_hinh_goc': 'side', 'duong_dan': 'view.dxf'}]}
            with patch('app.services.library_manufacturer_identity.EVIDENCE_PATH', registry):
                result = manufacturer_identity({'id': 'TB-test'}, current, root / 'profile.json')
                self.assertEqual(result['brand'], 'CHINT')
                self.assertEqual(result['brand_identity_note'], 'Original nested block label reviewed.')
                evidence = json.loads(registry.read_text(encoding='utf8'))
                evidence['evidence']['TB-test']['status'] = 'manufacturer_candidate_reviewed'
                registry.write_text(json.dumps(evidence), encoding='utf8')
                result = manufacturer_identity({'id': 'TB-test'}, current, root / 'profile.json')
                self.assertEqual(result['brand_identification_status'], 'candidate')
                self.assertEqual(result['brand_kind'], 'manufacturer_candidate')
                drawing.write_bytes(b'changed drawing')
                result = manufacturer_identity({'id': 'TB-test'}, current, root / 'profile.json')
                self.assertIsNone(result['brand'])

    def test_generic_hinge_is_not_a_manufacturer(self):
        result=manufacturer_identity({'type':'Bản lề cửa tủ','brand':'Asian'}, {})
        self.assertIsNone(result['brand'])
        self.assertEqual(result['brand_kind'],'generic')

    def test_electrical_device_does_not_default_to_asian(self):
        result=manufacturer_identity({'type':'MCCB','brand':'Asian','category':'Schneider'}, {})
        self.assertIsNone(result['brand'])
        self.assertEqual(result['brand_kind'],'unidentified_equipment')

    def test_source_library_attribution_is_separate_from_sku_confirmation(self):
        result=manufacturer_identity({'type':'MCCB'}, {'nguon_cad':{'file':r'D:\THƯ VIỆN\@SCHNEIDER.dwg','sha256':'source','block':'NSX250'}})
        self.assertEqual(result['brand'],'Schneider Electric')
        self.assertEqual(result['brand_identification_status'],'source_library')

    def test_explicit_brand_is_preserved_for_accessories(self):
        result=manufacturer_identity({'type':'Bản lề cửa tủ'}, {'hang_xac_nhan':'Rittal'})
        self.assertEqual(result['brand'],'Rittal')
        self.assertEqual(result['brand_identification_status'],'verified')


if __name__=='__main__':
    unittest.main()
