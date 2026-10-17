import unittest
from scripts.import_verified_manufacturer_information import reviewed_rows
from app.services.library_catalog_information import information_rows

class ReviewedManufacturerTests(unittest.TestCase):
    def test_public_rows_retain_unpriced_products(self):
        rows=reviewed_rows()
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertTrue(all(r['price'] is None and r['source_url'].startswith('https://') for r in rows))
    def test_spd_similar_variant_does_not_change_follow_current(self):
        rows={r['name']:r for r in reviewed_rows()}
        self.assertEqual(rows['OVR T1 25-255-7']['specifications']['Ifi'],'7 kA')
        self.assertEqual(rows['OVR T1 25-255']['specifications']['Ifi'],'50 kA')
    def test_phoenix_alias_matches_correct_model(self):
        rows=information_rows({'brand':'Phoenix','product_code':'UK3N','type':'TERMINAL_BLOCK'},reviewed_rows())
        self.assertEqual([r['sku'] for r in rows],['3001501'])
    def test_siemens_configurations_remain_separate(self):
        rows=[r for r in reviewed_rows() if r['brand']=='Siemens']
        self.assertEqual(len(rows),3)
        self.assertEqual(len({r['specifications']['Cấu hình CPU'] for r in rows}),3)

if __name__=='__main__':unittest.main()
