import unittest
from app.services.library_price_matching import configuration_links


class LibraryPriceMatchingTests(unittest.TestCase):
    def test_neutral_configuration_never_matches_plain_single_pole(self):
        row=self.row(brand='Mitsubishi Electric',category='MCB',item_name='BH-DN 1P+N 6A',
                     specifications={'Số cực':'1P+N','In (A)':'6'})
        device=self.device(brand='Mitsubishi Electric',type='MCB',product_code='BH-DN',spec={'so_cuc':'1P+N'})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})
        self.assertEqual(configuration_links(device,[{**row,'item_name':'BH-DN 1P 6A','specifications':{'Số cực':'1P','In (A)':'6'}}]),{})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc':'3P+N'}},[row]),{})

    def test_reviewed_np2_family_is_not_an_automatic_ordering_code(self):
        from app.services.ai.takeoff_pricebook import match_device
        row=self.row(brand='CHINT',category='PUSHBUTTON',sku='NP2-EA32',item_name='NP2-EA32',
                     specifications={'Họ thiết bị':'NP2'})
        d={'brand':'CHINT','category':'PUSHBUTTON','part_number':'NP2'}
        self.assertEqual(match_device(d,[row])['status'],'needs_selection')
        self.assertEqual(match_device(d,[{**row,'specifications':{}}])['status'],'not_found')
        self.assertEqual(match_device(d,[{**row,'sku':'NP20-EA32','item_name':'NP20-EA32'}])['status'],'not_found')

    def test_reviewed_ls_four_pole_price_does_not_change_other_models(self):
        from scripts.review_ls_four_pole_prices import review
        row=self.row(brand='LS Electric',category='CONTACTOR',sku='MC-9a/4',item_name='MC-9a/4',specifications={})
        others=[{**row,'sku':'MC-9a','specifications':{}},{**row,'brand':'ABB','specifications':{}},
                {**row,'category':'ACCESSORY','specifications':{}}]
        self.assertEqual(review([row,*others]),1)
        self.assertEqual(row['specifications']['Số cực'],'4P')
        self.assertTrue(all(not r['specifications'] for r in others))
        device=self.device(brand='LS Electric',type='CONTACTOR',product_code='MC-6a/4 / 9a/4',spec={'so_cuc_chinh':4})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc_chinh':3}},[row]),{})

    def test_abb_thermal_relay_body_keeps_current_range_as_choice(self):
        from app.services.ai.takeoff_pricebook import match_device
        row=self.row(category='THERMAL_RELAY',sku='1SAZ211201R2038',item_name='TA25DU-6.5M',
                     specifications={'Họ thiết bị':'TA25DU','Dải chỉnh định (A)':'4.50–6.50'})
        device=self.device(type='THERMAL_RELAY',product_code='TA25-DU',spec={})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})
        criteria={'brand':'ABB','category':'THERMAL_RELAY','part_number':'TA25DU','in_a':5}
        self.assertEqual(match_device(criteria,[row])['status'],'needs_selection')
        self.assertEqual(match_device({**criteria,'in_a':7},[row])['status'],'not_found')
        self.assertEqual(match_device({**criteria,'part_number':row['sku']},[row])['status'],'matched')
        self.assertEqual(configuration_links({**device,'product_code':'TA42-DU'},[row]),{})

    def test_abb_mcb_series_requires_reviewed_family_and_poles(self):
        from app.services.ai.takeoff_pricebook import match_device
        row=self.row(category='MCB',sku='2CDS211001R0064',item_name='SH201-C6 1P 6A',
                     specifications={'Họ thiết bị':'SH200','Số cực':'1P','In (A)':'6'})
        device=self.device(type='MCB',product_code='SH200',spec={'so_cuc':'1P'})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})
        self.assertEqual(configuration_links({**device,'product_code':'S200'},[row]),{})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc':'2P'}},[row]),{})
        self.assertEqual(match_device({'brand':'ABB','category':'MCB','part_number':'SH200','poles':1,'in_a':6},[row])['status'],'needs_selection')

    def test_mikro_reviewed_family_never_approves_voltage_variant(self):
        from app.services.ai.takeoff_pricebook import match_device
        row = self.row(brand='Mikro', category='VOLTAGE_RELAY', sku='MX200A-380V',
                       item_name='MX200A-380V', specifications={'Họ thiết bị':'MX200A'})
        device = self.device(brand='MIKRO', type='VOLTAGE_RELAY', product_code=None,
                             reviewed_description={'price_family_codes':['MX200A']}, spec={})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})
        self.assertEqual(configuration_links({**device,'brand_identification_status':'candidate'},[row]),{})
        result = match_device({'brand':'Mikro','category':'VOLTAGE_RELAY','part_number':'MX200A'},[row])
        self.assertEqual(result['status'],'needs_selection')
        self.assertFalse(result['candidates'][0]['auto_selectable'])
        self.assertEqual(match_device({'brand':'Mikro','category':'VOLTAGE_RELAY',
                                      'part_number':'MX200A','spec':'220V'},[row])['status'],'not_found')

    def test_shihlin_shared_frames_keep_pole_and_family_boundaries(self):
        row = self.row(brand='Shihlin',item_name='BM100-SN 3P',sku='BM100-SN',
                       specifications={'Họ thiết bị':'BM100','Số cực':'3P'})
        device = self.device(brand='Shihlin Electric',product_code='BM30/50/60/100',spec={'so_cuc':'3P'})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc':'4P'}},[row]),{})
        self.assertEqual(configuration_links({**device,'product_code':'BM300/500'},[row]),{})

    def test_abb_contactor_body_does_not_auto_select_coil_variant(self):
        from app.services.ai.takeoff_pricebook import match_device
        row = self.row(brand='ABB', category='CONTACTOR', item_name='AX32-30-10-80 3P 32A',
                       specifications={'Mã thân': 'AX32-30-10', 'Số cực': '3P', 'In (A)': '32'})
        device = {'brand': 'ABB', 'category': 'CONTACTOR', 'part_number': 'AX32-30-10', 'poles': 3, 'in_a': 32}
        self.assertEqual(match_device(device, [row])['status'], 'needs_selection')
        self.assertEqual(match_device({**device, 'part_number': 'AX40-30-10'}, [row])['status'], 'not_found')

    def test_abb_frame_options_need_reviewed_family_and_matching_poles(self):
        row = self.row(item_name='A1N TMF 4P 125A', sku='1SDA066768R1',
                       specifications={'Họ thiết bị': 'A1', 'Số cực': '4P', 'In (A)': '125'})
        device = self.device(product_code='A1', spec={'so_cuc': '4P'})
        self.assertEqual(configuration_links(device, [row]), {'price-A2': 'TB-A2'})
        self.assertEqual(configuration_links(self.device(product_code='A1'), [row]), {})
        self.assertEqual(configuration_links(device, [{**row, 'brand': 'CHINT'}]), {})
        self.assertEqual(configuration_links(device, [{**row, 'specifications': {'Số cực': '4P'}}]), {})
        from app.services.ai.takeoff_pricebook import match_device
        result = match_device({'brand': 'ABB', 'category': 'MCCB', 'part_number': 'A1',
                               'poles': 4, 'in_a': 125}, [row])
        self.assertEqual(result['status'], 'needs_selection')
        self.assertFalse(result['candidates'][0]['auto_selectable'])

    def device(self, **changes):
        return {**dict(id='TB-A2',brand='ABB',brand_identification_status='verified',
                       type='MCCB',product_code='A2',spec={'so_cuc':'2P'}), **changes}

    def row(self, **changes):
        return {**dict(id='price-A2',brand='ABB',category='MCCB',item_name='A2 2P 100A',
                       sku='ORDER-A2',price=100,specifications={'Số cực':'2P','In (A)':'100'}), **changes}

    def test_same_brand_different_type_model_or_poles_never_match(self):
        wrong = [self.row(id='MCB',category='MCB'), self.row(id='A1',item_name='A1 2P 100A'),
                 self.row(id='3P',item_name='A2 3P 100A',specifications={'Số cực':'3P','In (A)':'100'}),
                 self.row(id='maker',brand='CHINT')]
        self.assertEqual(configuration_links(self.device(),wrong),{})
        self.assertEqual(configuration_links(self.device(),[self.row(),*wrong]),{'price-A2':'TB-A2'})

    def test_all_matching_prices_remain_available_for_pagination(self):
        rows=[self.row(id=str(i),item_name=f'A2 2P {i+1}A',specifications={'Số cực':'2P','In (A)':str(i+1)}) for i in range(65)]
        self.assertEqual(len(configuration_links(self.device(),rows)),65)

    def test_unknown_brand_identity_missing_code_or_poles_stays_empty(self):
        for device in [self.device(brand_identification_status='unknown'),self.device(brand_identification_status='candidate'),self.device(product_code=None),self.device(spec={})]:
            self.assertEqual(configuration_links(device,[self.row()]),{})

    def test_shared_contactor_models_and_main_poles(self):
        device=self.device(type='Contactor',product_code='MC-6a / 9a / 12a',spec={'so_cuc_chinh':3})
        rows=[self.row(id=model,category='CONTACTOR',item_name=model+' (2)',sku=model,
                       group='CONTACTOR 3 POLES',specifications={}) for model in ['MC-6a','MC-9a','MC-12a','MC-18a']]
        self.assertEqual(set(configuration_links(device,rows)),{'MC-6a','MC-9a','MC-12a'})
        self.assertEqual(configuration_links({**device,'spec':{'so_cuc_chinh':4}},rows),{})

    def test_slash_is_part_of_four_pole_model_identity(self):
        device=self.device(type='Contactor',product_code='MC-6a/4 / 9a/4',spec={'so_cuc_chinh':4})
        row=self.row(category='CONTACTOR',item_name='MC-9a/4 (2)',group='CONTACTOR 4 POLES',specifications={})
        self.assertEqual(configuration_links(device,[row]),{'price-A2':'TB-A2'})


if __name__=='__main__':
    unittest.main()
