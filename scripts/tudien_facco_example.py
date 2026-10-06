from build_tudien_library import *
from ezdxf.math import Matrix44
sid='0785608caf266cc1'
instances=json.loads((OUT/'nguon'/sid/'dynamic_instances.json').read_text(encoding='utf8'))
origin=[13141.59366103308,-13758.75838387178]
selected=[p for p in instances if p['dynamic_parent'] in ['BKN-LS','ABN100AF-LS'] and 13000<p['visible_world_center'][0]<13700]
doc=ezdxf.new('R2018');doc.units=4;records=[]
for p in selected:
 source=ezdxf.readfile(OUT/'geometry'/p['geometry_profile_id']/'cad.dxf');before=set(e.dxf.handle for e in doc.modelspace());imp=Importer(source,doc);imp.import_entities(source.modelspace(),doc.modelspace());imp.finalize()
 lo=p['visible_world_bounds'][0];pos=[lo[0]-origin[0],lo[1]-origin[1]]
 for e in doc.modelspace():
  if e.dxf.handle not in before:e.transform(Matrix44.translate(*pos,0))
 records.append({'source_handle':p['handle'],'source_series':p['dynamic_parent'],'geometry_profile_id':p['geometry_profile_id'],'visible_lower_left_relative_to_enclosure':pos,'source_world_bounds':p['visible_world_bounds']})
folder=OUT/'form_tu/FACCO_100A_6MCB_2P_32A';folder.mkdir(parents=True,exist_ok=True);doc.saveas(folder/'equipment_layout.dxf')
save(folder/'layout_rules.json',{'source_id':sid,'source_frame_handle':'107DB6E','source_title':'TỦ ĐIỆN THI CÔNG 100A, 6 MCB 2P 32A','evidence':'Geometry visually reviewed against frame and coordinates read from visible dynamic entities.','enclosure_dimensions_drawing_units':{'height':600,'width':400,'depth':250,'base_height':300},'dimension_evidence_handles':['107DA7E','107DA8E','107DA91','107DBEE'],'source_origin_lower_left_main_body':origin,'placements':records,'observations':{'incoming':'LS ABN100AF at upper center','outgoing':'6 LS BKN-2P in a horizontal row below incoming','mcb_visible_outline':[36,81],'mcb_row_pitch':36,'mcb_row_total_width':216,'mcb_row_center_x':200,'mccb_visible_outline':[75,130],'mccb_center_x':200,'vertical_outline_gap_incoming_to_outgoing':101,'external_sockets':'Three outlets on each side; observed vertical row pitch 170 drawing units','door_layers':'First door outside; second door has operation cutouts aligned with internal breakers','ground_terminals':'Two vertical earth-terminal groups beside incoming breaker'},'reuse_limits':'Observed arrangement for this source only. The 101 gap is a measured drawing gap, not a clearance standard. equipment_layout.dxf contains seven device views only; use source_form.dxf for enclosure, cutouts and other views. Device labels do not certify all ratings share these housings.'})
assert len(selected)==7
assert sum(p['dynamic_parent']=='BKN-LS' for p in selected)==6
print('FACCO seven-device reusable layout exported')
