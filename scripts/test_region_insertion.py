import json,sys,unittest,hashlib,tempfile
from pathlib import Path
from unittest.mock import patch
import ezdxf
from ezdxf.disassemble import recursive_decompose
from ezdxf.addons import Importer
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
from app.services.cad.catalogtb_assets import insertion_source,assets,resolve
from app.services.cad import catalogtb_assets

class RegionInsertion(unittest.TestCase):
 def test_all_ten_repaired_views_keep_native_edges_in_portable_insert(self):
  rows=json.loads((BASE.parent/'outputs/catalogtb-linework-audit/repairs.json').read_text(encoding='utf8'))
  self.assertEqual(len(rows),10)
  for r in rows:
   with self.subTest(view=r['view']):
    path=BASE/'data/CatalogTB'/Path(r['profile']).parent/'CadDon'/r['view']/'ban_ve.dxf'
    converted=insertion_source(path);self.assertNotEqual(path.resolve(),converted)
    doc=ezdxf.readfile(converted)
    self.assertFalse(any(e.dxftype()=='REGION' for b in doc.blocks for e in b))
    target=ezdxf.new('R2018');importer=Importer(doc,target)
    importer.import_entities(list(recursive_decompose(doc.modelspace())));importer.finalize()
    self.assertTrue(len(target.modelspace()))
    self.assertFalse(any(e.dxftype()=='REGION' for e in target.modelspace()))
    self.assertFalse(target.audit().errors)
 def test_reported_incomplete_ezs_front_cannot_be_inserted(self):
  item=next(a for a in assets(refresh=True) if a['name']=='MCCB Schneider EZS400 · 4P' and a['face']=='front')
  with self.assertRaisesRegex(ValueError,'thiếu chi tiết'):resolve(item['id'])
 def test_projection_route_also_rejects_incomplete_view(self):
  from app.api.v1.endpoints.cad_library import catalog_tb_manifest,catalog_tb_insert_dxf
  from fastapi import HTTPException
  _,views=catalog_tb_manifest()
  view_id=next(k for k,v in views.items() if v.get('linework_review',{}).get('status')=='unresolved_visible_geometry_defect')
  with self.assertRaises(HTTPException) as raised:catalog_tb_insert_dxf(view_id)
  self.assertEqual(raised.exception.status_code,422)
 def test_changed_source_rejects_stale_outline(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);source=root/'ban_ve.dxf';derived=root/'ban_ve_net.dxf'
   source.write_bytes(b'original');derived.write_bytes(b'outline')
   (root/'native_preview.json').write_text(json.dumps({'insertion_outline':derived.name,'source_sha256':hashlib.sha256(b'original').hexdigest(),'outline_sha256':hashlib.sha256(b'outline').hexdigest()}))
   with patch.object(catalogtb_assets,'ROOT',root):
    self.assertEqual(insertion_source(source),derived)
    source.write_bytes(b'changed source')
    with self.assertRaisesRegex(ValueError,'nguồn đã đổi'):insertion_source(source)

if __name__=='__main__':unittest.main(verbosity=2)
