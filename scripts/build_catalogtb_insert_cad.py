"""Create one standalone insertion CAD for every available device projection."""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import ezdxf
from ezdxf import bbox, transform
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.layout import Page
from ezdxf.addons.drawing.properties import LayoutProperties
from ezdxf.addons.drawing.svg import SVGBackend

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'CatalogTB'
PROFILE_FILES = sorted(ROOT.rglob('thong_tin_thiet_bi.json'))
if len(sys.argv) > 1:
    PROFILE_FILES = [p for p in PROFILE_FILES if p.relative_to(ROOT).parts[0] in sys.argv[1:]]

# These blocks contain both a top and a side projection; top is the view
# needed to position the insulator on the cabinet assembly plan.
OVERRIDES = {
    'SuDo_S25':'B_35241864a9c5',
    'SuDo_S35':'B_80897f043c3a',
    'SuDo_S50':'B_e8e1e87c60ec',
    'SuDo_S54':'B_5ee5724fc101',
    'MSQ-30':'C08_cluster7-V003',
    'CML400A':'C08_cluster9-V002',
    'SuKepThanhCai_C100':'C02_cluster4-V003',
    'SuKepThanhCai_EL':'C02_cluster4-V005',
}


def choice_score(record):
    name=record['ten_hinh'].casefold()
    score=0
    if 'cover' in record.get('trang_thai_block', '').casefold():
        score-=200
    if any(s in name for s in ('front','mặt trước','mặt đứng','mat dung','mặt chính')):
        score+=100
    if re.search(r'(?:^|[-_])f(?:$|[-_0-9])',name):
        score+=65
    if any(s in name for s in ('mặt bằng','mat bang','top','mặt trên')):
        score+=45
    if any(s in name for s in ('side','mặt hông','mặt bên','mat hong')):
        score-=90
    if any(s in name for s in ('bottom','mặt dưới','chi tiết phía dưới')):
        score-=95
    if record['loai_hinh']=='block':
        score+=20
    return score


def face_label(record):
    name=record['ten_hinh'].casefold()
    if name.startswith('mặt '):
        return record['ten_hinh']
    if record['id'] in {f'C08_cluster10-V{i:03d}' for i in range(1,6)}:
        return 'Mặt trước'
    if any(s in name for s in ('front','mặt trước','mặt đứng','mat dung','font')):
        return 'Mặt trước'
    if any(s in name for s in ('mặt bằng','mat bang','top','mặt trên','đỉnh','dỉnh')):
        return 'Mặt trên'
    if any(s in name for s in ('side','mặt hông','mặt bên','mat hong','cạnh')):
        return 'Mặt bên'
    if record['id'] in {OVERRIDES[key] for key in ('SuDo_S25','SuDo_S35','SuDo_S50','SuDo_S54')}:
        return 'Mặt trên'
    return 'Chưa xác định hướng nhìn'


def preview(doc, target):
    ext=bbox.extents(doc.modelspace(),fast=True)
    assert ext.has_data
    backend=SVGBackend()
    Frontend(RenderContext(doc),backend).draw_layout(
        doc.modelspace(),layout_properties=LayoutProperties('Model','#212830','#ffffff',units=4,dark_background=True))
    svg=backend.get_string(Page(max(35,ext.size.x+20),max(35,ext.size.y+20)))
    target.write_text(svg,encoding='utf-8')
    return ext


def create_single_cad(record,record_path,cad_dir):
    if (cad_dir/'native_preview.json').exists():
        return json.loads((cad_dir/'thong_tin_cad_chen.json').read_text(encoding='utf-8'))
    source_dxf=record_path.parent/record['tep']['cad_dxf']
    doc=ezdxf.readfile(source_dxf)
    assert len(doc.modelspace()) and sum(e.dxftype()=='INSERT' for e in doc.modelspace())<=1
    source_extent=bbox.extents(doc.modelspace(),fast=True)
    assert source_extent.has_data
    source_center=source_extent.center
    cad_dir.mkdir(parents=True,exist_ok=True)
    assert cad_dir.resolve().is_relative_to(ROOT.resolve())
    target_dxf=cad_dir/'ban_ve.dxf'
    source_units=doc.header.get('$INSUNITS')
    assert source_units in (4,6)
    if source_units==6:
        # Three ABB drawings have millimetre geometry but a metre header.
        assert record['id'].startswith('A02_abb-V')
    doc.header['$INSUNITS']=4
    log=transform.translate(doc.modelspace(),(-source_center.x,-source_center.y,0))
    assert len(log)==0, (record['id'],list(log))
    doc.saveas(target_dxf)
    ext=preview(doc,cad_dir/'xem_truoc.svg')
    geometry={'don_vi':'mm','goc_chen_dxf_mm':{'x':0,'y':0},
              'bao_hinh_mm':{'min_x':round(ext.extmin.x,3),'min_y':round(ext.extmin.y,3),
                             'max_x':round(ext.extmax.x,3),'max_y':round(ext.extmax.y,3)},
              'tam_bao_hinh_mm':{'x':round(ext.center.x,3),'y':round(ext.center.y,3)},
              'dich_chuyen_tu_hinh_goc_mm':{'x':round(-source_center.x,3),
                                           'y':round(-source_center.y,3)}}
    metadata={'id_hinh_goc':record['id'],'huong_nhin':face_label(record),
              'tep':{'cad_dxf':'ban_ve.dxf','preview':'xem_truoc.svg'},
              'hinh_hoc_lap_dat':geometry,
              'ghi_chu':'Một hình chiếu riêng, đặt được độc lập vào bản vẽ tủ.'}
    old_path = cad_dir/'thong_tin_cad_chen.json'
    if old_path.exists():
        old = json.loads(old_path.read_text(encoding='utf-8'))
        for field in ('nhan_dien_mat', 'bo_tri_trong_tu', 'bo_tri_lap_dat'):
            if field in old:
                metadata[field] = old[field]
        if old.get('nhan_dien_mat'):
            metadata['huong_nhin'] = old['huong_nhin']
    (cad_dir/'thong_tin_cad_chen.json').write_text(
        json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return metadata


for profile_path in PROFILE_FILES:
    profile=json.loads(profile_path.read_text(encoding='utf-8'))
    records=[]
    for path in profile_path.parent.rglob('thong_tin.json'):
        record=json.loads(path.read_text(encoding='utf-8'))
        records.append((record,path))
    assert records and {r['id'] for r,_ in records}==set(profile['cac_hinh_cad'])
    key=profile_path.parent.name
    override=OVERRIDES.get(key)
    selected=(next((pair for pair in records if pair[0]['id']==override),None)
              if override else None)
    if not selected:
        selected=max(records,key=lambda pair:(choice_score(pair[0]),-profile['cac_hinh_cad'].index(pair[0]['id'])))
    single_views=[]
    for record,record_path in records:
        cad_dir=profile_path.parent/'CadDon'/record['id']
        metadata=create_single_cad(record,record_path,cad_dir)
        single_views.append({'id_hinh_goc':record['id'],'huong_nhin':metadata['huong_nhin'],
                             'nhan_hien_thi':record.get('nhan_hien_thi') or metadata['huong_nhin'],
                             'bo_tri_trong_tu':metadata.get('bo_tri_trong_tu', {}),
                             'duong_dan':f'CadDon/{record["id"]}/ban_ve.dxf'})
    record,_=selected
    selected_dir=profile_path.parent/'CadDon'/record['id']
    cad_dir=profile_path.parent/'CadChenTu'
    cad_dir.mkdir(exist_ok=True)
    for filename in ('ban_ve.dxf','xem_truoc.svg','thong_tin_cad_chen.json'):
        shutil.copy2(selected_dir/filename,cad_dir/filename)
    metadata=json.loads((cad_dir/'thong_tin_cad_chen.json').read_text(encoding='utf-8'))
    profile['cad_don']=single_views
    profile['cad_chen_tu']={'id_hinh_goc':record['id'],'huong_nhin':metadata['huong_nhin'],
                           'duong_dan':'CadChenTu/ban_ve.dxf'}
    profile_path.write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

print(json.dumps({'profiles':len(PROFILE_FILES),'single_view_cad':sum(
    len(json.loads(p.read_text(encoding='utf-8'))['cad_don']) for p in PROFILE_FILES)},ensure_ascii=False))
