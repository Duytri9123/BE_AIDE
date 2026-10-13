import json,re,time,hashlib,sys
from pathlib import Path
import ezdxf
from ezdxf import bbox
from populate_catalogtb_chint import ROOT,visible,save
from populate_catalogtb_abb_rmu_osung import profile
BASE=ROOT.parents[1]/'tmp/project_cabinet_sources';items=[];cache={};seen=set()
rows=json.loads((BASE/'support_candidates.json').read_text(encoding='utf-8'))
for row in rows:
 if re.search(r'^NN|DEN|LIGHT',row['name'],re.I):continue
 sid=row['source']['id']
 if sid not in cache:cache[sid]=ezdxf.readfile(ROOT.parents[2]/row['source']['dxf'])
 doc=cache[sid];e=doc.entitydb[row['handle']];es=list(visible(doc,e.virtual_entities()));b=bbox.extents(es,fast=False)
 if not b.has_data:continue
 key=(row['name'],round(b.size.x,2),round(b.size.y,2))
 if key in seen:continue
 seen.add(key);gid='DO-'+hashlib.sha256(str(key).encode()).hexdigest()[:12]
 # Replace full drawing import with only this isolated block.
 from populate_catalogtb_chint import drawing
 tmp=BASE/'support_single';tmp.mkdir(exist_ok=True);target=ezdxf.new('R2018');from ezdxf.addons import Importer
 imp=Importer(doc,target);imp.import_entities(es);imp.finalize();f=tmp/(gid+'.dxf');target.saveas(f)
 d,folder=profile('Đố',gid,'Support',None,None,[(gid,'Mặt trước','Mặt gá · theo CAD nguồn',f)],['https://www.rittal.com/com-en/products/PG20231215ZUB101/PG20240404ZUB101/PG2024040ZUB104'],['Thanh gá từ block dự án; chưa xác nhận vật liệu, tải chịu và mặt lắp.'],True)
 v=drawing(folder,gid,'Mặt trước','Mặt gá · theo CAD nguồn',source_path=f)
 import shutil
 for fn in ('ban_ve.dxf','xem_truoc.svg','thong_tin_cad_chen.json'):shutil.copy2(folder/'CadDon'/gid/fn,folder/'CadChenTu'/fn)
 d['ten_kieu']=d['ten_san_pham']=row['name']+' · '+f'{b.size.x:g}×{b.size.y:g} mm';d['thong_so']={'kich_thuoc_mat_CAD_mm':{'ngang':round(b.size.x,3),'cao':round(b.size.y,3)},'vat_lieu':None,'day_ton_mm':None,'tai_cho_phep':None};d['tu_khoa_tim_kiem']=[row['name'],'đố','thanh gá','thanh U','thanh dọc','support rail'];d['cad_don']=[v];d['nguon_block']=row
 d['yeu_cau_chon_day']={'can_day':False,'quy_tac':'Chi tiết gá cơ khí; xác nhận liên kết bảo vệ riêng nếu thiết kế yêu cầu.'};d['nhan_dien_ai']['loai_thiet_bi_code']='MountingSupport';d['nhan_dien_ai']['hang']=None;d['hang_xac_nhan']=None
 save(folder/'thong_tin_thiet_bi.json',d);items.append({'id':gid,'name':d['ten_kieu'],'source':row['source']['source_file'],'source_handle':row['handle']});print(gid,row['name'],flush=True)
save(ROOT/'Đố/kiem_tra_do.json',{'items':items,'profiles':len(items),'policy':'Mỗi CAD là một block đố/thanh gá riêng; chưa xác nhận tải hoặc mặt lắp.'})
print('Supports',len(items))
