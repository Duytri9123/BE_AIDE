import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.services.device_catalog_engine import DeviceCatalogEngine
class References(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.engine=DeviceCatalogEngine.get_instance()
 def test_all_profiles_present(self):self.assertEqual(len(self.engine.reference_profiles),835)
 def test_unclassified_not_absent(self):
  unresolved=[i for i in self.engine.reference_profiles if i['category']=='UNCLASSIFIED']
  self.assertTrue(unresolved)
  self.assertTrue(all(i['reference_path'] for i in unresolved))
 def test_terminal_search(self):self.assertEqual(len(self.engine.search_references('TERMINAL',limit=100)),37)
 def test_fuse_and_supply(self):
  self.assertTrue(self.engine.search_references('FUSE'))
  self.assertTrue(self.engine.search_references('POWER_SUPPLY'))
 def test_identity_query_does_not_always_return_first_five(self):
  old=self.engine.reference_profiles
  try:
   self.engine.reference_profiles=[dict(category='TIMER',name=f'Timer {i}',series=f'T{i}',brand='LS',poles=None,reference_path=f'{i}.json',search_aliases=[]) for i in range(10)]
   self.assertEqual(self.engine.search_references('TIMER',query='T9')[0]['reference_path'],'9.json')
  finally:self.engine.reference_profiles=old
 def test_unknown_brand_is_pending_not_missing(self):
  old=self.engine.reference_profiles
  try:
   self.engine.reference_profiles=[dict(category='TIMER',name='Timer',series=None,brand=None,poles=None,reference_path='unknown.json',search_aliases=[])]
   result=self.engine.search_references('TIMER',brand='LS')
   self.assertEqual(result[0]['brand_match'],'unknown_requires_confirmation')
  finally:self.engine.reference_profiles=old
 def test_source_documents_are_indexed(self):
  self.assertEqual(len(self.engine.source_documents),630)
  self.assertTrue(all(not i['insertable'] and not i['auto_select'] for i in self.engine.source_documents))
 def test_source_document_query_returns_pending_geometry(self):
  rows=self.engine.search_source_documents('MIKRO ZCT 80S')
  self.assertTrue(rows)
  self.assertTrue(all(r['status']=='source_document_requires_component_review' for r in rows))
 def test_ai_context_knows_system_library_is_present(self):
  from app.services.ai.analysis_pipeline_service import AnalysisPipelineService
  text=AnalysisPipelineService._compose_multifile_notes('Bóc tách cả hai trang',[],'test.pdf')
  self.assertIn('835 hồ sơ',text)
  self.assertIn('630 CAD nguồn',text)
  self.assertIn('108 form nguồn',text)
if __name__=='__main__':unittest.main(verbosity=2)
