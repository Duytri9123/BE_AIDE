"""Publish isolated interlock parts; AR600 parent assemblies are not standalone parts."""
import re
from import_ls_step_family import import_family
from project_ls_step_views import RCCB_AXES
MAPPING=[(c,c,0) for c,*_ in RCCB_AXES]
if __name__=='__main__':
 for sid,model,price,parent in [('55731/model-027','AR-180','AR-180','MC-185a~400a'),('55731/model-042','UR-02','UR-2','MC-6a~150a')]:
  import_family(sid,'ACCESSORY',[model],None,lambda r:r.get('category')=='ACCESSORY' and r['sku']==price,mapping=MAPPING,name='LS · Khóa liên động cơ khí · '+model+(' · Bảng giá '+price if model!=price else ''),spec={'Thiết bị tham chiếu theo bảng giá':parent,'Kiểu lắp':'Ghép hai contactor; xác nhận tư thế và cơ cấu ghép trước lắp đặt'},evidence={'catalog_url':'https://www.ls-electric.com/ko/cat/%5BMetasol_MS%5D_KO_C04001-37-202609.pdf','pdf_pages':[92,179] if model=='UR-02' else [],'price_alias':price,'orientation_review':'UR02 orientation matches the 83 mm-high manufacturer front; 12 mm is nominal body thickness, and the source envelope includes protruding clips/actuator; AR180 actuator axis is horizontal between adjacent contactors. Isolated source parts only; no parent contactors included.'})
