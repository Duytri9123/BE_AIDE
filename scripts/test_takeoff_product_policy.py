import unittest,threading,time
from unittest.mock import patch
from app.services.ai.takeoff_product_policy import apply_product_policy
from app.services import job_queue
class ProductPolicyTests(unittest.TestCase):
 def row(self,ident,price,brand='CHINT',current=32,icu=25):
  return dict(id=ident,category='MCCB',brand=brand,sku=ident,item_name=ident,price=price,specifications={'Số cực':'3P','In (A)':str(current),'Icu (kA)':str(icu)})
 def test_cheapest_same_brand_and_separate_alternatives(self):
  d=dict(category='MCCB',brand='CHINT',spec='32A 3P 25kA',poles=3,in_a=32,icu_ka=25,selection_source='user_request',part_number='EXPENSIVE')
  apply_product_policy([d],[self.row('EXPENSIVE',200),self.row('CHEAP',100),self.row('WRONG',1,current=50),self.row('LS32',50,'LS Electric')])
  self.assertEqual(d['part_number'],'CHEAP');self.assertEqual(d['pricebook_match']['row']['price'],100)
  self.assertEqual(set(d['catalog_candidates']),{'CHINT'});self.assertEqual(d['suggested_alternatives'][0]['brand'],'LS Electric')
 def test_missing_icu_is_proposal_without_firm_price(self):
  d=dict(category='MCCB',brand='CHINT',spec='32A 3P',poles=3,in_a=32,selection_source='user_request')
  apply_product_policy([d],[self.row('CHEAP',100)])
  self.assertEqual(d['part_number'],'CHEAP');self.assertIsNone(d['pricebook_match']['row']);self.assertFalse(d['selected_product']['rating_complete'])
 def test_spare_does_not_get_invented_rating_and_meter_name(self):
  spare=dict(category='MCCB',brand='CHINT',selection_source='user_request')
  meter=dict(category='METER',name='Đồng hồ đo lường')
  apply_product_policy([spare,meter],[self.row('CHEAP',100)])
  self.assertNotIn('part_number',spare);self.assertEqual(meter['name'],'Đồng hồ đa năng')
class FakeRedis:
 def __init__(self):self.info={'project_id':'1','pause_requested':'1'}
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def hgetall(self,*args):return dict(self.info)
 def expire(self,*args):pass
 def zadd(self,*args):pass
class PauseTests(unittest.TestCase):
 def test_same_running_job_waits_and_resumes(self):
  client=FakeRedis();events=[];paused=threading.Event();done=threading.Event()
  def publish(*args):
   events.append(args)
   if len(args)>2 and args[2]=='PAUSED':paused.set()
  with patch.object(job_queue,'sync_client',return_value=client),patch.object(job_queue,'publish',side_effect=publish):
   t=threading.Thread(target=lambda:(job_queue.control_point('same-id'),done.set()));t.start()
   self.assertTrue(paused.wait(2));self.assertFalse(done.is_set())
   client.info['pause_requested']='0';t.join(2);self.assertTrue(done.is_set())
   self.assertTrue(all(e[0]=='same-id' for e in events))
 def test_cancel_propagates_out_of_optional_callback_handlers(self):
  client=FakeRedis();client.info['cancel_requested']='1'
  with patch.object(job_queue,'sync_client',return_value=client):
   with self.assertRaises(job_queue.JobCancelled):job_queue.control_point('same-id')
if __name__=='__main__':unittest.main()
