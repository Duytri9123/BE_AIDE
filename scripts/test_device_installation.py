import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.services.cad.device_installation import installation_review, validate_body_face


class InstallationTests(unittest.TestCase):
    def test_front_bounds_never_become_cutout(self):
        for kind in ['MCCB','ACB','METER','LIGHT','PUSHBUTTON','FAN','UNKNOWN']:
            review=installation_review({'ban_chat':kind,'width':52,'height':72,
                'cad_don':[{'huong_nhin':'Mặt trước','unit_verification':{'width_mm':52,'height_mm':72}}]})
            self.assertFalse(review['auto_cutout_allowed'])
            self.assertIsNone(review['cutout'])

    def test_body_cannot_follow_operator_face(self):
        for kind in ['MCCB','ACB','MCB','CONTACTOR','VFD']:
            for face in ['inner_door','outer_door']:
                with self.assertRaises(ValueError): validate_body_face(kind,face)
        validate_body_face('MCCB','inner_door','operating_handle')
        validate_body_face('MCCB','mounting_plate')

    def test_unknown_is_not_assigned_a_door(self):
        review=installation_review({'ban_chat':'SOURCE_REFERENCE'})
        self.assertEqual(review['proposed_body_mounts'],[])
        self.assertIsNone(review['project_owner_face'])

    def test_meter_does_not_imply_outer_door(self):
        review=installation_review({'ban_chat':'METER'})
        self.assertFalse(review['body_mount_verified'])
        self.assertIsNone(review['project_owner_face'])

    def test_model_contract_hash_variant_and_polygon(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); source=root/'cutout.dxf'; source.write_bytes(b'synthetic geometry fixture')
            cutout=dict(verified=True,role='panel_cutout',units='mm',source_reference='unit-test-fixture',
                source_file=source.name,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                operation_origin_from_front_mm=[10,20],points_mm=[[-5,-5],[5,-5],[5,5],[-5,5]])
            profile={'ban_chat':'MCCB','verified_installation':dict(verified=True,model_code='test',variant_id='A',panel_cutout=cutout)}
            path=root/'thong_tin_thiet_bi.json'
            self.assertTrue(installation_review(profile,path,variant_id='A')['auto_cutout_allowed'])
            self.assertFalse(installation_review(profile,path,variant_id='B')['auto_cutout_allowed'])
            invalid=copy.deepcopy(profile); invalid['verified_installation']['panel_cutout']['points_mm']=[[0,0],[8,8],[0,8],[6,0]]
            self.assertFalse(installation_review(invalid,path)['auto_cutout_allowed'])
            invalid=copy.deepcopy(profile); invalid['verified_installation']['panel_cutout']['source_file']='../elsewhere.dxf'
            self.assertFalse(installation_review(invalid,path)['auto_cutout_allowed'])
            source.write_bytes(b'changed')
            self.assertFalse(installation_review(profile,path)['auto_cutout_allowed'])

    def test_xt1_no_confirmed_cutout(self):
        path=Path(__file__).resolve().parents[1]/'data/CatalogTB/ABB/ThietBi/XT1_3P/thong_tin_thiet_bi.json'
        review=installation_review(json.loads(path.read_text(encoding='utf8')),path)
        self.assertEqual(review['body_ownership'],'internal_body')
        self.assertFalse(review['auto_cutout_allowed'])

    def test_mccb_no_inferred_rail_or_door(self):
        from app.services.cad.physical_layout_engine import PhysicalLayoutEngine, MountingType
        self.assertEqual(PhysicalLayoutEngine.classify_mounting({'category':'MCCB','in_a':16}),MountingType.MOUNTING_PLATE_MOUNTED)
        with self.assertRaises(ValueError): PhysicalLayoutEngine.classify_mounting({'category':'MCCB','owner_face':'inner_door'})
        self.assertEqual(PhysicalLayoutEngine.classify_mounting({'category':'SWITCH_DISCONNECTOR'}),MountingType.MOUNTING_PLATE_MOUNTED)
        with self.assertRaises(ValueError): PhysicalLayoutEngine.classify_mounting({'category':'METER'})
        self.assertEqual(PhysicalLayoutEngine.classify_mounting({'category':'METER','owner_face':'mounting_plate'}),MountingType.MOUNTING_PLATE_MOUNTED)
        self.assertEqual(PhysicalLayoutEngine.classify_mounting({'category':'PUSHBUTTON','owner_face':'inner_door'}),MountingType.INNER_COVER_MOUNTED)


if __name__ == '__main__': unittest.main()
