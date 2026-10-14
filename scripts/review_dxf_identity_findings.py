"""Apply three explicit text findings from the full DXF extraction audit."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FINDINGS={
 'TB-7cc48f9630399020':('IDEC','IDEC',{'display':'Công tắc xoay IDEC · chưa rõ mã','type':'SELECTOR_SWITCH',
    'use':'Chọn chế độ điều khiển. SW0.1 là nhãn trên CAD, chưa xác nhận mã đặt hàng.'}),
 'TB-043714973953d640':('RISESUN','RISESUN',{'display':'Cụm cầu chì RISESUN RT18-32','type':'FUSE','product_code':'RT18-32',
    'use':'Bảo vệ bằng cầu chì; CAD ghi RT18-32, 32A, 690V và 10×38. Cần xác nhận mã và nguồn giá thực tế.'}),
 'TB-c02623ff6b0d78b7':('Elr DIN 310','MIKRO',{'display':'Rơ le bảo vệ dòng rò MIKRO DIN310','type':'EARTH_LEAKAGE_RELAY','product_code':'DIN310',
    'manufacturer_document':'https://itmikro.com.my/wp-content/uploads/2020/08/din310_man-1.pdf',
    'use':'Đo dòng rò qua ZCT và phát lệnh cắt. Đây là rơ le dòng rò, không phải bộ giám sát pha.'})
}


if __name__=='__main__':
    audit=json.loads((ROOT/'docs/library-dxf-identity-audit.json').read_text(encoding='utf8'))
    path=ROOT/'app/data/library_manufacturer_evidence.json'
    data=json.loads(path.read_text(encoding='utf8'))
    for cid,(text,maker,description) in FINDINGS.items():
        device=next(d for d in audit['items'] if d['id']==cid)
        views=[{'view_id':v['view_id'],'sha256':v['sha256']} for v in device['views'] if text in v.get('texts',[])]
        if not views:raise ValueError('Expected drawing text missing: '+cid)
        data['evidence'][cid]={'brand':maker,'status':'manufacturer_label_reviewed','views':views,
            'basis':'Exact DXF lettering reviewed; DIN310 matched to original Mikro user manual where maker is implicit.',
            'note':'Hãng/mã được đối chiếu từ chữ trong CAD; cấu hình điện và mã đặt hàng đầy đủ được chọn riêng.',
            'library_description':description}
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Updated',len(FINDINGS),'hash-bound identity findings')
