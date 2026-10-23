import unittest
from app.services.ai.response_parser import ExtractedDevice
from app.services.ai.cad_label_integrity import review_measurement_ranges


class MeasurementRangeTests(unittest.TestCase):
    def test_main_breaker_current_does_not_become_an_ammeter_range(self):
        meter=ExtractedDevice('METER','Ammeter','0-150A AC',150,None,None,1,'','',.9,tag='A')
        rows,warnings=review_measurement_ranges([meter],[dict(text='A',x=0,y=2000,height=100),dict(text='150A',x=0,y=0,height=100)])
        self.assertEqual(rows[0].spec,'');self.assertIsNone(rows[0].in_a);self.assertTrue(warnings)

    def test_explicit_local_voltmeter_range_is_preserved(self):
        meter=ExtractedDevice('METER','Voltmeter','0-600V',None,None,None,1,'','',.9,tag='V')
        rows,warnings=review_measurement_ranges([meter],[dict(text='V',x=0,y=0,height=100),dict(text='0-600V',x=10,y=50,height=100)])
        self.assertEqual(rows[0].spec,'0-600V');self.assertFalse(warnings)


if __name__=='__main__':unittest.main()
