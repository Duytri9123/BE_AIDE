"""Build frame-level layouts and conservative SKU/geometry candidate links."""
from build_tudien_library import *
import os, logging, math
logging.getLogger('ezdxf').setLevel(logging.ERROR)
def load(p):return json.loads(p.read_text(encoding='utf8'))
def inside(x,b):return b[0][0]<=x[0]<=b[1][0] and b[0][1]<=x[1]<=b[1][1]
def link(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():os.link(src,dst)
def run():
 profiles=load(OUT/'geometry_profiles.json');models=load(OUT/'models.json');catalog=[];form_index=[]
 families={}
 image_evidence=load(Path(__file__).with_name('tudien_image_evidence.json'));save(OUT/'nguon'/image_evidence['source_id']/'image_transcription.json',image_evidence)
 coverage=load(OUT/'coverage.json')
 for ev in load(Path(__file__).with_name('tudien_pdf_evidence.json')):
  src=next(c for c in coverage if ev['source_filename_contains'] in c['source_file'] and c['source_file'].endswith('.pdf'))
  ev['source_id']=src['id'];save(OUT/'nguon'/src['id']/'visual_evidence.json',ev)
  save(OUT/'form_tu'/src['id']/'schematic.json',ev)
 for c in coverage:
  if c['id']==image_evidence['source_id']:c['status']='read';c['method']='visual_transcription'
 save(OUT/'coverage.json',coverage)
 for g in profiles:
  label=' '.join(g['block_names']);g['category']=category(label);g['accessory_location']=accessory(label)
  g['classification_method']='block_name_keyword';g['mounting_location_status']='inferred_from_part_name' if g['accessory_location'] else None
  if re.search(r'KHUNG|BANG THONG SO|STANDARD ISO|_OPEN|LOGO|NAMELOAD|MARKING',norm(label)):
   g['asset_role']='drawing_annotation'
  elif g['accessory_location']:g['asset_role']='accessory_candidate'
  elif g['category']!='chua_phan_loai':g['asset_role']='device_candidate'
  else:g['asset_role']='unclassified_block'
  base=OUT/'phu_kien'/g['accessory_location'] if g['accessory_location'] else OUT/'thiet_bi'/g['category']/g['manufacturer']
  dest=base/('block_'+slug(g['block_names'][0])+'_'+g['id'][:8]);link(OUT/g['cad_views']['source_view'],dest/'cad/source_view.dxf');save(dest/'geometry.json',g)
  if g.get('visible_labels') is not None and g['asset_role']=='device_candidate':
   series=re.sub(r'(?i)(?:^|[- _])(LS|CHINT|SINO|SCHNEIDER|IDEC)(?:$|[- _])',' ',g['block_names'][0]).strip(' -_')
   poles=g.get('poles_from_visible_label');family=slug(series+('_'+poles if poles else '_chua_ro_so_cuc'));fk=g['category']+'/'+g['manufacturer']+'/'+family
   if fk not in families:families[fk]={'category':g['category'],'manufacturer':g['manufacturer'],'series_from_block_name':series,'poles':poles,'geometry_profile_ids':[],'sku_ids':[],'status':'source_geometry_family_sku_compatibility_not_verified'}
   families[fk]['geometry_profile_ids'].append(g['id']);link(OUT/g['cad_views']['source_view'],OUT/'thiet_bi'/fk/'cad'/f"{g['id']}.dxf")
 for m in models:
  model=m['model_from_source'];m['candidate_geometry_profile_ids']=[]
  if model and len(model)>2:
   token=norm(model)
   m['candidate_geometry_profile_ids']=[g['id'] for g in profiles if g['manufacturer'] in (m['manufacturer'],'chua_xac_dinh') and any(re.search(r'(?<![A-Z0-9])'+re.escape(token)+r'(?![A-Z0-9])',norm(n)) for n in g['block_names'])]
  # This key is a grouping proposal, never an assertion of equal dimensions.
  m['proposed_family_key']='|'.join([m['manufacturer'],model or 'unknown',m['poles'] or 'unknown'])
  m['geometry_status']='candidate_requires_dimension_and_view_verification' if m['candidate_geometry_profile_ids'] else 'no_verified_mapping'
  base=OUT/'phu_kien'/m['accessory_location'] if m['accessory_location'] else OUT/'thiet_bi'/m['category']/m['manufacturer']
  dest=base/slug(model or 'chua_co_model');save(dest/'models'/f"{m['id']}.json",m)
  for gid in m['candidate_geometry_profile_ids']:link(OUT/'geometry'/gid/'cad.dxf',dest/'cad_can_doi_chieu'/f'{gid}.dxf')
 save(OUT/'models.json',models);save(OUT/'geometry_profiles.json',profiles)
 # A quotation line is evidence, not automatically a unique commercial SKU.
 sku={};bom=[]
 ole_refs={}
 if (OUT/'embedded_ole.json').exists():
  for r in load(OUT/'embedded_ole.json'):ole_refs.setdefault(r['id'],[]).append({'source_id':r['source_id'],'ole_handle':r['handle']})
 for p in list((OUT/'nguon').glob('*/workbook.json'))+list((OUT/'nguon/embedded_ole').glob('*.json')):
  if p.stem.endswith('_visual'):continue
  for sh in load(p):
   cols={};context=None
   for row in sh['rows']:
    vals={c['column']:c.get('cached',c['value']) for c in row['cells']}
    for c in row['cells']:
     t=norm(c['value']).strip()
     if t in ['MO TA CHI TIET','TEN THIET BI','TEN VAT TU','TEN SAN PHAM','MO TA','DIEN GIAI','NOI DUNG','TEN HANG HOA']:cols['description']=c['column']
     if t in ['MA HANG','MA SAN PHAM','MA HIEU','MODEL']:cols['model']=c['column']
     if 'HANG SX' in t or t in ['XUAT XU','HANG']:cols['brand']=c['column']
     if t in ['S.LUONG','SO LUONG','SL','S.L']:cols['quantity']=c['column']
     if t in ['DON VI','DVT','D.VI']:cols['unit']=c['column']
    desc=str(vals.get(cols.get('description'),'') or '').strip()
    if not desc:continue
    if norm(desc) in ['MO TA CHI TIET','TEN THIET BI','MO TA','DIEN GIAI','TEN VAT TU','TEN SAN PHAM']:continue
    model=str(vals.get(cols.get('model'),'') or '').strip();maker=brand(str(vals.get(cols.get('brand'),'') or ''))
    q=vals.get(cols.get('quantity'));unit=vals.get(cols.get('unit'))
    refs=ole_refs.get(p.stem,[]) if p.parent.name=='embedded_ole' else []
    line={'source_id':refs[0]['source_id'] if refs else p.parent.name,'embedded_ole_id':p.stem if refs else None,'embedded_source_references':refs,'sheet':sh['sheet'],'row':row['row'],'description':desc,'model':model or None,'manufacturer':maker,'origin_or_brand_raw':vals.get(cols.get('brand')),'quantity':q,'unit':unit,'category':category(desc),'accessory_location':accessory(desc)}
    bom.append(line)
    if line['category']=='chua_phan_loai' and not line['accessory_location'] and not model:continue
    if not model and not unit:continue
    key=hid('|'.join([maker,model,norm(desc)]))
    if key not in sku:sku[key]={'id':key,'model':model or None,'manufacturer':maker,'description':desc,'category':line['category'],'accessory_location':line['accessory_location'],'geometry_profile_id':None,'geometry_status':'not_verified','sources':[]}
    sku[key]['sources'].append(line)
 for i,line in enumerate(image_evidence['items']):
  if line.get('model'):
   key=hid('image|'+line['model']);sku[key]={'id':key,'model':line['model'],'manufacturer':'chua_xac_dinh','description':line['description'],'category':category(line['description']),'geometry_profile_id':None,'geometry_status':'not_verified','sources':[{'source_id':image_evidence['source_id'],'item':i+1}]}
 save(OUT/'bom_lines.json',bom);save(OUT/'sku_registry.json',list(sku.values()))
 for s in sku.values():
  pp=re.search(r'\b[1-4]P(?:\s*\+\s*N)?\b',s['description'],re.I);s['poles']=pp.group(0) if pp else None
  s['candidate_geometry_profile_ids']=[]
  for fk,f in families.items():
   token=re.sub('[^A-Z0-9]','',norm(f['series_from_block_name']));description=re.sub('[^A-Z0-9]','',norm((s['model'] or '')+' '+s['description']))
   if len(token)>=3 and token in description and s['manufacturer']==f['manufacturer'] and s['poles'] and s['poles']==f['poles']:
    s['candidate_geometry_profile_ids'].extend(f['geometry_profile_ids']);f['sku_ids'].append(s['id'])
    save(OUT/'thiet_bi'/fk/'sku'/f"{s['id']}.json",s)
  base=OUT/'phu_kien'/s['accessory_location'] if s.get('accessory_location') else OUT/'thiet_bi'/s['category']/s['manufacturer']
  save(base/slug(s['model'] or 'chua_co_model')/'sku'/f"{s['id']}.json",s)
 save(OUT/'sku_registry.json',list(sku.values()));save(OUT/'family_index.json',families)
 for fk,f in families.items():save(OUT/'thiet_bi'/fk/'family.json',f)
 for item in load(OUT/'form_tu/index.json'):
  sid=item['id'];folder=OUT/'form_tu'/sid;inv=load(OUT/'nguon'/sid/'cad_inventory.json');doc=ezdxf.readfile(OUT/'nguon'/sid/'drawing.dxf');frames=[]
  dyn={x['handle']:x for x in load(OUT/'nguon'/sid/'dynamic_instances.json')}
  for placement in inv['inserts']:
   if placement['handle'] in dyn:
    placement.update(dyn[placement['handle']]);placement['placement_anchor']=placement['visible_world_center']
   else:
    ent=doc.entitydb.get(placement['handle']);eb=bounds([ent]) if ent is not None else None
    placement['placement_anchor']=[(eb[0][i]+eb[1][i])/2 for i in range(3)] if eb else placement['position']
  for e in doc.modelspace().query('INSERT'):
   if 'KHUNG' in norm(e.dxf.name) or any(a.dxf.tag=='DRAWING_NAME' for a in e.attribs):
    b=dyn[e.dxf.handle]['visible_world_bounds'] if e.dxf.handle in dyn else bounds([e])
    if b:frames.append((e,b))
  for e,b in frames:
   fid=e.dxf.handle;name=next((a.dxf.text for a in e.attribs if a.dxf.tag=='DRAWING_NAME'),e.dxf.name)
   labels=[t for t in inv['texts'] if t['layout']=='Model' and inside(t['position'],b)]
   placements=[dict(t) for t in inv['inserts'] if t['layout']=='Model' and inside(t['placement_anchor'],b) and t['handle']!=fid and 'KHUNG' not in norm(t['block'])]
   for p in placements:p['visible_center_relative_to_frame']=[p['placement_anchor'][0]-b[0][0],p['placement_anchor'][1]-b[0][1],p['placement_anchor'][2]]
   dimensions=[d for d in inv['dimensions'] if d['layout']=='Model' and inside(d['position'],b)]
   views=[t for t in labels if re.search('VIEW|MAT BANG|MAT TRUOC|MAT SAU|BO TRI',norm(t['text']))]
   # Record observations by view label; no clearance standard is fabricated.
   rules=[]
   for v in views:
    near=sorted(placements,key=lambda p:math.dist(p['placement_anchor'][:2],v['position'][:2]))[:12]
    rules.append({'view_label':v,'nearby_placements':[p['handle'] for p in near],'relation_status':'proximity_only_requires_view_boundary_review'})
   horizontal=[]
   by_family={}
   for p in placements:
    if p.get('geometry_profile_id'):
     by_family.setdefault(p['geometry_profile_id'],[]).append(p)
   for gid,group in by_family.items():
    buckets={}
    for p in group:buckets.setdefault(round(p['placement_anchor'][1],2),[]).append(p)
    for y,row in buckets.items():
     if len(row)<2:continue
     row.sort(key=lambda p:p['placement_anchor'][0]);xs=[p['placement_anchor'][0] for p in row]
     horizontal.append({'geometry_profile_id':gid,'handles':[p['handle'] for p in row],'world_center_y':y,'center_x_positions':xs,'center_pitches':[xs[i+1]-xs[i] for i in range(len(xs)-1)],'status':'observed_alignment_may_span_multiple_views'})
   record={'id':sid+'_'+fid,'source_id':sid,'frame_handle':fid,'name':name,'bounds':b,'units_code':doc.units,'attributes':{a.dxf.tag:a.dxf.text for a in e.attribs},'placements':placements,'dimensions':dimensions,'labels':labels,'view_observations':rules,'cad_file':f'nguon/{sid}/drawing.dxf','status':'frame_extracted_view_boundaries_not_certified'}
   record['observed_horizontal_rows']=horizontal
   record['source_assembly_notes']=[t for t in labels if re.search('LAP|HAN |KHOANG|THANH|DAY|CANH|CACH|CAT|KHOAN|KHE|LO |CAO|SAU|RONG',norm(t['text']))]
   save(folder/'frames'/fid/'layout.json',record);form_index.append({'id':record['id'],'name':name,'source_id':sid,'placements':len(placements),'view_labels':[v['text'] for v in views],'path':str((folder/'frames'/fid/'layout.json').relative_to(OUT)).replace('\\','/')})
  print(sid,'frames',len(frames),flush=True)
 save(OUT/'form_tu/frames.json',form_index)
 save(OUT/'bo_tri/rules.json',{'policy':{'geometry_sharing':'Only approved geometry_profile_id may drive generation. Proposed family keys and candidate IDs are not approvals.','same_housing':'Verify manufacturer, series, poles, frame size, dimensions, terminals, mounting and view; rating alone never proves equality.','coordinates':'Frame origins are drawing coordinates, not cabinet bottom-left. Keep source units and insert transforms.','accessories':'trong_tu/ngoai_tu describe mounting location; not indoor/outdoor enclosure protection. chua_xac_dinh requires source check.','forms':'Each drawing may contain multiple cabinets and multiple views. Frame count is not cabinet count.','dynamic_blocks':'Extracted DXF is static block geometry; dynamic parameters and FIELD objects may not survive Importer. Original DWG and full converted DXF remain authoritative.'},'frames_index':'form_tu/frames.json'})
if __name__=='__main__':run()
