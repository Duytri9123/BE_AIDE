"""Clean actual project sheets; preserve source enclosure name/material and mechanical geometry."""
import json,re,logging
from pathlib import Path
import ezdxf
from ezdxf import bbox,dynblkhelper,transform
from extract_project_helpers import ROOT,OUT,save,bounds,inside,render
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
BASE=ROOT/'BE_AIDE/tmp/project_cabinet_sources'
manifest=json.loads((BASE/'manifest.json').read_text(encoding='utf-8'))
SKIP={'TEXT','MTEXT','ATTRIB','ATTDEF','DIMENSION','LEADER','MULTILEADER','HATCH','WIPEOUT','VIEWPORT','POINT'}
ELEC=re.compile(r'MCCB|MCB|ACB|RCBO|RCCB|CONTACTOR|BKN|ABN|ABS\d|PLC|S7-|AMPERE|VOLTMET|METER|DONG HO|SELECTOR|BUTTON|ATS|CAU CHI|FUSE|S8FS|BIEN DONG|THANH DONG|BUSBAR|^MC[- _]?\d')
LAMP=re.compile(r'LIGHT|PILOT|DEN BAO|^DEN (DO|VANG|XANH)|^DCHINT')
MECHANICAL=re.compile(r'KHOA|LOCK|LATCH|MS406|TAI TREO|HINGE|BAN LE|^HL\d|^AB\d|^BASE|ISOLATE BKD|VTPK|DO NGANG|DO DOC|THANH U|^XA |PANEL')
def blockname(e):
 p=dynblkhelper.get_dynamic_block_definition(e);return p.name if p else e.dxf.name
def flatten(e,counts,depth=0):
 if depth>20:return
 t=e.dxftype()
 if t in SKIP:counts['annotations_or_hatches_removed']+=1;return
 if t=='INSERT':
  n=norm(blockname(e))
  if 'KHUNG' in n or 'BANG THONG SO' in n:return
  if ELEC.search(n) or LAMP.search(n):counts['electrical_blocks_removed']+=1;return
  if not MECHANICAL.search(n):
   counts['unknown_blocks_excluded']+=1;return
  try:
   for v in e.virtual_entities():yield from flatten(v,counts,depth+1)
  except Exception:counts['unresolved_blocks']+=1
 elif t=='LINE' and abs(e.dxf.start.x-e.dxf.end.x)>.01 and abs(e.dxf.start.y-e.dxf.end.y)>.01:
  counts['diagonal_marks_removed']+=1
 else:yield e.copy()
rows=json.loads((OUT/'catalog.json').read_text(encoding='utf-8')).get('shells',[]) if (OUT/'catalog.json').exists() else []
report=json.loads((OUT/'kiem_tra_nguon.json').read_text(encoding='utf-8')) if (OUT/'kiem_tra_nguon.json').exists() else []
done={r['source_id'] for r in report if 'source_id' in r}
for source in {r['id']:r for r in manifest if r['status']=='exported'}.values():
 if source['id'] in done:continue
 doc=ezdxf.readfile(ROOT/source['dxf']);model=doc.modelspace();frames=[];specs=[];cache=bbox.Cache()
 for e in model.query('INSERT'):
  attrs={a.dxf.tag:a.dxf.text for a in e.attribs};n=norm(blockname(e))
  if attrs.get('DRAWING_NAME') and 'KHUNG' in n:frames.append((e,attrs,bounds(e)))
  if 'MATERIAL' in attrs:specs.append((e,attrs))
 selected=0
 for frame,attrs,region in frames:
  if not region:continue
  matching=[v for v in specs if region[0]<=v[0].dxf.insert.x<=region[2] and region[1]<=v[0].dxf.insert.y<=region[3]]
  if not matching:continue
  spec=matching[0][1];name=attrs['DRAWING_NAME'];key=source['id']+'-'+frame.dxf.handle
  view_regions=[]
  for poly in model.query('LWPOLYLINE'):
   pts=list(poly.get_points('xy'))
   if not poly.closed or len(pts)!=4:continue
   xs={round(p[0],3) for p in pts};ys={round(p[1],3) for p in pts}
   if len(xs)!=2 or len(ys)!=2:continue
   rr=(min(xs),min(ys),max(xs),max(ys))
   if inside(rr,region) and 150<=rr[2]-rr[0]<=3000 and 150<=rr[3]-rr[1]<=3000:view_regions.append(rr)
  view_regions=[r for r in view_regions if not any(r!=q and inside(r,q) for q in view_regions)]
  if re.search(r'KHONG (DUNG|SU DUNG)|BAO LOI|LOI THIET KE|CANCEL',norm(name+' '+str(spec))):
   report.append({'id':key,'status':'excluded_source_note','name':name});continue
  folder=OUT/'Mau'/key;folder.mkdir(parents=True,exist_ok=True)
  clean=ezdxf.new('R2018');clean.units=4;counts={'annotations_or_hatches_removed':0,'electrical_blocks_removed':0,'diagonal_marks_removed':0,'unresolved_blocks':0,'unknown_blocks_excluded':0}
  for e in model:
   if e is frame or e.dxftype() in SKIP:continue
   if e.dxftype()=='INSERT':
    n=norm(blockname(e))
    if LAMP.search(n) or not MECHANICAL.search(n):
     continue
   try:box=bbox.extents([e],fast=True,cache=cache)
   except:continue
   if not box.has_data:continue
   b=(box.extmin.x,box.extmin.y,box.extmax.x,box.extmax.y)
   if not inside(b,region):continue
   if e.dxftype()!='INSERT':
    if any(inside(b,(v[0]+40,v[1]+40,v[2]-40,v[3]-40)) for v in view_regions):
     if not (e.dxftype()=='CIRCLE' and e.dxf.color in (1,2,3) and 7<=e.dxf.radius<=18):continue
   for entity in flatten(e,counts):
    try:clean.modelspace().add_entity(entity)
    except Exception:counts['unresolved_blocks']+=1
  if len(clean.modelspace())<20:continue
  ext=bbox.extents(clean.modelspace(),fast=True);transform.translate(clean.modelspace(),(-(ext.extmin.x+ext.extmax.x)/2,-(ext.extmin.y+ext.extmax.y)/2,0))
  clean.saveas(folder/'ban_ve.dxf');render(clean,folder/'xem_truoc.svg')
  info={'id':key,'name':name,'material_from_source':spec.get('MATERIAL'),'source_specification':spec,'source_title_attributes':attrs,'source_file':source['source_file'],'source_handle':frame.dxf.handle,'kind':'project','dimensions_mm':{'height':None,'width':None,'depth':None},'size_from_source':spec.get('SIZE'),'preview':f'Mau/{key}/xem_truoc.svg','source_dxf':f'Mau/{key}/ban_ve.dxf','original_dxf':source['dxf'],'drawing_labels':[],'cad_scope':'clean_source_sheet_multiple_views','auto_select':False,'verified_form':None,'cleaning':counts,'notes':['Giữ tên tủ và loại tôn nguyên văn trong JSON.','Giữ hình học cơ khí, khóa và đèn; bỏ chữ, kích thước, hatch, nét LINE chéo và block thiết bị điện đã nhận diện.','CAD còn nhiều mặt trên một tờ; cần đối chiếu trước tách mặt để chèn.']}
  save(folder/'thong_tin.json',info);rows.append(info);selected+=1
 report.append({'source':source['source_file'],'source_id':source['id'],'frames':len(frames),'selected':selected})
 save(OUT/'catalog.json',{'shells':rows,'separation_forms':[],'source_directory':'Tudien','rules':['Không lấy nguồn formtu cũ.','Gạch chéo/hatch là nét cần làm sạch, không tự coi là cả form bị hủy.','Tên tủ, loại tôn giữ nguyên từ thuộc tính nguồn.']});save(OUT/'kiem_tra_nguon.json',report)
 print(source['source_file'],selected,flush=True)
print('Published source sheets',len(rows))
