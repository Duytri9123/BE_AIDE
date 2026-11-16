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
