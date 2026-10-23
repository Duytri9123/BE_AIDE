import unittest,copy
from app.services.catalog_device_names import apply_device_name

def option(model,current,rating,poles=None):
 return {'brand':'CHINT','model':model,'specifications':{'In':str(current)+'A','Icu':str(rating)+'kA',**({'Số cực':poles} if poles else {})}}

class DeviceNameTests(unittest.TestCase):
 def device(self):
  return {'brand':'CHINT','type':'MCCB','product_code':'NXM-250S','spec':{'so_cuc':'3P'},'catalog_references':{'options':[option('NXM-250S/3300 180A',180,36),option('NXM-250S/3300 250A',250,36),option('NXM-250H/3300 250A',250,70),option('NXM-250S/4300 125A',125,50)]}}
 def test_only_same_frame_rating_suffix_and_poles(self):
  d=self.device();apply_device_name(d);self.assertEqual(d['display'],'MCCB CHINT NXM-250S · 3P · 180–250 A · Icu 36 kA')
 def test_unknown_poles_do_not_inherit_candidates(self):
  d=self.device();d['spec']={};apply_device_name(d);self.assertNotIn('kA',d['display']);self.assertNotIn('250 A',d['display'])
 def test_discrete_breaking_capacities_are_not_a_continuous_range(self):
  d=self.device();d['catalog_references']['options'].append(option('NXM-250S/3300 200A',200,50));apply_device_name(d);self.assertIn('Icu 36/50 kA',d['display'])
 def test_no_inferred_phase_count_from_poles(self):
  d=self.device();d['spec']['so_cuc']='2P';apply_device_name(d);self.assertIn('2P',d['display']);self.assertNotIn('pha',d['display'])
 def test_mcb_keeps_icn_designation(self):
  d={'brand':'CHINT','type':'MCB','product_code':'NXB-63','spec':{'so_cuc':'2P'},'catalog_references':{'options':[{'brand':'CHINT','model':'NXB-63 2P C6','specifications':{'Số cực':'2P','In':'6A','Icn':'6kA'}}]}};apply_device_name(d);self.assertIn('Icn 6 kA',d['display']);self.assertNotIn('Icu',d['display'])
 def test_control_contact_ratings_are_not_breaking_capacity(self):
  d={'brand':'CHINT','type':'Pushbutton','product_code':'NP2','spec':{'tiep_diem_tren_cad':'NC','dong_tiep_diem_tren_cad':'AC-15 220V/4.5A'}};apply_device_name(d);self.assertEqual(d['display'],'Nút nhấn CHINT NP2 · NC')
 def test_reference_transformer_does_not_acquire_suggested_model(self):
  d={'brand':'CHINT','type':'Transformer','catalog_references':{'options':[option('NDK-25',25,6)]}};apply_device_name(d);self.assertEqual(d['display'],'Biến áp điều khiển CHINT · CAD tham khảo')
 def test_repeated_application_preserves_shared_contactor_models(self):
  d={'brand':'CHINT','type':'CONTACTOR','display':'Contactor CHINT NCH8-20 / NCH8-25 · 2P','spec':{'dong_dinh_muc':'20 / 25 A'}};apply_device_name(d);first=d['display'];apply_device_name(d);self.assertEqual(d['display'],first)
 def test_other_brands_unchanged(self):
  d=self.device();d['brand']='LS';original=copy.deepcopy(d);self.assertFalse(apply_device_name(d));self.assertEqual(d,original)
if __name__=='__main__':unittest.main()
