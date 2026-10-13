import unittest
from app.services.device_catalog_browser import build_catalog_page, customer_catalog_page
from scripts.audit_library_price_coverage import build_options


class CoverageTests(unittest.TestCase):
    def row(self, **changes):
        row = dict(id='price', brand='Mitsubishi Electric', category='MCCB',
                   item_name='NF125-CV 3P 50A', currency='VND', price=100,
                   checked_at='2026-10-13', specifications={'Số cực':'3P'},
                   source_sha256='source', source_kind='supplier_pricebook')
        return {**row, **changes}

    def device(self, **changes):
        return {**dict(id='TB-device', brand='Mitsubishi Electric', type='MCCB',
                       product_code='NF125-CV', spec={'so_cuc':'3P'},
                       brand_identification_status='verified'), **changes}

    def test_zero_price_brand_has_no_priced_categories(self):
        page = customer_catalog_page(build_catalog_page([], [], supplier_items=[self.row()]))
        sk = next(m for m in page['brands'] if m['name']=='SK')
        self.assertEqual((sk['price_count'], sk['priced_categories']), (0, []))
        maker = next(m for m in page['brands'] if m['name']=='Mitsubishi Electric')
        self.assertEqual(maker['priced_categories'][0]['price_count'], 1)

    def test_options_are_exact_model_poles_and_never_geometry_approval(self):
        rows=[self.row(), self.row(id='price2', item_name='NF125-CV 3P 63A')]
        options, _ = build_options([self.device(), self.device(id='other',spec={'so_cuc':'4P'})], rows)
        self.assertEqual(len(options), 2)
        self.assertEqual({o['equipment_catalog_id'] for o in options}, {'TB-device'})
        self.assertFalse(any(o['cad_insertion_verified'] for o in options))
        self.assertEqual(build_options([self.device(product_code='NF125-SV')],rows)[0], [])
        self.assertEqual(build_options([self.device(),self.device(id='duplicate')],rows)[0], [])


if __name__=='__main__':
    unittest.main()
