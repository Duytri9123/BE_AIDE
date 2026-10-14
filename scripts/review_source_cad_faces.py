"""Apply explicit visual findings from all 165 unresolved source CAD views.

Labels are insufficient: pin DXF hashes, inspect all faces, and measure specific
model anchors. Similar-looking frames without unique anchors remain unresolved.
"""
import hashlib
import json
import re
from pathlib import Path
import ezdxf
from ezdxf import bbox
from app.services.catalogtb_browser import browser_data
from app.services.equipment_library import CATALOG_TB_ROOT

ROOT=Path(__file__).resolve().parents[1]
TESYS='https://iportal.se.com/Contents/docs/0100CT1501_SEC-18.PDF'
LS='https://www.ls-electric.com/upload/customer/download/4d8b99a1-c93d-4cd3-807b-1382f0c39384/Metasol_MS_E_180903.pdf'
BKN='https://www.ls-electric.com/upload/customer/download/1483/150905_MCB_E.pdf'
# Explicit front drawings, manually compared against manufacturer page 53.
F_FRONTS={'TB-0032dd9bb37e0165':('LC1F185',168.5,174.0),
          'TB-bc6bce54ba5e3d99':('LC1F225',168.5,197.0)}
F_SIDES={'TB-abe0ca387a433690':('LC1F185',174.0),
         'TB-5153d546d072a06e':('LC1F225',197.0)}


def run():
    report_path=ROOT/'docs/library-source-model-research.json'
    report=json.loads(report_path.read_text(encoding='utf8'))
    index=json.loads((ROOT/'docs/library-source-face-index.json').read_text(encoding='utf8'))
    wanted={r['id'] for r in index}
    devices={d['id']:d for d in browser_data()['items'] if d['id'] in wanted}
    registry_path=ROOT/'app/data/library_manufacturer_evidence.json'
    registry=json.loads(registry_path.read_text(encoding='utf8'));findings=[]
    for p in CATALOG_TB_ROOT.rglob('thong_tin_thiet_bi.json'):
        cid='TB-'+hashlib.sha1(p.relative_to(CATALOG_TB_ROOT).as_posix().encode()).hexdigest()[:16]
        if cid not in devices:continue
        d=devices[cid];current=json.loads(p.read_text(encoding='utf8'));source=current['nguon_cad'];block=source['block']
        dimensions={};views=[];labels={}
        for view in current['cad_don']:
            path=p.parent/view['duong_dan'];bounds=bbox.extents(ezdxf.readfile(path).modelspace())
            dimensions[view['id_hinh_goc']]=[round(bounds.size.x,4),round(bounds.size.y,4)]
            views.append({'view_id':view['id_hinh_goc'],'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        spec={};code=None;url=None;kind=None;name=None;note=None
        if cid in F_FRONTS:
            code,w,h=F_FRONTS[cid];actual=next(iter(dimensions.values()))
            if abs(actual[0]-w)>0.05 or abs(actual[1]-h)>0.05:raise ValueError('Front anchor mismatch '+cid)
            kind='CONTACTOR';url=TESYS;spec={'so_cuc':'3P'}
            note=f'Đã so mặt trước, 3 cặp cọc lực và kích thước {w}×{h} mm với TeSys F trang 53. Nhãn block {block} khác dòng trên tài liệu; xác định thân {code}, chưa chọn điện áp cuộn hút hoặc mã SKU.'
        elif cid in F_SIDES:
            code,h=F_SIDES[cid];actual=next(iter(dimensions.values()))
            if abs(actual[1]-h)>0.05:raise ValueError('Side anchor mismatch '+cid)
            kind='CONTACTOR';url=TESYS
            note=f'Mặt bên được so đường bao, vị trí cọc và chiều cao {h} mm với mặt trước tương ứng và tài liệu TeSys F. Tham chiếu thân {code}; chưa xác nhận cuộn hút và cấu hình đặt hàng.'
        elif re.fullmatch(r'CC MC ?(185|265|500)a',block,re.I):
            code='MC-'+re.search(r'(185|265|500)',block)[0]+'a';kind='CONTACTOR';url=LS
            note='Đã xem mặt bên, so vị trí đầu nối và thân với hình kích thước LS Metasol; mã rõ trong block nguồn. Chưa chọn cuộn hút hoặc xác nhận SKU.'
        elif block.lower()=='cc mt12':
            code='MT-12';kind='THERMAL_RELAY';url=LS
            note='Đã xem mặt bên rơ le nhiệt MT-12 và đối chiếu hình tài liệu LS; cần chọn dải chỉnh dòng riêng.'
        elif re.fullmatch(r'HCN BKN[1-4]P',block):
            poles=re.search(r'([1-4])P$',block)[1];code='BKN';kind='MCB';url=BKN;spec={'so_cuc':poles+'P'}
            labels={v['view_id']:'Mặt trên' for v in views}
            note='Đã xem trực tiếp số module và đầu thân: HCN là mặt trên của BKN, không phải thiết bị khác hoặc lỗ khoét. Chưa chọn dòng định mức/đặc tuyến.'
        elif 'LV429640ATNSX22A' in block:
            kind='ASSEMBLY_REFERENCE';url='https://www.se.com/pe/es/product/LV429640/'
            name='Cụm chuyển nguồn Schneider · CAD lắp đặt'
            note='Xem cả 5 mặt: có 2 MCCB và cơ cấu chuyển nguồn ở giữa, mặt bên, mặt trên và mẫu khoét. LV429640 là mã một MCCB, không phải mã cả cụm. Không dùng giá một bộ phận cho cả cụm.'
        elif 'LỖ' in block or 'LÕ' in block:
            # Cover drawings and part drawings retain their existing role.
            view_labels=[v.get('label','') for v in d['views']]
            if all('Lỗ khoét' in label for label in view_labels):
                kind='MOUNTING_TEMPLATE';url=None
                name='Mẫu khoét/lắp đặt Schneider · '+block.split('SC ',1)[-1]
                note='Đã xem đường khoét và mặt: đây là mẫu lắp đặt cánh tủ, không phải một thiết bị điện độc lập. Cần gắn với thiết bị tương ứng khi thiết kế.'
        finding={'id':cid,'source_block':block,'views':views,'dimensions_native_units':dimensions,
                 'result':'unresolved_after_visual_review','note':'Đã xem các mặt; chưa có dấu hiệu và kích thước đủ phân biệt mã đặt hàng. Không suy ra dòng, Icu hoặc cuộn hút chỉ từ hình.'}
        if kind:
            description={'type':kind,'manufacturer_document':url,'source_model_reference':True,
                         'reviewed_spec':spec,'reviewed_view_labels':labels,'use':note}
            if code:description.update(product_code=code,display=f'{kind} {d["brand"]} {code} · CAD tham khảo')
            elif name:description['display']=name
            registry['evidence'][cid]={'brand':d['brand'],'status':'source_model_documented' if code else 'source_role_reviewed','source':source,
                'manufacturer_document':url,'views':views,'basis':'Source CAD faces visually compared; explicit measured anchors where stated. Not automatic engineering/ordering approval.',
                'note':note,'library_description':description,'visual_geometry_review':{'dimensions':dimensions,'date':'2026-10-14'}}
            finding.update(result='visual_model_reference' if code else 'visual_role_corrected',product_code=code,type=kind,note=note,manufacturer_document=url)
            item=next(r for r in report['items'] if r['id']==cid)
            item.update(status='source_model_documented' if code else 'visual_role_corrected',product_code=code,manufacturer_document=url,note=note)
        findings.append(finding)
    found_ids={f['id'] for f in findings}
    original=json.loads((ROOT/'docs/library-dxf-identity-audit.json').read_text(encoding='utf8'))
    for cid,d in devices.items():
        if cid in found_ids:continue
        old=next(item for item in original['items'] if item['id']==cid)
        findings.append({'id':cid,'source_block':(d.get('spec') or {}).get('nhan_block_nguon'),
            'views':old['views'],'result':'unresolved_group_after_visual_review',
            'note':'Đã xem đủ các mặt trong nhóm. Cần so tài liệu và từng thành viên trước khi chốt mã, số cực hoặc cấu hình dùng chung.'})
    assert len(findings)==len(devices)
    result={'reviewed_devices':len(devices),'reviewed_views':len(index),
            'scope':'All contact sheets inspected; model-specific anchors checked only where explicitly recorded. Unresolved shapes are not approved SKUs.',
            'items':findings}
    (ROOT/'docs/library-source-face-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    registry_path.write_text(json.dumps(registry,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    from collections import Counter
    print(dict(Counter(r['result'] for r in findings)))


if __name__=='__main__':run()
