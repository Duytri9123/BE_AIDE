import unittest
from app.services.cad.catalogtb_assets import assets, candidates, resolve
from app.services.cad.reference_panel_layout import pack_rows, balanced_rows
from app.services.cad.library_assets import requested_asset
from app.api.v1.endpoints.cad_library import manifest, resolve_model_asset


class CatalogTBLayoutTests(unittest.TestCase):
    def test_current_folder_is_insertion_source_without_old_price_database(self):
        self.assertTrue(any(i['library']=='CatalogTB' for i in manifest()['items']))
        self.assertIsNone(resolve_model_asset('', {}))

    def test_explicit_front_binding_does_not_claim_exact_sku(self):
        a=candidates('MCB','LS',3)[0]
        self.assertFalse(a['exact_model'])
        self.assertEqual(requested_asset({'cad':{'asset_id':a['id']}}),(True,a['id']))
        with self.assertRaises(ValueError):resolve(a['id'],'side')

    def test_wrong_pole_count_cannot_be_selected(self):
        self.assertTrue(candidates('MCB','LS',2))
        self.assertFalse(candidates('MCB','LS',9))

    def test_different_widths_fit_without_resizing_or_fixed_count(self):
        entries=[{'w':54,'h':82} for _ in range(15)]+[{'w':36,'h':82} for _ in range(4)]
        rows=pack_rows(entries,460)
        self.assertEqual([len(r) for r in rows],[7,7,5])
        self.assertTrue(all(sum(e['w'] for e in row)+12*(len(row)-1)<=460 for row in rows))
        self.assertEqual(sum(len(r) for r in rows),19)
        with self.assertRaises(ValueError):pack_rows([{'w':500}],460)

    def test_unselected_candidate_does_not_become_inserted_device(self):
        self.assertEqual(requested_asset({'cad':{'reference_candidates':[{'id':candidates('MCB','LS',2)[0]['id']}]}}),(False,None))

    def test_label_and_replacement_configuration_is_not_auto_applied(self):
        lamp=next(a for a in candidates('LIGHT') if a['name']=='Đèn báo trạng thái mặt tủ')
        self.assertEqual(lamp['label_config']['text_template'],'{tag}')
        breaker=next(a for a in candidates('MCB','LS',2) if 'BKN' in a['name'])
        options=breaker['replacement_options']
        self.assertFalse(options['auto_apply'])
        self.assertEqual(options['options'][0]['original_spec'],'2P 30A 6kA')
        self.assertIsNone(options['options'][0]['order_code'])

    def test_distinct_pe_n_and_fuse_holder_references(self):
        for category in ('PE','N','FUSE_HOLDER'):
            rows=candidates(category)
            self.assertTrue(rows)
            self.assertTrue(all(a['category']==category for a in rows))
        self.assertNotEqual(candidates('PE')[0]['family_id'],candidates('N')[0]['family_id'])

    def test_adjacent_breakers_balance_by_width(self):
        entries=[{'w':54,'h':82} for _ in range(15)]+[{'w':36,'h':82} for _ in range(4)]
        rows=balanced_rows(entries,460,0)
        self.assertEqual(len(rows),3)
        widths=[sum(e['w'] for e in r) for r in rows]
        self.assertTrue(max(widths)<=460)
        self.assertTrue(max(widths)-min(widths)<=54)

    def test_conductors_require_connection_evidence(self):
        from app.services.ai.conductor_review import connection_requirements
        rows=connection_requirements([{'tag':'QF','category':'MCCB','in_a':200}])
        self.assertEqual([r['terminal'] for r in rows],['LINE','LOAD'])
        self.assertTrue(all(r['section_mm2'] is None and r['conductor_type'] is None for r in rows))
        self.assertTrue(all(not r['auto_assigned'] for r in rows))

    def test_three_fuses_use_one_group_not_nine_holders(self):
        from app.services.cad.catalogtb_assets import instance_count
        a=next(a for a in candidates('FUSE_HOLDER') if a['components_per_asset']==3)
        self.assertEqual(instance_count(3,a),1)
        self.assertEqual(instance_count(6,a),2)
        with self.assertRaises(ValueError):instance_count(1,a)

    def test_fishbone_needs_terminal_and_phase_evidence(self):
        from app.services.ai.distribution_review import review_distribution
        r=review_distribution([],requested_method='fabricated_fishbone')
        self.assertEqual(r['status'],'needs_information')
        self.assertIsNone(r['selected_method'])
        r=review_distribution([],{'terminal_allows_fabricated_copper':False},'fabricated_fishbone')
        self.assertEqual(r['status'],'rejected')

    def test_distribution_and_alignment_loaded_into_agent_context(self):
        from app.services.ai.selection_knowledge import prompt_context
        p=prompt_context()
        self.assertIn('fabricated_fishbone',p)
        self.assertIn('layout_alignment',p)


if __name__=='__main__':unittest.main()
