import json
import unittest
from pathlib import Path
from app.services.catalog_family_matching import matching_rows, information_choice, row_poles

ROOT = Path(__file__).resolve().parents[1]


class CatalogFamilyMatching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = sum([json.loads((ROOT/'app/data'/f).read_text(encoding='utf8'))['items']
                        for f in ('supplier_pricebooks.json', 'web_catalog_offers.json')], [])

    def sample(self, name):
        return json.loads((ROOT/'data/CatalogTB/ProjectSamples'/name/'thong_tin_thiet_bi.json').read_text(encoding='utf8'))

    def test_all_bkn_currents_for_each_pole_count(self):
        for count in (1, 2, 3):
            rows = matching_rows(self.sample(f'BKN_{count}P'), {}, self.rows)
            expected = {r['id'] for r in self.rows if r['sku'].startswith(f'BKN {count}P')}
            self.assertEqual({r['id'] for r, _ in rows}, expected)
            self.assertGreaterEqual(len(rows), 2)
            self.assertTrue(all(row_poles(r) == f'{count}P' for r, _ in rows))

    def test_24h_timer_uses_daily_weekly_timer_not_delay_timer(self):
        rows = matching_rows(self.sample('Timer24h'), {}, self.rows)
        self.assertEqual([r['sku'] for r, _ in rows], ['KG316T AC220V'])
        info = information_choice(*rows[0])
        self.assertEqual(info['specifications']['Mã hàng'], '309010')
        self.assertEqual(info['price'], '---')
        self.assertEqual(info['source_page'], 73)

    def test_contactor_variants_exclude_auxiliary_contact(self):
        rows = matching_rows(self.sample('MC12AF'), {}, self.rows)
        self.assertGreaterEqual(len(rows), 3)
        self.assertTrue(all(r['sku'].startswith('MC-12a') for r, _ in rows))

    def test_embedded_source_code_selects_exact_supply_variant(self):
        rows = matching_rows(self.sample('SupplyS8FS'), {}, self.rows)
        self.assertEqual([r['sku'] for r, _ in rows], ['S8FS-C05024J'])

    def test_enriched_aliases_cannot_prove_a_family(self):
        raw = {'ten_kieu':'Mẫu chưa biết','hang_xac_nhan':'LS Electric', 'tu_khoa_tim_kiem':['BKN']}
        self.assertEqual(matching_rows(raw, {}, self.rows), [])

    def test_numeric_family_boundary_and_explicit_member_models(self):
        raw = {'ten_kieu':'LC1D9-18', 'hang_xac_nhan':'Schneider Electric',
               'nhan_dien_ai':{'loai_thiet_bi_code':'CONTACTOR', 'cac_ma_dong_san_pham':['LC1D09','LC1D12','LC1D18']}}
        models = [r['sku'] for r, _ in matching_rows(raw, {}, self.rows)]
        self.assertTrue(any(m.startswith('LC1D18') for m in models))
        self.assertFalse(any(m.startswith('LC1D95') for m in models))

    def test_terminal_model_numbers_cannot_match_unrelated_relay(self):
        raw = {'ten_kieu':'HYT-2003 / HYT-3003',
               'nhan_dien_ai':{'loai_thiet_bi_code':'TERMINAL_BLOCK'}}
        self.assertEqual(matching_rows(raw, {}, self.rows), [])

    def test_shared_family_does_not_override_component_function(self):
        raw = {'ten_kieu':'NP2', 'hang_xac_nhan':'CHINT',
               'nhan_dien_ai':{'loai_thiet_bi_code':'LIGHT'}}
        matches = matching_rows(raw, {}, self.rows)
        self.assertFalse(any(r['category']=='PUSHBUTTON' for r, _ in matches))

    def test_related_series_keeps_variants_without_claiming_same_frame(self):
        raw = {'ten_kieu':'ABN400AF', 'hang_xac_nhan':'LS Electric',
               'nhan_dien_ai':{'loai_thiet_bi_code':'MCCB'}}
        matches = matching_rows(raw, {}, self.rows)
        self.assertGreater(len(matches), 1)
        self.assertTrue(all(r['sku'].startswith('ABN') and basis=='catalog_series_reference' for r,basis in matches))

    def test_source_samples_are_classified_by_manufacturer_without_project_group(self):
        from scripts.classify_project_sample_profiles import ASSIGNMENTS
        for name,(category,title,_) in ASSIGNMENTS.items():
            raw=self.sample(name)
            self.assertEqual(raw['nhom_thu_vien'],category)
            self.assertEqual(raw['ten_san_pham'],title)
            self.assertTrue(raw['cad_don'])
        for count in (1,2,3):
            raw=self.sample(f'BKN_{count}P')
            self.assertEqual(raw['ma_dong_san_pham'],'BKN')
            self.assertFalse(raw['quy_tac_ghep_mat']['exact_order_code_verified'])
        self.assertFalse(self.sample('Relay125SRQ')['hang_xac_nhan'])


if __name__ == '__main__':
    unittest.main()
