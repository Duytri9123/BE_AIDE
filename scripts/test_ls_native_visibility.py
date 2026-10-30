import io,unittest
from unittest.mock import patch
import ezdxf
from app.services.cad.ls_native_visibility import visibility_dxf,device_visibility_dxf
from app.services.cad.device_block_export import native_visibility_insert
class NativeVisibility(unittest.TestCase):
 def source(self,color):
  d=ezdxf.new();d.units=4;d.layers.new('SOURCE',dxfattribs={'color':3});d.modelspace().add_line((1,2),(3,5),dxfattribs={'color':color,'lineweight':35,'layer':'SOURCE'});s=io.StringIO();d.write(s);return s.getvalue().encode()
 def test_export_keeps_original_geometry_styles_and_one_active_face(self):
  faces=[('FRONT',self.source(1)),('SIDE',self.source(5))];d=ezdxf.read(io.StringIO(visibility_dxf(faces,'LS fixture','SIDE').decode()));self.assertTrue(native_visibility_insert(d));self.assertEqual(d.units,4);master=d.blocks[next(iter(d.modelspace())).dxf.name];self.assertEqual(sum(not e.dxf.invisible for e in master),1)
  visible=next(e for e in master if not e.dxf.invisible);line=next(iter(d.blocks[visible.dxf.name]));self.assertEqual(line.dxf.color,5);self.assertEqual(line.dxf.layer,'SOURCE');self.assertEqual(line.dxf.lineweight,35);self.assertEqual(tuple(line.dxf.start),(1,2,0));self.assertEqual(tuple(line.dxf.end),(3,5,0))
 def test_variant_isolation_and_revision_change(self):
  views=[{'id':'a','label':'Mặt trước','cad_variant_id':'A'},{'id':'b','label':'Mặt bên','cad_variant_id':'A'},{'id':'wrong','label':'Mặt sau','cad_variant_id':'B'}];d={'id':'LS fixture','brand':'LS','views':views};sources={'a':self.source(1),'b':self.source(2),'wrong':self.source(3)};reads=[]
  def read(k):reads.append(k);return sources[k]
  with patch('app.services.catalog_view_health.displayable',return_value=True):
   first=device_visibility_dxf(d,'a',read);self.assertEqual(reads,['a','b']);sources['b']=self.source(6);second=device_visibility_dxf(d,'a',read);self.assertNotEqual(first,second)
 def test_duplicate_and_unknown_states_are_not_fabricated(self):
  with self.assertRaises(ValueError):visibility_dxf([('FRONT',self.source(1)),('FRONT',self.source(2))],'bad','FRONT')
 def test_dangling_imported_layer_resources_keep_source_line_style(self):
  from app.services.cad.layer_resource_links import repair_invalid_layer_resources
  doc=ezdxf.read(io.StringIO(self.source(1).decode()));layer=doc.layers.get('SOURCE');line=next(iter(doc.modelspace()));before=dict(line.dxf.all_existing_dxf_attribs())
  layer.dxf.material_handle=line.dxf.handle;layer.dxf.plotstyle_handle='FFFFF'
  self.assertEqual(repair_invalid_layer_resources(doc),2)
  self.assertEqual(doc.entitydb[layer.dxf.material_handle].dxftype(),'MATERIAL')
  self.assertEqual(doc.entitydb[layer.dxf.plotstyle_handle].dxftype(),'ACDBPLACEHOLDER')
  self.assertEqual(layer.dxf.color,3);self.assertEqual(dict(line.dxf.all_existing_dxf_attribs()),before)
if __name__=='__main__':unittest.main()
