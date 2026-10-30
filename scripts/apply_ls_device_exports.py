"""Audit and prepare selectable LS exports while preserving the native catalog."""
import collections,hashlib,io,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ezdxf
from app.services.cad.device_block_export import single_device_block
from app.services.cad.ls_colored_views import clear_svg_preview
from app.services.cad.ls_view_coverage import view_coverage,is_ls
from app.services.catalog_publication_policy import public_device_allowed
from app.services.catalog_view_health import displayable

ROOT=Path(__file__).resolve().parents[1];CAT=ROOT/'data/CatalogTB';OUT=ROOT/'docs/ls-all-cad-2026-10-24';EXPORT=CAT/'_agent_index/ls_device_exports'

def signature(entity):
 values={k:v for k,v in entity.dxf.all_existing_dxf_attribs().items() if k not in ('owner','handle')}
 return entity.dxftype(),json.dumps(values,sort_keys=True,default=str)

def main():
 OUT.mkdir(exist_ok=True);EXPORT.mkdir(exist_ok=True)
 snapshot=json.loads((CAT/'_agent_index/browser_display_v5.json').read_text(encoding='utf8'));devices=[d for d in snapshot['items'] if is_ls(d.get('brand')) and public_device_allowed(d)]
 measurements=json.loads((ROOT/'app/data/catalog_customer_cad_measurements.json').read_text(encoding='utf8'))['views']
 verified=[];failed=[];profiles=[]
 for device in devices:
  groups=collections.defaultdict(list)
  for view in device['views']:
   if not displayable(view):continue
   groups[view.get('cad_variant_id') or device['id']].append(view)
   try:
    entry=measurements.get(device['id']+':'+view['id']);assert entry,'Missing reviewed measurement source'
    path=(CAT/entry['path']).resolve();assert path.is_relative_to(CAT.resolve()) and path.is_file()
    original=path.read_bytes();before_hash=hashlib.sha256(original).hexdigest();assert before_hash==entry['sha256']
    native=ezdxf.read(io.StringIO(original.decode('utf-8-sig'),newline=None));audit=native.audit();assert native.units==4 and len(native.modelspace()) and not audit.errors and not audit.fixes
    signatures=collections.Counter(signature(e) for e in native.modelspace())
    name=device['id']+'-'+hashlib.sha256(view['id'].encode()).hexdigest()[:16]
    output=single_device_block(original,name);doc=ezdxf.read(io.StringIO(output.decode('utf8')));assert doc.units==4
    refs=list(doc.modelspace());assert len(refs)==1 and refs[0].dxftype()=='INSERT'
    assert collections.Counter(signature(e) for e in doc.blocks[refs[0].dxf.name])==signatures,'Source entities changed'
    assert not doc.audit().errors
    preview=path.with_name('xem_truoc.svg');svg=preview.read_bytes();clear=clear_svg_preview(svg)
    from xml.etree import ElementTree as ET
    one,two=ET.fromstring(svg),ET.fromstring(clear)
    geometry=lambda tree:[(e.tag,e.get('d'),e.get('points'),e.get('transform')) for e in tree.iter() if e.tag.rsplit('}',1)[-1] in ('path','polyline','line','circle','ellipse','polygon')]
    assert geometry(one)==geometry(two),'Preview geometry changed'
    (EXPORT/(name+'.dxf')).write_bytes(output);(EXPORT/(name+'.svg')).write_bytes(clear)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before_hash
    verified.append({'catalog_id':device['id'],'view_id':view['id'],'variant_id':view.get('cad_variant_id'),'label':view['face'],'source_path':path.relative_to(CAT.resolve()).as_posix(),'source_sha256':before_hash,'entity_count':sum(signatures.values()),'export_path':(EXPORT/(name+'.dxf')).relative_to(CAT).as_posix(),'export_sha256':hashlib.sha256(output).hexdigest(),'original_colors_layers_lineweights_preserved':True,'one_selectable_block':True,'units_mm':True})
   except Exception as exc:failed.append({'catalog_id':device['id'],'view_id':view['id'],'reason':str(exc)})
  profiles.append({'id':device['id'],'model':device.get('product_code'),'variants':[{'variant_id':key,**view_coverage(views)} for key,views in groups.items()]})
  print(f'LS {len(profiles)}/{len(devices)} profiles; {len(verified)} exports; {len(failed)} held',flush=True)
 raw_inventory=[]
 for path in CAT.rglob('thong_tin_thiet_bi.json'):
  data=json.loads(path.read_text(encoding='utf-8-sig'))
  if path.relative_to(CAT).parts[0]!='LS' and not is_ls(data.get('hang_xac_nhan')):continue
  cid='TB-'+hashlib.sha1(path.relative_to(CAT).as_posix().encode()).hexdigest()[:16]
  raw_inventory.append({'profile':path.relative_to(CAT).as_posix(),'id':cid,'browser_hidden':data.get('browser_hidden',False),'published_directly':cid in {d['id'] for d in devices},'declared_faces':len(data.get('cad_don') or [])})
 (OUT/'all-ls-profile-inventory.json').write_text(json.dumps(raw_inventory,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 result={'profiles_checked':len(profiles),'exports_verified':len(verified),'held':failed,'native_files_unchanged':True,'static_block_export':True,'autocad_dynamic_visibility_verified':False,'profiles':profiles,'items':verified}
 (OUT/'all-ls-cad-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 (EXPORT/'manifest.json').write_text(json.dumps({'items':verified},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('profiles','items','held')},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
