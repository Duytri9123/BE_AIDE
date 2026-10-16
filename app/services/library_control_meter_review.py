"""Apply visual labels only while the reviewed drawing hashes still match."""
import hashlib
import json
from pathlib import Path

def apply_review(profile, current, path):
    registry=Path(__file__).resolve().parents[1]/'data/library_control_meter_review.json'
    row=json.loads(registry.read_text(encoding='utf8')).get(profile['id'])
    if not row:return
    paths={v['id_hinh_goc']:v.get('duong_dan') for v in current.get('cad_don',[])}
    for view in row['views']:
        relative=paths.get(view['id'])
        if not relative:return
        drawing=(path.parent/relative).resolve()
        if not drawing.is_relative_to(path.parent.resolve()) or not drawing.is_file():return
        if hashlib.sha256(drawing.read_bytes()).hexdigest()!=view['sha256']:return
    if row.get('display'):profile['display']=row['display']
    if row.get('observed_spec'):
        profile['spec']={**profile.get('spec',{}),**row['observed_spec']}
    if row.get('identification_review'):
        profile['identification_review']=row['identification_review']
    profile['use']=(profile.get('use') or '')+' '+row['note']
    profile['auto_select']=False
    profile['needs_review']=True
    if row.get('front_view'):
        for view in profile['views']:
            view['label']=view['face']='Mặt trước'
