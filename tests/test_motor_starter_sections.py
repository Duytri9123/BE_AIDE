import unittest

from app.services.ai.motor_starter_context import enrich_motor_starters


class MotorStarterSectionsTests(unittest.TestCase):
    def test_dol_has_separate_operators_without_assuming_input_quantities(self):
        device = {'name': 'DOL', 'tag': 'L1', 'quantity': 2}
        enrich_motor_starters([device])
        components = device['source_observations']['motor_starter']['components']
        operators = [c for c in components if c['category'] in {
            'PUSH_BUTTON_ON', 'PUSH_BUTTON_OFF', 'SELECTOR_SWITCH_3_POSITION'}]
        self.assertEqual(len(operators), 3)
        self.assertTrue(all(c['quantity'] is None for c in operators))
        self.assertTrue(all(c['included_in_total'] is False for c in components))
        self.assertEqual(device['quantity'], 2)

    def test_input_for_one_starter_survives_refresh_without_leaking_to_another(self):
        supplied = {'category': 'PUSH_BUTTON_ON', 'name': 'ON tại hai vị trí',
                    'quantity': 2, 'spec': '1NO', 'basis': 'user_request'}
        first = {'name': 'DOL', 'tag': 'L1', 'source_observations': {
            'motor_starter': {'components': [supplied]}}}
        second = {'name': 'DOL', 'tag': 'L2'}
        for _ in range(2):
            enrich_motor_starters([first, second])
        components = first['source_observations']['motor_starter']['components']
        on = next(c for c in components if c['category'] == 'PUSH_BUTTON_ON')
        self.assertEqual(on['quantity'], 2)
        self.assertEqual(on['spec'], '1NO')
        self.assertEqual(len(components), 1)
        other = second['source_observations']['motor_starter']['components']
        self.assertIsNone(next(c for c in other if c['category'] == 'PUSH_BUTTON_ON')['quantity'])

    def test_power_follows_each_load_and_requires_known_unit(self):
        devices = [
            {'name': 'DOL', 'connected_load': 'Bơm 1', 'circuit_context': {'power_w': 2200}},
            {'name': 'Sao tam giác', 'connected_load': 'Bơm 2',
             'source_observations': {'circuit': {'power_value': 15, 'power_unit': 'kW'}}},
            {'name': 'DOL', 'connected_load': 'Bơm 3', 'in_a': 25,
             'circuit_context': {'power_value': 7.5}},
        ]
        enrich_motor_starters(devices)
        assemblies = [d['source_observations']['motor_starter'] for d in devices]
        self.assertEqual([a['load_power_w'] for a in assemblies], [2200, 15000, None])
        self.assertNotIn('Công suất động cơ (kW)', assemblies[0]['missing_inputs'])
        self.assertIn('Công suất động cơ (kW)', assemblies[2]['missing_inputs'])
        self.assertEqual(assemblies[1]['type'], 'STAR_DELTA')
        self.assertEqual(len([c for c in assemblies[1]['components'] if c['category'] == 'CONTACTOR']), 3)
