"""Record original-block and manufacturer-document review of six remaining CADs."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding='utf8'))
def write(p,d):(ROOT/p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')

def main():
    cid='TB-991b8c4a7bab4123'
    url='https://prod-edam.honeywell.com/content/dam/honeywell-edam/pmt/hps/products/sme/electricity/commercial-and-industrial-meters/a1700/A1700-31052012.pdf'
    reviews=read('app/data/library_control_meter_review.json')
    row=reviews[cid]
    row['display']='Công tơ điện tử Elster A1700 (dòng ABB Vision)'
    row['note']='Block gốc ghi A1700; đối chiếu datasheet Elster trên website Honeywell và tài liệu ABB Vision/Elster của ESB. Xác nhận dòng A1700, chưa xác nhận đời nhãn, mã đặt hàng, kiểu đấu hoặc kích thước lắp của bản CAD này.'
    row['identification_review']={'status':'source_model_documented','observed':'Nhãn A1700 trong block *U2438.',
        'missing':'Dòng/áp, kiểu đấu trực tiếp hay qua CT, tùy chọn và kích thước gá; CAD 173.5×311.6 không đồng nhất kích thước thân catalog 170×279.',
        'comparison_source':url,'source_is_confirmed_match':True,'geometry_confirmed':False}
    evidence=read('app/data/library_manufacturer_evidence.json')
    evidence['evidence'][cid]={'brand':'Elster','status':'manufacturer_label_reviewed',
        'basis':'Literal A1700 model in original block *U2438 matched to Elster manufacturer datasheet hosted by Honeywell. ABB Vision is documented legacy lineage; exact badge/era and installation geometry remain unverified.',
        'source_export_sha256':'cc201e73955a9f06a3bae5c369a3bce6e9117ff6867fdc283f999f220d47843d',
        'source_blocks':[r for r in read('docs/library-control-meter-original-blocks.json') if r['id']==cid],
        'views':[{'view_id':v['id'],'sha256':v['sha256']} for v in row['views']],
        'note':row['note'],'library_description':{'display':row['display'],'type':'METER','product_code':'A1700',
          'manufacturer_document':url,'source_model_reference':True,'reviewed_spec':{'Dòng thiết bị':'Công tơ điện tử đa chức năng A1700','Cấu hình điện':'Chưa xác định biến thể trực tiếp / qua CT và điện áp'},'use':'Đo đếm điện năng; chọn cấu hình đấu dây và định mức theo nhãn thiết bị.'}}
    findings={
      'TB-8c40e2d424325405':('https://catalogue.lovatoelectric.com/gl_en/ATL20A240/snp','ATL20/30 có 8 phím, mặt 144×144; không khớp hình đứng 6 phím. MicroLogic P cũng có 6 phím nhưng chưa có nhãn hoặc bố trí đầy đủ để nhận hãng. Không đủ căn cứ giữ ATS là chức năng đã xác nhận.'),
      'TB-c6b859d113fa6bca':('https://sol.ls-electric.com/uploads/document/16411846892410/iG5A_User%2BManual%28Standard%29_Eng_210303.pdf','BT7.5 chỉ là tên block; mặt quạt/tản nhiệt không có chữ. Không đủ căn cứ gán LS iG5A hoặc coi 7.5 là công suất đã xác nhận.'),
      'TB-eeb533e15b1abd01':('https://www.kdsimeter.com/New-Model-BE-96-DC60mV-500A-Analog-Panel-DC-High-Precision-Ammeter-pd508517068.html','KDSI BE-96 có 96×96 và thang 500A nhưng có thể OEM, bản tham khảo DC60mV; CAD không xác nhận AC/DC hay CT/shunt. Không gán hãng theo kích thước.'),
      'TB-83c508f9a35bfbcf':('https://www.em.co.za/BE-96-500VAC','BE-96 500VAC là mẫu tham khảo 96×96. CAD chỉ có V và thang 500; chưa có logo/AC/DC. Không tự điền AC500V hay hãng EM.'),
      'TB-2250a9171c9f2733':('','Block nguồn có A/V, 400 và ký hiệu AC; ba hình gồm hai cấu hình đo khác nhau và mặt bên. Không có nhãn hãng/model, chưa xác nhận tỉ số CT hoặc kiểu đấu. Giữ loại ampe kế/vôn kế AC và thang 400 đã đọc được.')}
    report=read('docs/library-control-meter-18-followup.json')
    for item in report['items']:
        if item['id']==cid:
            item.update(name=row['display'],brand='Elster',model='A1700',manufacturer_confirmed=True,status='source_model_documented',comparison_source=url,missing=row['identification_review']['missing'])
        elif item['id'] in findings:
            source,note=findings[item['id']]
            item['review_2026_10_15']={'source':source,'conclusion':note}
            reviews[item['id']]['identification_review']['latest_comparison']=note
    reviews['TB-8c40e2d424325405']['display']='Bộ điều khiển · màn hình và 6 phím (chưa rõ chức năng)'
    reviews['TB-c6b859d113fa6bca']['display']='Bản vẽ biến tần · mặt quạt, block BT7.5'
    report['scope']='Reviewed all six remaining CADs against source labels, drawings and manufacturer references. A1700 family identified as Elster / legacy ABB Vision; five lack manufacturer/model evidence. Prices not required.'
    write('app/data/library_control_meter_review.json',reviews)
    write('app/data/library_manufacturer_evidence.json',evidence)
    write('docs/library-control-meter-18-followup.json',report)
    lines=['# Rà soát 18 CAD điều khiển và đo lường','','Đã xác định hãng/dòng cho 13/18 CAD; còn 5 CAD chưa đủ bằng chứng hãng/mã. Đây là số trong nhóm 18 CAD, không phải số toàn thư viện. Giá không phải điều kiện xác nhận.','','| CAD | Thiết bị | Hãng | Mã/dòng |','| --- | --- | --- | --- |']
    lines += ['| '+' | '.join([i['id'],reviews.get(i['id'],{}).get('display') or i['name'],i.get('brand') or '',i.get('model') or ''])+' |' for i in report['items']]
    lines+=['','## Sáu CAD đã tra cứu lại','',row['note'],f'Nguồn A1700: {url}','']
    lines += [f'- {key}: {note}'+(f' Nguồn: {source}' if source else '') for key,(source,note) in findings.items()]
    (ROOT/'docs/library-control-meter-18-followup.md').write_text('\n'.join(lines)+'\n',encoding='utf8')

if __name__=='__main__':main()
