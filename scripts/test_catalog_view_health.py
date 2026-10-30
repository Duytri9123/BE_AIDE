import hashlib,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import ezdxf
from app.services import catalog_view_health as health
from app.services.customer_equipment_information import customer_device,customer_browser,public_view_id

class CatalogViewHealthTests(unittest.TestCase):
 def test_changed_verified_bytes_are_blocked_until_reverification(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);drawing=root/'ban_ve.dxf';preview=root/'xem_truoc.svg';drawing.write_bytes(b'verified drawing');preview.write_bytes(b'<svg/>')
   ledger=root/'verified.json';ledger.write_text(json.dumps({'files':{'ban_ve.dxf':{'sha256':hashlib.sha256(drawing.read_bytes()).hexdigest(),'preview_sha256':hashlib.sha256(preview.read_bytes()).hexdigest()}}}))
   with patch.object(health,'VERIFIED',ledger),patch.object(health,'CATALOG',root):
    health._valid.cache_clear();health._verified.cache_clear()
    self.assertTrue(health._valid(str(drawing),(1,1),str(preview),(1,1)))
    drawing.write_bytes(b'changed drawing')
    self.assertFalse(health._valid(str(drawing),(2,2),str(preview),(1,1)))
 def test_unknown_or_defective_views_never_reach_customer_payload(self):
  base={'id':'health-test','brand':'ABB','product_code':'test','display':'test','primary_view':'bad','views':[{'id':'bad','face':'CAD cần đối chiếu thiết bị'},{'id':'good','face':'Mặt trước'},{'id':'broken','face':'Mặt bên','linework_review':{'status':'unresolved_visible_geometry_defect'}}]}
  result=customer_device(base)
  self.assertEqual([v['id'] for v in result['views']],[public_view_id('good')]);self.assertEqual(result['primary_view'],public_view_id('good'))
  self.assertEqual(customer_browser({'items':[{**base,'views':[base['views'][0]]}],'total':1})['items'],[])
 def test_quarantine_blocks_old_raw_and_opaque_identifiers(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'quarantine.json';p.write_text(json.dumps({'items':[{'catalog_id':'old','view_id':'bad'}]}))
   with patch.object(health,'QUARANTINE',p):
    health._quarantined.cache_clear()
    self.assertTrue(health.quarantined('old','bad'));self.assertTrue(health.quarantined('old',public_view_id('bad')));self.assertFalse(health.quarantined('other','bad'))
 def test_hidden_profile_blocks_previously_saved_asset_url(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);profile=root/'LS'/'ThietBi'/'MODEL';source=profile/'CadDon'/'front'/'ban_ve.dxf';source.parent.mkdir(parents=True);source.write_bytes(b'valid-source')
   (profile/'thong_tin_thiet_bi.json').write_text(json.dumps({'browser_hidden':True}))
   with patch.object(health,'CATALOG',root),patch('app.services.equipment_library._catalogtb_asset',return_value=source),patch.object(health,'_valid',return_value=True):
    self.assertFalse(health.asset_displayable('old/url'))
    (profile/'thong_tin_thiet_bi.json').write_text(json.dumps({'browser_hidden':False}))
    with patch('app.services.cad.catalogtb_assets.normalized_source',side_effect=lambda p:p):
     source.with_name('xem_truoc.svg').write_text('<svg/>')
     self.assertTrue(health.asset_displayable('old/url'))
 def test_invalid_source_hidden_until_repaired(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder);drawing=p/'ban_ve.dxf';preview=p/'xem_truoc.svg';preview.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
   doc=ezdxf.new();doc.units=1;doc.modelspace().add_circle((0,0),10);doc.saveas(drawing)
   entry={'huong_nhin':'Mặt trước','duong_dan':'ban_ve.dxf'}
   with patch('app.services.cad.catalogtb_assets.normalized_source',side_effect=lambda x:x):
    self.assertFalse(health.source_displayable(entry,p/'profile.json'))
    doc.units=4;doc.saveas(drawing);self.assertTrue(health.source_displayable(entry,p/'profile.json'))
    preview.write_text('broken');self.assertFalse(health.source_displayable(entry,p/'profile.json'))

if __name__=='__main__':unittest.main()
