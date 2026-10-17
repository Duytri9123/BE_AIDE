"""Source-label evidence, independent of selectable catalog references."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path

PATH=Path(__file__).resolve().parents[1]/'data/catalog_source_identification.json'


def model_pattern(value):
    chunks=re.findall(r'[A-Z]+|[0-9]+',str(value).upper())
    if not chunks or not any(any(c.isdigit() for c in chunk) for chunk in chunks):return None
    return re.compile(r'(?<![A-Z0-9])'+r'[\s_./\-‐‑‒–—−－]*'.join(re.escape(c) for c in chunks)+r'(?![A-Z0-9])',re.I)


def source_fingerprint(raw):
    fields={k:raw.get(k) for k in ('ma_dong_san_pham','hang_xac_nhan','nguon_cad')}
    fields['views']=[(v.get('id_hinh_goc'),v.get('duong_dan')) for v in raw.get('cad_don') or []]
    return hashlib.sha256(json.dumps(fields,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


@lru_cache(maxsize=2)
def _load(path,revision):
    return json.loads(Path(path).read_text(encoding='utf8')).get('profiles',{})


def identifications():
    path=PATH if PATH.is_file() else PATH.with_name('published_catalog_identification.json')
    if not path.is_file():return {}
    stat=path.stat()
    return _load(str(path),(stat.st_mtime_ns,stat.st_size))


@lru_cache(maxsize=8192)
def _drawing_hash(path,revision):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validated_identification(raw,path,root):
    relative=path.relative_to(root).as_posix();records=identifications()
    record=records.get(relative) or records.get('TB-'+hashlib.sha1(relative.encode()).hexdigest()[:16])
    if not record or record.get('source_fingerprint')!=source_fingerprint(raw):return None
    for view in record.get('views') or []:
        if view.get('path'):drawing=(root/view['path']).resolve()
        else:
            entry=next((v for v in raw.get('cad_don',[]) if 'v-'+hashlib.sha256(v['id_hinh_goc'].encode()).hexdigest()[:20]==view['id']),None)
            if not entry:return None
            drawing=(path.parent/entry['duong_dan']).resolve()
        if not drawing.is_relative_to(root.resolve()) or not drawing.is_file():return None
        stat=drawing.stat()
        if _drawing_hash(str(drawing),(stat.st_mtime_ns,stat.st_size))!=view['sha256']:return None
    observation=record.get('reviewed_outline_label')
    if observation:
        view=next((v for v in record.get('views',[]) if v['id']==observation['view']),None)
        if not view:return None
        preview=(root/view['path']).with_name('xem_truoc.svg')
        if not preview.is_file():return None
        stat=preview.stat()
        if _drawing_hash(str(preview),(stat.st_mtime_ns,stat.st_size))!=observation['preview_sha256']:return None
    return record


def apply_source_identification(profile,raw,path,root):
    record=validated_identification(raw,path,root)
    if not record:
        reference=profile.get('catalog_references') or {}
        if reference.get('source_identification'):
            reference={**reference,'options':[{**o,'basis':'catalog_type_reference',
                'note':'Thông tin catalog tham khảo; bằng chứng nhãn của phiên bản CAD hiện tại cần đối chiếu lại.'}
                if o.get('basis')=='verified_cad_label' else o for o in reference.get('options') or []]}
            reference.pop('source_identification',None)
            reference['research']={**(reference.get('research') or {}),'source_label_documented':False,
                'status':'source_model_requires_catalog_check' if raw.get('ma_dong_san_pham') else 'requires_source_identification'}
            profile['catalog_references']=reference
        return
    public={k:v for k,v in record.items() if k not in {'source_fingerprint','views'}}
    profile['source_identification']=public
    models=record.get('documented_models') or []
    # Display the actual source label even when the brand is only a candidate.
    # A catalog model label never fills electrical settings or approves geometry.
    if not profile.get('product_code') and len(models)==1 and not record.get('contains_multiple_components'):
        if record.get('status')=='documented_source_label':
            profile['product_code']=models[0]['model']
            display=str(profile.get('display') or '')
            display=re.sub(r'mẫu nguồn\s+\d+',models[0]['model']+' · nhãn CAD',display,flags=re.I)
            display=re.sub(r'chưa rõ mã','nhãn CAD '+models[0]['model'],display,flags=re.I)
            profile['display']=display
    if models:
        reference=dict(profile.get('catalog_references') or {})
        reference['source_identification']=public
        profile['catalog_references']=reference
    profile['search_aliases']=list(dict.fromkeys([*(profile.get('search_aliases') or []),
        *(m['model'] for m in models)]))
