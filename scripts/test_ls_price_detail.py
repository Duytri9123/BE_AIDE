import copy,hashlib,io,unittest,tempfile,json
from pathlib import Path
from unittest.mock import patch
import ezdxf
from app.services.net_catalog_prices import net_price_row
from app.services.price_row_cad_detail import price_row_detail,linked_cad_for_row
from app.services.cad.ls_colored_views import colored_dxf

class NetPrices(unittest.TestCase):
 def test_net_source_is_preserved_without_discount(self):
  row={'price':123456,'vat_status':'excluded','columns':['Tên hàng','Đơn giá'],'cells':['A','123,456']};old=copy.deepcopy(row);out=net_price_row(row)
  self.assertEqual(out['price'],123456);self.assertEqual(out['cells'][1],'123,456');self.assertEqual(row,old);self.assertEqual(net_price_row(out),out)
 def test_only_documented_rate_can_remove_vat(self):
  row={'price':110000,'vat_status':'included','vat_rate_percent':10,'columns':['Giá VNĐ'],'cells':['110,000']}
  self.assertIsNone(net_price_row(row)['price']);self.assertEqual(net_price_row(row)['cells'],[''])
  row['vat_rate_evidence']={'pdf_page':7};out=net_price_row(row);self.assertEqual(out['price'],100000);self.assertEqual(out['cells'],['100,000'])
 def test_unknown_or_invalid_price_never_becomes_net(self):
  for value in (None,float('nan'),-5,True):self.assertIsNone(net_price_row({'price':value,'vat_status':'unknown'})['price'])

class ColoredGeometry(unittest.TestCase):
 def test_native_control_records_are_byte_identical_except_rgb_tags(self):
  source=Path('data/CatalogTB/LS/ThietBi/MC_35/CadDon/D02_cluster2-V004/ban_ve.dxf')
  if not source.is_file():self.skipTest('Native LS integration fixture unavailable')
  def without_rgb(data):
   lines=io.BytesIO(data).readlines()
   return b''.join(b''.join(lines[i:i+2]) for i in range(0,len(lines),2) if lines[i].strip()!=b'420')
  raw=source.read_bytes();self.assertEqual(without_rgb(raw),without_rgb(colored_dxf(raw)))
 def test_true_white_and_neutral_curves_get_clear_colours(self):
  d=ezdxf.new();d.units=4;d.modelspace().add_line((0,0),(4,5),dxfattribs={'true_color':0xFFFFFF});d.modelspace().add_circle((8,9),2);s=io.StringIO();d.write(s)
  out=ezdxf.read(io.StringIO(colored_dxf(s.getvalue().encode()).decode()));line,circle=list(out.modelspace())
  self.assertEqual(line.dxf.true_color,0x40D9FF);self.assertEqual(circle.dxf.true_color,0xFFBF69);self.assertEqual(circle.dxf.radius,2)
 def test_native_coloured_layer_and_byblock_inheritance_are_preserved(self):
  d=ezdxf.new();d.layers.new('RED',dxfattribs={'color':7,'true_color':0xFF3300});d.modelspace().add_line((0,0),(1,2),dxfattribs={'layer':'RED'});b=d.blocks.new('NATIVE');b.add_line((0,0),(2,3),dxfattribs={'color':0});d.modelspace().add_blockref('NATIVE',(0,0),dxfattribs={'color':1});s=io.StringIO();d.write(s)
  out=ezdxf.read(io.StringIO(colored_dxf(s.getvalue().encode()).decode()));line,insert=list(out.modelspace())
  self.assertFalse(line.dxf.hasattr('true_color'));self.assertEqual(out.layers.get('RED').dxf.true_color,0xFF3300);self.assertEqual(insert.dxf.color,1);self.assertEqual(next(iter(out.blocks['NATIVE'])).dxf.color,0)
 def test_preview_clarity_keeps_paths_and_original_colors(self):
  from app.services.cad.ls_colored_views import clear_svg_preview
  source=b'<svg><style>.a{stroke:#ff0000;stroke-width: 200;fill:none;}</style><path d="M 1 2 L 3 4"/></svg>'
  out=clear_svg_preview(source);self.assertIn(b'stroke:#ff0000;',out);self.assertIn(b'd="M 1 2 L 3 4"',out);self.assertIn(b'vector-effect: non-scaling-stroke',out)
 def test_style_copy_preserves_geometry_units_and_explicit_source_color(self):
  d=ezdxf.new();d.units=4;a=d.modelspace().add_line((1,2),(3,4));b=d.modelspace().add_circle((8,9),2,dxfattribs={'color':1});stream=io.StringIO();d.write(stream);raw=stream.getvalue().encode();out=ezdxf.read(io.StringIO(colored_dxf(raw).decode()))
  es=list(out.modelspace());self.assertEqual(out.units,4);self.assertEqual(len(es),2);self.assertEqual(tuple(es[0].dxf.start),(1,2,0));self.assertEqual(tuple(es[0].dxf.end),(3,4,0));self.assertEqual(es[0].dxf.true_color,0x40D9FF);self.assertEqual(es[1].dxf.color,1);self.assertEqual(es[1].dxf.radius,2);self.assertFalse(a.dxf.hasattr('true_color'))
 def test_native_windows_line_endings_keep_entities_and_units(self):
  d=ezdxf.new();d.units=4;d.modelspace().add_line((0,0),(5,6));s=io.StringIO();d.write(s)
  native=s.getvalue().replace('\n','\r\n').encode();out=ezdxf.read(io.StringIO(colored_dxf(native).decode(),newline=None))
  self.assertEqual(out.units,4);self.assertEqual(len(out.modelspace()),1)

class DeviceBlockExport(unittest.TestCase):
 def test_single_click_block_keeps_source_entities_and_attributes(self):
  from app.services.cad.device_block_export import single_device_block
  d=ezdxf.new();d.units=4;d.layers.new('ORIGINAL',dxfattribs={'color':3});line=d.modelspace().add_line((1,2),(4,6),dxfattribs={'layer':'ORIGINAL','color':1,'lineweight':35});stream=io.StringIO();d.write(stream)
  exported=ezdxf.read(io.StringIO(single_device_block(stream.getvalue().encode(),'DEVICE').decode()))
  model=list(exported.modelspace());self.assertEqual(len(model),1);self.assertEqual(model[0].dxftype(),'INSERT');self.assertEqual(exported.units,4)
  entities=list(exported.blocks[model[0].dxf.name]);self.assertEqual(len(entities),1);e=entities[0];self.assertEqual(tuple(e.dxf.start),(1,2,0));self.assertEqual(tuple(e.dxf.end),(4,6,0));self.assertEqual(e.dxf.layer,'ORIGINAL');self.assertEqual(e.dxf.color,1);self.assertEqual(e.dxf.lineweight,35)
 def test_supplier_visibility_grip_is_not_hidden_by_an_outer_block(self):
  from app.services.cad.device_block_export import native_visibility_insert,single_device_block,prepared_device_block
  source=Path('data/CatalogTB/LS/ThietBi/MC_35/CadDon/D02_cluster2-V004/ban_ve.dxf')
  if not source.is_file():self.skipTest('Native LS integration fixture unavailable')
  raw=source.read_bytes();doc=ezdxf.read(io.StringIO(raw.decode('utf-8-sig'),newline=None))
  self.assertTrue(native_visibility_insert(doc))
  self.assertEqual(single_device_block(raw,'OUTER'),raw)
  self.assertEqual(prepared_device_block(raw,'OUTER'),raw)
 def test_prepared_export_reuses_only_matching_source_and_output_hashes(self):
  from app.services.cad import device_block_export as module
  doc=ezdxf.new();doc.units=4;doc.modelspace().add_line((0,0),(10,20));stream=io.StringIO();doc.write(stream);source=stream.getvalue().encode()
  prepared=module.single_device_block(source,'PREPARED')
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);manifest=root/'manifest.json';export=root/'prepared.dxf';export.write_bytes(prepared)
   manifest.write_text(json.dumps({'items':[{'source_sha256':hashlib.sha256(source).hexdigest(),'export_path':'prepared.dxf','export_sha256':hashlib.sha256(prepared).hexdigest()}]}),encoding='utf8')
   with patch.object(module,'ROOT',root),patch.object(module,'MANIFEST',manifest):
    module._prepared_exports.cache_clear();self.assertEqual(module.prepared_device_block(source,'FALLBACK'),prepared)
    export.write_bytes(b'broken');fallback=module.prepared_device_block(source,'FALLBACK');read=ezdxf.read(io.StringIO(fallback.decode()));self.assertEqual(list(read.modelspace())[0].dxf.name,'FALLBACK')
   module._prepared_exports.cache_clear()

class RowCadLinks(unittest.TestCase):
 def setUp(self):
  self.row={'id':'row','brand':'LS Electric','sku':'MC-9a','price':10,'vat_status':'excluded'}
  self.device={'id':'TB-test','brand':'LS Electric','product_code':'MC-9a','display':'MC-9a','views':[{'id':'one'}],'catalog_references':{'options':[{'source_row_id':'row'}]}}
 def test_unknown_price_id_returns_no_detail(self):self.assertIsNone(price_row_detail('missing',[self.row],[]))
 @patch('app.services.price_row_cad_detail.customer_device')
 @patch('app.services.price_row_cad_detail.information_rows')
 def test_link_requires_explicit_row_same_brand_and_family_match(self,matches,public):
  matches.return_value=[{'match_scope':'source_family'}];from app.services.customer_equipment_information import public_view_id
  public.side_effect=lambda d:{'id':d['id'],'views':[{'id':public_view_id('one')}]}
  self.assertEqual(len(linked_cad_for_row(self.row,[self.device])),1)
  self.assertEqual(linked_cad_for_row({**self.row,'brand':'CHINT'},[self.device]),[])
  self.assertEqual(linked_cad_for_row({**self.row,'id':'other'},[self.device]),[])
  matches.return_value=[{'match_scope':'catalog_reference'}];self.assertEqual(linked_cad_for_row(self.row,[self.device]),[])
 @patch('app.services.price_row_cad_detail.customer_device')
 @patch('app.services.price_row_cad_detail.information_rows')
 def test_each_native_cad_variant_has_its_own_face_menu(self,matches,public):
  from app.services.customer_equipment_information import public_view_id
  device={**self.device,'views':[{'id':'front-a','cad_variant_id':'a'},{'id':'side-a','cad_variant_id':'a'},{'id':'front-b','cad_variant_id':'b'}]}
  matches.return_value=[{'match_scope':'source_family'}]
  public.return_value={'id':device['id'],'views':[{'id':public_view_id(v['id'])} for v in device['views']]}
  result=linked_cad_for_row(self.row,[device]);self.assertEqual(len(result),2)
  self.assertEqual(sorted(len(d['views']) for d in result),[1,2]);self.assertNotEqual(result[0]['selection_id'],result[1]['selection_id'])
  ids=[v['id'] for d in result for v in d['views']];self.assertEqual(len(ids),len(set(ids)))

class SourceViewModels(unittest.TestCase):
 def test_exact_native_model_does_not_expand_a_suffix_alias(self):
  from app.services.catalog_view_models import view_models
  d={'product_code':'MC-35 / MC-40 / MC-50 / MC-63'}
  self.assertEqual(view_models(d,{'source_info':{'Mã trên CAD':'MC-40'}}),['MC-40'])
  self.assertEqual(view_models(d,{'source_info':{'Mã trên CAD':'MC-40a'}}),[])
  self.assertEqual(view_models(d,{'source_info':{'Mã trên CAD':'MC-63AF/b'}}),[])
 def test_requested_model_is_validated_against_native_view_models(self):
  from app.services.catalog_publication_policy import selected_model_rows
  d={'product_code':'MC-35 / MC-40','views':[{'source_info':{'Mã trên CAD':'MC-40'}}]}
  rows=[{'sku':'MC-40 220V'},{'sku':'MC-35 220V'}]
  self.assertEqual(selected_model_rows(d,rows,'MC-40'),rows[:1])
  with self.assertRaises(ValueError):selected_model_rows(d,rows,'MC-40a')

if __name__=='__main__':unittest.main()
