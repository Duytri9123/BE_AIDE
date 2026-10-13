import unittest
from bs4 import BeautifulSoup
from app.services.device_catalog_browser import load_supplier_items,load_web_offers,build_catalog_page,customer_catalog_page
from scripts.refresh_additional_seller_prices import parse_card


class AdditionalCatalogDataTests(unittest.TestCase):
    def test_invt_complete_source_sequence_and_unknown_dates(self):
        rows=[r for r in load_supplier_items() if r['brand']=='INVT']
        self.assertEqual(len(rows),102)
        first=next(r for r in rows if r['item_name']=='GD20-0R7G-S2-BK')
        self.assertEqual(first['price'],1786000)
        self.assertEqual(first['specifications']['Công suất'],'0.75 kW')
        self.assertEqual(first['specifications']['In (A)'],'9.3 A')
        last=next(r for r in rows if r['item_name']=='GD270-355-4')
        self.assertEqual(last['price'],109409000)
        self.assertEqual(last['specifications']['Công suất'],'355 kW')
        self.assertTrue(all(r['effective_date'] is None and r['vat_status']=='unknown' for r in rows))

    def test_mitsubishi_source_samples_and_unpriced_sheets(self):
        rows=[r for r in load_supplier_items() if r['brand']=='Mitsubishi Electric']
        self.assertEqual(len(rows),3026)
        nf=next(r for r in rows if r['item_name']=='NF32-SV 2P 3A' and r['source_sheet']=='MCCB-Fukuyama')
        self.assertEqual(nf['price'],932000)
        self.assertEqual(nf['sku'],'2CB002A000002')
        self.assertEqual(nf['specifications']['Số cực'],'2P')
        self.assertEqual(nf['specifications']['In (A)'],'3')
        self.assertIn('7.5kA',nf['specifications']['Khả năng cắt và điện áp'])
        self.assertTrue(all(r['vat_status']=='unknown' and r['effective_date'] is None for r in rows))
        self.assertFalse(any(r['source_sheet'] in ('MCB India','MV Relays') for r in rows))
        self.assertTrue(all(len(r['columns'])==len(r['cells']) for r in rows))

    def test_seller_card_uses_live_price_not_struck_price(self):
        html='<article><h3 class="product-title"><a href="https://etinco.vn/example/">ENU-41210KS | Tụ bù Nuintek 10kVAr 415V</a></h3><div class="price"><span class="line-through">1.180.000 đ</span><span>649.000 đ</span></div></article>'
        row=parse_card(BeautifulSoup(html,'html.parser'),'Nuintek','CAPACITOR','https://etinco.vn/tu-bu-nuintek/','2026-10-13')
        self.assertEqual(row['price'],649000)
        self.assertEqual(row['sku'],'ENU-41210KS')
        self.assertEqual(row['specifications']['Điện áp'],'415V')
        self.assertIsNone(parse_card(BeautifulSoup(html.replace('649.000 đ','Liên hệ'),'html.parser'),'Nuintek','CAPACITOR','url','date'))

    def test_brand_categories_include_the_actual_imported_prices(self):
        result=customer_catalog_page(build_catalog_page([],[],supplier_items=load_supplier_items(),web_offers=load_web_offers()))
        maker=next(m for m in result['brands'] if m['name']=='Mitsubishi Electric')
        self.assertIn('CONTACTOR',{g['code'] for g in maker['categories']})
        self.assertIn('THERMAL_RELAY',{g['code'] for g in maker['categories']})
        self.assertFalse(any('source' in str(m) for m in result['brands']))
