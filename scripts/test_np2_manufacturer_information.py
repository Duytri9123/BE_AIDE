import unittest
from scripts.import_np2_manufacturer_information import extract
from app.services.library_catalog_information import information_rows


class Page:
    def __init__(self,text):self.text=text
    def get_text(self):return self.text


class NP2ManufacturerTests(unittest.TestCase):
    def test_only_explicit_models_keep_each_row_voltage_and_contact_counts(self):
        rows=extract([Page('NP2-BA □□□□\nNP2-BA35\n1\n1\nNP2-BW1462 6V LED\n-\n1\nDirect\n6V~230V')])
        self.assertEqual(len(rows),2)
        a,b=rows
        self.assertEqual(a['sku'],'NP2-BA35')
        self.assertEqual(a['specifications']['Tiếp điểm NO'],1)
        self.assertEqual(b['specifications']['Tiếp điểm NO'],0)
        self.assertEqual(b['specifications']['Điện áp đèn theo cấu hình catalog'],'6V')
        self.assertNotIn('230V',str(b['specifications']))
        self.assertTrue(all(r['price'] is None for r in rows))

    def test_conflicting_contact_tables_fail_instead_of_silent_overwrite(self):
        with self.assertRaises(ValueError):
            extract([Page('NP2-BA35\n1\n1\nNP2-BA35\n2\n-')])

    def test_specific_device_label_does_not_match_neighbor_sku_or_other_brand(self):
        rows=extract([Page('NP2-BA35\n1\n1\nNP2-BA350\n2\n-')])
        rows.append({**rows[0],'id':'external:other:np2-ba35','brand':'Other'})
        selected=information_rows({'brand':'CHINT','product_code':'NP2-BA35','type':'PUSHBUTTON'},rows)
        self.assertEqual([r['sku'] for r in selected],['NP2-BA35'])


if __name__=='__main__':unittest.main()
