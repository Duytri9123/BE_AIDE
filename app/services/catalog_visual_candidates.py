"""Checksum-bound visual candidates, separate from a device's identity."""
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from functools import lru_cache
from .catalog_source_identification import _load,_drawing_hash,validated_identification

PATH=Path(__file__).resolve().parents[1]/'data/catalog_visual_candidates.json'


@lru_cache(maxsize=2)
def _profile_paths(root):
    return {'TB-'+hashlib.sha1(p.relative_to(root).as_posix().encode()).hexdigest()[:16]:p for p in root.rglob('thong_tin_thiet_bi.json')}


def _profile_path(root,profile):
    return _profile_paths(root).get(profile) if profile.startswith('TB-') else (root/profile).resolve()


def matching_view(root,profile,view_id,dxf_hash,preview_hash):
    path=_profile_path(root,profile)
    if not path or not path.is_relative_to(root.resolve()) or not path.is_file():return None
    raw=json.loads(path.read_text(encoding='utf8'))
    view=next((v for v in raw.get('cad_don',[]) if v['id_hinh_goc']==view_id or 'v-'+hashlib.sha256(v['id_hinh_goc'].encode()).hexdigest()[:20]==view_id),None)
    if not view:return None
    drawing=(path.parent/view['duong_dan']).resolve();preview=drawing.with_name('xem_truoc.svg')
    for file,expected in ((drawing,dxf_hash),(preview,preview_hash)):
        if not file.is_relative_to(root.resolve()) or not file.is_file():return None
        stat=file.stat()
        if _drawing_hash(str(file),(stat.st_mtime_ns,stat.st_size))!=expected:return None
    return view


def apply_visual_candidates(profiles,root):
    registry=PATH if PATH.is_file() else PATH.with_name('published_visual_candidates.json')
    if not registry.is_file():return
    stat=registry.stat();records=_load(str(registry),(stat.st_mtime_ns,stat.st_size))
    public={cid:profile for profile in profiles for cid in profile.get('member_profile_ids') or [profile['id']]}
    def cid(relative):return relative if relative.startswith('TB-') else 'TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
    for relative,candidates in records.items():
        target=public.get(cid(relative))
        if not target:continue
        result=[]
        for record in candidates:
            if not matching_view(root,relative,record['source_view'],record['source_dxf_sha256'],record['source_preview_sha256']):continue
            if not matching_view(root,record['candidate_profile'],record['candidate_view'],record['candidate_dxf_sha256'],record['candidate_preview_sha256']):continue
            donor_path=_profile_path(root,record['candidate_profile'])
            donor_raw=json.loads(donor_path.read_text(encoding='utf8'))
            reviewed=validated_identification(donor_raw,donor_path,root)
            if not reviewed or reviewed['status']!='documented_source_label':continue
            if {(m['brand'],m['model']) for m in record['models']}!={(m['brand'],m['model']) for m in reviewed['documented_models']}:continue
            donor=public.get(cid(record['candidate_profile']))
            if not donor:continue
            view=next((v for v in donor['views'] if v['id']==record['candidate_view'] or 'v-'+hashlib.sha256(v['id'].encode()).hexdigest()[:20]==record['candidate_view']),None)
            if not view:continue
            docs={d['url']:d for m in record['models'] for d in m['documents']}
            result.append({'source_view':record['source_view'],'comparison_device_id':donor['id'],
                'comparison_view':record['candidate_view'],
                'comparison_name':donor['display'],'comparison_preview':view['preview'],
                'models':[{'brand':m['brand'],'model':m['model']} for m in record['models']],
                'documents':[{'url':d['url'],'page':d.get('page')} for d in docs.values()],
                'source_domains':sorted({urlparse(url).hostname for url in docs}),
                'corroboration_status':'multiple_documents_to_review' if len(docs)>1 else 'needs_additional_source',
                'basis':'So sánh ảnh nét CAD và tỷ lệ bao hình; chưa kiểm tra nhãn, kích thước và cấu hình tương ứng.',
                'identity_verified':False,'manual_reviewed':record.get('manual_reviewed',False)})
        if result:target['visual_candidates']=result
