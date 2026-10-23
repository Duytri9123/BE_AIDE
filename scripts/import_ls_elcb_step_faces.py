"""Six-view ELCB models: exact source frame/poles, busbars kept in envelope."""
from import_ls_step_family import import_family,ZUP_YPLUS
from project_ls_step_views import RCCB_AXES
PORTRAIT=[(c,c,0) for c,*_ in RCCB_AXES]
JOBS=[('45226/model-016',['EBN53c','EBN103c'],3,100,PORTRAIT,False),('45226/model-019',['EBN104c'],4,100,PORTRAIT,False),('45226/model-025',['EBS104c'],4,125,PORTRAIT,False),('45226/model-028',['EBN203c'],3,250,PORTRAIT,False),('45226/model-001',['EBS204c'],4,250,PORTRAIT,False),('45226/model-004',['EBN403c'],3,400,ZUP_YPLUS,True),('45226/model-007',['EBN404c'],4,400,ZUP_YPLUS,True),('45226/model-010',['EBN803c'],3,800,ZUP_YPLUS,True)]
if __name__=='__main__':
 import sys
 for sid,models,poles,frame,mapping,bars in JOBS:
  if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
  import_family(sid,'ELCB',models,str(poles)+'P',lambda r:r.get('category')=='ELCB' and r['sku'] in models,mapping=mapping,name='LS · ELCB Metasol · '+' / '.join(models)+' · '+str(poles)+'P'+(' · Có thanh đấu nối' if bars else ''),spec={'Khung (AF)':str(frame),**({'Kiểu đầu nối theo CAD':'Có thanh đấu nối; bao hình tính cả thanh đấu nối'} if bars else {})})
