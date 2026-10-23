"""Apply a visual orientation review only while its source DXF hash still matches."""
import hashlib
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=512)
def _hash(path,revision):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def apply_projection_review(profile,raw,path):
    entries={v['id_hinh_goc']:v for v in raw.get('cad_don',[])}
    reviewed=False
    for view in profile.get('views',[]):
        entry=entries.get(view['id']) or {};review=entry.get('orientation_review') or {}
        if review.get('status')!='orientation_identified':continue
        drawing=(path.parent/entry.get('duong_dan','')).resolve()
        if not drawing.is_relative_to(path.parent.resolve()) or not drawing.is_file():continue
        stat=drawing.stat()
        if _hash(str(drawing),(stat.st_mtime_ns,stat.st_size))!=review.get('source_dxf_sha256'):continue
        if review.get('reviewed_label')!=entry.get('huong_nhin'):continue
        view['label']=view['face']=entry['huong_nhin'];reviewed=True
    # A whole drawing sheet must not revert to one of its component types due
    # to older manufacturer/model enrichment bound to the same source drawing.
    if reviewed and (raw.get('nhan_dien_ai') or {}).get('loai_thiet_bi_code')=='ASSEMBLY_REFERENCE' and (raw.get('source_catalog_review') or {}).get('contains_multiple_components'):
        profile.update(type='ASSEMBLY_REFERENCE',display=raw['ten_san_pham'],product_code=None,auto_select=False,needs_review=True,catalog_references={'category':'ASSEMBLY_REFERENCE','options':[]})
    return reviewed
