"""Import reviewed public manufacturer facts; never manufacture prices or order codes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def reviewed_rows():
    rows = []
    def add(brand, model, sku, category, url, spec):
        spec = {'Dòng sản phẩm': model, **spec}
        rows.append({'id': f'external:reviewed:{brand}:{sku}', 'brand': brand,
            'sku': sku, 'name': model, 'item_name': model, 'category': category,
            'group': 'Catalog sản phẩm', 'price': None, 'source_url': url,
            'specifications': spec, 'checked_at': '2026-10-18',
            'columns': ['Tên hàng', 'Mã hàng', 'Thông số'],
            'cells': [model, sku, '; '.join(f'{k}: {v}' for k,v in spec.items())]})
    add('Phoenix Contact', 'UK 3 N', '3001501', 'TERMINAL_BLOCK',
        'https://www.phoenixcontact.com/en-pc/products/feed-through-terminal-block-uk-3-n-3001501',
        {'Tiêu chuẩn': 'IEC 60947-7-1', 'Dòng định mức': '24 A', 'Điện áp định mức': '800 V',
         'Tiết diện danh định': '2.5 mm²', 'Kết nối': 'Vít M3; 2 điểm nối, 1 tầng',
         'Chiều rộng': '5.2 mm', 'Chiều cao': '42.5 mm', 'Chiều sâu trên NS 35/7.5': '47 mm'})
    for suffix, voltage in [('230', '184–276 VAC'), ('400', '320–480 VAC')]:
        add('Mikro', 'MX100', 'MX100-'+suffix, 'PHASE_RELAY',
            'https://itmikro.com.my/wp-content/uploads/2020/08/mx100-1.pdf',
            {'Điện áp nguồn phụ': voltage, 'Chức năng': 'Giám sát mất pha và thứ tự pha',
             'Kích thước bao': '80 × 72.5 × 35 mm'})
    add('Schneider Electric', 'PM710', 'PM710', 'POWER_METER',
        'https://www.se.com/uk/en/faqs/FA132164/',
        {'Giao tiếp': 'RS485 Modbus', 'Ngõ ra xung': 'Không có', 'Tình trạng dòng sản phẩm': 'PM700 đã ngừng kinh doanh'})
    add('ABB', 'CAL5-11', '1SBN010020R1011', 'AUX_CONTACT',
        'https://library.e.abb.com/public/15e87a4a627c26d2c1256f0800219d52/1SBC009500R1002.pdf',
        {'Tiếp điểm': '1NO + 1NC', 'Lắp đặt': 'Khối tiếp điểm phụ lắp bên hông'})
    # Explicit ordering pairs in ABB's Type 1 ordering tables, not combinations.
    spd = [('25-255-7','8700','1'), ('25-440-50','9300','1'), ('25-255','0100','1'),
           ('3L 25-255','1300','3'), ('3L 25-255 TS','0600','3'),
           ('1N 25-255','1500','1+1'), ('1N 25-255 TS','1000','1+1'),
           ('2L 25-255','1200','2'), ('2L 25-255 TS','1100','2'),
           ('4L 25-255','1400','4'), ('4L 25-255 TS','0800','4'),
           ('3N 25-255','1600','3+1'), ('3N 25-255 TS','0700','3+1'),
           ('3N 25-255-7','8800','3+1')]
    for model, order, lines in spd:
        add('ABB', 'OVR T1 '+model, '2CTB815101R'+order, 'SPD',
            'https://new.abb.com/docs/librariesprovider74/lp-materials/main-catalog_surge-and-lightning-protection-solutions_en.pdf?sfvrsn=2',
            {'Loại chống sét': 'Type 1', 'Đường bảo vệ': lines, 'Dòng điện': 'AC',
             'Uc': '440 V' if '440' in model else '255 V', 'Iimp (10/350 µs)': '25 kA',
             'Ifi': '7 kA' if model.endswith('-7') else '50 kA',
             'Tiếp điểm phụ': '1NO + 1NC' if model.endswith(' TS') else 'Không có'})
    add('CHINT', 'XJ3-G', 'XJ3-G', 'PHASE_RELAY',
        'https://www.chintglobal.com/content/dam/chintsite/co/es/product-center/lv/iec/control-industrial/xj3/documentos/XJ3-Protection%20Relays-catalog.pdf',
        {'Điện áp hoạt động': '380 VAC ±10%', 'Tần số': '50/60 Hz',
         'Chức năng': 'Bảo vệ mất pha, thứ tự pha và mất cân bằng ba pha',
         'Tiếp điểm': '1NO + 1NC', 'Dòng nhiệt quy ước Ith': '5 A'})
    for family, slug, airflow, current in [
        ('FKL6621','enclosure-fan-and-filter','55/66','0.07/0.06'),
        ('FKL6622','cooling-ventilation-panel-fan-filter','72/75','0.12/0.10'),
        ('FKL6623','electric-fan-filter','105/120','0.12/0.10')]:
        add('Leipole', family, family+'.230', 'FAN',
            f'https://www.leipole.net/product/{family.lower()}-{slug}.html',
            {'Điện áp định mức': '230 VAC', 'Tần số': '50/60 Hz', 'Cấp bảo vệ': 'IP54',
             'Lưu lượng thổi tự do tại 50/60 Hz': airflow+' m³/h',
             'Dòng điện tại 50/60 Hz': current+' A'})
    for code, configuration in [('1AG40','DC/DC/DC'),('1BG40','AC/DC/Relay'),('1HG40','DC/DC/Relay')]:
        add('Siemens', 'S7-1200 CPU 1214C', '6ES7214-'+code+'-0XB0', 'PLC',
            'https://docs.tia.siemens.cloud/r/simatic_s7_1200_manual_collection_enus_20/ordering-information/cpu-modules',
            {'Cấu hình CPU': configuration, 'Ngõ vào số': '14 DI', 'Ngõ ra số': '10 DO', 'Ngõ vào tương tự': '2 AI'})
    add('EMIC', 'ME-41', 'ME-41', 'ENERGY_METER',
        'https://emic.com.vn/vn/cong-to-dien-tu-3-pha-da-chuc-nang-me-41_p9710.html',
        {'Điện áp danh định': '3 × 57.5/100 V đến 3 × 240/415 V', 'Dòng danh định': '3 × 5(10) A',
         'Tần số': '50 Hz', 'Cấp chính xác hữu công': '0.5S', 'Cấp chính xác vô công': '2',
         'Đấu nối': 'Gián tiếp; lưới 3 pha 3 dây hoặc 3 pha 4 dây', 'Cấp bảo vệ vỏ': 'IP51'})
    return rows

def main():
    path = ROOT/'app/data/external_product_information.json'
    data = json.loads(path.read_text(encoding='utf8'))
    additions = reviewed_rows()
    ids = {r['id'] for r in additions}
    data['items'] = [r for r in data['items'] if r.get('id') not in ids] + additions
    data['checked_at'] = '2026-10-18'
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(f'Imported {len(additions)} reviewed manufacturer records')

if __name__ == '__main__': main()
