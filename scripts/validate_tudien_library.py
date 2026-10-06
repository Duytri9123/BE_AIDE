from build_tudien_library import *
from ezdxf.math import Matrix44
def load(p):return json.loads(p.read_text(encoding='utf8'))
errors=[];coverage=load(OUT/'coverage.json');profiles=load(OUT/'geometry_profiles.json');ids={g['id']:g for g in profiles};checked=0
for s in coverage:
 p=SOURCE/s['source_file']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=s['sha256']:errors.append({'source':s['source_file'],'error':'source hash mismatch'})
 if s['status']!='read':errors.append({'source':s['source_file'],'error':s['status']})
for g in profiles:
 if '--transforms-only' in sys.argv:continue
 p=OUT/g['cad_views']['source_view']
 try:
  doc=ezdxf.readfile(p)
  if not len(doc.modelspace()):errors.append({'geometry':g['id'],'error':'empty modelspace'})
  checked+=1
 except Exception as e:errors.append({'geometry':g['id'],'error':str(e)})
 if checked%500==0:print('checked',checked,flush=True)
transforms=[]
for ins in load(OUT/'dynamic_instances.json'):
 if ins['geometry_profile_id'] not in ids:errors.append({'instance':ins['handle'],'error':'missing geometry ID'});continue
 g=ids[ins['geometry_profile_id']];b=g['bounds_drawing_units']
 if b:
  mat=Matrix44(ins['normalized_to_source_matrix']);corners=[mat.transform((x,y,z)) for x in [b[0][0],b[1][0]] for y in [b[0][1],b[1][1]] for z in [b[0][2],b[1][2]]]
  actual=[[min(v[i] for v in corners) for i in range(3)],[max(v[i] for v in corners) for i in range(3)]]
  delta=max(abs(actual[j][i]-ins['visible_world_bounds'][j][i]) for j in range(2) for i in range(3))
  if delta>1e-4:transforms.append({'source_id':ins['source_id'],'handle':ins['handle'],'geometry_id':g['id'],'maximum_bound_delta':delta})
if '--transforms-only' in sys.argv:
 old=load(OUT/'validation.json');checked=old['geometry_files_checked'];errors+=old['errors']
result={'source_files_checked':len(coverage),'source_files_on_disk':len(list(SOURCE.iterdir())),'geometry_files_checked':checked,'errors':errors,'geometry_transform_bound_differences':transforms,'validation_scope':'All source hashes, coverage, DXF parsing and nonempty modelspaces; normalized visible geometry transformations checked against source bounds. This does not certify SKU compatibility or electrical clearances.'}
save(OUT/'validation.json',result);print(json.dumps({k:v for k,v in result.items() if k not in ['geometry_transform_bound_differences','validation_scope']},ensure_ascii=False));print('transform bound differences',len(transforms))
