import unittest
import json
from pathlib import Path
from scripts.complete_all_catalog_information import enrich, research_category
from app.services.catalog_family_matching import matching_rows


class AllCatalogInformationTests(unittest.TestCase):
    def test_every_published_profile_has_customer_safe_information(self):
        root=Path(__file__).resolve().parents[1]
        overlay=json.loads((root/'app/data/catalogtb_published_information.json').read_text(encoding='utf8'))['profiles']
        self.assertGreaterEqual(len(overlay),1304)
        for relative,row in overlay.items():
            with self.subTest(profile=relative):
                reference=row['catalog_tham_khao']
                self.assertNotIn('research',reference)
                self.assertNotIn('source_identification',reference)
                self.assertTrue(relative.startswith('TB-'))
                self.assertTrue(all(o['model'].strip().casefold() not in {'mặt trước','mặt bên','mặt sau','mặt trên','mặt dưới'} for o in reference['options']))
                for option in reference['options']:
                    self.assertNotIn('source_page',option)
                    self.assertNotIn('Căn cứ',option.get('specifications',{}))

    def test_source_block_dictionary_is_used_and_accessory_is_excluded(self):
        raw={'nguon_cad':{'block':'SN_LC1E32'},'hang_xac_nhan':'Schneider Electric'}
        rows=[{'sku':'LC1E32M7','brand':'Schneider Electric','category':'CONTACTOR'},
              {'sku':'LC1E32-AUX','brand':'Schneider Electric','category':'ACCESSORY'}]
        found=matching_rows(raw,{},rows,'CONTACTOR')
        self.assertEqual([r['sku'] for r,_ in found],['LC1E32M7'])

    def test_vfd_and_inverter_spellings_match(self):
        raw={'ten_kieu':'ATV320U22N4C','hang_xac_nhan':'Schneider Electric'}
        rows=[{'sku':'ATV320U22N4C','brand':'Schneider Electric','category':'VFD'}]
        self.assertEqual(len(matching_rows(raw,{},rows,'INVERTER')),1)

    def test_source_review_is_preserved_and_face_name_cannot_become_model(self):
        raw={'ten_san_pham':'Test','tu_khoa_tim_kiem':['Mặt trước','LC1D95','Test'],
             'catalog_tham_khao':{'options':[{'brand':'X','model':'Mặt trước'},
                {'brand':'X','model':'LC1D95','specifications':{'current':95},'source_url':'https://example.com'}]}}
        result=enrich(raw,{'type':'CONTACTOR'},[],{})
        self.assertEqual(result['removed_face_models'],1)
        self.assertEqual(raw['catalog_tham_khao']['options'][0]['specifications']['current'],95)
        self.assertNotIn('LC1D95',raw['tu_khoa_tim_kiem'])
        self.assertFalse(raw['catalog_tham_khao']['research']['model_identity_verified'])
        self.assertIsNone(raw.get('ma_dong_san_pham'))

    def test_references_do_not_count_as_resolved_source_identity(self):
        raw={'ten_san_pham':'Biến áp CHINT','hang_xac_nhan':'CHINT'}
        result=enrich(raw,{'type':'TRANSFORMER'},[],{})
        self.assertEqual(result['status'],'requires_source_identification')
        self.assertEqual(result['reference_count'],16)
        self.assertFalse(result['model_identity_verified'])


if __name__=='__main__':unittest.main()
