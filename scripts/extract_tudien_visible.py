"""Resolve dynamic parents and export only visible entities, preserving evidence."""
from build_tudien_library import *
from ezdxf import dynblkhelper
from ezdxf.math import Matrix44
import logging
logging.getLogger('ezdxf').setLevel(logging.ERROR)
def load(p):return json.loads(p.read_text(encoding='utf8'))
def run():
 profiles=load(OUT/'geometry_profiles.json');byid={p['id']:p for p in profiles};observations=[]
 for source in (OUT/'nguon').glob('*/drawing.dxf'):
  sid=source.parent.name;doc=ezdxf.readfile(source);cache={};local_boxes={};instances=[]
  for layout in doc.layouts:
   for insert in layout.query('INSERT'):
    parent=dynblkhelper.get_dynamic_block_definition(insert)
    if parent is None:continue
    name=insert.dxf.name
    if name not in cache:
     block=doc.blocks[name];visible=[e for e in block if not e.dxf.get('invisible',0)]
     b=bounds(visible)
     if not b:continue
     texts=[text(e) for e in visible if text(e)];label=parent.name+' '+' '.join(texts)
     dest=ezdxf.new(doc.dxfversion);imp=Importer(doc,dest);imp.import_entities(visible,dest.modelspace());imp.finalize()
     # Maintain z and normalize the 2D insertion origin to visible lower-left.
     translation=Matrix44.translate(-b[0][0],-b[0][1],0)
     for e in dest.modelspace():
      try:e.transform(translation)
      except (NotImplementedError,AttributeError):pass
     payload=[[e.dxftype(),{k:str(v) for k,v in e.dxf.all_existing_dxf_attribs().items() if k not in ['handle','owner']}] for e in dest.modelspace()]
     gid=hid('visible|'+parent.name+'|'+str(doc.units)+'|'+entity_fingerprint(dest.modelspace())+(sid+name if any(e.dxftype()=='INSERT' for e in dest.modelspace()) else ''))
     if gid not in byid:
      path=OUT/'geometry'/gid/'cad.dxf';path.parent.mkdir(parents=True,exist_ok=True);dest.units=doc.units;dest.saveas(path)
      poles=sorted(set(re.findall(r'\b[1-4]P(?:\+N)?\b',' '.join(texts),re.I)))
      g={'id':gid,'cad_views':{'source_view':str(path.relative_to(OUT)).replace('\\','/')},'block_names':[parent.name],'visible_labels':texts,'source_anonymous_blocks':[],'bounds_drawing_units':bounds(dest.modelspace()),'visible_width_drawing_units':b[1][0]-b[0][0],'visible_height_drawing_units':b[1][1]-b[0][1],'units_code':doc.units,'category':category(label),'manufacturer':brand(label),'accessory_location':accessory(label),'poles_from_visible_label':poles[0] if len(poles)==1 else None,'view_status':'visible_dynamic_state_view_not_yet_semantically_named','sources':[],'normalization':'visible lower-left translated to 0,0; not a certified mounting datum','hidden_entity_count_removed':len(block)-len(visible)}
      profiles.append(g);byid[gid]=g
     g=byid[gid];g['sources'].append({'source_id':sid,'block':name,'dynamic_parent':parent.name,'original_visible_bounds':b});g['source_anonymous_blocks'].append(name) if name not in g['source_anonymous_blocks'] else None;cache[name]=gid;local_boxes[name]=b
    if name not in cache:continue
    local_bounds=local_boxes[name];matrix=insert.matrix44()
    corners=[matrix.transform((x,y,z)) for x in [local_bounds[0][0],local_bounds[1][0]] for y in [local_bounds[0][1],local_bounds[1][1]] for z in [local_bounds[0][2],local_bounds[1][2]]]
    world=[[min(v[i] for v in corners) for i in range(3)],[max(v[i] for v in corners) for i in range(3)]]
    instances.append({'handle':insert.dxf.handle,'layout':layout.name,'anonymous_block':name,'dynamic_parent':parent.name,'geometry_profile_id':cache[name],'position':list(insert.dxf.insert),'visible_world_bounds':world,'visible_world_center':[(world[0][i]+world[1][i])/2 for i in range(3)],'normalized_to_source_matrix':list(Matrix44.translate(local_bounds[0][0],local_bounds[0][1],0)*matrix),'rotation':insert.dxf.get('rotation',0),'scale':[insert.dxf.get(n,1) for n in ['xscale','yscale','zscale']]})
  save(source.parent/'dynamic_instances.json',instances);observations.extend({'source_id':sid,**x} for x in instances);print(sid,len(cache),flush=True)
 save(OUT/'geometry_profiles.json',profiles);save(OUT/'dynamic_instances.json',observations)
if __name__=='__main__':run()
