from build_tudien_library import *
def load(p):return json.loads(p.read_text(encoding='utf8'))
profiles=load(OUT/'geometry_profiles.json');instances=load(OUT/'dynamic_instances.json');active={i['geometry_profile_id'] for i in instances};kept=[];archive=[]
for g in profiles:
 if 'hidden_entity_count_removed' in g:
  if g['id'] not in active:archive.append(g);continue
  g['fingerprint_method']='full_DXF_tags_including_polyline_vertices'
 else:
  archive.append(g);continue
 kept.append(g)
kept.extend(load(OUT/'raw_profiles_verified.json'))
save(OUT/'geometry_profiles.json',kept);save(OUT/'nguon/superseded_visible_profiles.json',archive)
ole=load(OUT/'embedded_ole.json');decoded=load(OUT/'embedded_ole_decoded.json');di={d['id']:d for d in decoded}
for o in ole:
 d=di.get(o['id'],{});o['status']=d.get('status','not_decoded')
 if o['id']=='e3b0c44298fc1c149afb':o['status']='empty_ole_payload'
 if o['status']=='non_workbook_ole':o['status']='raster_image_visually_reviewed'
save(OUT/'embedded_ole.json',ole)
notes=load(Path(__file__).with_name('tudien_ole_image_notes.json'))
for oid,n in notes.items():
 n['sources']=[{'source_id':o['source_id'],'handle':o['handle']} for o in ole if o['id']==oid];save(OUT/'nguon/embedded_ole'/f'{oid}_visual.json',n)
save(OUT/'embedded_summary.json',{'ole_instances':len(ole),'unique_payloads':len(di),'workbooks':sum(d['status']=='workbook_extracted' for d in decoded),'sheets':sum(d.get('sheets',0) for d in decoded),'rows':sum(d.get('rows',0) for d in decoded),'image_payloads':2,'empty_payloads':1,'excel_unique_images':31,'image_review':'31 contact-sheet reviews; partial text notes, full row transcription remains in review_queue.json'})
print('active visible',len(active),'raw evidence',len(kept)-len(active))
