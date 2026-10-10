"""Evidence-based identity. A library filename is never manufacturer evidence."""
import json,re
from functools import lru_cache
from pathlib import Path
from app.services.cad.library_taxonomy import normalize,explicit_brands
DATA=Path(__file__).resolve().parents[3]/'data/CatalogTB/_agent_index/cad_text_inventory.json'

@lru_cache(maxsize=2)
def _read(stamp):
    return {r['id']:r for r in json.loads(DATA.read_text(encoding='utf8'))}

def evidence(item):
    row=_read(DATA.stat().st_mtime_ns).get(item['id'],{}) if DATA.exists() else {}
    texts=row.get('texts',[])
    text=' '.join(texts); key=normalize(item.get('source_block') or item['name'])
    known=explicit_brands(text)
    named=explicit_brands(item.get('source_block') or item['name'])
    brand=known[0] if len(known)==1 else named[0] if not known and len(named)==1 else 'Chưa xác định hãng'
    basis='Chữ trong hình CAD: '+brand if len(known)==1 else 'Tên block ghi: '+brand if not known and len(named)==1 else 'Chưa đủ bằng chứng; không lấy hãng từ tên file thư viện'
    result={'brand':brand,'brand_basis':basis,'texts':texts,'description':item['name'], 'face':None,
            'ai_auto_select':False,'ai_note':'Chỉ dùng tham khảo; AI chưa được tự chọn khi chưa xác nhận model, mặt nhìn và tỷ lệ.',
            'dimensions_from_text':None}
    dims=re.search(r'w\s*(\d+(?:\.\d+)?)\s*[x;]?\s*h\s*(\d+(?:\.\d+)?)\s*[x;]?\s*d\s*(\d+(?:\.\d+)?)',text,re.I)
    if dims: result['dimensions_from_text']=dict(zip(('w','h','d'),map(float,dims.groups())))
    # Keep only text and dimensions read from the source. Catalog curation supplies
    # manufacturer, family and model metadata when it becomes available.
    return result
