"""Audit all LS view files and reconcile exact MCCB/ELCB rows from supplied PDF page 1.

Does not infer a face from geometry or approve CAD from a homepage citation.
"""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path
import ezdxf
from ezdxf import bbox

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'data/thu_vien_tu_dien_v2'
FACES={'front':('cad.dxf','front.svg','Mặt trước'), 'side':('side.dxf','side.svg','Mặt bên'),
       'back':('back.dxf','back.svg','Mặt sau'), 'top':('top.dxf','top.svg','Mặt trên'),
       'bottom':('bottom.dxf','bottom.svg','Mặt dưới'), 'cutout':('cutout.dxf','cutout.svg','Lỗ khoét')}

def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def price_rows(tables):
    rows=[]
    poles=None
    for table in tables[0]:
        for r in table:
            title=r[0] or ''
            m=re.search(r'([234]) (?:Pha|pha)',title)
            if m and not r[-1]: poles=int(m[1])
            if len(r)!=4 or not re.fullmatch(r'\d{1,3}(?:,\d{3})+',r[3] or ''): continue
            if not re.match(r'^(AB[NS]|EB[NSE]|TS)',title): continue
            rows.append(dict(model=title.split()[0].upper(),poles=poles,
                             currents=[int(x) for x in re.findall(r'\d+',r[1])],
                             icu=float(r[2]),price=int(r[3].replace(',','')),page=1))
    return rows

def match_price(sku,current,poles,rows):
    model=sku.split()[0].upper()
    currents=[int(x) for x in re.findall(r'\d+',str(current))]
    matches=[r for r in rows if r['model']==model and r['poles']==poles
             and currents and all(x in r['currents'] for x in currents)]
    return matches[0] if len(matches)==1 else None

def run(tables_path):
    tables=json.loads(Path(tables_path).read_text(encoding='utf8'))
    prices=price_rows(tables)
    save(BASE/'nguon/ls_price_2026_10_01_tables.json',tables)
    report={'groups':[], 'price_changes':[], 'price_unmatched':[], 'scope':'78 LS folders; DXF structure and extents, not visual approval. Price reconciliation: exact page-1 MCCB/ELCB rows only.'}
    external_path=BASE/'nguon/ls_external/manifest.json'
    external=json.loads(external_path.read_text(encoding='utf8')) if external_path.exists() else []
    for file in sorted((BASE/'LS').rglob('data.json')):
        data=json.loads(file.read_text(encoding='utf8')); folder=file.parent; rel=folder.relative_to(BASE).as_posix()
        category=folder.relative_to(BASE/'LS').parts[0]
        poles=data.get('poles') or (int(folder.name[0]) if re.fullmatch('[1-4]P',folder.name) else None)
        issues=[]; views=[]
        models={v.get('sku','').split()[0].upper() for v in data.get('variants',[]) if v.get('sku')}
        if len(models)>1 and category in ('MCCB','ELCB','ACB'):
            issues.append('Nhóm chứa nhiều mã khung; chưa đủ bằng chứng dùng chung kích thước/CAD.')
        if 'ABN402C' in models and poles!=2:
            issues.append('ABN402c là 2P theo bảng giá trang 1; dữ liệu nhóm đang ghi 3P. Không tự gán CAD 3P.')
        for face,(cad,preview,title) in FACES.items():
            path=folder/cad
            row=dict(face=face,title=title,status='missing',approved_for_layout=False)
            if path.exists():
                try:
                    doc=ezdxf.readfile(path); audit=doc.audit(); bounds=bbox.extents(doc.modelspace())
                    good=bounds.has_data and len(doc.modelspace())>0 and not audit.errors and not audit.fixes
                    row.update(status='needs_model_and_face_review' if good else 'invalid_geometry',
                               cad_path=path.relative_to(BASE).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               entity_count=len(doc.modelspace()),units_code=doc.units,
                               audit_errors=len(audit.errors),audit_fixes=len(audit.fixes))
                    if bounds.has_data: row['drawing_extent_mm_if_units_4']=[round(bounds.size.x,4),round(bounds.size.y,4)]
                    if (folder/preview).exists(): row['preview_path']=(folder/preview).relative_to(BASE).as_posix()
                except Exception as exc: row.update(status='invalid_geometry',error=str(exc))
            views.append(row)
        data['views']=views
        if 'verification' in data and 'verification_before_ls_audit' not in data:
            data['verification_before_ls_audit']=data['verification']
        data['verification']={'status':'NEEDS_REVIEW','cad_device_match':'NOT_ESTABLISHED',
                              'front_view_verified':False,'side_view_verified':False,
                              'reason':'Chưa có tài liệu theo mã và mặt xác nhận hình học. PDF bảng giá không xác nhận kích thước.'}
        data['review_issues']=issues
        data['dimensions_status']='unverified_not_certified_by_price_list'
        data['external_sources']=[{'title':'LS Product Finder · chọn đúng mã rồi CAD Data','url':'https://pfinder.ls-electric.com/IEC/product/'+('mc.do' if category=='Contactor' else 'tor.do' if category=='Ro_le' else 'mccb_metasol.do' if category in ('MCCB','ELCB') else 'mccb_susol.do' if category=='ACB' else 'mc.do')}]
        # Generic download center for categories without a verified product finder URL.
        if category not in ('Contactor','Ro_le','MCCB','ELCB'):
            data['external_sources']=[{'title':'LS ELECTRIC · Download Center','url':'https://www.ls-electric.com/support/download-center'}]
        data['external_reference_files']=[r for r in external if
            (category in ('MCCB','ELCB') and ('MCCB' in r['name'] or 'AB_bX' in r['name'])) or
            (category=='Contactor' and 'MC-' in r['name']) or
            (category=='Ro_le' and 'MT' in r['name']) or
            (category=='ACB' and 'AN_AS_AH' in r['name'])]
        for v in data.get('variants',[]):
            match=match_price(v.get('sku',''),v.get('in'),poles,prices)
            if match:
                old=v.get('price'); v['price']=match['price']; v['icu']=match['icu']
                v['price_source']={'file':'nguon/ls_price_2026_10_01_tables.json','page':1,'effective_date':'2026-10-01','vat_included':False}
                if old!=v['price']: report['price_changes'].append({'folder':rel,'sku':v['sku'],'old':old,'new':v['price']})
            elif category in ('MCCB','ELCB'):
                report['price_unmatched'].append({'folder':rel,'sku':v.get('sku'),'current':v.get('in')})
                v['price_review_status']='not_matched_to_page_1'
        save(file,data)
        report['groups'].append({'folder':rel,'issues':issues,'faces':views})
    report['face_counts']=dict(collections.Counter(v['status'] for g in report['groups'] for v in g['faces']))
    save(BASE/'ls_review.json',report)
    print(json.dumps({'groups':len(report['groups']),'price_changes':len(report['price_changes']),'unmatched':len(report['price_unmatched']),'faces':report['face_counts']},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('tables');run(parser.parse_args().tables)
