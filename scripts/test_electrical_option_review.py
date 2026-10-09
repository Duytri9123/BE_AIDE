import unittest
from app.services.cad.electrical_option_review import assess,review


class ElectricalOptionsTests(unittest.TestCase):
    def setUp(self):
        self.circuit=dict(load_current_a=210,cable_derated_ampacity_a=270,prospective_short_circuit_ka=40,voltage_v=400,poles=3)
        self.option=dict(rated_current_a=250,breaking_capacity_ka=50,voltage_v=400,poles=3,manufacturer_source='verified manufacturer table')

    def test_changed_rating_can_be_suitable_for_circuit(self):
        device=dict(tag='MAIN',category='MCCB',in_a=200,poles=3,spec='200A',compatible_proposal=dict(circuit_inputs=self.circuit,electrical_candidates=[self.option]))
        result=review([device])[0]
        self.assertEqual(result['preferred_candidate']['rated_current_a'],250)
        self.assertEqual(result['drawing_current_a'],200)
        self.assertFalse(result['release_ready'])

    def test_overrating_cable_or_underrating_load_is_rejected(self):
        for current in (200,300):
            self.assertEqual(assess(dict(self.option,rated_current_a=current),self.circuit)['status'],'not_suitable')

    def test_capacity_must_apply_at_system_voltage(self):
        self.assertEqual(assess(dict(self.option,voltage_v=220),self.circuit)['status'],'not_suitable')
        self.assertEqual(assess(dict(self.option,breaking_capacity_ka=26),self.circuit)['status'],'not_suitable')

    def test_missing_load_data_or_malformed_ratings_are_not_approved(self):
        self.assertEqual(assess(self.option,{})['status'],'needs_data')
        self.assertEqual(assess(dict(self.option,rated_current_a='250AF'),self.circuit)['status'],'needs_data')


if __name__=='__main__':unittest.main()
