"""Inventory named CAD blocks beyond the six price-table zones."""
import html
import json
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
CAT=ROOT/'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
SOURCE=CAT/'02_BLOCK_VA_THIET_BI'
excluded={'D01','D02','D03','D04','D05','D06'}
reviewed={
    'B_7dfcc870f53f': 'Đã xem DXF: mặt bên Shihlin, không có mã model hoặc số cực; chưa đủ căn cứ ghép dòng giá.',
    'B_99e5cfa9e951': 'CAD ABN 400c ngoài F02; họ ABN400c và trạng thái 2P/4P đã được đối chiếu tại bảng LS.',
    'B_e1e16ab8e872': 'CAD ABN 400c ngoài F01; họ ABN400c và trạng thái 2P/4P đã được đối chiếu tại bảng LS.',
    'B_b6602f58690c': 'Block đồng hồ PM2220, ngoài các họ MCB/MCCB đang có trong bảng giá Schneider.',
}
rows=[]
for file in SOURCE.glob('*/thong_tin.json'):
    item=json.loads(file.read_text(encoding='utf8'))
    if excluded.intersection(item.get('zones',[])): continue
    brands=sorted({x['name'] for x in item.get('brand_mentions',[])})
    if not brands: continue
    cad=CAT/item.get('cad',{}).get('path','')
    if not cad.is_file(): continue
    rows.append({'id':item['id'],'brands':brands,
                 'display_name':item.get('display_name') or item['source_block_name'],
                 'block_name':item['source_block_name'],
                 'zones':item.get('zones',[]),
                 'placed_count':item.get('placed_count',0),
                 'text_evidence':item.get('text_evidence',[])[:8],
                 'cad_dxf':cad.relative_to(CAT).as_posix(),
                 'status':reviewed.get(item['id'],'Ứng viên ngoài D01–D06; chưa ghép mã giá'),
                 'preview':(cad.with_name('cad-verified.png').relative_to(CAT).as_posix()
                            if cad.with_name('cad-verified.png').is_file() else None)})
rows.sort(key=lambda x:(','.join(x['brands']),x['display_name']))
(CAT/'outside_cad_audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
cells=[]
for i,row in enumerate(rows,1):
    label=html.escape(row['display_name'])
    evidence=html.escape(' · '.join(row['text_evidence']) or 'Chưa có chữ model trong block')
    picture=f'<a href="{html.escape(row["preview"])}"><img src="{html.escape(row["preview"])}" alt="Ảnh kiểm tra CAD" width="95"></a>' if row['preview'] else ''
    cells.append(f'<tr><td>{i}</td><td>{html.escape(", ".join(row["brands"]))}</td><td><strong>{label}</strong><small>{html.escape(row["block_name"])}</small></td><td>{html.escape(", ".join(row["zones"]) or "Chưa đặt")}</td><td>{evidence}</td><td>{picture}<a href="{html.escape(row["cad_dxf"])}" download>DXF nguồn</a></td><td>{html.escape(row["status"])}</td></tr>')
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Kiểm tra CAD ngoài D01–D06</title><style>*{box-sizing:border-box}body{font:14px system-ui;color:#183044;background:#edf2f6;margin:0}main{max-width:1450px;margin:auto;padding:20px}h1{margin:0 0 9px}.lead{background:#fff;border:1px solid #cbd9e3;border-radius:9px;padding:18px;line-height:1.5}.tools{padding:12px 0}input{width:100%;padding:9px;border:1px solid #afc4d5;border-radius:6px;font:inherit}.wrap{overflow:auto;background:#fff;border:1px solid #cbd9e3}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #dae4eb;vertical-align:top;text-align:left}th{background:#e5edf3}small{display:block;color:#5c7282}a{color:#075e9f}img{display:block;border:1px solid #cbd9e3;margin-bottom:4px}</style><main><div class="lead"><h1>CAD ở các vùng khác của bản vẽ gốc</h1><p>Danh sách block có tên hãng hoặc chữ hãng, nằm ngoài D01–D06. Các hình này là ứng viên cần xem tiếp; tên hãng và block chưa đủ để ghép vào mã bảng giá. DXF liên kết là bản bóc tách từ bản vẽ gốc.</p><p><a href="index_2026.html">← Tổng hợp bảng giá 2026</a> · <a href="outside_cad_audit.json">Dữ liệu kiểm kê</a></p></div><div class="tools"><input id="q" placeholder="Tìm hãng, model, vùng, chữ CAD..."><span id="count"></span></div><div class="wrap"><table><thead><tr><th>STT</th><th>Hãng</th><th>Block</th><th>Vùng</th><th>Chữ trong CAD</th><th>CAD</th><th>Kết quả kiểm tra</th></tr></thead><tbody>__ROWS__</tbody></table></div></main><script>const q=document.querySelector('#q'),trs=[...document.querySelectorAll('tbody tr')],count=document.querySelector('#count');function update(){const term=q.value.toLocaleLowerCase('vi');let shown=0;for(const tr of trs){const hit=tr.textContent.toLocaleLowerCase('vi').includes(term);tr.hidden=!hit;if(hit)shown++}count.textContent=`${shown} / ${trs.length} block ứng viên`}q.oninput=update;update();</script></html>'''.replace('__ROWS__',''.join(cells))
(CAT/'outside_cad_audit.html').write_text(page,encoding='utf8')
print(json.dumps({'outside_brand_blocks':len(rows),'by_brand':Counter(b for r in rows for b in r['brands'])},ensure_ascii=False))
