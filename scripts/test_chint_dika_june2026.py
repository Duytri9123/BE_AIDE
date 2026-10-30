"""Check the imported source against public serialization and commercial variants."""
import unittest
from pathlib import Path

from scripts.import_chint_dika_june2026 import extract, SOURCE_KEY
from app.services.device_catalog_browser import build_catalog_page, customer_catalog_page, load_supplier_items


class ChintDikaJuneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.counts = extract(Path(__file__).resolve().parents[1]/'storage/catalog-pricebooks'/f'{SOURCE_KEY}.pdf')

    def test_all_160_source_price_cells_accounted_for(self):
        self.assertEqual(len(self.rows), 160)
        self.assertEqual(self.counts, {1:0,2:24,3:9,4:44,5:14,6:8,7:11,8:22,9:14,10:10,11:4})
        self.assertTrue(all(r['vat_status']=='excluded' and r['discount_applied_percent']==0 for r in self.rows))
        self.assertTrue(all(r['effective_date'] is None for r in self.rows))

    def test_coil_prices_and_poles_are_not_collapsed(self):
        nxc = [r for r in self.rows if r['sku']=='NXC-12']
        self.assertEqual({r['specifications']['Điện áp cuộn hút']:r['price'] for r in nxc}, {'220VAC':312000,'380VAC':339000})
        self.assertEqual(len([r for r in self.rows if r['sku']=='NXC-09']),2)
        self.assertTrue(all(r['specifications']['Số cực']=='2P' for r in self.rows if r['sku'].startswith('NCH8')))
        nxb = [r for r in self.rows if r['sku']=='NXB-63' and r['specifications']['In (A)']=='63']
        self.assertEqual({r['specifications']['Số cực']:r['price'] for r in nxb}, {'1P':79000,'2P':144500,'3P':230000,'4P':329000})

    def test_merged_ranges_and_duplicate_model_configs_remain_distinct(self):
        nxr = [r for r in self.rows if r['sku']=='NXR-100']
        self.assertEqual({r['specifications']['Dải chỉnh định Ir (A)']:r['price'] for r in nxr},
                         {'23-32, 30-40, 37-50, 48-65, 55-70':595000,'63-80, 80-93':658000,'80-100':699000})
        selectors = [r for r in self.rows if r['sku']=='NP2-ED/J*']
        self.assertEqual({r['specifications']['Số vị trí']:r['price'] for r in selectors},{'2':48000,'3':55000})
        self.assertFalse(any(r['category']=='RCBO' or r['sku']=='NXC-06' or r['sku']=='NXC-330' for r in self.rows))

    def test_every_imported_price_survives_real_customer_serialization(self):
        loaded = [r for r in load_supplier_items() if r['id'].startswith(SOURCE_KEY+':')]
        self.assertEqual(len(loaded),160)
        raw = build_catalog_page([],[],supplier_items=loaded,brand='CHINT',limit=1000)
        public = customer_catalog_page(raw)
        self.assertEqual(public['total'],160)
        self.assertEqual(sorted(r['price'] for r in public['items']), sorted(r['price'] for r in self.rows))
        for r in public['items']:
            self.assertEqual(len(r['columns']),len(r['cells']))
            self.assertEqual(r['vat_status'],'excluded')
            self.assertFalse({'source_url','source_sha256','source_cell'} & r.keys())


if __name__ == '__main__':
    unittest.main()
