"""Expose every unresolved view and evidence, without inventing its projection."""
import html,json,sys
from collections import Counter
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(BASE))
from app.services.cad import catalogtb_assets as ca
OUT=BASE.parent/'outputs/catalogtb-projection-review'
evidence=json.loads((OUT/'evidence.json').read_text(encoding='utf8'))
cards={(r['profile'],r['view']):r for r in evidence}
remaining=[]
for asset in ca.assets(refresh=True):
    if asset['face']!='unknown':continue
    p=ca.ROOT/asset['profile_path'];profile=json.loads(p.read_text(encoding='utf8'))
    entry=next(v for v in profile['cad_don'] if (p.parent/v['duong_dan']).resolve()==Path(asset['original_path']))
    card=cards.get((asset['profile_path'],entry['id_hinh_goc'])) or {}
    number=card.get('number')
    if number in [63,73,160,189,232,241]:reason='Hình cả cụm/phụ kiện; chưa xác định mặt độc lập và phạm vi thiết bị.'
    elif number in [64,72,79,89]:reason='Hình vùng tay gạt/nắp/lỗ; chưa đủ căn cứ phân biệt mặt thiết bị với lỗ khoét.'
    elif number in [76,78,81,87,92,93,94,95,163]:reason='Hình nhìn đầu thiết bị; chưa phân biệt mặt trên với mặt dưới từ mốc nguồn.'
    elif asset['profile_path'].split('/')[0] in ['Phíp','Phụ kiện tủ điện']:
        reason='Phụ kiện cơ khí: CAD chưa có mốc lắp để xác định mặt trên/bên/trước.'
    elif entry.get('huong_nhin')=='CAD thiếu đường nét':reason='Có lỗi hình học đã ghi nhận; xác định hướng không khắc phục được thiếu nét.'
    else:reason='Chưa có đủ cặp hình chiếu hoặc mốc CAD để xác nhận hướng và tư thế lắp.'
    remaining.append({'profile':asset['profile_path'],'view':entry['id_hinh_goc'],
        'name':asset['name'],'group':profile.get('nhom'),'card':number,
        'image':card.get('image'),'reason':reason,'automatic_insertion_allowed':False})
summary={'unknown_faces':len(remaining),'groups':dict(Counter(r['group'] for r in remaining))}
(OUT/'remaining-views.json').write_text(json.dumps({'summary':summary,'views':remaining},ensure_ascii=False,indent=2),encoding='utf8')
esc=lambda value:html.escape(str(value or ''))
parts=['<!doctype html><meta charset="utf-8"><title>Đối chiếu hướng nhìn CatalogTB</title><style>body{font:15px Arial;max-width:1250px;margin:30px auto;color:#243547}article{display:grid;grid-template-columns:260px 1fr;gap:20px;border:1px solid #d8dfe6;border-radius:10px;margin:15px 0;padding:15px}img{max-width:250px;max-height:280px;background:#202830}small{overflow-wrap:anywhere;color:#586674}</style>',
    '<h1>Các mặt còn cần xác minh</h1>',
    '<p>Đã bổ sung 176 mặt theo ảnh, sửa 33 nhãn bị bộ nạp coi là không rõ; còn '+str(len(remaining))+' mặt. Đơn vị của 195 mặt được hiệu chuẩn từ tài liệu hãng, không thay đổi tọa độ CAD.</p>']
for r in remaining:
    parts.append('<article><a href="'+esc(r['image'])+'"><img src="'+esc(r['image'])+'"></a><div><h3>'+esc(r['name'])+'</h3><p>'+esc(r['reason'])+'</p><small>'+esc(r['profile'])+'<br>'+esc(r['view'])+'</small></div></article>')
(OUT/'remaining-review.html').write_text('\n'.join(parts),encoding='utf8')
print(json.dumps(summary,ensure_ascii=True))
