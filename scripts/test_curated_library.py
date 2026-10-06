"""Selection invariants against the actual curated library."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.cad import curated_library as lib

class SelectionTests(unittest.TestCase):
    def test_every_product_resolves_to_exactly_one_front(self):
        data=lib.catalog()
        self.assertTrue(data['products'])
        for p in data['products']:
            asset,path=lib.product_asset(p['sku'],p['manufacturer'])
            self.assertEqual(asset,p['cad_by_face']['front'])
            self.assertTrue(path.is_file())

    def test_unknown_sku_and_face_never_fall_back(self):
        with self.assertRaises(ValueError):lib.product_asset('MISSING','LS')
        p=lib.catalog()['products'][0]
        with self.assertRaises(ValueError):lib.product_asset(p['sku'],p['manufacturer'],'invented_face')

    def test_shells_blank_and_no_implicit_resizing(self):
        for f in lib.catalog()['forms']:
            item,path=lib.shell(f['id'])
            self.assertEqual(item['door_policy']['equipment_cutouts'],[])
            self.assertTrue(path.is_file())
            d=dict(f['dimensions_mm_from_source_title']);d['height']+=100
            with self.assertRaises(ValueError):lib.shell(f['id'],d)

    def test_nonactive_source_assets_cannot_be_inserted(self):
        data=lib.catalog();active={a['id'] for a in data['cad_assets']}
        snapshot=json.loads((lib.LIBRARY/'nguon/catalog_tong_hop_truoc_loc.json').read_text(encoding='utf8'))
        excluded=next(a['id'] for a in snapshot['cad_assets'] if a['id'] not in active)
        with self.assertRaises(ValueError):lib.asset_path(excluded)

    def test_title_quantity_is_not_sheet_thickness(self):
        forms={f['id']:f for f in lib.catalog()['forms']}
        self.assertEqual(forms['shell_formtu-15e624']['specifications']['sheet_thickness_source'],'1.5')
        self.assertEqual(forms['shell_formtu-2618d5']['specifications']['sheet_thickness_source'],'1.0')
        self.assertEqual(forms['shell_formtu-22198']['specifications']['sheet_thickness_source'],'1.5')

if __name__=='__main__':unittest.main()
