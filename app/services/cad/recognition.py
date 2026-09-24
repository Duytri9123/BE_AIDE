"""Evidence-based identity. A library filename is never manufacturer evidence."""
import json,re
from functools import lru_cache
from pathlib import Path
from app.services.cad.library_taxonomy import normalize,explicit_brands
DATA=Path(__file__).resolve().parents[3]/'data/cad_text_inventory.json'

@lru_cache(maxsize=2)
def _read(stamp):
    return {r['id']:r for r in json.loads(DATA.read_text(encoding='utf8'))}

def evidence(item):
    row=_read(DATA.stat().st_mtime_ns).get(item['id'],{}) if DATA.exists() else {}
    texts=row.get('texts',[])
    text=' '.join(texts); key=normalize(item.get('source_block') or item['name'])
    known=explicit_brands(text)
    for pattern,brand in [(r'\brisesun\b','RISESUN'),(r'robot','ROBOT'),(r'siemens','Siemens'),(r'panasonic','Panasonic'),(r'hager','Hager'),(r'smartgen','SmartGen'),(r'\bomega\b','Omega'),(r'shikiwa','Shikiwa'),(r'merlin gerin','Merlin Gerin'),(r'clman','CLMan')]:
        if re.search(pattern,normalize(text)) and brand not in known: known.append(brand)
    named=explicit_brands(item.get('source_block') or item['name'])
    brand=known[0] if len(known)==1 else named[0] if not known and len(named)==1 else 'Chưa xác định hãng'
    basis='Chữ trong hình CAD: '+brand if len(known)==1 else 'Tên block ghi: '+brand if not known and len(named)==1 else 'Chưa đủ bằng chứng; không lấy hãng từ tên file thư viện'
    result={'brand':brand,'brand_basis':basis,'texts':texts,'description':item['name'], 'face':None,
            'ai_auto_select':False,'ai_note':'Chỉ dùng tham khảo; AI chưa được tự chọn khi chưa xác nhận model, mặt nhìn và tỷ lệ.',
            'dimensions_from_text':None}
    dims=re.search(r'w\s*(\d+(?:\.\d+)?)\s*[x;]?\s*h\s*(\d+(?:\.\d+)?)\s*[x;]?\s*d\s*(\d+(?:\.\d+)?)',text,re.I)
    if dims: result['dimensions_from_text']=dict(zip(('w','h','d'),map(float,dims.groups())))
    # Reviewed against the source drawing and the user-provided CT table.
    em=re.fullmatch(r'em4h0([3-7])-([123])',key)
    if em:
        model='EM4H0'+em[1]
        result.update(family='emic:'+model,name='Biến dòng EMIC '+model,brand='EMIC',
                      brand_basis='Chữ EMIC trên mặt trước của cùng bộ '+model,
                      face={'1':'front','2':'side','3':'top'}[em[2]],description='Biến dòng xuyên cáp; ba hình chiếu của cùng khung '+model)
    hinges={'hl036-1-1':('HL036','front'),'hl036-1-2':('HL036','side'),'hl036-top':('HL036','top'),
        'hl044-1':('HL044','front'),'hl044-2':('HL044','side'),
        'hl003-2-1':('HL003-2','section'),'hl003-2-2':('HL003-2','front'),'hl003-2-3':('HL003-2','section'),
        'bl012':('BL012','section'),'bl012-front':('BL012','front'),'bl012-side':('BL012','side')}
    if key in hinges:
        model,face=hinges[key];result.update(family='hinge:'+model,name='Bản lề tủ '+model,face=face,
            description='Bản lề cơ khí tủ; hình có gạch mặt cắt biểu diễn tiết diện, không phải thiết bị đã lắp trong tủ.')
    if key in ('hl003-2-1', 'hl003-2-3'):
        variant = 'A' if key.endswith('-1') else 'B'
        result.update(view_variant=variant, view_title='Mặt cắt · cấu hình '+variant)
    sc=re.fullmatch(r'06 - n - sc (.+)', key)
    if sc:
        base=re.sub(r'chieu hong\s*|chieu tren\s*', '', sc[1])
        face='side' if 'chieu hong' in sc[1] else 'top' if 'chieu tren' in sc[1] else None
        if face or re.match(r'(mccb|mcb|vsd) ',base):
            result.update(family='schneider:'+base,name='Schneider · '+base.upper(),face=face or 'front',
                brand='Schneider Electric',brand_basis='Ký hiệu SC trong bộ block; cần đối chiếu mã đặt hàng',
                description='Hình trong bộ nguồn Schneider. Hướng nhìn theo nhãn CHIẾU HÔNG/CHIẾU TRÊN và mẫu mặt trước của bộ; dải mã dùng chung hình không phải một mã đặt hàng.')
        if base.startswith('vsd '): result.update(kind='device',group='Biến tần')
    if key.startswith('banlela-'):
        number=key.split('-')[1]; model='lá '+number
        result.update(family='hinge:leaf:'+number,name='Bản lề lá '+('4' if number in ('1','2') else '6')+' lỗ · kiểu '+number,
                      face='side' if key=='banlela-4-1' else 'front',description='Các kiểu khác nhau về hình học/kích thước; không phải bốn mặt của một bản lề.')
    if 'risesun' in normalize(text) and 'rt18-32' in normalize(text):
        poles=3 if item['id']=='b081864d4fb3ed5d98c7' else 1
        result.update(family=f'fuse:risesun:rt18-32:{poles}p',name=f'Đế cầu chì RISESUN RT18-32 · {poles}P · 10×38 · 32 A',face='front',
                      description=('Cụm ba đế cầu chì đặt cạnh nhau; không phải ba mặt của một đế.' if poles==3 else 'Đế cầu chì ống 10×38, một cực. Chữ nguồn: 32 A, 690 V.'))
    if item['id'] in ('32b654b3b19dcb130b55','605514ffacb5044f1e46'):
        result.update(family='fuse:chint:rt36-00',name='Cầu chì CHINT RT36-00 (NT00) · 160 A',face='front' if item['id'].startswith('32b') else 'side',
                      description='Hai mặt của cùng cầu chì; chữ nguồn AC 690 V, 160 A.')
    if item['id']=='2654c396f95b80d1d5d1':
        result.update(name='Cầu chì 6 A · chữ SIEMENS / OMEGA',face='front',description='Chữ trong CAD: SIEMENS, OMEGA, 6 A; chưa có mã đặt hàng để đối chiếu.')
    if 'robot' in normalize(text) and 'AP15' in text:
        result.update(family='stabilizer:robot:ap15',name='Ổn áp ROBOT AP15 · 350 VA',face='front',
                      description='Mặt trước ổn áp hoàn chỉnh: đồng hồ, công tắc và ổ ra 100/120/220 V. Đây là một thiết bị, không phải form tủ.')
    if key=='tr' and '220VAC/24VAC' in text:
        result.update(family='transformer:generic:220-24',name='Biến áp điều khiển 220 VAC → 24 VAC',face='front',description='Bản vẽ ghi tỷ số điện áp; chưa ghi hãng hoặc công suất.')
    if '24vdc' in normalize(text) or '24vdc' in key or 'power supply' in normalize(text):
        result.update(group='Bộ nguồn DC',kind='device',name='Bộ nguồn AC/DC '+('24 VDC · 5 A' if '24VDC-5A' in text else '220 VAC → 24 VDC' if '24vdc' in normalize(text+key) else '· chưa rõ điện áp'),
                      description='Nguồn chuyển đổi AC/DC; không phải biến áp AC/AC. Hãng và model cần đối chiếu trước khi chọn thay thế.')
    if key.startswith('tu 40kvar'):
        result.update(name='Tụ bù S-D-15 · thông số nguồn mâu thuẫn',description='Tên block ghi 40 kVAr nhưng chữ trong hình ghi 50 kVAr. Không tự chọn thông số nào.')
    models = list(dict.fromkeys(re.findall(r'\b(?:RT(?:18|36)[- ]?[A-Z0-9()/-]+|EM4H0[3-7]|AP15|PM\d{4}|MFM\d+[A-Z]?|VAF[- ]?\d+|LC1[A-Z0-9~/-]+|LRE[A-Z0-9~/-]+|NXM[- ]?[A-Z0-9~/-]+|HGM[A-Z0-9~/-]+|TB118K|PFR\d+|ME-\d+)\b', text, re.I)))
    result['model_markings'] = models
    if item.get('kind') == 'unclassified' and models:
        if any(re.match(r'PM|MFM|VAF|ME-', m, re.I) for m in models): result.update(kind='device',group='Đồng hồ và công tơ')
        elif any(re.match(r'LC1',m,re.I) for m in models): result.update(kind='device',group='Contactor')
        elif any(re.match(r'LRE|TB118',m,re.I) for m in models): result.update(kind='device',group='Rơ le và timer')
        elif any(re.match(r'NXM|HGM',m,re.I) for m in models): result.update(kind='device',group='Thiết bị đóng cắt')
    if models and 'name' not in result and ('mẫu' in item['name'] or item.get('kind')=='unclassified'):
        result['name'] = (result.get('group') or item['group'])+' · '+(' '.join(known)+' ' if known else '')+' / '.join(models)
        result['description'] = 'Mã đọc trực tiếp trong CAD: '+', '.join(models)+'. Chưa xác nhận đây là mã đặt hàng đầy đủ.'
    return result
