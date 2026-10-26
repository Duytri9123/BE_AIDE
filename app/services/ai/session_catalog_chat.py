"""Catalog follow-ups reuse a saved inventory and never reopen source extraction."""
import copy
import re
import unicodedata
from app.schemas.ai import ExtractedDeviceSchema
from app.services.library_review_scope import MAIN_DEVICE_TYPES

def catalog_request_brand(message):
    text=''.join(c for c in unicodedata.normalize('NFD',message.lower().replace('đ','d')) if not unicodedata.combining(c))
    if not re.search(r'\b(tim|tra cuu|doi chieu|goi y)\b',text): return None
    if re.search(r'\b(them|xoa|thay)\b|\bdoi\s+hang\b',text): return None
    for pattern,brand in ((r'\bls(?: electric)?\b','LS Electric'),(r'\bschneider(?: electric)?\b','Schneider'),(r'\bchint\b','CHINT'),(r'\bmitsubishi\b','Mitsubishi Electric'),(r'\babb\b','ABB')):
        if re.search(pattern,text): return brand
    return None

async def lookup_session_catalog(devices, brand, connections, db):
    from app.services.ai.device_recommendations import recommendations
    from app.services.device_catalog_engine import DeviceCatalogEngine
    from app.services.ai.web_device_recommendations import research_device_products
    from app.services.ai.manufacturer_registry import canonical_brand
    result=copy.deepcopy(devices)
    targets=[]
    for index,row in enumerate(result):
        if str(row.get('category') or '').upper() not in MAIN_DEVICE_TYPES: continue
        device=ExtractedDeviceSchema.model_validate(row)
        # A search preference is not a selected product or detected source brand.
        device.brand=''
        device.detected_brand=''
        device.catalog_matches={}
        device.pricebook_match=None
        choices=recommendations(DeviceCatalogEngine.get_instance(),device,brand)
        device.catalog_candidates={k:v for k,v in choices.items() if canonical_brand(k)==canonical_brand(brand)}
        targets.append((index,device))
    if targets:
        await research_device_products([d for _,d in targets],connections,db,preferred_brand=brand)
    count=0
    for index,device in targets:
        candidates={k:v for k,v in (device.catalog_candidates or {}).items() if canonical_brand(k)==canonical_brand(brand)}
        result[index]['catalog_candidates']=candidates
        result[index]['web_research']=device.web_research
        result[index]['suggested_brands']=[brand] if candidates else []
        count += bool(candidates)
    return result, f'Đã đối chiếu catalog {brand} cho {len(targets)} dòng thiết bị chính; {count} dòng có phương án tham khảo. Giữ nguyên số lượng, thông số, ảnh nguồn và hãng đã nhận diện; chưa tự chốt mã hoặc giá. Vật tư phụ không bị gán hãng theo yêu cầu này.'
