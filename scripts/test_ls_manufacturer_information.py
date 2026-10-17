import unittest
from scripts.import_ls_manufacturer_information import extract
from app.services.library_catalog_information import information_rows,catalog_model_pattern

class Page:
    def __init__(self,text):self.text=text
    def get_text(self):return self.text

class LSManufacturerTests(unittest.TestCase):
    def test_explicit_complete_model_alternatives(self):
        pattern=catalog_model_pattern('TD100 / TD160')
        self.assertTrue(pattern.search('TD100'))
        self.assertTrue(pattern.search('TD160'))
        self.assertFalse(pattern.search('TD1600'))
        self.assertFalse(catalog_model_pattern('MC-6a / 9a').search('MC-9a'))
    def test_explicit_order_codes_keep_leading_zeros_and_poles(self):
        rows=extract([Page('BKH 4P C125A\n06110364R0\n18\nBKD 3P 63A\n06130063R0\n40')],'2022-04','https://www.ls-electric.com/catalog.pdf')
        self.assertEqual([r['sku'] for r in rows],['06110364R0','06130063R0'])
        self.assertEqual(rows[0]['specifications']['Số cực'],'4P')
        self.assertTrue(all(r['price'] is None for r in rows))
        self.assertEqual(rows[1]['category'],'ISOLATOR')
    def test_alphabetic_family_finds_order_codes_without_merging_b_variant(self):
        rows=extract([Page('BKN 4P C20A\n1234567890\n20\nBKN-b 4P C20A\n1234567891\n20')],'2018','https://www.ls-electric.com/catalog.pdf')
        result=information_rows({'brand':'LS Electric','product_code':'BKN','type':'MCB','spec':{'so_cuc':'4P'}},rows)
        self.assertEqual([r['sku'] for r in result],['1234567890'])
    def test_conflicting_2022_kgr_rating_is_not_silently_imported(self):
        page=Page('32A\n32KGRc 30A 30mA 0.03s\n0750000300\n60')
        self.assertEqual(extract([page],'2022-04','https://www.ls-electric.com/catalog.pdf'),[])
        self.assertEqual(extract([page],'2018','https://www.ls-electric.com/catalog.pdf')[0]['sku'],'0750000300')
    def test_bkp_pole_count_requires_page_table_evidence(self):
        page=Page('BKP type\n1P+N\nBKP C16A\n06120237R0\n120')
        row=extract([page],'2018','https://www.ls-electric.com/catalog.pdf')[0]
        self.assertEqual(row['specifications']['Số cực'],'1P+N')
        self.assertEqual(extract([Page('BKP C16A\n06120237R0')],'2018','https://www.ls-electric.com/catalog.pdf'),[])

if __name__=='__main__':unittest.main()
