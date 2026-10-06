"""Turn source CAD views into device tables, retaining the unmodified DXF files.

The tables deliberately distinguish text printed in CAD from manufacturer data.
An anonymous AutoCAD block is never promoted to a product model.
"""
import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
import ezdxf
from ezdxf import bbox
from ezdxf.addons.drawing import Frontend, RenderContext, config, layout, svg

ROOT = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
OUT = ROOT / 'THIET_BI_KHAC_2026'
OUT.mkdir(exist_ok=True)
data = json.loads((ROOT / 'full_accessory_cad_inventory.json').read_text(encoding='utf8'))
records = data['records']
analysis_file = OUT / 'cad_view_analysis.json'
analysis = json.loads(analysis_file.read_text(encoding='utf8'))['views'] if analysis_file.exists() else {}
blocks_by_view = defaultdict(list)
for r in records:
    if r['kind'] == 'block':
        for vid in r.get('matched_view_ids', []):
            blocks_by_view[vid].append(r)

CATEGORIES = {
    'do_luong': ('Đồng hồ và đo lường', {'A01','C04'}),
    'bao_ve': ('Cầu dao và bảo vệ', set()),
    'bien_dong': ('Biến dòng', {'A02','C08','C12'}),
    'dieu_khien': ('Điều khiển và nguồn', {'A05','A10','C03','C05','C06'}),
    'dau_noi': ('Đấu nối và bù điện', {'A03','B05','C07','C09','C10','C11'}),
    'lam_mat': ('Quạt và làm mát', {'A11','A12','A16','C01'}),
    'phu_kien': ('Phụ kiện tủ điện', {'A04','A06','A07','A08','A09','A13','A15','B01','B02','B04','B06','B07','C02','C15'}),
    'rmu': ('Tủ trung thế RMU', {'E01','E02','E03','E04','E05','E06','E07','E08'}),
    'chua_phan_loai': ('Thiết bị và chi tiết cần nhận dạng', {'D07','D08','D09','F01','F02','F03','F04','F05','F06','F07'}),
}
Z_TO_CAT = {zone: key for key, (_, zones) in CATEGORIES.items() for zone in zones}
TYPE_WORDS = [
    (r'ATV320|INVERTER|BIẾN TẦN', 'Biến tần'),
    (r'61F-GP-N-2|61F-GP-N2', 'Bộ điều khiển mức nước'),
    (r'\bMCB\b|MCB\d|HMCB|ELCB', 'Cầu dao điện'),
    (r'WARNING LIGHT|ĐÈN BÁO', 'Đèn báo'),
    (r'APFC|\bPFC\b', 'Bộ điều khiển tụ bù'),
    (r'PM2220|PM710|MFM38|MFM383|MFM384|VAF\s*36|ĐỒNG HỒ|CÔNG TƠ|ĐIỆN KẾ|KWH|HOLLEY|VOLTMETER|AMMETER|VOLT.?METER|AMPE.?METER|BE-96', 'Đồng hồ đo điện'),
    (r'BIẾN DÒNG|CURRENT TRANSFORMER|\bCT\b|\bTI\b', 'Biến dòng đo lường'),
    (r'S8FS|S8JC|POWER SUPPLY|NGUỒN', 'Bộ nguồn'),
    (r'\bMBA\b|TRANSFORMER|MÁY BIẾN ÁP', 'Máy biến áp'),
    (r'RELAY|RƠ.?LE|RƠLE', 'Rơ le'),
    (r'TIMER|THỜI GIAN', 'Bộ định thời'),
    (r'CONTACTOR|KHỞI ĐỘNG TỪ', 'Khởi động từ'),
    (r'UK\s*3\s*N|TERMINAL|CẦU ĐẤU|CẦU ĐẤU DÂY', 'Cầu đấu dây'),
    (r'CAPACITOR|TỤ BÙ', 'Tụ bù'),
    (r'REACTOR|CUỘN KHÁNG', 'Cuộn kháng'),
    (r'FAN|QUẠT|FKL66', 'Quạt hoặc bộ lọc tủ'),
    (r'RM6|RMU', 'Tủ trung thế RMU'),
    (r'BẢN LỀ|HINGE', 'Bản lề tủ'),
    (r'KHÓA|LOCK', 'Khóa tủ'),
]
DEFAULT_TYPE = {
    'do_luong':'Thiết bị đo điện', 'bao_ve':'Thiết bị bảo vệ', 'bien_dong':'Biến dòng', 'dieu_khien':'Thiết bị điều khiển',
    'dau_noi':'Thiết bị đấu nối hoặc bù điện', 'lam_mat':'Thiết bị làm mát tủ',
    'phu_kien':'Phụ kiện tủ điện', 'rmu':'Thiết bị tủ trung thế',
    'chua_phan_loai':'Chi tiết CAD cần nhận dạng',
}
EXTERNAL = [
    (r'\bPM2220\b', 'Schneider Electric', 'Đồng hồ đo điện đa năng EasyLogic PM2220; màn hình LCD, RS485, cấp chính xác 1.', 'https://www.se.com/us/en/product/METSEPM2220/easylogic-pm2220-power-energy-meter-up-to-the-15th-harmonic-lcd-display-rs485-class-1/'),
    (r'\bPM710\b', 'Schneider Electric', 'Đồng hồ đo điện PM710; đo điện cơ bản, THD, giá trị min/max và RS485.', 'https://www.se.com/us/en/product/PM710MG/power-meter-pm710-basic-readings-thd-%2B-min-max-%2B-rs485/'),
    (r'\bS8FS-C05024J\b', 'Omron', 'Bộ nguồn 50 W, 24 V DC, 2,2 A.', 'https://www.ia.omron.com/products/family/3460/lineup.html'),
    (r'\bFKL6621\.230\b', 'Leipole', 'Quạt lọc tủ FKL6621.230; xem cấu hình điện và kích thước tại hãng.', 'https://www.leipole.net/product/fkl6621-enclosure-fan-and-filter.html'),
    (r'\bFKL6621\.300\b', 'Leipole', 'Lưới lọc thoát gió FKL6621.300 của dòng FKL6621; xem màu và kích thước tại hãng.', 'https://www.leipole.net/product/fkl6621-enclosure-fan-and-filter.html'),
    (r'\bS8JC-Z10024CD\b', 'Omron', 'Bộ nguồn S8JC-Z10024CD, 100 W, 24 V DC; mã được liệt kê trong tài liệu thay thế chính hãng.', 'https://www.ia.omron.com/data_pdf/cat/s8fs-c_t062-e1_4_1_csm1045833.pdf'),
    (r'\bUK\s*3\s*N\b', 'Phoenix Contact (tham khảo model)', 'Cầu đấu xuyên UK 3 N, 2,5 mm²; cần đối chiếu nhãn hãng trên CAD.', 'https://www.phoenixcontact.com/en-pc/products/feed-through-terminal-block-uk-3-n-3001501'),
    (r'\bATV320D11N4B\b', 'Schneider Electric', 'Biến tần Altivar Machine ATV320, 11 kW, nguồn 3 pha 380–500 V.', 'https://www.se.com/nl/en/product/ATV320D11N4B/variable-speed-drive-altivar-machine-atv320-11kw-380-to-500v-3-phases-book/'),
    (r'\b61F-GP-N-?2\b', 'Omron', 'Bộ điều khiển mức chất lỏng dùng điện cực, dòng 61F-GP-N2; điện áp phiên bản cần đọc từ nhãn thiết bị.', 'https://www.ia.omron.com/data_pdf/cat/61f-gp-n2_ds_e_1_5_csm542.pdf'),
    (r'\bRM6\b', 'Schneider Electric', 'Dòng tủ RM6 trung thế; thông số cấu hình cụ thể phụ thuộc model.', 'https://www.se.com/au/en/product-range/967-rm6/'),
]

def anonymous(s):
    return not s or bool(re.match(r'^(?:\*U\d+|A\$C[0-9A-F]+|\d{2,5}|\d{3}_U\d+_thiet_bi|Hình CAD chưa xác định tên|Mặt bằng|Mặt đứng|Mặt hông|Logo|SPACE|MODEL)$', s, re.I))

def clean_name(s):
    s = re.sub(r'\s*[-–]\s*(?:FRONT|FONT|SIDE|TOP|BACK|CẠNH|ĐỈNH|MẶT TRƯỚC|MẶT CẠNH|MẶT SAU)\b.*$', '', s, flags=re.I)
    return re.sub(r'\s+', ' ', s).strip()

def device_label(name, zone):
    """Collapse only documented C08 view suffixes, retaining each source view below."""
    label = clean_name(name)
    if zone == 'C08':
        match = re.fullmatch(r'(CML\d+A|KDE\s+\d+A)-[123]', label, re.I)
        if match:
            return match.group(1)
        match = re.fullmatch(r'(BD\d+A)-[TFS]', label, re.I)
        if match:
            return match.group(1)
    return label

def source_context_label(view):
    # These A02 groups explicitly name the CT model while their individual
    # source views are only labelled plan/front/side.
    if view['zone'] == 'A02' and re.fullmatch(r'A02_set[1-7]-V\d+', view['id']):
        return view['group']
    return ''

def c08_text_label(view, evidence):
    """Read model/range only from text attached to this C08 source block."""
    if view['zone'] != 'C08':
        return ''
    block_text = ' '.join(str(t) for b in evidence for t in b.get('text_evidence', []))
    if view['id']=='C08_cluster8-V017' and re.search(r'\bMORELE\s+MSQ-125\b', block_text, re.I):
        # The adjacent FONT/SIDE placements use the same MSQ-125 label and
        # complementary 172×47 / 47×159 / 172×159 geometry.
        return 'MSQ-125'
    if re.search(r'\bMITEX\b', block_text, re.I):
        match = re.search(r'\bBD01[- ]\d+(?:~\d+)?/5A\b', block_text, re.I)
        if match:
            return match.group(0)
    if re.search(r'\bMORELE\b', block_text, re.I):
        model = re.search(r'\bMSQ[- ]\d+\b', block_text, re.I)
        ratio = re.search(r'\b\d+(?:[-–]\d+)?/5A\b', block_text, re.I)
        if model:
            return model.group(0) + (f' · {ratio.group(0)}' if ratio else '')
    match = re.search(r'\bCML\s+(\d+/5A)\b', block_text, re.I)
    if match and anonymous(view['name']):
        return 'CML ' + match.group(1)
    return ''

def other_block_label(view, evidence):
    if view['zone'] not in {'C03','C05','C09','F01','F02'}:
        return ''
    text = ' '.join(str(t).strip() for b in evidence for t in b.get('text_evidence', []))
    patterns = {
        'C03': r'\bMC\s+\d+[aAbB](?:\s*[,~]\s*\d+[aAbB])?\b',
        'C05': r'\b(?:ACD-?III|NX\s*204A|MX\s*200A)\b',
        'C09': r'\bHYBT\s*-?\s*\d+A?\b',
        'F01': r'\b(?:ABN|ABS)\s*\d{2,4}[cb]\b',
        'F02': r'\b(?:ABN|ABS|ABH)\s*\d{2,4}[cb]\b',
    }
    match = re.search(patterns[view['zone']], text, re.I)
    return re.sub(r'\s+', ' ', match.group(0)).strip() if match else ''

def block_capacitor_facts(view, evidence):
    if view['zone']!='C10':
        return ''
    texts = [str(t).strip() for b in evidence for t in b.get('text_evidence', [])]
    upper = ' '.join(texts).upper()
    if 'CAPACITOR' not in upper:
        return ''
    if 'SHAMWHA CAPACITOR' in upper or 'SAMWHA CAPACITOR' in upper:
        # This nameplate stores Un, Qn and In as successive text entities.
        try:
            pos = next(i for i,t in enumerate(texts) if t.upper()=='IN(A)')
            voltage, kvar, current = texts[pos+1:pos+4]
            if re.fullmatch(r'\d+(?:\.\d+)?', voltage) and re.fullmatch(r'\d+(?:\.\d+)?', kvar):
                return f'Nhãn CAD: Un {voltage} V; Qn {kvar} kvar; In {current} A.'
        except (StopIteration, ValueError):
            pass
    return 'Nhãn CAD ghi tụ điện; giá trị định mức riêng chưa đọc được.'

def view_state(s):
    m = re.search(r'\b(FRONT|FONT|SIDE|TOP|BACK|CẠNH|ĐỈNH|MẶT TRƯỚC|MẶT CẠNH|MẶT SAU)\b', s, re.I)
    return m.group(1).title() if m else 'Góc nhìn CAD'

def esc(s):
    return html.escape(str(s or ''), quote=True)

views = [r for r in records if r['kind']=='view' and r.get('zone') in Z_TO_CAT]
groups = defaultdict(list)
for v in views:
    evidence = blocks_by_view[v['id']]
    exact = next((b['name'] for b in evidence if not anonymous(b.get('name')) and ('—' in b['name'] or len(b['name']) > 15)), None)
    label = (c08_text_label(v, evidence) or other_block_label(v, evidence) or source_context_label(v) or
             (device_label(v['name'], v['zone']) if not anonymous(clean_name(v['name'])) else (exact or '')))
    if v['id'] in {'A02_abb-V002', 'A02_abb-V003'}:
        # The two smaller shapes share a drawing area with the ABB ZCT, but
        # neither isolated DXF contains a model or establishes device identity.
        label = ('Chi tiết hình học 1' if v['id'].endswith('V002') else 'Chi tiết hình học 2') + ' cạnh ABB-ZCT-300A — chưa xác định model'
    if anonymous(label):
        # A short exact model printed *inside* a block is stronger than an anonymous CAD handle.
        texts = [str(t).strip() for b in evidence for t in b.get('text_evidence', [])]
        label = next((t for t in texts if re.fullmatch(r'[A-Za-z][A-Za-z0-9./-]{3,24}', t)
                      and re.search(r'\d', t) and t.upper() not in {'SPACE','MODEL','A1700'}), '')
    if not label:
        label = 'Chưa đọc được model'
    cluster = v['id'].split('-V')[0]
    group_key = v['id'] if label=='Chưa đọc được model' or v['id'] in {'A02_abb-V002', 'A02_abb-V003'} else label.casefold()
    groups[(Z_TO_CAT[v['zone']], cluster, group_key)].append((v,label,evidence))

products = []
for (cat, cluster, _), items in groups.items():
    v, label, _ = items[0]
    evidence = [b for _,_,bs in items for b in bs]
    cad_text = list(dict.fromkeys(str(t).strip() for b in evidence for t in b.get('text_evidence', []) if str(t).strip()))
    match_text = ' '.join([label] + cad_text)
    type_text = match_text + ' ' + v['group']
    type_name = next((kind for rx,kind in TYPE_WORDS if re.search(rx, type_text, re.I)), DEFAULT_TYPE[cat])
    if v['zone']=='A05' and type_name==DEFAULT_TYPE[cat]:
        type_name='Chi tiết trong cụm bảo vệ pha'
    if type_name=='Cầu dao điện':
        cat='bao_ve'
    elif cat=='do_luong' and type_name in {'Bộ điều khiển tụ bù','Bộ định thời','Đèn báo'}:
        cat='dieu_khien'
    exact_model = label != 'Chưa đọc được model' and not anonymous(label) and len(label) >= 4
    # Product-level source matches require a model in the device label or text of its own block.
    source = next(((brand, spec, url) for rx,brand,spec,url in EXTERNAL if re.search(rx, match_text, re.I)), None)
    source_level = 'Đối chiếu model'
    if source and (label=='Chưa đọc được model' or 'tham khảo' in source[0].lower()):
        source_level = 'Tham khảo dòng sản phẩm'
    identity_text = match_text+' '+v['group']+' '+' '.join(str(b.get('name','')) for b in evidence)
    if not source and re.search(r'\bEMIC\b', identity_text, re.I) and cat=='do_luong':
        source = ('EMIC', 'Hãng sản xuất công tơ điện; chưa xác minh thông số riêng của model CAD này.', 'https://emic.com.vn/vn/cong-to-dien')
        source_level = 'Tham khảo hãng'
    if not source and re.search(r'\bHOLLEY\b', identity_text, re.I) and cat=='do_luong':
        source = ('Holley', 'Hãng sản xuất thiết bị đo điện; chưa xác minh thông số riêng của model CAD này.', 'https://www.holleymetering.com/')
        source_level = 'Tham khảo hãng'
    # MSQ is used by several manufacturers; its model prefix alone cannot
    # identify a manufacturer. Prefer the lettering inside this CAD block.
    brand_aliases = [('Samwha',r'\bS(?:H)?AMWHA\b'),('Nuintek',r'\bNUINTEK\b'),
                     ('MITEX',r'\bMITEX\b'),('MORELE',r'\bMORELE\b'),
                     ('MIKRO',r'\bMIKRO\b'),('OSEMCO',r'\bOSEMCO\b'),
                     ('Himel',r'\bHIMEL\b'),('Vinakip',r'\bVINAKIP\b'),
                     ('CML',r'\bCML\b'),('Schneider',r'\bSCHNEIDER\b'),
                     ('Omron',r'\bOMRON\b'),('Leipole',r'\bLEIPOLE\b'),
                     ('EMIC',r'\bEMIC\b'),('Holley',r'\bHOLLEY\b'),
                     ('Selec',r'\bSELEC\b'),('Chint',r'\bCHINT\b'),
                     ('Phoenix Contact',r'\bPHOENIX CONTACT\b'),
                     ('Mitsubishi',r'\bMITSUBISHI\b'),('LS',r'\bLS\b'),('ABB',r'\bABB\b')]
    brand = next((b for b,rx in brand_aliases if re.search(rx, ' '.join(cad_text), re.I)), '')
    brand_evidence = 'Chữ trong block CAD' if brand else ''
    if not brand:
        brand = next((b for b,rx in brand_aliases if re.search(rx, label, re.I)), '')
        brand_evidence = 'Nhãn hình CAD' if brand else ''
    if not brand and v.get('brand'):
        brand = v['brand']
        brand_evidence = 'Nhãn vùng CAD'
    if not brand and v['zone']=='C03' and v['group'].strip().casefold()=='contactor ls':
        brand = 'LS'
        brand_evidence = 'Nhãn cụm CAD gốc'
    if not brand and cat=='do_luong':
        brand = next((b+' (theo cụm CAD)' for b in ('EMIC','Holley') if re.search(re.escape(b),identity_text,re.I)), '')
    if source and not brand and source_level=='Đối chiếu model' and 'tham khảo' not in source[0].lower():
        brand = source[0]
        brand_evidence = 'Nguồn nhà sản xuất đối chiếu model'
    all_views = []
    for i, (a, _, _) in enumerate(items, 1):
        rel_preview = a.get('preview')
        examined = analysis.get(a['id'], {})
        state = examined.get('face') or 'Chưa xác định mặt'
        label_parts = [f'Hình {i}', state]
        entry = {'name':a['name'], 'state':state,
                 'dxf':'../'+a['cad_dxf'],
                 'preview':'../'+rel_preview if rel_preview else '',
                 'id':a['id'], 'source_ids':[a['id']],
                 'label':' · '.join(label_parts),
                 'analysis':examined}
        all_views.append(entry)
    product = {
        'id':v['id'],
        'category':cat, 'type':type_name, 'model':label, 'brand':brand, 'brand_evidence':brand_evidence,
        'cad_text':cad_text[:18], 'source_group':v['group'], 'zone':v['zone'],
        'status': 'Tên/model đọc từ CAD; chưa xác minh mã hàng' if exact_model else 'Tên block CAD; chưa xác minh model',
        'external':{'publisher':source[0], 'spec':source[1], 'url':source[2], 'level':source_level} if source else None,
        'views':all_views,
        'source_placements':len(items),
    }
    if source_context_label(v):
        product['status'] = 'Model lấy từ nhãn cụm CAD gốc; từng hình chiếu không ghi model'
        product['cad_info'] = f'Nhãn cụm CAD gốc: {v["group"]}. {len(all_views)} hình chiếu tách từ cụm.'
    if c08_text_label(v, evidence):
        product['status'] = 'Model/dải tỷ số đọc từ chữ trong block CAD; chưa xác minh cấu hình SKU'
    if other_block_label(v, evidence):
        product['status'] = 'Tên/dải model đọc từ chữ trong block CAD; chưa xác minh cấu hình SKU'
    capacitor_facts = block_capacitor_facts(v, evidence)
    if capacitor_facts:
        product['cad_info'] = capacitor_facts
        product['status'] = 'Thông số đọc từ nhãn trong CAD; chưa đối chiếu mã hàng và hãng'
    if v['id']=='A02_abb-V001':
        product['status'] = 'ABB-ZCT-300A ghi ở cụm CAD gốc; hình vòng này không chứa chữ'
        product['cad_info'] = 'Hình vòng biến dòng trong cụm ABB-ZCT-300A; khung hình 290 × 310 đơn vị bản vẽ.'
    if v['id'] in {'A02_abb-V002', 'A02_abb-V003'}:
        product['type'] = 'Chi tiết hình học trong cụm biến dòng'
        product['status'] = 'Tên ABB-ZCT-300A ở cụm nguồn; hình này không ghi model'
        product['cad_info'] = ('DXF này chỉ chứa hình học. Khung hình '
                               + ' / '.join(f'{view["analysis"]["bounds_drawing_units"][0]:g} × '
                                            f'{view["analysis"]["bounds_drawing_units"][1]:g}'
                                            for view in all_views)
                               + ' đơn vị bản vẽ; chưa xác định đây là thiết bị nào.')
    if v['id']=='A03_set1-V001':
        product['type']='Bản bố trí cụm thanh E và N'
        product['model']='Cụm E/N · mặt bằng CAD gốc'
        product['status']='Cụm gồm hai thanh riêng; xem hai dòng block E và N bên dưới để lấy CAD từng thiết bị'
        product['cad_info']='Bản vẽ cụm A03 chứa block E (PE) và N. Đây là mặt bằng lắp đặt, không phải một SKU.'
    products.append(product)

# A03's MB and MH placements show the same E/N assembly in two views. The
# previous table incorrectly counted the side view as another device.
en_assembly=next(p for p in products if p['id']=='A03_set1-V001')
en_side=next(p for p in products if p['id']=='A03_set1-V002')
en_assembly['views'].extend(en_side['views'])
en_assembly['source_placements']+=en_side['source_placements']
products.remove(en_side)

# The A03 source contains distinct E and N blocks. The old combined top-view
# row remains as an assembly view, while these two source blocks are the
# actual downloadable components. Bounds are source drawing extents, not
# manufacturer product dimensions.
preview_dir=OUT/'source_block_previews'; preview_dir.mkdir(exist_ok=True)
for block_id,suffix,kind,model in (
    ('B_8ce86a6ae65d','N','Thanh trung tính','Thanh N'),
    ('B_a9f51566bd67','E','Thanh tiếp địa','Thanh E (PE)')):
    source=next(r for r in records if r['id']==block_id)
    dxf=ROOT/source['cad_dxf']; doc=ezdxf.readfile(dxf)
    bounds=bbox.extents(doc.modelspace())
    assert doc.units==4 and bounds.has_data,(block_id,dxf)
    backend=svg.SVGBackend()
    Frontend(RenderContext(doc),backend,
             config=config.Configuration(background_policy=config.BackgroundPolicy.WHITE)).draw_layout(doc.modelspace())
    preview=preview_dir/f'A03-{suffix}.svg'
    preview.write_text(backend.get_string(layout.Page(90,180,layout.Units.mm,
                                                     margins=layout.Margins.all(6))),encoding='utf8')
    w,h=round(bounds.size.x,2),round(bounds.size.y,2)
    view_id=f'{block_id}-source'
    products.append({'id':block_id,'category':'dau_noi','type':kind,'model':model,
        'brand':'','brand_evidence':'','cad_text':[],'source_group':'A03 · Thanh E & N',
        'zone':'A03','status':'Block CAD riêng trong bản vẽ gốc; chưa xác minh hãng, tiết diện hoặc dòng',
        'external':None,'cad_info':f'Khung hình CAD {w:g} × {h:g} mm; không phải kích thước sản phẩm đã chứng nhận.',
        'views':[{'name':model,'state':'Mặt bằng theo cụm CAD gốc','dxf':'../'+source['cad_dxf'].replace('\\','/'),
                  'preview':'source_block_previews/'+preview.name,'id':view_id,
                  'source_ids':[block_id],'label':'CAD block riêng · mặt bằng',
                  'analysis':{'face':'Mặt bằng','face_evidence':'Nhãn MB của cụm A03',
                              'drawing_name':model,'bounds_drawing_units':[w,h],
                              'inserts':[],'entity_types':sorted({e.dxftype() for e in doc.modelspace()}),
                              'dynamic_visibility_states':[]}}],
        'source_placements':source.get('placed_count',1)})

# Preserve the exact extra CAD sources used in the current cabinet design as
# general catalog items. They have no verified manufacturer or ordering code.
supplemental_dir=OUT/'supplemental_cad'; supplemental_dir.mkdir(exist_ok=True)
for item_id,source_file,kind,model,category in (
    ('DATA-PNE-BAR-7',Path(r'D:\data\thu_vien_tu_dien_v2\phu_kien\trong_tu\thanh_dong_dau_cos\CHUA_XAC_DINH\PNE-BAR__td_26abfa7ea3ace14e34e5\cad.dxf'),
     'Thanh đấu N/PE tham chiếu','PNE-BAR · 7 vị trí','dau_noi'),
    ('DATA-RED-LIGHT',Path(r'D:\data\thu_vien_tu_dien_v2\thiet_bi\den_bao\CHUA_XAC_DINH\RED_LIGHT__td_319328eb811a51702117\cad.dxf'),
     'Đèn báo','RED LIGHT · CAD tham chiếu','phu_kien')):
    assert source_file.is_file(),source_file
    target=supplemental_dir/(item_id+'.dxf')
    shutil.copy2(source_file,target)
    doc=ezdxf.readfile(target); bounds=bbox.extents(doc.modelspace())
    assert doc.units==4 and bounds.has_data,(item_id,target)
    backend=svg.SVGBackend()
    Frontend(RenderContext(doc),backend,
             config=config.Configuration(background_policy=config.BackgroundPolicy.WHITE)).draw_layout(doc.modelspace())
    preview=supplemental_dir/(item_id+'.svg')
    preview.write_text(backend.get_string(layout.Page(90,170,layout.Units.mm,
                                                     margins=layout.Margins.all(6))),encoding='utf8')
    w,h=round(bounds.size.x,2),round(bounds.size.y,2)
    products.append({'id':item_id,'category':category,'type':kind,'model':model,
        'brand':'','brand_evidence':'','cad_text':[],'source_group':'D:data · CAD thư viện tham chiếu',
        'zone':'D:data','status':'CAD có thật; chưa xác minh hãng, mã đặt hàng hoặc thông số điện',
        'external':None,'cad_info':f'Khung hình CAD {w:g} × {h:g} mm; kích thước sản phẩm chưa được nhà sản xuất xác nhận.',
        'source_original':str(source_file),
        'views':[{'name':model,'state':'Hình CAD tham chiếu','dxf':'supplemental_cad/'+target.name,
                  'preview':'supplemental_cad/'+preview.name,'id':item_id+'-V1',
                  'source_ids':[item_id],'label':'CAD nguồn · một hình',
                  'analysis':{'face':None,'face_evidence':'Không có nhãn góc nhìn được xác minh',
                              'drawing_name':model,'bounds_drawing_units':[w,h],
                              'inserts':[],'entity_types':sorted({e.dxftype() for e in doc.modelspace()}),
                              'dynamic_visibility_states':[]}}],
        'source_placements':1})

board_map={}
board_source=ROOT/'06_TU_DB_FACADE_12F/cad_da_chen.json'
if board_source.is_file():
    for row in json.loads(board_source.read_text(encoding='utf8')):
        if row['tag'] in {'FU1','KT1'} or row['tag'].startswith(('X-IN-','X-OUT-')):
            board_map.setdefault(row['source'].replace('\\','/'),[]).append(row['tag'])
for p in products:
    tags=[]
    for view in p['views']:
        key=view['dxf'].removeprefix('../').replace('\\','/')
        tags.extend(board_map.get(key,[]))
    if p['id']=='DATA-PNE-BAR-7': tags.extend(['N-BAR','PE-BAR'])
    if p['id']=='DATA-RED-LIGHT': tags.append('HL1')
    if tags: p['cabinet_reference']={'board':'DB FACADE 12F','tags':sorted(set(tags)),
                                    'use_level':'CAD tham chiếu; không phải xác nhận đúng mã mua'}

products.sort(key=lambda p:(list(CATEGORIES).index(p['category']),p['type'],p['model'],p['zone']))
(OUT/'products.json').write_text(json.dumps({'source_dwg_sha256':data['source_dwg_sha256'],
    'isolated_views_covered':len(views),'additional_cad_records':4,
    'additional_cad_basis':'Hai block E/N tách từ DWG nguồn và hai CAD tham chiếu D:data; không gán hãng khi chưa có chứng cứ.',
    'product_rows':len(products), 'products':products},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

by_view = {view['id']:product for product in products for view in product['views']}
evidence_audit=[]
for view in views:
    product=by_view[view['id']]
    blocks=blocks_by_view[view['id']]
    raw_text=list(dict.fromkeys(str(t).strip() for b in blocks for t in b.get('text_evidence',[]) if str(t).strip()))
    model=product['model']
    if model=='Chưa đọc được model' or 'chưa xác định model' in model:
        model_basis='chưa xác định'
    elif any(model.casefold() in text.casefold() for text in raw_text):
        model_basis='chữ trong block'
    elif model.casefold() in view['name'].casefold():
        model_basis='tên hình CAD'
    elif model.casefold() in view['group'].casefold():
        model_basis='nhãn cụm CAD'
    else:
        model_basis='diễn giải từ nhãn block/hình; cần đối chiếu'
    detail=analysis.get(view['id'],{})
    evidence_audit.append({'view_id':view['id'], 'product_id':product['id'],
        'model_in_table':model, 'model_basis':model_basis, 'brand_in_table':product['brand'],
        'brand_basis':product['brand_evidence'], 'source_view_name':view['name'],
        'source_group':view['group'], 'block_names':[b['name'] for b in blocks],
        'block_text':raw_text, 'face':detail.get('face'),
        'bounds_drawing_units':detail.get('bounds_drawing_units'),
        'source_dxf':view['cad_dxf']})
(OUT/'cad_evidence_audit.json').write_text(json.dumps({
    'source_dwg_sha256':data['source_dwg_sha256'], 'views_audited':len(evidence_audit),
    'view_evidence':evidence_audit},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
full_audit=[]
for source_view in (r for r in records if r['kind']=='view'):
    vid=source_view['id']
    product=by_view.get(vid)
    blocks=blocks_by_view[vid]
    detail=analysis.get(vid,{})
    full_audit.append({'view_id':vid,'zone':source_view['zone'],
        'source_view_name':source_view['name'],'source_group':source_view['group'],
        'source_dxf':source_view['cad_dxf'],
        'block_names':[b['name'] for b in blocks],
        'block_text':list(dict.fromkeys(str(t).strip() for b in blocks
                       for t in b.get('text_evidence',[]) if str(t).strip())),
        'face':detail.get('face'), 'bounds_drawing_units':detail.get('bounds_drawing_units'),
        'table_product_id':product['id'] if product else None,
        'table_model':product['model'] if product else None})
(ROOT/'all_cad_view_evidence_audit.json').write_text(json.dumps({
    'source_dwg_sha256':data['source_dwg_sha256'], 'views_audited':len(full_audit),
    'note':'124 brand-zone views are audited here; their price-table matching remains in the six brand datasets.',
    'view_evidence':full_audit},ensure_ascii=False,indent=2)+'\n',encoding='utf8')

CSS='''*{box-sizing:border-box}body{margin:0;background:#edf3f7;color:#102b40;font:14px system-ui}main{max-width:1550px;margin:auto;padding:18px}header{background:#fff;border:1px solid #c7d8e4;border-radius:10px;padding:20px;margin-bottom:14px}h1{margin:0 0 8px;font-size:26px}p{line-height:1.5}.nav{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.nav a{background:#fff;border:1px solid #bfcfdb;border-radius:7px;padding:8px;color:#075e9f}.filters{display:flex;gap:8px;margin:14px 0}.filters input{padding:11px;border:1px solid #afc4d4;border-radius:6px;font:inherit;flex:1}table{width:100%;border-collapse:collapse;background:#fff}th{background:#e2ebf2;text-align:left;position:sticky;top:0}td,th{padding:9px;border:1px solid #d4e0e9;vertical-align:top}td small{display:block;color:#536c80;margin-top:4px}td strong{color:#052c4d}.cad-cell{min-width:150px}.cad-cover{display:block;width:144px;height:155px;object-fit:contain;border:1px solid #d4e0e9;background:white}.cad-views{display:flex;flex-wrap:wrap;gap:12px}.cad-view{width:180px;border:1px solid #cbdbe6;padding:8px;background:#fbfdff;border-radius:5px}.cad-view img{display:block;width:160px;height:195px;object-fit:contain;border:1px solid #d4e0e9;background:white}.cad-view b{display:block;font-size:13px;min-height:32px}.cad-view a{font-size:13px}.cad-view .cad-id{display:block;color:#536c80;font-size:11px;overflow-wrap:anywhere}.gallery-product{background:white;border:1px solid #cbdbe6;padding:16px;margin:14px 0;border-radius:8px;scroll-margin-top:12px}.gallery-product:target{outline:3px solid #2f84c4}.gallery-product h2{margin:0 0 5px}a{color:#075e9f}@media(max-width:800px){.wrap{overflow:auto}table{min-width:1150px}}'''

def nav():
    return '<nav class="nav"><a href="../index_2026.html">Bảng giá các hãng</a>'+''.join(
        f'<a href="{key}.html">{esc(title)}</a>' for key,(title,_) in CATEGORIES.items())+'</nav>'

def row_html(p, n):
    views=p['views']
    dynamic_count=len({state for view in views for state in view['analysis'].get('dynamic_visibility_states',[])})
    first=views[0]
    gallery=f'{p["category"]}_goc_nhin.html#{p["id"]}'
    cover=(f'<a href="{esc(gallery)}"><img class="cad-cover" loading="lazy" src="{esc(first["preview"])}" alt="CAD {esc(p["model"])}"></a>'
           if first['preview'] else '<span>CAD không có hình hiển thị</span>')
    external=p['external']
    specs=(esc(external['spec'])+f'<small>{esc(external["level"])} · <a href="{esc(external["url"])}" target="_blank" rel="noopener">{esc(external["publisher"])} ↗</a></small>') if external else 'Chưa có thông số nhà sản xuất xác minh'
    evidence=', '.join(p['cad_text'][:8])
    board_note=('<small>Trong tủ DB FACADE 12F: '+esc(', '.join(p['cabinet_reference']['tags']))
                +' · CAD tham chiếu</small>') if p.get('cabinet_reference') else ''
    return (f'<tr data-filter="{esc(" ".join([p["model"],p["type"],p["brand"],p["source_group"],evidence]))}">'
            f'<td>{n}</td><td><strong>{esc(p["type"])}</strong><small>{esc(p["model"])}</small>'
            f'<small>{esc(p["source_group"])}</small></td><td>{esc(p["brand"] or "Chưa xác minh")}'
            f'{"<small>"+esc(p["brand_evidence"])+"</small>" if p["brand_evidence"] else ""}</td>'
            f'<td>{esc(p.get("cad_info") or evidence or "DXF hình này không chứa chữ/model")}<small>{esc(p["status"])}</small>{board_note}</td>'
            f'<td>{specs}</td><td>—<small>Chưa có PDF giá 2026 đối chiếu</small></td><td class="cad-cell">{cover}'
            f'<small><a href="{esc(first["dxf"])}" download>DXF</a> · <a href="{esc(gallery)}">Các góc nhìn ({len(views)} bản CAD{", "+str(dynamic_count)+" trạng thái AutoCAD" if dynamic_count else ""})</a></small></td>'
            f'<td>{esc(p["zone"])}</td></tr>')

JS='''<script>const q=document.querySelector('#search'),rows=[...document.querySelectorAll('tbody tr')],count=document.querySelector('#count');q.addEventListener('input',()=>{let n=0;const term=q.value.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();for(const r of rows){const show=r.dataset.filter.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().includes(term);r.hidden=!show;if(show)n++}count.textContent=n+' / '+rows.length+' thiết bị'});</script>'''

def gallery_product(p):
    hashes = [v['analysis'].get('preview_sha256') for v in p['views']]
    duplicate_count = len(hashes)-len({h for h in hashes if h})
    note = (f'<p>{duplicate_count} bản đặt có ảnh giống bản khác trong nhóm. Mỗi bản vẫn có DXF và ID riêng; '
            'ảnh giống nhau không chứng minh đó là các mặt khác nhau.</p>') if duplicate_count else ''
    cards=[]
    for v in p['views']:
        examined=v['analysis']
        block_names=', '.join(dict.fromkeys(i['name'] for i in examined.get('inserts',[])))
        bounds=examined.get('bounds_drawing_units')
        evidence=(f'Nhãn mặt: {examined["face_evidence"]}' if examined.get('face')
                  else 'CAD chưa ghi rõ mặt; không suy đoán từ tỷ lệ hình')
        shape=f'Khung hình CAD: {bounds[0]:g} × {bounds[1]:g} đơn vị bản vẽ' if bounds else 'Không đo được khung hình'
        preview=(f'<a href="{esc(v["preview"])}" target="_blank"><img loading="lazy" src="{esc(v["preview"])}" alt="{esc(v["label"])}"></a>'
                 if v['preview'] else '<p>Không có hình xem trước từ DXF này</p>')
        dynamic=examined.get('dynamic_visibility_states',[])
        states=(f'<details><summary>{len(dynamic)} trạng thái động trong AutoCAD</summary>'
                '<p>DXF tĩnh hiện tại chỉ chứa hình của bản đặt này. Các trạng thái dưới đây '
                'có tên trong block DWG gốc nhưng chưa có ảnh và DXF riêng:</p><ul>'
                + ''.join(f'<li>{esc(state)}</li>' for state in dynamic)
                + '</ul></details>') if dynamic else ''
        cards.append(f'<article class="cad-view"><b>{esc(v["label"])}</b>{preview}'
                     f'<small>Tên trong CAD: {esc(v["name"])}</small>'
                     f'<small>{esc(evidence)}</small><small>{esc(shape)}</small>'
                     f'<small>Block: {esc(block_names or "không có INSERT")}</small>'
                     f'{states}'
                     f'<a href="{esc(v["dxf"])}" download>Tải DXF bản này</a>'
                     f'<span class="cad-id">{esc(v["id"])}</span></article>')
    return (f'<section class="gallery-product" id="{esc(p["id"])}">'
            f'<h2>{esc(p["type"])} · {esc(p["model"])}</h2>'
            f'<p>{len(p["views"])} bản CAD trong cụm {esc(p["source_group"])}. '
            'Nhãn mặt chỉ được ghi khi có bằng chứng từ tên góc nhìn trong CAD.</p>'
            f'{note}<div class="cad-views">{"".join(cards)}</div>'
            f'<p><a href="{esc(p["category"])}.html">← Bảng thiết bị</a></p></section>')

for key,(title,_) in CATEGORIES.items():
    subset=[p for p in products if p['category']==key]
    rows=''.join(row_html(p,n) for n,p in enumerate(subset,1))
    page=(f'<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
          f'<title>{esc(title)} · CAD thiết bị</title><style>{CSS}</style><main><header><h1>{esc(title)}</h1>'
          f'<p>Mỗi dòng là một thiết bị hoặc model đọc từ bản vẽ CAD. Các trạng thái và góc nhìn được gom trong ô CAD; DXF giữ hình gốc. Thông số nhà sản xuất chỉ hiện khi đối chiếu được model với nguồn ngoài. Chưa có bảng giá xác minh cho nhóm này.</p>'
          f'{nav()}</header><div class="filters"><input id="search" placeholder="Tìm thiết bị, model, chữ trong CAD…"><span id="count">{len(subset)} / {len(subset)} thiết bị</span></div>'
          f'<div class="wrap"><table><thead><tr><th>STT</th><th>Thiết bị / model CAD</th><th>Hãng</th><th>Thông tin đọc trong CAD</th><th>Thông số đối chiếu ngoài</th><th>Giá 2026</th><th>CAD nguyên bản / góc nhìn</th><th>Vùng</th></tr></thead><tbody>{rows}</tbody></table></div>'
          f'<p><a href="../full_accessory_cad_library.html">Kiểm kê toàn bộ block, cụm và hình rời từ DWG</a> · <a href="products.json">Dữ liệu bảng</a></p>{JS}</main></html>')
    (OUT/f'{key}.html').write_text(page,encoding='utf8')
    gallery=(f'<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
             f'<title>Các góc nhìn · {esc(title)}</title><style>{CSS}</style><main><header><h1>Các góc nhìn · {esc(title)}</h1>'
             '<p>Hình và DXF lấy từ từng bản CAD. Tên mặt được ghi khi CAD có nhãn Front, Side, Đỉnh, Mặt trước hoặc tương đương; các bản không có nhãn được để “Chưa xác định mặt”. Các bản DXF tĩnh chưa chứng minh đã bao gồm mọi trạng thái động trong block AutoCAD gốc.</p>'
             f'<a href="{key}.html">← Về bảng thiết bị</a> · <a href="../../THƯ VIỆN PHỤ KIỆN( Mới nhất).dwg" download>DWG gốc để kiểm tra trạng thái động</a></header>'
             + ''.join(gallery_product(p) for p in subset)+'</main></html>')
    (OUT/f'{key}_goc_nhin.html').write_text(gallery,encoding='utf8')

cards=''.join(f'<article><h2>{esc(title)}</h2><strong>{sum(p["category"]==key for p in products)} thiết bị</strong><p><a href="{key}.html">Mở bảng →</a></p></article>' for key,(title,_) in CATEGORIES.items())
index=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Thiết bị khác từ CAD nguồn</title><style>{CSS}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}}article{{background:white;border:1px solid #c7d8e4;border-radius:8px;padding:15px}}</style><main><header><h1>Thiết bị khác từ thư viện CAD</h1><p>{len(products)} dòng thiết bị: {len(views)} góc nhìn cô lập ngoài sáu vùng hãng, hai block thanh N/E tách từ DWG nguồn và hai CAD D:data dùng tham chiếu. Tên thiết bị và chữ CAD được trình bày riêng với thông số xác minh từ nhà sản xuất. Bảng giá 2026 chỉ hiển thị ở các bảng hãng khi có PDF giá tương ứng.</p><a href="../index_2026.html">← Bảng giá các hãng</a> · <a href="../full_accessory_cad_library.html">Kiểm kê toàn bộ DWG</a> · <a href="cad_evidence_audit.json">Bằng chứng từng hình CAD</a> · <a href="../all_cad_view_evidence_audit.json">Đủ 1.049 hình CAD</a></header><div class="grid">{cards}</div></main></html>'''
(OUT/'index.html').write_text(index,encoding='utf8')
print(json.dumps({'views':len(views),'device_rows':len(products),'external_matches':sum(bool(p['external']) for p in products),
                  'by_category':{k:sum(p['category']==k for p in products) for k in CATEGORIES}},ensure_ascii=False))
