import io,unittest,json
from pathlib import Path
from unittest.mock import patch
import ezdxf
from fastapi import HTTPException
from app.services.cad.ls_native_visibility import device_visibility_dxf
from app.services.cad.device_block_export import native_visibility_insert
from app.services.customer_equipment_information import public_view_id
from app.api.v1.endpoints import equipment_library as api
class ChintVisibility(unittest.TestCase):
 def source(self):
  doc=ezdxf.new();doc.units=4;doc.modelspace().add_line((1,2),(3,4),dxfattribs={'color':1,'lineweight':35});s=io.StringIO();doc.write(s);return s.getvalue().encode()
 def device(self):
  return {'id':'CHINT-fixture','brand':'CHINT','product_code':'NXC-40','views':[{'id':str(i),'face':face,'label':face,'cad_variant_id':'same'} for i,face in enumerate(['Mặt trước','Mặt sau','Mặt bên trái','Mặt bên phải','Mặt trên','Mặt dưới'])]}
 def test_complete_chint_download_is_one_native_block_of_only_its_faces(self):
  d=self.device();raw=device_visibility_dxf(d,public_view_id('0'),lambda key:self.source());doc=ezdxf.read(io.StringIO(raw.decode()));self.assertTrue(native_visibility_insert(doc));ref=next(iter(doc.modelspace()));self.assertTrue(ref.dxf.name.startswith('CHINT_'));self.assertEqual(len(doc.blocks[ref.dxf.name]),6)
 def test_partial_or_mixed_variants_do_not_become_an_invented_complete_set(self):
  d=self.device();d['views'][-1]['cad_variant_id']='other';self.assertIsNone(device_visibility_dxf(d,'0',lambda key:self.source()));d['views']=d['views'][:1];self.assertIsNone(device_visibility_dxf(d,'0',lambda key:self.source()))
class ChintMergedFaces(unittest.TestCase):
 def fixture(self,owner_brand='CHINT'):
  device={'id':'PARENT','brand':'CHINT','product_code':'NXB-63','views':[{'id':'side','face':'Mặt bên','download':'/equipment-library/OWNER/views/side/dxf'}]}
  def record(brand,views):return {'record_type':'source_cad_device_or_assembly','brand':brand,'cad':{'views':views}}
  records={'PARENT':record('CHINT',[]),'OWNER':record(owner_brand,[{'id':'side','face':'Mặt bên','dxf':{'path':'catalogtb/Chint/reviewed/side.dxf'}}])}
  return device,records
 def read(self,requested='side',brand='CHINT'):
  device,records=self.fixture(brand)
  with patch('app.services.catalogtb_browser.browser_data',return_value={'items':[device]}),patch.object(api,'get_equipment',side_effect=records.get),patch.object(api,'asset_available',return_value=True),patch('app.services.catalog_view_health.quarantined',return_value=False),patch('app.services.catalog_view_health.asset_displayable',return_value=True):
   return api._cad_view_file('PARENT',public_view_id(requested),'dxf')
 def test_current_public_member_alias_resolves_to_its_own_file(self):self.assertEqual(self.read(),'catalogtb/Chint/reviewed/side.dxf')
 def test_member_from_another_brand_or_unlisted_view_is_rejected(self):
  with self.assertRaises(HTTPException):self.read(brand='ABB')
  with self.assertRaises(HTTPException):self.read(requested='unlisted')

class ReviewedNxmLinks(unittest.TestCase):
 def test_exact_repaired_rows_keep_prices_and_match_only_the_reviewed_poles(self):
  evidence=Path('docs/chint-audit-2026-10-26/nxm-pole-metadata-repair.json')
  if not evidence.is_file():self.skipTest('Reviewed catalog metadata fixture unavailable')
  from app.services.library_catalog_information import source_rows
  from app.services.price_row_cad_detail import linked_cad_for_row
  rows={r['id']:r for r in source_rows()};devices=json.loads(Path('data/CatalogTB/_agent_index/browser_display_v5.json').read_text(encoding='utf8'))['items'];changes=json.loads(evidence.read_text(encoding='utf8'))['items'];self.assertEqual(len(changes),11)
  for change in changes:
   row=rows[change['before']['id']];self.assertEqual(row['price'],change['before']['price']);matches=linked_cad_for_row(row,devices);self.assertEqual({m['id'] for m in matches},{change['cad_catalog_id']});self.assertTrue(all(len(m['views'])==6 for m in matches))
if __name__=='__main__':unittest.main()
