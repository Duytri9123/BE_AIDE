import json
import unittest
from app.services.ai.response_parser import ResponseParserService as Parser

class NestedCompletenessTests(unittest.TestCase):
    def test_accessories_and_inferred_parts_do_not_count_as_missing_devices(self):
        row={'category':'MCCB','name':'Main','quantity':1,
             'accompanying_accessories':[{'category':'SHUNT_TRIP','name':'Cuộn cắt','evidence':'SHT trên nguồn','quantity':1}],
             'inferred_components':[{'category':'AUX_CONTACT','name':'Tiếp điểm phụ','reason':'Cần tín hiệu trạng thái'}]}
        for payload in ({'devices':[row]}, {'panels':[{'panel_code':'MDB','devices':[row]}]},[row]):
            self.assertEqual(Parser.extract_completeness_warnings(json.dumps(payload)),[])

    def test_truncated_device_tail_still_reports_missing_row(self):
        response=json.dumps({'devices':[{'category':'MCB','name':'Q1','quantity':1}]})+'\n{"devices":[{"category":"MCCB"'
        self.assertTrue(any('chưa đọc đủ' in warning for warning in Parser.extract_completeness_warnings(response)))

    def test_explicit_missing_device_review_is_retained(self):
        response=json.dumps({'devices':[{'category':'MCB','name':'Q1','quantity':1}],
            'completeness_review':{'missing_devices':['Cần rà soát Q2']}})
        self.assertTrue(any('Q2' in warning for warning in Parser.extract_completeness_warnings(response)))

if __name__=='__main__':unittest.main()
