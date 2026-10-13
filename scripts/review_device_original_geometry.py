"""Audit device CAD against its source projection. Never strip copper or conductors."""
import json
from pathlib import Path
from collections import Counter
import ezdxf
from ezdxf import bbox
root=Path(__file__).resolve().parents[1]/'data/CatalogTB'
old='Chọn theo biến thể; cỡ khung AF không phải dòng tải đã chọn'
new='Dòng định mức In: chọn theo cấu hình thiết bị'
for path in root.rglob('*.json'):
    text=path.read_text(encoding='utf-8')
    if old in text:path.write_text(text.replace(old,new),encoding='utf-8')
script=Path(__file__).parent/'populate_catalogtb_mitsubishi.py'
text=script.read_text(encoding='utf-8');script.write_text(text.replace(old,new),encoding='utf-8')
report={'checked':0,'missing_source':[],'differences':[], 'policy':'Giữ toàn bộ hình học thiết bị gốc, gồm thanh đồng, đầu nối và phụ kiện hãng. Không áp dụng bộ lọc làm sạch form tủ cho CAD thiết bị.'}
for profile in root.rglob('thong_tin_thiet_bi.json'):
    data=json.loads(profile.read_text(encoding='utf-8'))
    for view in data.get('cad_don',[]):
        vid=view['id_hinh_goc'];target=profile.parent/'CadDon'/vid/'ban_ve.dxf'
        candidates=[p for p in profile.parent.rglob('ban_ve.dxf') if p.parent.name==vid and not {'CadDon','CadChenTu'}.intersection(p.relative_to(profile.parent).parts)]
        if not candidates:
            report['missing_source'].append(str(target.relative_to(root)));continue
        source=ezdxf.readfile(candidates[0]);current=ezdxf.readfile(target)
        def signature(doc):return Counter((e.dxftype(),e.dxf.layer,e.dxf.get('color',256)) for e in doc.modelspace())
        a,b=signature(source),signature(current)
        ext_a=bbox.extents(source.modelspace(),fast=True);ext_b=bbox.extents(current.modelspace(),fast=True)
        size_match=ext_a.has_data and ext_b.has_data and all(abs(ext_a.size[i]-ext_b.size[i])<0.01 for i in (0,1))
        report['checked']+=1
        if a!=b or not size_match:
            report['differences'].append({'view':str(target.relative_to(root)),'entity_counts_equal':a==b,'dimensions_equal':size_match})
    if report['checked'] and report['checked']%200==0:print('Reviewed',report['checked'],flush=True)
out=root/'kiem_tra_giu_nguyen_cad_thiet_bi.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({key:len(value) if isinstance(value,list) else value for key,value in report.items()},ensure_ascii=False))
