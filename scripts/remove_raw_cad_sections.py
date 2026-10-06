"""Remove the file-level DWG inventory that was appended to price tables."""
import re
from pathlib import Path

base = Path(__file__).resolve().parents[2] / 'Tudien/CATALOG_PHU_KIEN_DOC_LAP'
folders = ('LS_D02_DU_LIEU_MOI','MITSUBISHI_D04_DU_LIEU_MOI',
           'SCHNEIDER_D01_DU_LIEU_MOI','ABB_D03_DU_LIEU_MOI',
           'OSUNG_D05_DU_LIEU_MOI','SHIHLIN_D06_DU_LIEU_MOI')
for folder in folders:
    path = base / folder / 'index.html'
    page = path.read_text(encoding='utf8')
    page, count = re.subn(r'<!-- SOURCE_CAD_TABLE_START -->.*?<!-- SOURCE_CAD_TABLE_END -->', '', page, flags=re.S)
    page = re.sub(r'\s*·\s*<a href="#cad-nguon">CAD nguồn trong thư viện</a>', '', page)
    page = re.sub(r'<a href="\.\./full_accessory_cad_library\.html\?zone=[^"]+">Toàn bộ CAD vùng [^<]+</a>',
                  '<a href="../THIET_BI_KHAC_2026/index.html">Bảng thiết bị khác</a>', page)
    path.write_text(page, encoding='utf8')
    print(folder, count)
