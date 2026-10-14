"""Track the folder-by-folder web review without equating review with price coverage."""
import hashlib
import json
import sys
from collections import Counter,defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app.services.catalogtb_browser import browser_data
from app.services.ai.takeoff_pricebook import published_rows
from app.services.library_price_matching import configuration_links,device_price_diagnostic
from app.services.equipment_library import CATALOG_TB_ROOT


def audit():
    paths={'TB-'+hashlib.sha1(p.relative_to(CATALOG_TB_ROOT).as_posix().encode()).hexdigest()[:16]:p
           for p in CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json')}
    registry=ROOT/'docs/library-folder-web-sources.json'
    reviews=json.loads(registry.read_text(encoding='utf8')) if registry.is_file() else {}
    groups=defaultdict(list);prices=published_rows()
    for d in browser_data()['items']:
        path=paths.get(d['id']) or next((paths[cid] for cid in d.get('member_profile_ids',[]) if cid in paths),None)
        if path is None:raise ValueError('Missing profile folder: '+d['id'])
        folder=path.relative_to(CATALOG_TB_ROOT).parts[0]
        groups[folder].append({'id':d['id'],'name':d.get('display'),'type':d.get('type'),'brand':d.get('brand'),
            'product_code':d.get('product_code'),'price_choices':len(configuration_links(d,prices)),
            'diagnostic':device_price_diagnostic(d['id'])})
    records=[]
    for folder,items in sorted(groups.items()):
        records.append({'folder':folder,'devices':len(items),'with_prices':sum(bool(i['price_choices']) for i in items),
            'review':reviews.get(folder,{'status':'pending_web_review','sources':[]}),
            'remaining_reasons':dict(Counter(i['diagnostic']['status'] for i in items if not i['price_choices'])),
            'items':items})
    return {'devices':sum(r['devices'] for r in records),'folders':records}


if __name__=='__main__':
    result=audit()
    assert result['devices']==837
    (ROOT/'docs/library-folder-price-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    lines=['# Rà thư viện theo thư mục','',
        'Một thư mục đã rà tài liệu web vẫn có thể còn thiếu giá hoặc mã cấu hình. Hãng/mã theo block nguồn và hãng đọc trực tiếp từ CAD được ghi riêng.','',
        '| Thư mục | CAD | Có lựa chọn giá | Chưa có lựa chọn | Trạng thái rà web |','| --- | ---: | ---: | ---: | --- |']
    for r in result['folders']:
        lines.append(f'| {r["folder"]} | {r["devices"]} | {r["with_prices"]} | {r["devices"]-r["with_prices"]} | {r["review"]["status"]} |')
    for r in result['folders']:
        lines += ['', '## '+r['folder'], '', r['review'].get('note','Chưa hoàn tất rà web cho thư mục này.'),'']
        lines += [f'- [{s["title"]}]({s["url"]})' for s in r['review'].get('sources',[])]
        lines += ['', '| Thiết bị | Hãng | Mã/dòng | Lựa chọn giá | Kết quả |','| --- | --- | --- | ---: | --- |']
        for i in r['items']:
            cells=[i['name'],i['brand'] or 'Chưa chỉ định hãng',i['product_code'] or 'Chưa xác nhận mã',i['price_choices'],i['diagnostic']['message'] or 'Có lựa chọn cấu hình; chốt mã đặt hàng riêng.']
            lines.append('| '+' | '.join(str(c).replace('|','/').replace('\n',' ') for c in cells)+' |')
    (ROOT/'docs/library-folder-price-audit.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    print(json.dumps([{k:r[k] for k in ('folder','devices','with_prices')} for r in result['folders']],ensure_ascii=False))
