import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.review_source_model_documents import documented_model
from scripts.import_schneider_drive_prices import page_offers
from app.services.library_manufacturer_identity import manufacturer_identity
from app.services.library_price_matching import configuration_links


class SourceModelResearchTests(unittest.TestCase):
    def test_shared_breaker_families_keep_poles_and_do_not_choose_rating(self):
        code,kind,url,spec=documented_model('Schneider Electric','06 - N - SC MCCB CVS100~250B~F 4 PHASE')
        self.assertEqual(spec['so_cuc'],'4P')
        self.assertEqual(len(spec['documented_model_options']),6)
        self.assertNotIn('CVS250N',spec['documented_model_options'])
        self.assertNotIn('dong_dinh_muc_da_chon',spec)
        self.assertIsNone(documented_model('Schneider Electric','06 - N - SC MCCB LỖ ĐỤC CVS100~250B~F 4 PHASE'))
        self.assertIsNone(documented_model('Schneider Electric','cvs-03'))
        ls=documented_model('LS Electric','MC 75a-100a AC')[3]
        self.assertEqual(ls['documented_model_options'],['MC-75a','MC-85a','MC-100a'])
        self.assertNotIn('dien_ap_da_chon',ls)

    def test_source_identity_cannot_survive_changed_block_or_document(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'view.dxf').write_bytes(b'original')
            source={'block':'SN_LC1E32','file':'@SCHNEIDER.dwg','sha256':'source-checksum'}
            entry={'brand':'Schneider Electric','status':'source_model_documented','source':source.copy(),
                'manufacturer_document':'https://www.se.com/us/en/download/document/EAV78697/',
                'views':[{'view_id':'v','sha256':hashlib.sha256(b'original').hexdigest()}],
                'library_description':{'product_code':'LC1E32','source_model_reference':True}}
            registry=root/'evidence.json';registry.write_text(json.dumps({'evidence':{'D':entry}}),encoding='utf8')
            current={'nguon_cad':source,'cad_don':[{'id_hinh_goc':'v','duong_dan':'view.dxf'}]}
            with patch('app.services.library_manufacturer_identity.EVIDENCE_PATH',registry):
                self.assertEqual(manufacturer_identity({'id':'D'},current,root/'profile.json')['brand_identification_status'],'verified')
                source['block']='SN_LC1E25'
                result=manufacturer_identity({'id':'D'},current,root/'profile.json')
                self.assertNotIn('reviewed_description',result)
                source['block']='SN_LC1E32';source['sha256']='changed'
                self.assertNotIn('reviewed_description',manufacturer_identity({'id':'D'},current,root/'profile.json'))
                source['sha256']='source-checksum';entry['manufacturer_document']=''
                registry.write_text(json.dumps({'evidence':{'D':entry}}),encoding='utf8')
                self.assertNotIn('reviewed_description',manufacturer_identity({'id':'D'},current,root/'profile.json'))

    def test_no_false_model_substitution_or_complete_device_from_cutout(self):
        for maker,block in [('LS Electric','ABS103'),('LS Electric','LS 800AF 3P'),
                            ('Schneider Electric','06 - N - SC CTT LC1D185'),
                            ('Schneider Electric','06 - N - SC MCCB LÕ ĐỤC EZC100 3 PHASE')]:
            self.assertIsNone(documented_model(maker,block))
        self.assertEqual(documented_model('CHINT','nxb63-2p')[3],{'so_cuc':'2P'})

    def test_drive_shared_models_keep_exact_format_and_power_options(self):
        code,kind,url,spec=documented_model('Schneider Electric','06 - N - SC VSD ATV320U55~75N4B')
        options=spec['documented_model_options']
        device={'id':'D','type':kind,'brand':'Schneider Electric','brand_identification_status':'verified',
                'product_code':code,'reviewed_description':{'price_family_codes':options}}
        rows=[{'id':sku,'sku':sku,'brand':'Schneider Electric','category':'VFD','price':1,
               'item_name':sku,'specifications':{'Họ thiết bị':sku}}
              for sku in ['ATV320U55N4B','ATV320U75N4B','ATV320U55N4C','ATV320U40N4B']]
        self.assertEqual(set(configuration_links(device,rows)),{'ATV320U55N4B','ATV320U75N4B'})

    def test_pdf_drive_prices_stay_in_their_columns_and_skip_contact_price(self):
        def w(x,y,text):return (x,y,x+20,y+10,text,0,0,0)
        words=[w(225,210,'ATV212HU15N4'),w(390,210,'ATV212WU15N4'),
               w(334,210.4,'18.579.000'),w(500,210.3,'24.926.000')]
        self.assertEqual(dict(page_offers(words,189)),{'ATV212HU15N4':18579000,'ATV212WU15N4':24926000})
        self.assertEqual(list(page_offers([w(403,574,'ATV630C11N4(5)'),w(500,574,'Contact')],191)),[])


if __name__=='__main__':unittest.main()
