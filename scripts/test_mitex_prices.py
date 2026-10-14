import unittest
from bs4 import BeautifulSoup
from scripts.import_mitex_prices import parse_ct
from app.services.ai.takeoff_pricebook import match_device


class MitexPriceTests(unittest.TestCase):
    def card(self, name, price='300,000 ₫'):
        return BeautifulSoup(f'<div><h2><a href="/ct-detail.html">{name}</a></h2><div class="product-price"><span class="PricesalesPrice">{price}</span></div></div>', 'html.parser')

    def test_explicit_configuration_and_manual_selection(self):
        row = parse_ct(self.card('Mitex BD01 CCX 0.5 tỷ số 50/5A 5VA W=2, ĐK 23'), '2026-10-14')
        self.assertEqual(row['category'], 'CT')
        self.assertEqual(row['price'], 300000)
        self.assertEqual(row['specifications']['In (A)'], '50')
        self.assertEqual(row['specifications']['Số vòng dây'], '2')
        self.assertIn('50/5A', row['sku'])
        result = match_device({'brand':'MITEX','category':'CT','part_number':'BD01'}, [{**row, 'item_name':row['sku']}])
        self.assertTrue(result['candidates'])
        self.assertNotEqual(result['status'], 'matched')

    def test_no_contact_price_or_incomplete_configuration(self):
        self.assertIsNone(parse_ct(self.card('Mitex BD01', 'Liên hệ'), '2026-10-14'))
        self.assertIsNone(parse_ct(self.card('Mitex BD01 100/5A'), '2026-10-14'))
        self.assertIsNone(parse_ct(self.card('Mitex BD01-BE CCX 0.5 tỷ số 50/5A 5VA W=2, ĐK 23'), '2026-10-14'))


if __name__ == '__main__':
    unittest.main()
