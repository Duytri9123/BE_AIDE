"""Large Metasol source frames; internal trip/rating options remain unapproved."""
import sys
from import_ls_step_family import import_family
JOBS=[('45208/model-008',['ABN402c'],2,400,False),('45208/model-015',['ABN803c','ABS803c'],3,800,False),('45208/model-017',['ABN804c','ABS804c'],4,800,False),('45208/model-026',['ABS1203b'],3,1200,True),('45208/model-027',['ABS1204b'],4,1200,True)]
if __name__=='__main__':
 for sid,models,poles,frame,bars in JOBS:
  if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
  import_family(sid,'MCCB',models,str(poles)+'P',lambda r:r.get('category')=='MCCB' and r['sku'] in models,name='LS · MCCB Metasol · '+str(frame)+'AF · '+str(poles)+'P'+(' · Có thanh đấu nối' if bars else ''),spec={'Khung (AF)':str(frame),**({'Kiểu đầu nối theo CAD':'Có thanh đấu nối; bao hình tính cả thanh đấu nối'} if bars else {})})
