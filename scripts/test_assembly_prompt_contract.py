import unittest
from app.core.prompts import append_completeness_review_instruction
from app.services.ai.cluster_equipment_service import AccompanyingEquipmentService


class AssemblyPromptContractTests(unittest.TestCase):
    def test_runtime_contract_covers_bundles_without_assuming_dor_meaning(self):
        prompt = append_completeness_review_instruction('Custom admin prompt')
        self.assertTrue(prompt.startswith('Custom admin prompt'))
        for requirement in ('bộ tích hợp mua nguyên bộ', 'Không mua trùng',
                            'không tự đổi DOR thành DOL', 'không tạo bộ hoặc linh kiện'):
            self.assertIn(requirement, prompt)

    def test_absent_bundle_does_not_generate_customary_accessories(self):
        self.assertEqual(AccompanyingEquipmentService.format_accessories([]), [])
        self.assertEqual(AccompanyingEquipmentService.format_accessories([
            {'name': 'Contactor', 'quantity': 1},
            {'name': 'Relay nhiệt', 'quantity': 1}
        ]), [])

    def test_dol_is_a_functional_assembly_without_duplicate_upstream_breaker(self):
        prompt = append_completeness_review_instruction('Read DWG')
        for requirement in ('Direct On Line', 'một dòng bộ DOL', 'basis=assembly_function',
                            'không nhân đôi trong bộ', 'Không suy dòng động cơ/dải relay/dòng contactor',
                            'không tự gán điện áp cuộn'):
            self.assertIn(requirement, prompt)

    def test_evidenced_bundle_member_retains_quantity_and_explanation(self):
        rows = AccompanyingEquipmentService.format_accessories([{
            'name': 'Contactor', 'category': 'CONTACTOR', 'quantity': 2,
            'evidence': 'Chú giải bộ ghi 2 contactor',
            'technical_reason': 'Đóng cắt hai nhánh trong bộ'
        }])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['quantity'], 2)
        self.assertEqual(rows[0]['technical_reason'], 'Đóng cắt hai nhánh trong bộ')


if __name__ == '__main__':
    unittest.main()
