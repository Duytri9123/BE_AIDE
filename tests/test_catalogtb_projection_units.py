import hashlib,json,re,tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from app.services.cad import catalogtb_assets as ca


class ProjectionUnitsTests(TestCase):
    def test_projection_states_and_cutouts_stay_distinct(self):
        self.assertEqual(ca.face_code('Mặt trước · 125 A'),'front')
        self.assertEqual(ca.face_code('Mặt dưới'),'bottom')
        self.assertEqual(ca.face_code('Mặt trước mở nắp'),'front_open')
        self.assertEqual(ca.face_code('Lỗ khoét cánh'),'cutout')
        self.assertEqual(ca.face_code('Chưa xác định hướng nhìn'),'unknown')

    def test_all_normalizations_preserve_every_byte_except_units(self):
        pattern=rb'(\$INSUNITS\s*\r?\n\s*70\s*\r?\n[ \t]*)(-?\d+)'
        markers=list(ca.ROOT.rglob('verified_units.json'))
        self.assertEqual(len(markers),195)
        for path in markers:
            meta=json.loads(path.read_text(encoding='utf8'))
            for contract in [meta,*([meta['outline']] if meta.get('outline') else [])]:
                source=path.parent/contract['source_file']
                target=ca.normalized_source(source)
                original=source.read_bytes();normalized=target.read_bytes()
                self.assertEqual(re.sub(pattern,rb'\g<1>0',original),re.sub(pattern,rb'\g<1>0',normalized))
                self.assertEqual(contract['coordinate_scale_to_mm'],1)
            self.assertEqual(len(meta['evidence']['anchors'])>=2,True)

    def test_modified_geometry_is_rejected_before_insertion(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'ban_ve.dxf';source.write_bytes(b'source')
            normalized=root/'ban_ve_mm.dxf';normalized.write_bytes(b'normalized')
            contract={'source_file':source.name,'normalized_file':normalized.name,
                      'source_sha256':hashlib.sha256(b'source').hexdigest(),
                      'normalized_sha256':hashlib.sha256(b'normalized').hexdigest(),
                      'target_units_code':4,'coordinate_scale_to_mm':1}
            (root/'verified_units.json').write_text(json.dumps(contract))
            with patch.object(ca,'ROOT',root):
                self.assertEqual(ca.insertion_source(normalized),normalized)
                source.write_bytes(b'changed geometry')
                with self.assertRaisesRegex(ValueError,'nguồn đã đổi'):ca.insertion_source(normalized)

    def test_cutouts_are_not_candidates_for_full_device_insertion(self):
        assets=ca.assets(refresh=True)
        cutouts=[a for a in assets if a['face']=='cutout']
        self.assertTrue(cutouts)
        for asset in cutouts:
            self.assertEqual(asset['asset_role'],'door_cutout')
            with self.assertRaisesRegex(ValueError,'không cho phép'):ca.resolve(asset['id'])

    def test_uncertain_projection_is_blocked_even_if_legacy_permission_is_true(self):
        with patch.object(ca,'assets',return_value=[dict(id='uncertain',category='MCCB',face='unknown',placement={'cho_phep_chen':True})]):
            with self.assertRaisesRegex(ValueError,'chưa xác nhận hướng'):ca.resolve('uncertain')

    def test_public_download_and_complete_json_index_use_current_library(self):
        from app.services.equipment_library import asset_bytes
        source=next(ca.ROOT.rglob('verified_units.json'))
        contract=json.loads(source.read_text(encoding='utf8'))
        path=source.parent/contract['source_file']
        self.assertEqual(asset_bytes('catalogtb/'+path.relative_to(ca.ROOT).as_posix()),ca.normalized_source(path).read_bytes())
        index=json.loads((ca.ROOT/'ai_device_index.json').read_text(encoding='utf8'))
        self.assertEqual({r['profile'] for r in index['items']},{p.relative_to(ca.ROOT).as_posix() for p in ca.ROOT.rglob('thong_tin_thiet_bi.json')})

    def test_mx100_function_and_original_front_dimensions_are_available(self):
        mx=[a for a in ca.assets() if 'BaoVePha_MX100' in a['profile_path']]
        self.assertEqual(len(mx),1)
        self.assertEqual(mx[0]['category'],'PHASE_RELAY')
        data=json.loads((ca.ROOT/mx[0]['profile_path']).read_text(encoding='utf8'))
        self.assertEqual(data['nhan_dien_web']['cad_front_dimensions_mm'],{'width':35,'height':80})
        self.assertIsNone(data['nhan_dien_web']['selected_voltage'])
        self.assertFalse(data['nhan_dien_web']['exact_sku_verified'])
