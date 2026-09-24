"""Whole-document circuit assessment before any device takeoff."""
from __future__ import annotations

import json
import tempfile
import unicodedata
from PIL import Image, ImageDraw
from pathlib import Path
from typing import Any

from app.services.ingestion.document_context import DocumentContextService
from app.services.ai.connection_pool import ConnectionPoolService
from app.services.ai.response_parser import ResponseParserService
from app.services.ai.vision_analyzer import VisionAnalyzerService


PREFLIGHT_INSTRUCTIONS = """Bạn là kỹ sư điện đang đọc TOÀN BỘ hồ sơ trước bước bóc tách.
Hãy xác định vai trò từng tệp, ranh giới sơ đồ nguyên lý, nguồn cấp, tải, mạch đo lường,
điều khiển, bảo vệ, liên hệ giữa các trang/tủ và các cụm có nhiều phần tử.
Đồng hồ chung chung có thể là ampe kế, vôn kế, đồng hồ đa năng hoặc công tơ; khởi động từ
có thể thuộc mạch sao-tam giác, đảo chiều hoặc đóng cắt đơn. Chỉ xác định chức năng khi
đường dây, tag, ký hiệu hay ghi chú hỗ trợ; nếu thiếu hãy nêu các khả năng và thông tin cần tra.
Tiếp địa, thanh nối đất, cầu đấu và phụ kiện lắp đặt có thể cần thiết dù không có tag BOM;
ghi ở installation_considerations với trạng thái đề xuất, không nhận là thiết bị đã thấy.
Không lập BOM, không đếm thiết bị, không chọn SKU, không tạo CAD ở bước này.
has_sld chỉ đúng khi trực tiếp nhận thấy sơ đồ một sợi hoặc mạch nguyên lý điện trong tệp;
nếu chỉ có bảng giá, thông số hay bản vẽ hình chiếu thì trả false.
Trả đúng một JSON: {"circuit_summary":"", "file_roles":[], "circuits":[],
"functional_groups":[], "ambiguous_symbols":[], "installation_considerations":[],
"questions":[], "source_limits":[], "has_sld": true}.
Mỗi kết luận phải có nguồn tệp/trang/tag khi thấy rõ. Viết tiếng Việt. Không suy đoán thành sự thật.
"""


class CircuitPreflightService:
    @staticmethod
    def _context(contexts: list[dict[str, Any]]) -> str:
        parts = []
        for row in contexts:
            filename = row.get('filename') or ''
            text = str(row.get('text') or '').strip()
            if text:
                parts.append(f"[{filename}]\n{text[:10000]}")
        return '\n\n'.join(parts)[:24000]

    @staticmethod
    def _visual_pages(files):
        """Collect every image and each scanned PDF page for whole-file review."""
        import pypdfium2 as pdfium
        pages = []
        for file in files:
            path = Path(str(file.file_path))
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            try:
                if ext in {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}:
                    with Image.open(path) as opened:
                        pages.append((file.filename, opened.convert('RGB').copy()))
                elif ext == '.pdf':
                    document = pdfium.PdfDocument(str(path))
                    try:
                        for index in range(len(document)):
                            page = document[index]
                            try:
                                pages.append((f'{file.filename} / trang {index + 1}',
                                              page.render(scale=0.5).to_pil().convert('RGB')))
                            finally:
                                page.close()
                    finally:
                        document.close()
            except Exception:
                # A readable text layer may still be available; do not claim the
                # unreadable image/page as visual evidence.
                continue
        return pages

    @staticmethod
    def _contact_sheet(pages):
        columns, width, height = 2, 640, 470
        sheet = Image.new('RGB', (columns * width, ((len(pages) + 1) // 2) * height), 'white')
        draw = ImageDraw.Draw(sheet)
        for index, (label, picture) in enumerate(pages):
            x, y = index % 2 * width, index // 2 * height
            picture.thumbnail((width - 20, height - 50), Image.Resampling.LANCZOS)
            sheet.paste(picture, (x + 10, y + 40))
            safe_label = ''.join(c for c in unicodedata.normalize('NFD', label.replace('Đ', 'D').replace('đ', 'd')) if not unicodedata.combining(c))
            draw.text((x + 10, y + 10), safe_label.encode('ascii', 'replace').decode()[:90], fill='black')
        return sheet

    @staticmethod
    async def assess(files, contexts, db, connections, user_prompt='') -> dict[str, Any]:
        context = CircuitPreflightService._context(contexts)
        pages = CircuitPreflightService._visual_pages(files)
        if not context and not pages:
            return {'status': 'unavailable', 'circuit_summary': '',
                    'source_limits': ['Chưa đọc được nội dung sơ đồ từ tệp nguồn.']}
        if not db or not connections:
            return {'status': 'unavailable', 'circuit_summary': '',
                    'source_limits': ['Chưa có kết nối AI để đánh giá sơ đồ.']}
        prompt = (PREFLIGHT_INSTRUCTIONS
                  + f"\nYêu cầu người dùng: {user_prompt or 'Đọc sơ đồ trước khi bóc tách.'}\n"
                  + f"\nNhãn và văn bản từ hồ sơ:\n{context}" if context else
                  PREFLIGHT_INSTRUCTIONS + f"\nYêu cầu người dùng: {user_prompt or 'Đọc sơ đồ trước khi bóc tách.'}\n")
        assessments = []
        source_limits = []
        if pages:
            for start in range(0, len(pages), 8):
                batch = pages[start:start + 8]
                sheet = CircuitPreflightService._contact_sheet(batch)
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp:
                    sheet.save(temp, format='JPEG', quality=88)
                    image_path = temp.name
                try:
                    response, _ = await ConnectionPoolService.call_with_fallback(
                        db=db, connections=connections,
                        call_fn=VisionAnalyzerService.analyze_image,
                        image_path=image_path,
                        prompt=prompt + '\nCác trang trong ảnh: ' + ', '.join(label for label, _ in batch) + '. '
                                      + 'Chỉ đánh giá các trang có nhãn trong ảnh này. '
                                        'Nêu trang và căn cứ cụ thể cho các kết luận.')
                    parsed = next((block for block in ResponseParserService.extract_json_blocks(response)
                                   if isinstance(block, dict) and block.get('circuit_summary')), None)
                    if parsed:
                        assessments.append(parsed)
                    else:
                        source_limits.append('Không nhận được đánh giá hợp lệ cho ' + ', '.join(label for label, _ in batch))
                finally:
                    Path(image_path).unlink(missing_ok=True)
        elif context:
            response, _ = await ConnectionPoolService.call_with_fallback(
                db=db, connections=connections, call_fn=VisionAnalyzerService.analyze_text,
                prompt=prompt)
            parsed = next((block for block in ResponseParserService.extract_json_blocks(response)
                           if isinstance(block, dict) and block.get('circuit_summary')), None)
            if parsed:
                assessments.append(parsed)
        if assessments and not any(part.get('has_sld') is True for part in assessments):
            source_limits.append('Chua xac nhan duoc so do mot soi trong ho so.')
        if not assessments or source_limits:
            return {'status': 'unavailable', 'circuit_summary': '',
                    'source_limits': source_limits or ['AI chưa trả được đánh giá sơ đồ có cấu trúc.']}
        keys = ('file_roles', 'circuits', 'functional_groups', 'ambiguous_symbols',
                'installation_considerations', 'questions', 'source_limits')
        result = {key: [entry for part in assessments for entry in
                        (part.get(key) if isinstance(part.get(key), list) else [])]
                  for key in keys}
        result['circuit_summary'] = '\n'.join(str(part['circuit_summary']) for part in assessments)
        result['has_sld'] = True
        result['status'] = 'assessed'
        result['source_type'] = 'visual' if pages else 'text'
        return result

    @staticmethod
    def extraction_context(assessment: dict[str, Any]) -> str:
        if assessment.get('status') != 'assessed':
            return ''
        bounded = {key: assessment.get(key) for key in ('circuit_summary','file_roles','circuits',
                    'functional_groups','ambiguous_symbols','installation_considerations','questions')}
        return ('ĐÁNH GIÁ SƠ ĐỒ TOÀN HỒ SƠ ĐÃ HOÀN THÀNH TRƯỚC BÓC TÁCH:\n'
                + json.dumps(bounded, ensure_ascii=False)[:12000]
                + '\nĐây là ngữ cảnh kiểm tra, không phải danh sách thiết bị đã quan sát. '
                  'Chỉ thêm vào BOM thiết bị có căn cứ trong sơ đồ hoặc ghi chú cụ thể; '
                  'các chi tiết lắp đặt suy luận để ở đề xuất kỹ thuật, không tự thêm như đã vẽ.')
