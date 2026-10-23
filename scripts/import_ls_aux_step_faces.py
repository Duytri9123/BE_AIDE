"""Standalone genuine auxiliary modules, not substituted by a parent contactor."""
import re
from import_ls_step_family import import_family,ZUP_YPLUS
from project_ls_step_views import RCCB_AXES
PORTRAIT=[(c,c,0) for c,*_ in RCCB_AXES]
JOBS=[('55731/model-036','AU-100',PORTRAIT,'Bên hông','MC-185a~800a'),('55731/model-038','UA-1',PORTRAIT,'Bên hông','MC-6a~150a'),('55731/model-039','UA-2',ZUP_YPLUS,'Mặt trước','MC-6a~150a'),('55731/model-040','UA-4',ZUP_YPLUS,'Mặt trước','MC-6a~150a')]
if __name__=='__main__':
 for sid,model,mapping,mount,parent in JOBS:
  import_family(sid,'AUX_CONTACT',[model],None,lambda r:r.get('category')=='AUX_CONTACT' and bool(re.match(re.escape(model)+r'(?=\s|$)',r['sku'])),mapping=mapping,name='LS · Tiếp điểm phụ · '+model+' · Gắn '+mount.lower(),spec={'Kiểu lắp':mount+' contactor; xác nhận vị trí ghép với thiết bị chính','Thiết bị tham chiếu theo bảng giá':parent,'Bao hình CAD':'Tính cả lẫy và cơ cấu gá; không chỉ chiều dày thân danh định'},evidence={'catalog_url':'https://www.ls-electric.com/ko/cat/%5BMetasol_MS%5D_KO_C04001-37-202609.pdf','pdf_page':179 if model!='AU-100' else None,'orientation_review':'Front narrow vertical screw-terminal face for side-mounted modules; front screw-terminal grid for head-mounted UA-2/UA-4. Parent assembly mating must be checked separately.'})
