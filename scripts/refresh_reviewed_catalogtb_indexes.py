"""Refresh read indexes without rewriting or reclassifying source profiles."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];ROOT=BASE/'data/CatalogTB'
index_path=ROOT/'ai_device_index.json'
index=json.loads(index_path.read_text(encoding='utf8'))
manifest=json.loads((ROOT/'ai_library_manifest.json').read_text(encoding='utf8'))
discovery={r['profile']:r for r in manifest['items']}
known={item['profile']:item for item in index['items']}
index['items']=[known.get(row['profile']) or {'profile':row['profile'],
    'category':row['group'],'brand':row['brand'],'auto_select':False,'needs_review':True}
    for row in manifest['items']]
index['count']=len(index['items'])
for item in index['items']:
    path=ROOT/item['profile'];profile=json.loads(path.read_text(encoding='utf8'))
    item.update(name=profile.get('ten_san_pham'),use=profile.get('cong_dung'),
        type=profile.get('ban_chat'),search_aliases=profile.get('tu_khoa_tim_kiem') or [],
        identification=profile.get('nhan_dien_ai') or {'loai_thiet_bi_code':discovery[item['profile']]['category_code'],'recognition_basis':'ai_library_manifest'},
        approximate_identity=profile.get('nhan_dien_web') or {})
    item['views']=[{'id':v['id_hinh_goc'],'face':v.get('huong_nhin'),
        'dxf':(path.parent/v['duong_dan']).relative_to(ROOT).as_posix(),
        'placement':v.get('bo_tri_trong_tu') or {},'asset_role':v.get('asset_role') or 'device_projection',
        'unit_verification':v.get('unit_verification') or {},'projection_review':v.get('nhan_dien_mat') or {}}
        for v in profile.get('cad_don',[])]
index_path.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('Reviewed profiles indexed:',len(index['items']))
