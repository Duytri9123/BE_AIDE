"""Apply individually reviewed face/family corrections without changing CAD bytes."""
import hashlib
import json
from pathlib import Path
from .catalog_source_identification import _drawing_hash
PATH=Path(__file__).resolve().parents[1]/'data/catalog_projection_corrections.json'


def apply_projection_corrections(profiles,root):
    registry=PATH if PATH.is_file() else PATH.with_name('published_projection_corrections.json')
    if not registry.is_file():return
    by_id={p['id']:p for p in profiles}
    def cid(relative):return relative if relative.startswith('TB-') else 'TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16]
    paths={cid(p.relative_to(root).as_posix()):p for p in root.rglob('thong_tin_thiet_bi.json')}
    for correction in json.loads(registry.read_text(encoding='utf8'))['items']:
        source=by_id.get(cid(correction['profile']))
        if not source:continue
        path=paths.get(cid(correction['profile']))
        if not path:continue
        raw=json.loads(path.read_text(encoding='utf8'))
        entry=next((v for v in raw.get('cad_don',[]) if v['id_hinh_goc']==correction['view'] or 'v-'+hashlib.sha256(v['id_hinh_goc'].encode()).hexdigest()[:20]==correction['view']),None)
        if not entry:continue
        drawing=(path.parent/entry['duong_dan']).resolve();preview=drawing.with_name('xem_truoc.svg')
        valid=True
        for file,key in ((drawing,'dxf_sha256'),(preview,'preview_sha256')):
            if not file.is_relative_to(root.resolve()) or not file.is_file():valid=False;break
            stat=file.stat()
            if _drawing_hash(str(file),(stat.st_mtime_ns,stat.st_size))!=correction[key]:valid=False;break
        if not valid:continue
        view=next((v for v in source['views'] if v['id']==entry['id_hinh_goc']),None)
        if not view:continue
        if correction['reference_only']:
            source['views'].remove(view)
        else:
            view['label']=view['face']=correction['face']
            if correction.get('target_profile'):
                target=by_id.get(cid(correction['target_profile']))
                if target and not any(v['id']==view['id'] for v in target['views']):
                    source['views'].remove(view);target['views'].append(view)
        if source['views'] and source['primary_view'] not in {v['id'] for v in source['views']}:
            source['primary_view']=source['views'][0]['id']
        source['auto_select']=False;source['needs_review']=True
