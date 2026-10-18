"""Inventory incomplete, conflicting and unreviewed projections without guessing faces."""
import hashlib
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'


def main():
    rows=[];counts=Counter()
    for path in sorted(CAT.rglob('thong_tin_thiet_bi.json')):
        raw=json.loads(path.read_text(encoding='utf8'));views=[];hashes={}
        for view in raw.get('cad_don',[]):
            drawing=path.parent/view['duong_dan'];preview=drawing.with_name('xem_truoc.svg')
            face=view.get('huong_nhin') or '';issues=[]
            if not drawing.is_file():issues.append('missing_dxf')
            if not preview.is_file():issues.append('missing_preview')
            review=view.get('nhan_dien_mat') or {}
            if not review.get('method'):issues.append('projection_needs_individual_review')
            if any(word in face.lower() for word in ('thiếu','khuyết')):issues.append('source_linework_incomplete')
            if not face or any(word in face.lower() for word in ('chưa','unknown')):issues.append('projection_needs_source_or_manufacturer_comparison')
            if preview.is_file():
                digest=hashlib.sha256(preview.read_bytes()).hexdigest()
                if digest in hashes and hashes[digest]!=face:issues.append('same_preview_conflicting_face_labels')
                hashes[digest]=face
            views.append({'id':view['id_hinh_goc'],'face':face,'issues':issues,'projection_review':review})
            counts.update(issues)
        source=raw.get('source_catalog_review') or {}
        if len(views)==1 and source.get('component_type') not in {'ENCLOSURE_REFERENCE','NAMEPLATE'}:
            counts['single_view_needs_catalog_dimension_check']+=1
        rows.append({'profile':path.relative_to(CAT).as_posix(),'name':raw.get('ten_san_pham'),
            'brand':raw.get('hang_xac_nhan'),'views':views,'one_projection_only':len(views)==1,
            'ordering_code_verified':False,'view_completeness_verified':False})
    report={'profiles':len(rows),'view_uses':sum(len(r['views']) for r in rows),'issue_counts':dict(counts),'items':rows,
        'rule':'One view alone does not prove missing geometry. Never fabricate a missing projection; recover from matching source state or manufacturer CAD after model validation.'}
    (ROOT/'docs/all-catalog-projection-completeness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k!='items'}),flush=True)


if __name__=='__main__':main()
