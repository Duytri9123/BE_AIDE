"""Conservative corrections backed by device-local evidence, before procurement."""
import re


def normalize_takeoff(devices):
    warnings, kept = [], []
    for d in devices:
        # A generated lamp alias that points to the same printed phase label is
        # a duplicate reference, not another load. Never collapse HL1/HL2 lamps.
        if d.category == 'LIGHT' and re.fullmatch(r'HL\d+', str(d.tag or ''), re.I):
            aliases = [x for x in devices if x is not d and x.category == 'LIGHT'
                       and re.fullmatch(r'[RSTYB]', str(x.tag or ''), re.I)
                       and (x.panel_code,x.source_filename,x.source_page)==(d.panel_code,d.source_filename,d.source_page)
                       and x.name == d.name and x.spec == d.spec
                       and re.search(r'\b'+re.escape(x.tag)+r'\b', str(d.downstream_device or ''), re.I)]
            if d.source_filename and len(aliases) == 1:
                warnings.append(f"{d.tag} → {aliases[0].tag}: loại tham chiếu đèn trùng; giữ ký hiệu nguồn và kiểm tra vị trí ảnh.")
                continue
        if d.category == 'LIGHT' and d.in_a and not re.search(r'\d+(?:[.,]\d+)?\s*(?:mA|A)\b', d.spec, re.I):
            d.in_a = None
            warnings.append(f"{d.tag or d.name}: đã bỏ dòng điện không có trong nhãn đèn; kiểm tra điện áp trước khi chọn mã.")
        duplicate = None
        for other in kept:
            if not d.source_filename or (d.tag and other.tag and d.tag != other.tag):
                continue
            if (d.category, d.panel_code, d.source_filename, d.source_page) != (other.category, other.panel_code, other.source_filename, other.source_page):
                continue
            a, b = d.box_2d, other.box_2d
            if not a or not b:
                continue
            intersection = max(0, min(a[2],b[2])-max(a[0],b[0])) * max(0,min(a[3],b[3])-max(a[1],b[1]))
            area = min((a[2]-a[0])*(a[3]-a[1]),(b[2]-b[0])*(b[3]-b[1]))
            # Require both spatial overlap and the same electrical rating.
            if area and intersection/area >= .8 and (d.spec, d.in_a, d.poles) == (other.spec, other.in_a, other.poles):
                duplicate = other
                break
        if duplicate:
            duplicate.quantity = max(d.quantity, duplicate.quantity)
            duplicate.drawing_quantity = max(d.drawing_quantity or 1, duplicate.drawing_quantity or 1)
            duplicate.procurement_quantity = duplicate.quantity
            warnings.append(f"{d.tag or d.name}: gộp nhận diện trùng vùng nguồn với {duplicate.tag or duplicate.name}; không cộng hai lần số lượng.")
        else:
            kept.append(d)
    return kept, warnings
