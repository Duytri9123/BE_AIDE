import json
import tempfile
import unittest
from pathlib import Path
from app.services.pricebook_library_links import validate_links, publish_reviewed_links, load_links
from app.services.device_catalog_browser import load_supplier_items, build_catalog_page
from scripts.import_catalog_reference import import_reference


class PricebookReferenceTests(unittest.TestCase):
    def test_chint_source_ratings_without_pack_quantity(self):
        row = next(r for r in load_supplier_items() if r['brand'] == 'CHINT'
                   and r['item_name'] == 'NXB-63H 1P C6 10kA')
        self.assertEqual(row['price'], 112200)
        self.assertEqual(row['specifications']['Số cực'], '1P')
        self.assertEqual(row['specifications']['In'], '6A')
        self.assertEqual(row['specifications']['Icn'], '10kA')
        self.assertEqual(row['specifications']['Mã hàng'], '813791')
        self.assertNotIn('SL/Thùng', row['columns'])
        self.assertEqual(len(row['columns']), len(row['cells']))

    def test_supplied_data_stays_staged_even_with_verified_flag(self):
        with tempfile.TemporaryDirectory() as folder:
            source, target = Path(folder)/'input.json', Path(folder)/'staged.json'
            source.write_text(json.dumps([{'ma': 'MODEL', 'g': 100, 'w': 18,
                                          '_verified': True}]), encoding='utf8')
            result = import_reference(source, target)
            self.assertFalse(result['prices_published'])
            self.assertFalse(result['library_imported'])
            self.assertIsNone(result['items'][0]['equipment_catalog_id'])
            self.assertFalse(result['items'][0]['drawing_ready'])
            self.assertNotIn('g', result['items'][0]['technical_data'])

    def test_one_library_device_many_prices_with_explicit_review(self):
        prices = [{'id': 'a', 'brand': 'LS'}, {'id': 'b', 'brand': 'LS'}]
        library = [{'catalog_id': 'device', 'brand': 'LS Electric'}]
        links = [{'price_row_id': p['id'], 'equipment_catalog_id': 'device',
                  'status': 'verified', 'identity_evidence': 'Exact model, poles and rated-current checked'}
                 for p in prices]
        with self.assertRaises(ValueError):
            validate_links(links, prices, library, review_complete=False)
        with self.assertRaises(ValueError):
            validate_links(links+links[:1], prices, library, review_complete=True)
        with self.assertRaises(ValueError):
            validate_links(links, prices, [{'catalog_id': 'device', 'brand': 'CHINT'}], review_complete=True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'links.json'
            publish_reviewed_links(links, prices, library, review_complete=True, path=path)
            self.assertEqual(load_links(path), {'a': 'device', 'b': 'device'})

    def test_price_records_have_no_implicit_library_match(self):
        row = {'id': 'a', 'brand': 'LS', 'item_name': 'MODEL', 'sku': 'MODEL',
               'category': 'MCB', 'price': 100, 'currency': 'VND', 'checked_at': '2026-10-13'}
        self.assertIsNone(build_catalog_page([], [], supplier_items=[row])['items'][0]['equipment_catalog_id'])
        self.assertEqual(build_catalog_page([], [], supplier_items=[row], library_links={'a': 'device'})
                         ['items'][0]['equipment_catalog_id'], 'device')

    def test_hyundai_merged_cells_preserve_model_and_poles(self):
        rows = [r for r in load_supplier_items() if r['brand'] == 'Hyundai' and r['item_name'] == 'HGD63M']
        self.assertEqual({r['specifications']['Số cực'] for r in rows}, {'1P', '2P', '3P'})
        self.assertEqual({r['price'] for r in rows}, {90000, 185000, 290000})
        self.assertTrue(all(r['effective_date'] == '2026-04-20' and r['vat_status'] == 'excluded' for r in rows))
        mccb = [r for r in load_supplier_items() if r['brand'] == 'Hyundai' and r['item_name'] == 'HGM100E- F']
        self.assertEqual({r['specifications']['Số cực'] for r in mccb}, {'2P', '3P'})
