"""Six-view Metasol body CAD selected by source frame and checked front dimensions."""
from import_ls_step_family import import_family,entities,ZUP_YPLUS,PRICES
from import_ls_main_faces import GROUPS,options
from project_ls_step_views import RCCB_AXES
from ezdxf import bbox
JOBS=[('45208/model-000','META100',2,50,130),('45208/model-001','META100',3,75,130),('45208/model-002','META100',4,100,130),('45208/model-003','META125',2,60,155),('45208/model-004','META125',3,90,155),('45208/model-005','META125',4,120,155),('45208/model-006','META250',3,105,165),('45208/model-007','META250',4,140,165),('45208/model-010','META400',3,140,257),('45208/model-012','META400',4,184,257)]
if __name__=='__main__':
 import sys
 for sid,group,poles,width,height in JOBS:
  if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
  models=next(g[4] for g in GROUPS if g[0]==group);refs=options(group,'MCCB',poles,models,width,height);ids={r['source_row_id'] for r in refs}
  mapping=ZUP_YPLUS if group=='META400' else [(c,c,0) for c,*_ in RCCB_AXES]
  views,prefix=entities(sid,mapping)
  if not views:print('Pending',sid,flush=True);continue
  b=bbox.extents(views[0][2]);assert abs(b.size.x-width)<.2 and abs(b.size.y-height)<.2,(sid,b.size)
  model_names=sorted({r['model'] for r in refs})
  import_family(sid,'MCCB',model_names,str(poles)+'P',lambda r:r['id'] in ids,mapping=mapping,name='LS · MCCB Metasol · '+group.replace('META','')+'AF · '+str(poles)+'P',spec={'Khung (AF)':group.replace('META','')})
