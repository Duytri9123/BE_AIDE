"""Isolated LS rotary handle bodies/sets, with explicit parent frame and source pose."""
from import_ls_step_family import import_family,ZUP_YPLUS
from project_ls_step_views import RCCB_AXES
XUP=[(c,c,0) for c,*_ in RCCB_AXES]
N_FACE=[('FRONT','SIDE',90),('REAR','SIDE-L',-90),('SIDE-L','TOP',0),('SIDE','BOTTOM',180),('TOP','REAR',90),('BOTTOM','FRONT',90)]
EH_NEG=[('FRONT','REAR',90),('REAR','FRONT',-90),('SIDE-L','TOP',-90),('SIDE','BOTTOM',-90),('TOP','SIDE-L',90),('BOTTOM','SIDE',90)]
JOBS=[('45207/model-000','DH100','DH100-S for ABN103c','ABN103c',XUP,False),('45207/model-003','DH125','DH125-S for ABS125c','ABS125c',XUP,False),('45207/model-006','DH250','DH250-S for ABH250c','ABH250c',XUP,False),('45210','N-70','N~70S for ABN403c','ABN403c',N_FACE,False),('45211','N-80','N~80S for ABN803c','ABN803c',N_FACE,False),('45204/model-001-handle','EH100','EH100-S for ABN103c','ABN103c',ZUP_YPLUS,True),('45205/model-001-handle','EH125','EH125-S for ABS125c','ABS125c',ZUP_YPLUS,True),('45206/model-001-handle','EH250','EH250-S for ABN250c','ABN250c',EH_NEG,True)]
if __name__=='__main__':
 import sys
 for sid,model,sku,parent,mapping,external in JOBS:
  if len(sys.argv)>1 and sid not in sys.argv[1:]:continue
  import_family(sid,'ACCESSORY',[model],None,lambda r:r.get('category')=='ACCESSORY' and r['sku']==sku,mapping=mapping,name='LS · Tay xoay '+('ngoài tủ' if external else 'trực tiếp')+' · '+model+' · '+parent,spec={'Thiết bị chính tham chiếu':parent,'Kiểu CAD':'Bộ tay xoay riêng; không bao gồm thân MCCB','Cấu hình đặt hàng':'Đối chiếu mã S/U, phụ kiện gá và cơ cấu cửa theo bộ hàng',**({'Trục và khoảng cách cửa':'Giữ tư thế và chiều dài trục của mô hình LS; chọn chiều dài theo tủ thực tế'} if external else {})},evidence={'review':'Manufacturer named handle subassemblies only. EH parent breaker was removed by exact STEP assembly name; reconstructed unfiltered world bounds/volume match original. All retained manufacturer parts and placements are unchanged. Direct DH/N files contain handle-specific parts, not a parent MCCB.'})
