"""Read critical labels from close-ups; preserve disagreement as uncertainty."""
import asyncio
import json
import logging
import re
from pathlib import Path
from collections import Counter
from PIL import Image
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.vision_analyzer import VisionAnalyzerService
from app.services.ingestion.cad_source_evidence import validate_region

logger = logging.getLogger(__name__)

DIMENSION_POLICY = ('Không dùng kích thước, khoảng cách, tỷ lệ hình học, chiều dày vỏ tủ để kết luận chính xác; '
                    'chúng chỉ tương đối. Tọa độ chỉ để định vị/crop. Chỉ kiểm chứng thông số điện ghi thành nhãn.')


def json_object(text):
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\{', text or ''):
        try:
            obj, _ = decoder.raw_decode(text[match.start():])
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
    return None


def normalized_label(value):
    return re.sub(r'\s+', '', str(value).translate(str.maketrans({'–': '-', '—': '-', '−': '-'}))).upper()


def replace_label(information, old, new):
    pattern = r'\s*'.join(re.escape(c) if c != '-' else r'[-–—−]' for c in normalized_label(old))
    return re.sub(pattern, lambda _: new, information, flags=re.I)


async def read_image_checked(db, connections, image_path, label, message, instruction, native='', check_numbers=True):
    prompt = instruction + '\n' + DIMENSION_POLICY + """
Trả đúng JSON {"information":"nội dung đọc nguồn bằng tiếng Việt", "critical_labels":[
 {"text":"nhãn số nguyên văn", "box":[trái,trên,phải,dưới], "kind":"voltage_range/ratio/uncertain_rating"}]}.
box chuẩn hóa 0..1 trên đúng ảnh này, khoanh sát nhãn nhưng giữ đủ ký tự.
Bắt buộc liệt kê dải đo V và tỷ số CT nếu có. Chỉ thêm định mức khác khi chữ số khó phân biệt.
Không liệt kê kích thước cơ khí. Không đoán nhãn, không dùng mã mẫu.
""" + json.dumps({'request': message, 'source': label, 'native_labels': native}, ensure_ascii=False)
    raw, _ = await ConnectionPoolService.call_with_fallback(
        db, connections, VisionAnalyzerService.analyze_image, image_path=str(image_path), prompt=prompt)
    obj = json_object(raw) or {'information': raw, 'critical_labels': []}
    information = str(obj.get('information') or '')
    checks = []
    if not check_numbers:
        return {'information': information, 'numeric_checks': []}
    labels = sorted([r for r in (obj.get('critical_labels') or []) if isinstance(r, dict)],
                    key=lambda r: 0 if r.get('kind') == 'voltage_range' else 1)[:4]
    deadline = asyncio.get_running_loop().time() + 60
    for index, item in enumerate(labels):
        observed = str(item.get('text') or '')
        try:
            box = validate_region(item.get('box'))
        except ValueError:
            box = None
        if not observed or box is None:
            continue
        with Image.open(image_path) as img:
            width, height = img.size
            x1 = max(0, box[0] - .012); y1 = max(0, box[1] - .012)
            x2 = min(1, box[2] + .012); y2 = min(1, box[3] + .012)
            patch = img.crop((int(x1 * width), int(y1 * height),
                              max(int(x2 * width), int(x1 * width) + 1),
                              max(int(y2 * height), int(y1 * height) + 1)))
            if max(patch.size) < 1000:
                scale = min(4, 1000 / max(patch.size))
                patch = patch.resize((max(1, int(patch.width * scale)), max(1, int(patch.height * scale))))
            target = Path(image_path).with_name(Path(image_path).stem + f'-label-{index}.png')
            patch.save(target)
        votes = [normalized_label(observed)]; readings = [observed]
        for attempt in (1, 2):
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                break
            try:
                response, _ = await asyncio.wait_for(ConnectionPoolService.call_with_fallback(
                    db, connections, VisionAnalyzerService.analyze_image, image_path=str(target),
                    prompt='Chép nguyên văn nhãn điện trong ảnh cận cảnh. Không suy theo danh mục. Đọc kỹ hình dạng từng chữ số và đơn vị. '
                           'Nếu không rõ hoặc thiếu nhãn, legible=false, không đoán. '
                           'Trả JSON {"text":"nhãn nguyên văn","legible":true/false}. '
                           + json.dumps({'source': label, 'independent_read': attempt}, ensure_ascii=False)),
                    timeout=min(25, remaining))
            except Exception as exc:
                logger.warning('Optional label verification failed for %s: %s', label, type(exc).__name__)
                continue
            reading = json_object(response) or {}
            value = str(reading.get('text') or '') if reading.get('legible') is True else ''
            readings.append(value)
            if value:
                votes.append(normalized_label(value))
            winner, count = Counter(votes).most_common(1)[0]
            if count >= 2:
                break
        winner, count = Counter(votes).most_common(1)[0]
        confirmed = next((v for v in readings if normalized_label(v) == winner), '') if count >= 2 else ''
        information = replace_label(information, observed, confirmed or f'{observed} (đọc sơ bộ, cần đối chiếu)')
        checks.append({'initial': observed, 'readings': readings, 'confirmed_text': confirmed,
                       'status': 'confirmed' if confirmed else 'uncertain', 'box': box, 'kind': item.get('kind')})
    return {'information': information, 'numeric_checks': checks}


def numeric_conflicts(devices, checks):
    ranges = {normalized_label(c['confirmed_text']) for c in checks if c.get('status') == 'confirmed'
              and re.fullmatch(r'\d+(?:\.\d+)?-\d+(?:\.\d+)?V', normalized_label(c.get('confirmed_text', '')))}
    if len(ranges) != 1:
        return []
    expected = next(iter(ranges)); issues = []
    for device in devices:
        for value in re.findall(r'\d+\s*[-–]\s*\d+\s*V', str(device.get('spec', '')), re.I):
            if normalized_label(value) != expected:
                issues.append(f"{device.get('tag') or device.get('name')}: nhãn nguồn đọc cận cảnh là {expected}, không phải {value}.")
    return issues
