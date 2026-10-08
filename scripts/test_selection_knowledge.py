import unittest
from app.services.ai.selection_knowledge import load_knowledge,evaluate_checks,prompt_context


class SelectionKnowledgeTests(unittest.TestCase):
    def test_source_tables_are_not_default_ampacity(self):
        d=load_knowledge()
        self.assertFalse(d['source_review']['full_article_tables_imported'])
        self.assertFalse(d['source_review']['limited_busbar_reference']['auto_apply'])
        self.assertFalse(d['guardrails']['auto_upsize_breaker'])

    def test_missing_input_does_not_pass(self):
        r=evaluate_checks({'protection_current_a':200})
        self.assertEqual(r['status'],'needs_information')
        self.assertFalse(r['release_ready'])

    def test_known_overload_rejects_even_if_other_checks_unknown(self):
        r=evaluate_checks({'Ib_a':18,'protection_current_a':32,'Iz_effective_a':25})
        self.assertEqual(r['status'],'rejected')

    def test_full_numeric_checks_still_require_review(self):
        data=dict(Ib_a=18,protection_current_a=20,Iz_effective_a=25,I2_a=29,
            breaking_capacity_ka=6,prospective_fault_ka=4,
            let_through_energy_a2s=10000,k=100,section_mm2=2.5,
            temperature_rise_verification=True,short_circuit_verification=True,
            mechanical_and_terminal_verification=True)
        r=evaluate_checks(data)
        self.assertEqual(r['status'],'candidate_requires_review')
        self.assertFalse(r['release_ready'])

    def test_runtime_prompt_reads_local_rules(self):
        from app.core.prompts import append_canonical_output_contract
        p=append_canonical_output_contract('test')
        self.assertIn('overload_current',p)
        self.assertIn('auto_upsize_breaker',p)


if __name__=='__main__':unittest.main()
