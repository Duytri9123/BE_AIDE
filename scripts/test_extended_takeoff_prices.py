import unittest
from app.services.ai.takeoff_pricebook import match_device
from app.services.library_price_matching import configuration_links


class ExtendedPriceTests(unittest.TestCase):
    def row(self, model, kind, family, poles, sku):
        return {'id':sku,'brand':'Schneider Electric','category':kind,'item_name':model+' '+poles+' 63A',
                'sku':sku,'price':100,'specifications':{'Họ thiết bị':family,'Số cực':poles,'In (A)':'63'}}

    def test_c120_and_cvs_choices_do_not_auto_select_or_mix_bs_geometry(self):
        rows=[self.row('CVS100B','MCCB','CVS100','3P','LV510300'),
              self.row('CVS100BS','MCCB','CVS100BS','3P','LV510930'),
              self.row('CVS100N','MCCB','CVS100','4P','LV510480')]
        result=match_device({'brand':'Schneider Electric','category':'MCCB','part_number':'CVS100','poles':3},rows)
        self.assertEqual(result['candidate_count'],1)
        self.assertEqual(result['status'],'needs_selection')
        self.assertEqual(result['candidates'][0]['price_row_id'],__import__('hashlib').sha256(b'LV510300').hexdigest()[:24])
        row=self.row('C120H','MCB','C120','4P','A9N18478')
        self.assertEqual(match_device({'brand':'Schneider Electric','category':'MCB','part_number':'C120','poles':4},[row])['status'],'needs_selection')

    def test_shared_easytesys_group_keeps_coil_options_and_excludes_other_frames(self):
        rows=[self.row(model,'CONTACTOR',model,'3P',model+coil) for model in ['LC1E06','LC1E09','LC1E18','LC1E25'] for coil in ['M7','BD']]
        device={'id':'D1','brand':'Schneider Electric','brand_identification_status':'verified',
                'type':'CONTACTOR','product_code':'LC1E06-18','spec':{'so_cuc':'3P'}}
        links=configuration_links(device,rows)
        self.assertEqual(len(links),6)
        self.assertFalse(any('LC1E25' in key for key in links))

    def test_ats_prices_never_cross_pole_count(self):
        rows=[{'id':str(p),'sku':f'OSS-612-PC {p}P','item_name':f'OSS-612-PC {p}P',
              'brand':'O-Sung / OSEMCO','category':'ATS','price':price,'specifications':{'Số cực':f'{p}P','In (A)':'1250'}}
              for p,price in [(3,56500000),(4,70150000)]]
        device={'id':'ATS','brand':'O-Sung / OSEMCO','brand_identification_status':'verified','type':'ATS',
                'product_code':'OSS-612-PC','spec':{'so_cuc':'4P'}}
        self.assertEqual(configuration_links(device,rows),{'4':'ATS'})


if __name__=='__main__':unittest.main()
