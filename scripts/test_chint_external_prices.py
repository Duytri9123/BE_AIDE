import unittest
from unittest.mock import patch

from scripts.complete_chint_external_prices import ats_rows, component_rows
from app.services.device_catalog_browser import build_catalog_page, customer_catalog_page
from app.services.library_price_matching import configuration_links
from app.services.ai.takeoff_pricebook import match_device


class ChintExternalPriceTests(unittest.TestCase):
    def test_ats_variant_preserves_current_and_poles_and_rejects_quote_only(self):
        def card(model, amount):
            return f'<div class="product-container"><h2><a href="/ats-detail.html">ATS Chint {model}</a></h2><div class="product-price"><span class="PricesalesPrice">{amount}</span></div></div>'
        html = card('NZ7-125H/4 100A','7,092,000 ₫')+card('NZ7-125S/3 63A','Liên hệ')
        rows = ats_rows(html, '2026-10-16')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['sku'],'NZ7-125H/4 100A')
        self.assertEqual(rows[0]['specifications']['Số cực'],'4P')
        self.assertEqual(rows[0]['specifications']['In (A)'],'100')

    def test_component_scope_and_availability_survive_public_catalog(self):
        rows = component_rows('2026-10-16')
        page = customer_catalog_page(build_catalog_page([],[],web_offers=rows,q='RT36-00'))
        self.assertEqual(page['total'],2)
        fuse = next(r for r in page['items'] if r['category']=='FUSE')
        self.assertEqual(fuse['price'],170000)
        self.assertIn('Hàng đặt trước; không có sẵn',fuse['cells'])
        self.assertEqual(fuse['vat_status'],'unknown')
        self.assertNotIn('source_url',fuse)
        # A fuse-link offer is never an automatic price for the whole assembly.
        self.assertEqual(match_device({'brand':'CHINT','category':'FUSEASSEMBLY','part_number':'RT36-00'},rows)['candidate_count'],0)

    def test_reviewed_component_choices_are_brand_scoped(self):
        rows = component_rows('2026-10-16')
        device = {'id':'assembly','brand':'CHINT','brand_identification_status':'verified','type':'FuseAssembly','product_code':'RT36-00'}
        with patch('app.services.pricebook_library_links.load_price_options',return_value={r['id']:'assembly' for r in rows}):
            self.assertEqual(len(configuration_links(device,rows)),2)
            self.assertEqual(configuration_links({**device,'brand':'ABB'},rows),{})
            self.assertEqual(configuration_links({**device,'brand_identification_status':'unknown'},rows),{})


if __name__ == '__main__':
    unittest.main()
