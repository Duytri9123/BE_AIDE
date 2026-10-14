import unittest
from bs4 import BeautifulSoup
from scripts.refresh_ple_prices import parse_card
from scripts.refresh_makel_prices import parse_card as makel_card
from scripts.refresh_scope_gaps import sino_rows


class SellerPriceImportTests(unittest.TestCase):
    def ple(self, title, price='210,000 ₫'):
        return BeautifulSoup(f'<div><h2><a href="/product-detail.html">{title}</a></h2><div class="product-price"><span class="PricesalesPrice">{price}</span></div></div>','html.parser')

    def test_ct_primary_rating_is_not_secondary_or_model(self):
        row = parse_card(self.ple('Biến dòng EMIC EM4H03 200/5A'),'EMIC','EMIC','https://www.ple.vn/manufacturer/emic','today')
        self.assertEqual(row['sku'],'EM4H03 200/5A')
        self.assertEqual(row['specifications']['In (A)'],'200')
        self.assertIsNone(parse_card(self.ple('Biến dòng EMIC 0.6 200/5A'),'EMIC','EMIC','https://www.ple.vn/','today'))

    def test_units_quote_only_foreign_brand_are_not_imported(self):
        for title, price in [('Tụ bù Samwha 20kVAR 440V','210,000 ₫'),
                             ('Tụ bù Mikro ABC20 20kVAR','210,000 ₫'),
                             ('Tụ bù Samwha ABC20','Liên hệ'),
                             ('Tụ bù Samwha ABC20','210,000 – 300,000 ₫')]:
            self.assertIsNone(parse_card(self.ple(title,price),'Samwha','Samwha','https://www.ple.vn/','today'))

    def test_makel_uses_current_offer_and_explicit_identity(self):
        html = '<div><a itemprop="name" href="/mu116a.html">MCB 1P 16A MU116A</a><div itemprop="description">Thương hiệu: Hager<br>Mã sản phẩm: MU116A<br>Số cực: 1P<br>Dòng điện định mức In (A): 16 A</div><span itemprop="price">137500.0</span><span itemprop="priceCurrency">VND</span><del>200000</del></div>'
        soup = BeautifulSoup(html,'html.parser')
        row = makel_card(soup,'Hager','https://www.makel.vn/','today')
        self.assertEqual((row['sku'],row['price']),('MU116A',137500))
        self.assertEqual(row['specifications'],{'Số cực':'1P','In (A)':'16'})
        self.assertIsNone(makel_card(soup,'Siemens','https://www.makel.vn/','today'))

    def test_sino_price_and_code_come_from_same_table_row(self):
        html = '<table><tr><td>1</td><td>Aptomat 1P 10A 6kA PS65S /C1010</td><td>Cái</td><td>57.200</td></tr><tr><td>2</td><td>Aptomat 1P 16A PS65S/C1016</td><td>Cái</td><td>Liên hệ</td></tr></table>'
        self.assertEqual(sino_rows(BeautifulSoup(html,'html.parser')),
                         [('PS65S/C1010','Aptomat 1P 10A 6kA PS65S /C1010',57200,{'Số cực':'1P','In (A)':'10'})])

    def test_conflicting_source_code_is_not_silently_overwritten(self):
        html = '<table><tr><td>1</td><td>Aptomat 3P 6A SC45N/C3006</td><td>Cái</td><td>182.000</td></tr><tr><td>2</td><td>Aptomat 4P 6A SC45N/C3006</td><td>Cái</td><td>253.600</td></tr></table>'
        self.assertEqual(sino_rows(BeautifulSoup(html,'html.parser')),[])


if __name__ == '__main__':
    unittest.main()
