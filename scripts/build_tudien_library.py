"""Extract source evidence; never infer manufacturer geometry from current rating."""
import sys, json, hashlib, re, unicodedata, collections, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'tmp/tudien_deps'))
import ezdxf, openpyxl, xlrd, pdfplumber
from ezdxf.addons import Importer
from ezdxf import bbox
OUT=ROOT/'data/tudien'; SOURCE=ROOT.parent/'Tudien'
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,indent=2,default=str),encoding='utf8')
def norm(s):
 return unicodedata.normalize('NFKD',str(s).replace('Đ','D').replace('đ','d')).encode('ascii','ignore').decode().upper()
def slug(s): return re.sub(r'[^A-Za-z0-9_.-]+','_',norm(s)).strip('_.')[:80] or 'CHUA_XAC_DINH'
def hid(s): return hashlib.sha256(s.encode()).hexdigest()[:20]
def entity_fingerprint(entities):
 from ezdxf.lldxf.tagwriter import TagCollector
 result=[]
 for e in entities:
  tags=TagCollector.dxftags(e)
  result.append([(t.code,str(t.value)) for t in tags if t.code not in (5,105,330,360)])
 return json.dumps(result,sort_keys=True)
def brand(s):
 for b in ['Schneider','Mitsubishi','Siemens','Omron','Chint','LS','Sino','Shihlin','Hyundai','ABB','Idec','Autonics','Selec','Cadivi','Emic','Mikro','Samwha','Teco','Himel','Fuji']:
  if re.search(r'(?<![A-Z])'+b.upper()+r'(?![A-Z])',norm(s)): return b
 return 'chua_xac_dinh'
def category(s):
 t=norm(s)
 if re.search(r'ABN|ABS\d|ABS-\d',t):return 'MCCB'
 if re.search(r'LIGHT|BUTTON|SELECTOR SWITCH|EMERGENCY SWITCH|DEN (XANH|DO|VANG)|NN (XANH|DO)',t):return 'dieu_khien_cua'
 if re.search(r'CONG TO',t):return 'cong_to'
 if re.search(r'S7-12|SM1223',t):return 'PLC'
 if re.search(r'S8FS|NGUON 24|BO NGUON',t):return 'bo_nguon'
 for c in ['RCBO','RCCB','MCCB','MCB','ACB','ELCB','ATS','PLC','SPD']:
  if re.search(r'\b'+c+r'\b',t):return c
 for pat,c in [(r'CONTACTOR|KHOI DONG TU|MC-\d','contactor'),('RELAY|ROLE|RO LE','relay'),('BIEN TAN','bien_tan'),('BIEN DONG|CURRENT TRANSFORMER','bien_dong'),('TU BU|CAPACITOR','tu_bu'),('CAU CHI|FUSE','cau_chi'),('DONG HO|VOLTMETER|AMMETER','dong_ho'),('DEN BAO|NUT NHAN|CHUYEN MACH','dieu_khien_cua'),('BKN','MCB')]:
  if re.search(pat,t):return c
 return 'chua_phan_loai'
def accessory(s):
 t=norm(s)
 for pat,loc in [('BAN LE|BAN-LE|KHOA TU|TAY NAM|MS308|MS406|MS722|HL0|LOCKJAPAN|LIFTING|TAI TREO','ngoai_tu'),('MANG CAP|MANG NHUA|THANH RAY|DIN RAIL|DIN35|CAU DAU|TERMINAL|TEMINAL|THANH DONG|SU DO|SU KEP|TIEP DIA|PNE-BAR|DUCT|CTS ?[0-9]|TAM CHAN PHA','trong_tu'),('QUAT|LUOI LOC|GIOANG|OC VIT|BU LONG|BULONG|DAU COS|PHU KIEN|CABLE GLAND|O CAM|CAM 32|SCREW|RONDELLE|ECU|COS [0-9]|^NUT$','chua_xac_dinh')]:
  if re.search(pat,t):return loc
 return None
def text(e):
 try:
  if e.dxftype()=='MTEXT':return e.plain_text()
  if e.dxftype() in ('TEXT','ATTRIB','ATTDEF'):return e.dxf.text
 except Exception:pass
 return None
def bounds(es):
 try:
  b=bbox.extents(es,fast=True)
  if b.has_data:return [list(b.extmin),list(b.extmax)]
 except Exception:pass
 return None
def run():
 manifest=[]; products={}; geometries={}; sheets_count=0; rows_count=0; drawings=[]; errors=[]
 only=sys.argv[1] if len(sys.argv)>1 else None
 if only:
  load=lambda p:json.loads(p.read_text(encoding='utf8'))
  manifest=[m for m in load(OUT/'coverage.json') if m['id']!=only]
  products={p['id']:p for p in load(OUT/'models.json')};geometries={g['id']:g for g in load(OUT/'geometry_profiles.json')}
  drawings=[d for d in load(OUT/'form_tu/index.json') if d['id']!=only]
  old=load(OUT/'summary.json');sheets_count=old['sheets_read'];rows_count=old['nonempty_rows_read']
  errors=[e for e in load(OUT/'errors.json') if hashlib.sha256((SOURCE/e['file']).read_bytes()).hexdigest()[:16]!=only]
 for path in sorted(SOURCE.iterdir()):
  if not path.is_file():continue
  sha=hashlib.sha256(path.read_bytes()).hexdigest(); sid=sha[:16]; folder=OUT/'nguon'/sid
  if only and sid!=only:continue
  folder.mkdir(parents=True,exist_ok=True)
  entry={'id':sid,'source_file':path.name,'sha256':sha,'bytes':path.stat().st_size,'status':'read'};manifest.append(entry)
  try:
   ext=path.suffix.lower()
   if ext in ('.xlsx','.xls'):
    sheets=[]
    if ext=='.xlsx':
     w=openpyxl.load_workbook(path,data_only=False); values=openpyxl.load_workbook(path,data_only=True)
     for s in w:
      rows=[]
      for row in s:
       cells=[{'column':c.column,'value':c.value,'cached':values[s.title].cell(c.row,c.column).value} for c in row if c.value is not None]
       if cells:rows.append({'row':row[0].row,'cells':cells})
      sheets.append({'sheet':s.title,'state':s.sheet_state,'merged_ranges':[str(x) for x in s.merged_cells.ranges],'rows':rows})
    else:
     w=xlrd.open_workbook(path)
     for s in w.sheets():
      sheets.append({'sheet':s.name,'rows':[{'row':r+1,'cells':[{'column':c+1,'value':s.cell_value(r,c)} for c in range(s.ncols) if s.cell_value(r,c)!='']} for r in range(s.nrows) if any(s.row_values(r))]})
    save(folder/'workbook.json',sheets);entry['sheets']=len(sheets);sheets_count+=len(sheets)
    for s in sheets:
     headers={}; cabinet=None
     for row in s['rows']:
      rows_count+=1; cells=row['cells']; joined=' | '.join(str(c.get('cached',c['value']) if not str(c['value']).startswith('=') else c.get('cached','')) for c in cells)
      for c in cells:
       n=norm(c['value']).strip()
       if n in ['MA HANG','MA SAN PHAM','MODEL','MA HIEU','MA THIET BI']:headers['model']=c['column']
       if 'HANG SX' in n or n in ['XUAT XU','HANG SAN XUAT','HANG']:headers['brand']=c['column']
      if re.search(r'\bTU\b',norm(joined)) and ('IP' in joined or re.search(r'\d{3,4}\s*[xX*]',joined)):cabinet=joined
      cat=category(joined);acc=accessory(joined)
      if cat=='chua_phan_loai' and not acc:continue
      vals={c['column']:c.get('cached',c['value']) for c in cells}; model=str(vals.get(headers.get('model'), '') or '').strip(); b=brand(str(vals.get(headers.get('brand'),'') or joined))
      poles=re.search(r'\b([1-4]P(?:\s*\+\s*N)?)\b',joined,re.I);rating=re.findall(r'\b\d+(?:[.,]\d+)?\s*(?:mA|kA|A|kW|kVAr)\b',joined,re.I)
      # Row-derived variants stay distinct when order code does not encode rating.
      key=hid('|'.join([cat,b,model,joined])); ref={'source_id':sid,'sheet':s['sheet'],'row':row['row'],'cabinet_context':cabinet}
      if key not in products:products[key]={'id':key,'category':cat,'manufacturer':b,'model_from_source':model or None,'description_raw':joined,'poles':poles.group(1) if poles else None,'ratings_raw':rating,'geometry_profile_id':None,'geometry_status':'unverified','accessory_location':acc,'sources':[]}
      products[key]['sources'].append(ref)
   elif ext=='.dwg':
    dxf=folder/'drawing.dxf'
    if not dxf.exists():raise RuntimeError('DWG conversion missing')
    doc=ezdxf.readfile(dxf); texts=[]; inserts=[]; dims=[]; blocks=[]
    for layout in doc.layouts:
     for e in layout:
      t=text(e)
      if t:texts.append({'handle':e.dxf.handle,'layout':layout.name,'text':t,'position':list(e.dxf.get('insert',(0,0,0)))})
      if e.dxftype()=='DIMENSION':
       try:measure=e.get_measurement()
       except Exception:measure=None
       dims.append({'handle':e.dxf.handle,'layout':layout.name,'measurement':measure,'text_override':e.dxf.get('text'),'position':list(e.dxf.get('defpoint',(0,0,0)))})
      if e.dxftype()=='INSERT':inserts.append({'handle':e.dxf.handle,'layout':layout.name,'block':e.dxf.name,'position':list(e.dxf.insert),'rotation':e.dxf.get('rotation',0),'scale':[e.dxf.get(x,1) for x in ['xscale','yscale','zscale']],'attributes':[{'tag':a.dxf.tag,'text':a.dxf.text} for a in e.attribs]})
    for block in doc.blocks:
     if block.name.startswith('*Model_Space') or block.name.startswith('*Paper_Space'):continue
     bt=[text(e) for e in block if text(e)]; summary={'name':block.name,'entities':len(block),'texts':bt}
     blocks.append(summary)
     if not len(block) or block.name.startswith('*D'):continue
     # Export all blocks, including anonymous ones, to avoid silently losing devices.
     target=ezdxf.new(doc.dxfversion); imp=Importer(doc,target);imp.import_block(block.name);imp.finalize(); target.modelspace().add_blockref(block.name,(0,0,0))
     payload=[]
     for e in block:
      payload.append([e.dxftype(),{k:str(v) for k,v in e.dxf.all_existing_dxf_attribs().items() if k not in ['handle','owner']}])
     gid=hid(entity_fingerprint(block)+sid+block.name);summary['geometry_id']=gid
     if gid not in geometries:
      p=OUT/'geometry'/gid/'cad.dxf';p.parent.mkdir(parents=True,exist_ok=True);target.saveas(p)
      label=block.name+' '+' '.join(bt);loc=accessory(label);cat=category(label);b=brand(label)
      geometries[gid]={'id':gid,'cad_views':{'source_view':str(p.relative_to(OUT)).replace('\\','/')},'block_names':[],'bounds_drawing_units':bounds(target.modelspace()),'units_code':doc.units,'category':cat,'manufacturer':b,'accessory_location':loc,'view_status':'source_block_not_certified_physical_envelope','sources':[]}
     g=geometries[gid];g['block_names'].append(block.name) if block.name not in g['block_names'] else None;g['sources'].append({'source_id':sid,'block':block.name})
    save(folder/'cad_inventory.json',{'units_code':doc.units,'layouts':[l.name for l in doc.layouts],'entity_counts':dict(collections.Counter(e.dxftype() for e in doc.modelspace())),'texts':texts,'dimensions':dims,'inserts':inserts,'blocks':blocks})
    # Keep complete form drawing and all placement evidence, including exploded geometry.
    form={'id':sid,'source_file':path.name,'cad_file':str(dxf.relative_to(OUT)).replace('\\','/'),'units_code':doc.units,'placements':inserts,'dimensions':dims,'labels':texts,'status':'source_project_multiple_forms','placement_policy':'Reuse source coordinates and scale only after selecting matching cabinet/view; no generic clearance inferred.'}
    save(OUT/'form_tu'/sid/'form.json',form);drawings.append({'id':sid,'file':path.name,'blocks':len(blocks),'placements':len(inserts),'texts':len(texts)})
   elif ext=='.pdf':
    pages=[]
    with pdfplumber.open(path) as pdf:
     for i,p in enumerate(pdf.pages):
      pages.append({'page':i+1,'text':p.extract_text(layout=True),'words':p.extract_words(),'width':p.width,'height':p.height});p.to_image(resolution=110).save(str(folder/f'page_{i+1}.png'))
    save(folder/'pdf.json',pages);entry['pages']=len(pages)
   elif ext in ('.jpg','.png','.jpeg'):
    entry['status']='pending_visual_review';entry['image_path']=str(path)
   else:entry['status']='unsupported'
  except Exception as exc:
   entry['status']='error';entry['error']=str(exc);errors.append({'file':path.name,'error':traceback.format_exc()})
  save(OUT/'coverage.json',manifest);print(path.name,entry['status'],flush=True)
 for g in geometries.values():
  loc=g['accessory_location']; base=OUT/'phu_kien'/loc if loc else OUT/'thiet_bi'/g['category']/g['manufacturer']
  save(base/('block_'+slug(g['block_names'][0])+'_'+g['id'][:8])/'geometry.json',g)
 for p in products.values():
  base=OUT/'phu_kien'/p['accessory_location'] if p['accessory_location'] else OUT/'thiet_bi'/p['category']/p['manufacturer']
  save(base/slug(p['model_from_source'] or 'chua_co_model')/'models'/f"{p['id']}.json",p)
 for loc in ['trong_tu','ngoai_tu','chua_xac_dinh']:(OUT/'phu_kien'/loc).mkdir(parents=True,exist_ok=True)
 save(OUT/'models.json',list(products.values()));save(OUT/'geometry_profiles.json',list(geometries.values()));save(OUT/'form_tu/index.json',drawings);save(OUT/'errors.json',errors)
 save(OUT/'summary.json',{'source_files':len(manifest),'status_counts':dict(collections.Counter(e['status'] for e in manifest)),'sheets_read':sheets_count,'nonempty_rows_read':rows_count,'drawing_projects':len(drawings),'geometry_profiles':len(geometries),'product_variants':len(products),'errors':len(errors)})
if __name__=='__main__':run()
