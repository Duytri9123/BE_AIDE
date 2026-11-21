"""Dependency-free regression checks for EL extraction policy and normalization."""
import ast
from pathlib import Path
import unittest

SOURCE = Path(__file__).parents[1] / "app/api/v1/endpoints/el_agent.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
NAMESPACE = {}
# Isolate pure production functions without loading database/provider services.
FUNCTIONS = {"grounded_takeoff_devices", "clean_devices_list", "meter_type_is_grounded",
             "is_brand_or_catalog_update_request", "is_explicit_takeoff_request"}
exec(compile(ast.Module(body=[n for n in TREE.body if isinstance(n, ast.FunctionDef)
                             and n.name in FUNCTIONS], type_ignores=[]), str(SOURCE), "exec"), NAMESPACE)


class TakeoffGroundingTests(unittest.TestCase):
    def test_proposed_and_cached_skus_carry_their_own_manufacturer(self):
        from app.services.ai.takeoff_catalog import _candidate_dict, suggest_takeoff_products
        self.assertEqual(_candidate_dict({'sku': 'SAMPLE-20', 'brand': 'ABB'}, 'Source')['brand'], 'ABB')
        row = {'name': 'MCB', 'category': 'MCB', 'spec': '20A',
               'catalog_candidates': {'ABB': [{'sku': 'SAMPLE-20'}]}}
        result = suggest_takeoff_products([row], catalog_rows=[])[0]
        self.assertEqual(result['catalog_candidates']['ABB'][0]['brand'], 'ABB')
        self.assertNotIn('brand', result)

    def test_source_function_is_retained_as_analysis_and_ats_is_not_mccb(self):
        from app.services.ai.scoped_takeoff import normalize_scoped_row
        row = normalize_scoped_row({'name': 'Bộ chuyển nguồn tự động', 'category': 'MCCB',
            'spec': '', 'observed_text': 'ATS', 'electrical_function': 'Chuyển giữa hai nguồn cấp.'})
        self.assertEqual(row['category'], 'ATS')
        self.assertEqual(row['technical_analysis'], row['electrical_function'])

    def test_whole_panel_review_cannot_replace_individual_device_images(self):
        import tempfile
        from types import SimpleNamespace
        from app.services.ai.scoped_validation import seal_scoped_validation, source_revision
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'source.png'; path.write_bytes(b'source')
            panel = {'source_file_id': 7, 'source_page': 1, 'panel_code': 'MDB', 'source_region': [0, 0, 1, 1]}
            row = {'source_file_id': 7, 'source_page': 1, 'panel_code': 'MDB',
                'evidence_region': {'status': 'panel_checked', 'frame': 'selected_panel', 'source_region': [0, 0, 1, 1]},
                'source_observations': {'evidence_gaps': [], 'source_revision': source_revision(path),
                    'coverage_review': {'status': 'passed', 'issues': [], 'read_failed': False, 'method': 'whole_panel'}}}
            self.assertIsNone(seal_scoped_validation([SimpleNamespace(id=7, file_path=str(path))], [panel], [row]))

    def test_roles_use_local_source_position_and_equipment_type(self):
        rows = [
            dict(name='Aptomat tép', category='MCB', location='Đầu vào tổng', spec='3P 40A', quantity=1),
            dict(name='Biến dòng tổng', category='CT', location='Mạch đo dòng tổng', spec='', quantity=3),
            dict(name='Khởi động từ', category='CONTACTOR', spec='', quantity=1),
            dict(name='Aptomat', category='MCB', tag='L1', connected_load='Chiếu sáng', spec='', quantity=1),
            dict(name='Thiết bị', category='OTHER', spec='', quantity=1),
            dict(name='Aptomat khối', category='MCCB', section='Chưa xác định', spec='3P 80A', quantity=1,
                 evidence_region={'status': 'verified'}, device_assessment={'function': 'Đóng cắt tổng và bảo vệ thanh cái tủ điện.'}),
        ]
        result = NAMESPACE['clean_devices_list'](rows, 1)
        self.assertEqual([r['section'] for r in result], [
            'Đầu vào', 'Đo lường & Giám sát', 'Điều khiển & Chiếu sáng', 'Đầu ra', 'Chưa xác định', 'Đầu vào'])

    def test_no_brand_request_is_a_new_takeoff(self):
        request = 'Bóc tách CHỈ 2 MCB và 1 nút STOP. Không chọn hãng.'
        self.assertFalse(NAMESPACE['is_brand_or_catalog_update_request'](request))
        self.assertTrue(NAMESPACE['is_explicit_takeoff_request'](request))
        self.assertTrue(NAMESPACE['is_brand_or_catalog_update_request']('Bổ sung hãng LS'))

    def device(self, **overrides):
        return dict(name="DOL", spec="", quantity=2, source_file_id=7,
                    evidence="Motor starter Q2", **overrides)

    def validate(self, devices):
        return NAMESPACE["grounded_takeoff_devices"](devices, {7: "actual.dxf"})

    def test_meter_symbol_does_not_establish_multifunction_type(self):
        check = NAMESPACE['meter_type_is_grounded']
        self.assertFalse(check({'name': 'Đồng hồ', 'spec': 'Đồng hồ đa năng'}))
        self.assertTrue(check({'name': 'Đồng hồ đo', 'spec': 'Chưa ghi loại'}))
        self.assertTrue(check({'name': 'Đồng hồ đa năng', 'observed_text': 'MFM'}))

    def test_selected_source_required(self):
        for fields in ({"source_file_id": 8}, {"source_filename": "other.pdf"},
                       {"evidence": "", "catalog_source": "catalog"},
                       {"quantity": None}, {"quantity": True}, {"quantity": 0}):
            device = self.device()
            device.update(fields)
            self.assertEqual(self.validate([device]), [])
        self.assertEqual(len(self.validate([self.device()])), 1)

    def test_accessory_requires_own_evidence(self):
        device = self.device(accompanying_accessories=[{"name": "Relay", "quantity": 1}])
        self.assertEqual(self.validate([device]), [])
        device["accompanying_accessories"][0]["evidence"] = "Relay FR2 beside Q2"
        self.assertEqual(len(self.validate([device])), 1)

    def test_normalizer_does_not_invent_motor_accessories_or_sku(self):
        result = NAMESPACE["clean_devices_list"]([self.device()], 1)[0]
        self.assertEqual(result["accompanying_accessories"], [])
        self.assertEqual(result["brand"], "")
        self.assertEqual(result["part_number"], "")
        self.assertEqual(result["spec"], "")
        self.assertEqual(result["location"], "")
        self.assertEqual(result["evidence"], "Motor starter Q2")
        self.assertEqual(result["quantity"], 2)

    def test_normalizer_retains_load_reasoning_and_catalog_proposals(self):
        fields = {'source_observations': {'relationship_evidence': 'L4 nối tải Chiếu sáng'},
                  'connected_load': 'Chiếu sáng', 'catalog_candidates': {'ABB': [{'sku': 'ACTUAL'}]},
                  'suggested_brands': ['ABB'], 'selection_analysis': {'reason': 'Catalog source'},
                  'device_assessment': {'function': 'Đóng cắt nhánh động cơ.'}}
        result = NAMESPACE['clean_devices_list']([self.device(**fields)], 1)[0]
        for key, value in fields.items():
            self.assertEqual(result[key], value)

    def test_persistence_does_not_turn_lamp_function_into_a_rating_or_erase_analysis(self):
        device={'name':'Đèn báo pha','category':'LIGHT','spec':'','quantity':3,
                'technical_analysis':'Ba đèn thể hiện trạng thái các pha R, Y, B.',
                'selection_analysis':{'status':'no_verified_catalog_match'},'notes':'Nguồn không ghi điện áp.'}
        result=NAMESPACE['clean_devices_list']([device],1)[0]
        for key in ('category','spec','technical_analysis','selection_analysis','notes'):
            self.assertEqual(result[key],device[key])

    def test_normalizer_preserves_group_unit(self):
        row = self.device(unit='Cụm')
        self.assertEqual(NAMESPACE['clean_devices_list']([row], 1)[0]['unit'], 'Cụm')

    def test_unknown_quantity_is_not_defaulted(self):
        device = self.device()
        device.pop("quantity")
        self.assertIsNone(NAMESPACE["clean_devices_list"]([device], 1)[0]["quantity"])

    def test_prompt_allows_verification_without_sample_panels(self):
        strings = [n.value for n in ast.walk(TREE) if isinstance(n, ast.Constant)
                   and isinstance(n.value, str)]
        prompt = next(s for s in strings if s.startswith("Bạn là EL"))
        self.assertNotIn("TĐ-30.A", prompt)
        self.assertNotIn("Không gọi thêm bất kỳ tool", prompt)
        self.assertIn("Được tiếp tục gọi các tool", prompt)
        self.assertIn("Catalog chỉ xác minh", prompt)
        self.assertNotIn("extract_devices_from_cad_for_panels", {getattr(n, "name", "") for n in TREE.body})


if __name__ == "__main__":
    unittest.main()
