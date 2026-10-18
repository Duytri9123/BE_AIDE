"""Publish source-label findings; keep candidate makers and order-code gaps explicit."""
import json
from pathlib import Path
from app.services.catalog_source_identification import validated_identification

ROOT=Path(__file__).resolve().parents[1]
CAT=ROOT/'data/CatalogTB'


def main():
    updated=0;labels=0
    for path in CAT.rglob('thong_tin_thiet_bi.json'):
        raw=json.loads(path.read_text(encoding='utf8'))
        evidence=validated_identification(raw,path,CAT)
        if not evidence:continue
        reference=raw['catalog_tham_khao'];options=reference['options']
        if not evidence['documented_models'] and evidence['status']!='source_label_conflict':
            reference['source_identification']={k:v for k,v in evidence.items() if k not in {'views','source_fingerprint'}}
            reference.setdefault('research',{}).update(status=evidence['status'],checked_at='2026-10-17',
                source_label_documented=False,ordering_code_verified=False,geometry_verified=False)
            path.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
            updated+=1
            continue
        options[:]=[o for o in options if o.get('basis')!='verified_cad_label']
        for model in reversed(evidence['documented_models']):
            document=model['documents'][0]
            options.insert(0,{'brand':model['brand'],'model':model['model'],
                'specifications':{'Căn cứ':'Nhãn đọc trực tiếp từ CAD nguồn, đối chiếu tài liệu sản phẩm',
                    'Phạm vi':'Mã/dòng trên bản vẽ; chưa xác nhận mã đặt hàng hoặc cấu hình điện',
                    'Trang tài liệu':document['page']},
                'source_url':document['url'],'source_page':document['page'],
                'basis':'verified_cad_label','price':'---','exact_cad_match':False,
                'note':'Hãng '+('được ghi trong hồ sơ nguồn' if model['manufacturer_confirmed_on_source'] else
                    'là ứng viên theo mã trong tài liệu; chưa xác nhận logo trên CAD')+'. Chưa xác nhận kích thước lắp.'})
        reference['source_identification']={k:v for k,v in evidence.items() if k not in {'views','source_fingerprint'}}
        review=reference.setdefault('research',{})
        review.update(source_label_documented=True,source_label_models=[m['model'] for m in evidence['documented_models']],
                      ordering_code_verified=False,geometry_verified=False)
        if evidence['status'] in {'documented_source_label','source_label_conflict'}:review['status']=evidence['status']
        if evidence.get('reviewed_outline_label'):
            review['source_label_note']=evidence['reviewed_outline_label']['note']
            review['source_label_documented']=bool(evidence['documented_models'])
        model_names=list(dict.fromkeys(m['model'] for m in evidence['documented_models']))
        brands=list(dict.fromkeys(m['brand'] for m in evidence['documented_models']))
        web=raw.setdefault('nhan_dien_web',{})
        web['source_label_review']={'status':evidence['status'],'models':model_names,
            'manufacturer_candidates':brands,'checked_at':'2026-10-17',
            'ordering_code_verified':False,'geometry_verified':False}
        raw['tu_khoa_tim_kiem']=list(dict.fromkeys([*(raw.get('tu_khoa_tim_kiem') or []),*model_names]))
        # Preserve stronger pre-existing candidate records and confirmed makers.
        if not raw.get('hang_xac_nhan') and len(brands)==1 and not web.get('brand_candidate'):
            web.update(brand_candidate=brands[0],status='candidate_from_documented_source_label')
        path.write_text(json.dumps(raw,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        updated+=1;labels+=len(model_names)
    from scripts.export_published_catalog_information import main as publish
    from scripts.refresh_catalogtb_offline_information import main as offline
    publish();offline()
    print(json.dumps({'updated_profiles':updated,'documented_labels':labels,'ordering_codes_auto_selected':0}),flush=True)


if __name__=='__main__':main()
