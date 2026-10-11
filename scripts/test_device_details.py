import unittest
from app.services.ai.device_details import details_prompt, parse_details


class DeviceDetailsTests(unittest.TestCase):
    def test_provider_plain_text_missing_information_is_preserved(self):
        result = parse_details('{"function":"Bảo vệ.","assessment":"Cần biết tải.","suitable_product":"MCB.","missing_information":"Dòng tải và điện áp"}')
        self.assertEqual(result['missing_information'], ['Dòng tải và điện áp'])

    def test_incomplete_answer_is_not_presented_as_analysis(self):
        with self.assertRaises(ValueError):
            parse_details('{"assessment":"3P 20A"}')

    def test_customer_conclusions_survive_without_internal_metadata(self):
        result = parse_details('{"function":"Bảo vệ mạch tổng.","assessment":"Cần biết dòng tải để đánh giá 20A.","suitable_product":"MCB 3P theo yêu cầu.","missing_information":["Dòng tải"],"internal_reasoning":"hidden"}')
        self.assertEqual(result['missing_information'], ['Dòng tải'])
        self.assertNotIn('internal_reasoning', result)

    def test_request_and_source_data_are_included_without_cad_search(self):
        prompt = details_prompt({'spec': '3P 20A 10kA', 'connected_load': 'Bơm'}, 'Ưu tiên LS')
        self.assertIn('Ưu tiên LS', prompt)
        self.assertIn('3P 20A 10kA', prompt)
        self.assertIn('Không tra CAD', prompt)


if __name__ == '__main__':
    unittest.main()
