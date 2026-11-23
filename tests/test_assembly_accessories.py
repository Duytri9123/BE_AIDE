import unittest

from app.services.ai.assembly_accessories import propose_assembly_accessories
from app.services.ai.motor_starter_context import enrich_motor_starters


class AssemblyAccessoriesTests(unittest.TestCase):
    def test_each_topology_gets_its_own_accessories(self):
        def categories(kind, inputs=None):
            return {r['category'] for r in propose_assembly_accessories(kind, inputs or {}, [])}
        self.assertNotIn('MECHANICAL_INTERLOCK', categories('DOL'))
        self.assertIn('MECHANICAL_INTERLOCK', categories('REVERSING'))
        self.assertIn('STAR_DELTA_WIRING_KIT', categories('STAR_DELTA'))
        self.assertIn('BYPASS_CONTACTOR', categories('SOFT_STARTER'))
        self.assertNotIn('BYPASS_CONTACTOR', categories('SOFT_STARTER', {'bypass_integrated': True}))
        self.assertNotIn('SPEED_POTENTIOMETER', categories('VFD'))
        self.assertIn('SPEED_POTENTIOMETER', categories('VFD', {'speed_control_mode': 'potentiometer'}))
        self.assertIn('ATS_INTERLOCK', categories('ATS'))
        self.assertEqual(categories('UNKNOWN'), set())

    def test_existing_parts_are_not_proposed_twice_and_power_is_not_a_rating(self):
        rows = propose_assembly_accessories('DOL', {'control_voltage_v': 24},
            [{'category': 'AUX_CONTACT'}, {'category': 'FAULT_INDICATOR'}], 2200, 'Bơm 1')
        self.assertNotIn('AUX_CONTACT', {r['category'] for r in rows})
        self.assertNotIn('FAULT_INDICATOR', {r['category'] for r in rows})
        self.assertTrue(all(r['status'] == 'proposal' and not r['included_in_total'] for r in rows))
        self.assertTrue(all(r['part_number'] is None and r['condition'] for r in rows))
        self.assertIn('Công suất phụ tải 2200 W', rows[0]['input_context'])
        self.assertNotIn('spec', rows[0])

    def test_refresh_keeps_source_components_and_replaces_suggestions_without_accumulation(self):
        device = {'name': 'DOL', 'connected_load': 'Bơm 1', 'source_observations': {
            'motor_starter': {'components': [{'category': 'AUX_CONTACT', 'quantity': 1, 'basis': 'source'}]}}}
        enrich_motor_starters([device])
        first = device['source_observations']['motor_starter']['accessory_proposals']
        enrich_motor_starters([device])
        assembly = device['source_observations']['motor_starter']
        self.assertEqual(assembly['accessory_proposals'], first)
        self.assertEqual(len(assembly['components']), 1)
        self.assertNotIn('AUX_CONTACT', {r['category'] for r in first})

    def test_ats_has_accessory_guidance_without_motor_input_requirements(self):
        device = {'name': 'Bộ chuyển nguồn ATS', 'quantity': 1}
        enrich_motor_starters([device])
        assembly = device['source_observations']['assembly']
        self.assertEqual(assembly['type'], 'ATS')
        self.assertNotIn('motor_starter', device['source_observations'])
        self.assertIn('ATS_INTERLOCK', {r['category'] for r in assembly['accessory_proposals']})
