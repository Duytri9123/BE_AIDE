"""Shared Susol geometry verified against LS catalogue dimension pages 246-248."""
import re
from import_ls_step_family import import_family,ZUP_YPLUS,ROOT
from project_ls_step_views import RCCB_AXES
PORTRAIT=[(c,c,0) for c,*_ in RCCB_AXES]
ACB_AXES=[('FRONT','SIDE-L',90),('REAR','SIDE',-90),('SIDE-L','TOP',180),('SIDE','BOTTOM',0),('TOP','FRONT',90),('BOTTOM','REAR',90)]
JOBS=[('47023/model-001',['TD100','TD160'],3,None,ACB_AXES,False),('47023/model-002',['TD100','TD160'],4,'L',ACB_AXES,False),('47023/model-003',['TD100','TD160'],4,'R',ACB_AXES,False),('47023/model-004',['TS100','TS160','TS250'],3,None,ZUP_YPLUS,False),('47023/model-005',['TS100','TS160','TS250'],4,'L',ZUP_YPLUS,False),('47023/model-006',['TS100','TS160','TS250'],4,'R',ZUP_YPLUS,False),('47023/model-009',['TS400','TS630'],3,None,ZUP_YPLUS,True),('47023/model-010',['TS400','TS630'],4,'L',ZUP_YPLUS,True),('47023/model-011',['TS400','TS630'],4,'R',ZUP_YPLUS,True),('47023/model-012',['TS800'],3,None,PORTRAIT,False),('47023/model-013',['TS800'],4,'L',PORTRAIT,False),('47023/model-014',['TS800'],4,'R',PORTRAIT,False)]
JOBS += [('47023/model-017',['TS1000','TS1250','TS1600'],3,None,ZUP_YPLUS,False),('47023/model-018',['TS1000','TS1250','TS1600'],4,None,ZUP_YPLUS,False)]
if __name__=='__main__':
 import sys
 for ident,models,poles,neutral,mapping,bars in JOBS:
  if len(sys.argv)>1 and ident not in sys.argv[1:]:continue
  def choose(r):
   if r.get('category')!='MCCB' or str((r.get('specifications') or {}).get('Số cực'))!=str(poles)+'P':return False
   return any(re.match(re.escape(m)+r'[NHL](?=\s|$)',r['sku']) for m in models)
  spec={'Họ dùng chung kích thước':' / '.join(models)}
  if neutral:spec['Vị trí cực N theo CAD']='Trái (L)' if neutral=='L' else 'Phải (R)'
  if bars:spec['Kiểu đầu nối theo CAD']='Có thanh đấu nối; đối chiếu phụ kiện với đơn hàng'
  name='LS · MCCB Susol · '+' / '.join(models)+' · '+str(poles)+'P'+(' · N '+('trái' if neutral=='L' else 'phải') if neutral else '')+(' · Có thanh đấu nối' if bars else '')
  evidence={'catalog_url':'https://www.ls-electric.com/ko/cat/%5BSusol%20MCCB%5D_Catalog_EN_202006.pdf','pdf_page':110 if models[0]=='TS1000' else 246 if models[0]=='TD100' else 247 if models[0]=='TS100' else 248 if models[0]=='TS400' else 249,'manufacturer_shared_dimension_heading':' / '.join(models)}
  import_family(ident,'MCCB',models,str(poles)+'P',choose,mapping=mapping,name=name,spec=spec,evidence=evidence)
