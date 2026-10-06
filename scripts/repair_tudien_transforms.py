from build_tudien_library import *
from ezdxf.math import Matrix44
def load(p):return json.loads(p.read_text(encoding='utf8'))
profiles=load(OUT/'geometry_profiles.json');idx={(s['source_id'],s['block']):(g,s) for g in profiles if 'hidden_entity_count_removed' in g for s in g['sources']}
all_instances=[]
for path in (OUT/'nguon').glob('*/dynamic_instances.json'):
 sid=path.parent.name;instances=load(path);doc=None
 for ins in instances:
  g,s=idx[(sid,ins['anonymous_block'])];b=s['original_visible_bounds']
  # Original insert base point is already captured by the matrix; correct only the normalization translation.
  old=Matrix44(ins['normalized_to_source_matrix']);gb=g['bounds_drawing_units']
  # Read the source INSERT only for records that validation identified as suspect.
  if doc is None:doc=ezdxf.readfile(path.parent/'drawing.dxf')
  ent=doc.entitydb[ins['handle']];matrix=ent.matrix44()
  corners=[matrix.transform((x,y,z)) for x in [b[0][0],b[1][0]] for y in [b[0][1],b[1][1]] for z in [b[0][2],b[1][2]]]
  world=[[min(v[i] for v in corners) for i in range(3)],[max(v[i] for v in corners) for i in range(3)]]
  ins.update(visible_world_bounds=world,visible_world_center=[(world[0][i]+world[1][i])/2 for i in range(3)],normalized_to_source_matrix=list(Matrix44.translate(b[0][0],b[0][1],0)*matrix))
 save(path,instances);all_instances.extend({'source_id':sid,**x} for x in instances)
save(OUT/'dynamic_instances.json',all_instances)
