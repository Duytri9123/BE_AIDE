import json
import hashlib
import unittest
from pathlib import Path
from app.services.catalog_family_matching import matching_rows
from app.services.published_catalog_information import apply_published_information, published_information

ROOT=Path(__file__).resolve().parents[1]


class PublishedCatalogInformation(unittest.TestCase):
    def test_overlay_cannot_change_cad_geometry_identity_or_electrical_facts(self):
        source={'hang_xac_nhan':'ABB','thong_so':{'current':None},'auto_select':False,'cad_don':[{'id':'original'}]}
        published={'p':{'catalog_tham_khao':{'options':[{'model':'TF42'}]},'hang_xac_nhan':'Other',
                        'auto_select':True,'cad_don':[],'thong_so':{'current':100}}}
        result=apply_published_information(source,'p',published)
        for key in source:
            self.assertEqual(result[key],source[key])
        self.assertEqual(result['catalog_tham_khao']['options'][0]['model'],'TF42')

    def test_all_information_tables_ship_without_private_cad_dataset(self):
        rows=published_information()
        self.assertGreaterEqual(len(rows),1304)
        for profile,data in rows.items():
            with self.subTest(profile=profile):
                self.assertTrue(profile.startswith('TB-'))
                self.assertIsInstance(data['catalog_tham_khao']['options'],list)
                self.assertTrue(all(o['price']=='---' for o in data['catalog_tham_khao']['options']))

    def test_legacy_category_spelling_and_voltage_suffix_do_not_hide_mikro(self):
        rows=json.loads((ROOT/'app/data/supplier_pricebooks.json').read_text(encoding='utf8'))['items']
        cases=[('DIN300','EARTHLEAKAGERELAY','DIN300-240A'),('MX100','PHASERELAY','MX100-400V'),('MX200A','VOLTAGE_RELAY','MX200A-380V')]
        for code,category,sku in cases:
            raw={'ten_kieu':code,'hang_xac_nhan':'Mikro','nhan_dien_ai':{'loai_thiet_bi_code':category}}
            matched=matching_rows(raw,{},rows)
            self.assertTrue(any(r['sku']==sku and basis=='catalog_family_match' for r,basis in matched))

    def test_reviewed_display_can_supply_family_when_legacy_source_is_anonymous(self):
        row={'sku':'MX200A-380V','brand':'Mikro','category':'VOLTAGE_RELAY'}
        matched=matching_rows({'ten_kieu':'*U962'},{'brand':'Mikro','display':'Rơ le Mikro MX200A','type':'VOLTAGE_RELAY'},[row])
        self.assertEqual([r['sku'] for r,_ in matched],['MX200A-380V'])

    def test_abb_has_named_manufacturer_reference_without_a_selling_price(self):
        key='TB-'+hashlib.sha1('ABB/ThietBi/ABB_D03_C2_I08/thong_tin_thiet_bi.json'.encode()).hexdigest()[:16]
        row=published_information()[key]
        self.assertEqual(row['catalog_information_type'],'THERMAL_RELAY')
        self.assertTrue(any(o['brand']=='ABB' and o['model'].startswith('TF42') and o['source_url'] for o in row['catalog_tham_khao']['options']))


if __name__=='__main__':unittest.main()
