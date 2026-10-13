"""Rebuild shell-only forms from source, retaining source colors and dimensions."""
import json,re,logging,os
import ezdxf
from ezdxf import bbox,dynblkhelper
from ezdxf.addons import Importer
from ezdxf.addons.drawing import Frontend,RenderContext
from ezdxf.addons.drawing.config import Configuration
from ezdxf.addons.drawing.svg import SVGBackend
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
from extract_project_helpers import ROOT,OUT,inside,save
from project_form_rejections import norm
logging.getLogger('ezdxf').setLevel(logging.ERROR)
HARDWARE=re.compile(r'KHOA|LOCK|LATCH|\bMS(?:722|303|308|325|406)|AB301|^HL\d|BAN LE|HINGE|TAI TREO')
def box(e):
 try:
  b=bbox.extents([e],fast=True);return (b.extmin.x,b.extmin.y,b.extmax.x,b.extmax.y) if b.has_data else None
 except:return None
def name(e):
 p=dynblkhelper.get_dynamic_block_definition(e);return p.name if p else e.dxf.name
def render(doc,path):
 backend=SVGBackend();Frontend(RenderContext(doc),backend,config=Configuration()).draw_layout(doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
 svg=backend.get_string(Page(0,0));svg=re.sub(r'stroke-width: ([0-9.]+)',lambda m:'stroke-width: '+str(max(1000,float(m[1]))),svg);path.write_text(svg,encoding='utf-8')
d=json.loads((OUT/'catalog.json').read_text(encoding='utf-8'));groups={}
for row in d['shells']:groups.setdefault(row['original_dxf'],[]).append(row)
report=[]
for path,rows in groups.items():
 if os.environ.get('FORM_REPAIR_ONLY') and not any(r.get('mechanical_cleaning',{}).get('needs_review') for r in rows):continue
 source=ezdxf.readfile(ROOT/path);entities=[(e,box(e)) for e in source.modelspace() if e.dxftype() in ('LINE','LWPOLYLINE','POLYLINE','ARC','ELLIPSE','SPLINE','DIMENSION','TEXT','MTEXT') or (e.dxftype()=='INSERT' and HARDWARE.search(norm(name(e))))]
 for row in rows:
  if os.environ.get('FORM_REPAIR_ONLY') and not row.get('mechanical_cleaning',{}).get('needs_review'):continue
  if row.get('mechanical_cleaning',{}).get('style_revision')==3 and not os.environ.get('FORM_REPAIR_ONLY'):
   report.append({'id':row['id'],**row['mechanical_cleaning']});continue
  folder=OUT/'Mau'/row['id'];analysis=json.loads((folder/'bo_tri_goc.json').read_text(encoding='utf-8'));sheet=analysis['source_sheet_bounds'];regions=[]
  for e,b in entities:
   if e.dxftype()!='LWPOLYLINE' or not b or not inside(b,sheet):continue
   pts=list(e.get_points('xy'))
   if b[2]-b[0]>=40 and b[3]-b[1]>=80 and len(pts)>=4:regions.append(b)
  offset=row['cleaning'].get('accessory_alignment_translation')
  labels=[(e.dxf.insert.x,e.dxf.insert.y) for f in row.get('faces',[]) if (e:=source.entitydb.get(f.get('source_label_handle'))) is not None]
  regions.extend(tuple(f['source_bounds']) for f in row.get('faces',[]) if f.get('source_bounds'))
  regions=[r for r in regions if any(r[0]-150<=x<=r[2]+150 and r[1]-300<=y<=r[3]+400 for x,y in labels)]
  regions=list({tuple(round(v,1) for v in r):r for r in regions}.values())
  regions=[r for r in regions if not any(r!=q and inside(r,q) for q in regions)]
  dims=row.get('dimensions_mm') or {};height=dims.get('height');depth=dims.get('depth');vertical=[r for r in regions if r[3]-r[1]>400]
  if vertical:
   top=max(r[3] for r in vertical);bottom=min(r[1] for r in vertical)
   if height and bottom>top-height and height-(top-bottom)<height*.3:bottom=top-height
   regions=[(r[0],min(r[1],bottom),r[2],r[3]) if r in vertical else r for r in regions]
   if depth:
    for f,(x,y) in zip(row.get('faces',[]),labels):
     if 'SIDE' in f['source_label'].upper() and not any(r[0]-20<=x<=r[2]+20 and r[3]-r[1]>400 for r in regions):regions.append((x-depth/2,bottom,x+depth/2,top))
  target=ezdxf.new('R2018');target.units=4;imp=Importer(source,target);selected=[];dimensions=0;hardware=0
  for e,b in entities:
   if not b or not inside(b,sheet):continue
   t=e.dxftype();keep=False
   if t=='INSERT':keep=bool(HARDWARE.search(norm(name(e))));hardware+=int(keep)
   elif t=='DIMENSION':keep=any(inside(b,(r[0]-180,r[1]-180,r[2]+180,r[3]+180)) for r in regions);dimensions+=int(keep)
   elif t in ('TEXT','MTEXT'):
    text=e.dxf.text if t=='TEXT' else e.plain_text()
    keep=any(norm(text).strip()==norm(f['source_label']).strip() for f in row.get('faces',[]))
   elif t in ('LINE','LWPOLYLINE','POLYLINE','ARC','ELLIPSE','SPLINE'):
    enclosing=[r for r in regions if inside(b,(r[0]-1,r[1]-1,r[2]+1,r[3]+1))]
    if enclosing:
     r=min(enclosing,key=lambda q:(q[2]-q[0])*(q[3]-q[1]));inset=min(12,(r[2]-r[0])*.15)
     interior=inside(b,(r[0]+inset,r[1]+inset,r[2]-inset,r[3]-inset))
     broad=(b[2]-b[0]>.8*(r[2]-r[0]) and b[3]-b[1]>.8*(r[3]-r[1]))
     bottom=any(r[0]-150<=x<=r[2]+150 and r[1]-180<=y<=r[1] for x,y in labels) and r[2]-r[0]>r[3]-r[1]
     keep=not interior or broad or bottom
   if keep:selected.append(e)
  imp.import_entities(selected);imp.finalize()
  # Equipment and support blocks never enter the output. Source locks/hinges remain intact.
  target.saveas(folder/'ban_ve.dxf');target.saveas(folder/'ban_ve_co_khung_goc.dxf')
  try:render(target,folder/'xem_truoc.svg')
  except ValueError:
   (folder/'xem_truoc.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400"><text x="30" y="60">Form requires source boundary review</text></svg>',encoding='utf-8')
  row['cad_scope']='source_shell_views_with_original_dimensions_and_colors'
  row['mechanical_cleaning']={'style_revision':3,'source_rebuild':True,'removed_equipment_holes_lamps_copper_supports':True,'retained_source_colors':True,'retained_source_dimensions':dimensions,'retained_hardware_blocks':hardware,'source_regions':len(regions),'needs_review':not regions,'selection_basis':'source_face_boundary_filter_and_named_lock_hinge_blocks_requires_visual_review'}
  row['notes']=['Vỏ và các mặt theo nguồn; bỏ thiết bị, lỗ thiết bị, đèn, đồng và đố.','Giữ màu nét, kích thước, khóa và bản lề nguồn; bỏ thông tin dự án/khách hàng/logo.','Bố trí thiết bị và đồng cũ chỉ dùng tham chiếu. Cần đối chiếu cơ khí trước khi dùng.'];row['auto_select']=False
  save(folder/'thong_tin.json',row);report.append({'id':row['id'],**row['mechanical_cleaning']})
 save(OUT/'catalog.json',d);save(OUT/'kiem_tra_form_co_khi.json',report);print('Source shell style',len(report),flush=True)
print('Done',len(report))
