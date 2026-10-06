from build_tudien_library import *
import logging
logging.getLogger('ezdxf').setLevel(logging.ERROR)
def load(p):return json.loads(p.read_text(encoding='utf8'))
old=load(OUT/'geometry_profiles.json');by_source={};fixed={}
for g in old:
 if 'hidden_entity_count_removed' in g:continue
 for s in g['sources']:by_source.setdefault(s['source_id'],[]).append((g,s))
for sid,entries in by_source.items():
 doc=ezdxf.readfile(OUT/'nguon'/sid/'drawing.dxf');mapping={}
 for g,s in entries:
  block=doc.blocks[s['block']];fp=entity_fingerprint(block)
  # Isolate INSERT dependencies by source and block, preventing nested geometry aliasing.
  gid=hid('rawfull|'+fp+str(doc.units)+(sid+s['block'] if any(e.dxftype()=='INSERT' for e in block) else ''))
  mapping[s['block']]=gid
  if gid not in fixed:
   dest=ezdxf.new(doc.dxfversion);dest.units=doc.units;imp=Importer(doc,dest);imp.import_block(block.name);imp.finalize();dest.modelspace().add_blockref(block.name,(0,0,0));p=OUT/'geometry'/gid/'cad.dxf';p.parent.mkdir(parents=True,exist_ok=True);dest.saveas(p)
   ng=dict(g);ng.update(id=gid,cad_views={'source_view':str(p.relative_to(OUT)).replace('\\','/')},block_names=[block.name],sources=[],fingerprint_method='full_DXF_tags_including_polyline_vertices',view_status='raw_block_includes_hidden_states_not_physical_envelope',bounds_drawing_units=bounds(dest.modelspace()))
   ng.pop('deduplication_warning',None);fixed[gid]=ng
  fixed[gid]['sources'].append(s)
  if block.name not in fixed[gid]['block_names']:fixed[gid]['block_names'].append(block.name)
 invpath=OUT/'nguon'/sid/'cad_inventory.json';inv=load(invpath)
 for b in inv['blocks']:
  if b['name'] in mapping:b['geometry_id']=mapping[b['name']]
 save(invpath,inv);print(sid,len(fixed),flush=True)
save(OUT/'raw_profiles_verified.json',list(fixed.values()))
